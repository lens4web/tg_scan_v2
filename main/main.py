import os
import asyncio
import re
import json
import sys
from pyrogram import Client, raw

# --- Базовые настройки ---
BASE_DIR = "/home/adminamin2/tg_monitor"
os.chdir(BASE_DIR)
POLL_INTERVAL = 22 
JSON_PATH = "words.json"

# --- Глобальные переменные ---
FOLDERS_CONFIG = []
last_checked_ids = {}
last_notified_content = ""

# --- Чтение системных данных для запуска ---
if not os.path.exists(JSON_PATH):
    print(f"Файл {JSON_PATH} не найден. Скрипт остановлен.")
    sys.exit(1)

with open(JSON_PATH, "r", encoding="utf-8") as f:
    boot_data = json.load(f)
    
SESSION_NAME = boot_data.get("system", {}).get("session_name", "my_account")
API_ID = boot_data.get("system", {}).get("api_id")
API_HASH = boot_data.get("system", {}).get("api_hash")

if not API_ID or not API_HASH:
    print("Ошибка: В words.json отсутствуют api_id или api_hash.")
    sys.exit(1)

app = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH, workdir=BASE_DIR)

def load_config():
    global FOLDERS_CONFIG
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
            
        global_stops = [w.lower().strip() for w in data.get("global_stop_words", [])]
        new_config = []
        

        global_notify_id = data.get("system", {}).get("notify_id")

        for folder_data in data.get("folders", []):
            folder_name = folder_data.get("folder_name")

            if not folder_name or not global_notify_id:
                continue

            notify_id = global_notify_id
            
            if not folder_name or not notify_id:
                continue

            processed_k = []
            for k in folder_data.get("keywords", []):
                if isinstance(k, list):
                    processed_k.append([str(w).lower().strip() for w in k])
                else:
                    processed_k.append(str(k).lower().strip())
                    
            local_stops = [str(w).lower().strip() for w in folder_data.get("stop_words", [])]
            combined_stops = list(set(global_stops + local_stops))
            
            existing_chats = []
            for existing_folder in FOLDERS_CONFIG:
                if existing_folder["name"] == folder_name:
                    existing_chats = existing_folder.get("chats", [])
                    break
            
            new_config.append({
                "name": folder_name,
                "notify_id": notify_id,
                "processed_keywords": processed_k,
                "processed_stop_words": combined_stops,
                "chats": existing_chats
            })
            
        FOLDERS_CONFIG = new_config
    except Exception as e:
        pass # Игнорируем временные конфликты при сохранении файла через сайт

async def init_folders_and_cache():
    print("🔄 Синхронизация папок и чатов...")
    try:
        async for dialog in app.get_dialogs(limit=50): pass
        all_filters = await app.invoke(raw.functions.messages.GetDialogFilters())
        
        for folder_cfg in FOLDERS_CONFIG:
            folder_cfg["chats"] = []
            for f in all_filters:
                if hasattr(f, "title") and f.title == folder_cfg["name"]:
                    for peer in f.include_peers:
                        c_id = 0
                        if isinstance(peer, raw.types.InputPeerChat): c_id = -peer.chat_id
                        elif isinstance(peer, raw.types.InputPeerChannel): c_id = int("-100" + str(peer.channel_id))
                        elif isinstance(peer, raw.types.InputPeerUser): c_id = peer.user_id
                        
                        if c_id:
                            if c_id not in last_checked_ids:
                                last_checked_ids[c_id] = 0
                            folder_cfg["chats"].append(c_id)
            print(f"✅ Папка '{folder_cfg['name']}': найдено {len(folder_cfg['chats'])} чатов")
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")

async def monitor():
    global last_notified_content
    load_config()
    
    async with app:
        await init_folders_and_cache()
        
        for folder in FOLDERS_CONFIG:
            try:
                await app.send_message(
                    folder["notify_id"], 
                    f"🚀 **Scanner started!**\n📂 Folder: `{folder['name']}`\n👥 Chats: `{len(folder['chats'])}`"
                )
            except: pass

        while True:
            try:
                load_config()
                
                # --- ГОРЯЧЕЕ ОБНОВЛЕНИЕ ПАПОК ---
                needs_sync = any(len(f.get("chats", [])) == 0 for f in FOLDERS_CONFIG)
                if needs_sync:
                    await init_folders_and_cache()
                
                for folder in FOLDERS_CONFIG:
                    if not folder.get("processed_keywords") or not folder.get("chats"):
                        continue
                        
                    for chat_id in folder["chats"]:
                        last_id = last_checked_ids.get(chat_id, 0)
                        try:
                            new_messages = []
                            async for message in app.get_chat_history(chat_id, limit=20):
                                if last_id != 0 and message.id <= last_id:
                                    break
                                new_messages.append(message)
                            
                            for message in reversed(new_messages):
                                if message.id > last_checked_ids.get(chat_id, 0):
                                    last_checked_ids[chat_id] = message.id
                                
                                if message.from_user and message.from_user.is_self: continue

                                content = message.text or message.caption
                                if not content: continue

                                current_content_strip = content.strip()
                                if current_content_strip == last_notified_content: continue

                                text_lower = current_content_strip.lower()
                                
                                if any(sw in text_lower for sw in folder["processed_stop_words"]):
                                    continue

                                clean_text = " ".join(re.findall(r'\w+', text_lower))

                                found_match = None
                                for pattern in folder["processed_keywords"]:
                                    if isinstance(pattern, list):
                                        if all(word in clean_text for word in pattern):
                                            found_match = " + ".join(pattern)
                                            break
                                    else:
                                        if pattern in clean_text:
                                            found_match = pattern
                                            break

                                if found_match:
                                    last_notified_content = current_content_strip
                                    
                                    if message.from_user:
                                        user = message.from_user
                                        user_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                                        author_info = f"👤 {user_name} (@{user.username})" if user.username else f"👤 {user_name}"
                                    else:
                                        author_info = "📢 Channel/Admin"

                                    link = f"https://t.me/c/{str(chat_id).replace('-100', '')}/{message.id}"
                                    if message.chat and message.chat.username:
                                        link = f"https://t.me/{message.chat.username}/{message.id}"
                                    
                                    await app.send_message(
                                        folder["notify_id"], 
                                        f"🔔 **Found in {folder['name']}: {found_match}**\n"
                                        f"💬 Chat: {message.chat.title}\n"
                                        f"{author_info}\n\n"
                                        f"{content[:500]}\n\n"
                                        f"🔗 {link}"
                                    )
                                    await asyncio.sleep(0.5)
                            
                            await asyncio.sleep(0.1) 
                        except: continue
                
                await asyncio.sleep(POLL_INTERVAL)
            except Exception as e:
                print(f"Global loop error: {e}")
                await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(monitor())