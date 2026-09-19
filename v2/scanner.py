import asyncio
import os
import re
from pyrogram import Client, raw, filters
from pyrogram.handlers import MessageHandler
import database

# Dictionary to hold running pyrogram clients. Key: user_id (from DB)
running_clients = {}

# In-memory config for quick filtering. Structure:
# {
#   user_id: {
#      "notify_id": 1234,
#      "global_stop_words": ["word1", "word2"],
#      "folders": {
#         "folder_name1": {
#             "chats": [-100123, -100456, ...],
#             "keywords": [["word1"], ["word2", "word3"]],
#             "stop_words": ["stop1"]
#         }
#      }
#   }
# }
user_configs = {}

# Last notified content per user to avoid duplicates
last_notified = {}

async def load_user_config(user_id: int):
    """Loads a specific user's config from the DB into memory."""
    user = await database.get_user_by_id(user_id)
    if not user:
        return None
        
    global_stops = await database.get_global_stop_words_by_user(user_id)
    global_stops = [w.lower().strip() for w in global_stops]
    
    folders_db = await database.get_folders_by_user(user_id)
    folders_dict = {}
    
    for f in folders_db:
        folder_id = f['id']
        folder_name = f['name']
        
        keywords_db = await database.get_keywords_by_folder(folder_id)
        # Parse compound keywords (e.g., "word1 + word2")
        processed_k = []
        for k in keywords_db:
            if "+" in k:
                processed_k.append([p.strip().lower() for p in k.split("+")])
            else:
                processed_k.append([k.strip().lower()])
                
        stop_words_db = await database.get_stop_words_by_folder(folder_id)
        local_stops = [w.lower().strip() for w in stop_words_db]
        
        folders_dict[folder_name] = {
            "chats": set(), # Will be populated by Pyrogram
            "keywords": processed_k,
            "stop_words": local_stops
        }
        
    user_configs[user_id] = {
        "notify_id": user["notify_id"],
        "global_stop_words": global_stops,
        "folders": folders_dict
    }
    return user_configs[user_id]

async def sync_folder_chats(user_id: int, app: Client):
    """Uses Pyrogram to fetch dialog filters (folders) and map them to chat IDs."""
    if user_id not in user_configs:
        return
        
    print(f"[{user_id}] Syncing folders from Telegram...")
    try:
        # Fetch some dialogs to cache peers
        async for _ in app.get_dialogs(limit=50): pass
        
        all_filters = await app.invoke(raw.functions.messages.GetDialogFilters())
        
        cfg = user_configs[user_id]["folders"]
        
        for f in all_filters:
            if hasattr(f, "title"):
                folder_name = f.title
                if folder_name in cfg:
                    cfg[folder_name]["chats"] = set()
                    for peer in f.include_peers:
                        c_id = 0
                        if isinstance(peer, raw.types.InputPeerChat): c_id = -peer.chat_id
                        elif isinstance(peer, raw.types.InputPeerChannel): c_id = int("-100" + str(peer.channel_id))
                        elif isinstance(peer, raw.types.InputPeerUser): c_id = peer.user_id
                        
                        if c_id:
                            cfg[folder_name]["chats"].add(c_id)
                    print(f"[{user_id}] Folder '{folder_name}' synced: {len(cfg[folder_name]['chats'])} chats.")
    except Exception as e:
        print(f"[{user_id}] Error syncing folders: {e}")

async def handle_message(client: Client, message, user_id: int):
    """The main event handler for incoming messages."""
    if user_id not in user_configs:
        return
        
    if message.from_user and message.from_user.is_self:
        return
        
    content = message.text or message.caption
    if not content:
        return
        
    chat_id = message.chat.id
    cfg = user_configs[user_id]
    
    current_content_strip = content.strip()
    if user_id not in last_notified:
        last_notified[user_id] = ""
        
    if current_content_strip == last_notified[user_id]:
        return # duplicate
        
    text_lower = current_content_strip.lower()
    clean_text = " ".join(re.findall(r'\w+', text_lower))
    
    # Global stop words check
    if any(sw in text_lower for sw in cfg["global_stop_words"]):
        return
        
    # Check which folder this chat belongs to
    matched_folder_name = None
    folder_data = None
    
    for f_name, f_data in cfg["folders"].items():
        if chat_id in f_data["chats"]:
            matched_folder_name = f_name
            folder_data = f_data
            break
            
    if not matched_folder_name:
        return # Not in any monitored folder
        
    print(f"[{user_id}] Message received in monitored folder '{matched_folder_name}' (chat {chat_id})")
    
    # Local stop words check
    if any(sw in text_lower for sw in folder_data["stop_words"]):
        return
        
    # Keywords check
    found_match = None
    for pattern_list in folder_data["keywords"]:
        if all(word in clean_text for word in pattern_list):
            found_match = " + ".join(pattern_list)
            break
            
    if found_match:
        print(f"[{user_id}] MATCH FOUND: {found_match}")
        last_notified[user_id] = current_content_strip
        
        if message.from_user:
            user = message.from_user
            user_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            author_info = f"👤 {user_name} (@{user.username})" if user.username else f"👤 {user_name}"
        else:
            author_info = "📢 Channel/Admin"
            
        link = f"https://t.me/c/{str(chat_id).replace('-100', '')}/{message.id}"
        if message.chat and message.chat.username:
            link = f"https://t.me/{message.chat.username}/{message.id}"
            
        text_to_send = (
            f"🔔 **Found in {matched_folder_name}: {found_match}**\n"
            f"💬 Chat: {message.chat.title}\n"
            f"{author_info}\n\n"
            f"{content[:500]}\n\n"
            f"🔗 {link}"
        )
        
        try:
            await client.send_message(cfg["notify_id"], text_to_send)
        except Exception as e:
            print(f"[{user_id}] Failed to send notification: {e}")


def get_message_handler(user_id: int):
    async def wrapper(client, message):
        await handle_message(client, message, user_id)
    return wrapper


async def start_client(user: dict):
    user_id = user["id"]
    if user_id in running_clients:
        print(f"[{user_id}] Client already running.")
        return

    print(f"[{user_id}] Starting Pyrogram client...")
    
    session_str = user["session_name"]
    # We will store session files in a 'sessions' directory
    os.makedirs("sessions", exist_ok=True)
    workdir = os.path.join(os.getcwd(), "sessions")
    
    app = Client(
        session_str,
        api_id=user["api_id"],
        api_hash=user["api_hash"],
        workdir=workdir
    )
    
    try:
        await app.start()
    except Exception as e:
        print(f"[{user_id}] Failed to start client: {e}")
        return False
        
    await load_user_config(user_id)
    await sync_folder_chats(user_id, app)
    
    # Register handler
    handler = MessageHandler(get_message_handler(user_id), filters.all)
    app.add_handler(handler)
    
    running_clients[user_id] = app
    
    cfg = user_configs.get(user_id)
    if cfg:
        total_folders = len(cfg["folders"])
        total_chats = sum(len(f["chats"]) for f in cfg["folders"].values())
        total_kws = sum(len(f["keywords"]) for f in cfg["folders"].values())
        
        report_text = (
            f"🚀 **Сканер запущен!**\n"
            f"📱 Аккаунт: {user['phone']}\n"
            f"📁 Активных папок: {total_folders}\n"
            f"💬 Отслеживаемых чатов: {total_chats}\n"
            f"🔑 Ключевых слов (сумма): {total_kws}\n\n"
            f"Система мониторинга включена."
        )
        try:
            await app.send_message(user["notify_id"], report_text)
        except Exception as e:
            print(f"[{user_id}] Failed to send startup report: {e}")

    print(f"[{user_id}] Client started and monitoring.")
    return True

async def stop_client(user_id: int):
    if user_id in running_clients:
        print(f"[{user_id}] Stopping client...")
        try:
            await running_clients[user_id].stop()
        except:
            pass
        del running_clients[user_id]
        
async def reload_user(user_id: int):
    """Reloads config and resyncs folders for a user."""
    if user_id in running_clients:
        await load_user_config(user_id)
        await sync_folder_chats(user_id, running_clients[user_id])

async def start_all_active_clients():
    users = await database.get_all_users()
    for u in users:
        if u["is_active"]:
            await start_client(dict(u))
