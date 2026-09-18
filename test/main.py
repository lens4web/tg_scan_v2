import os
import json
import asyncio
import re
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
import db

# --- CONFIG ---
API_ID = 29553756
API_HASH = "752adfaf32eb7dedcadbded199107af2"
BOT_TOKEN = "8722872314:AAEUZEzn8ItOYZxdxRkIzVwbP2bDZ86oxfs"
WEBAPP_URL = "https://tg.lens4web.com"

WORK_DIR = "/home/adminamin2/tg_scanner_app"

GLOBAL_STOP_WORDS = []

# --- CLIENTS ---
userbot = Client("userbot_session", workers=50, api_id=API_ID, api_hash=API_HASH, workdir=WORK_DIR)
bot = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, workdir=WORK_DIR)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

routing_table = {}
last_processed = {}  # {chat_id: last_message_id}
dead_chats = set()   # Chats that returned 406 CHANNEL_PRIVATE

# --- BUILD ROUTING ---
def build_routing_table():
    global routing_table, dead_chats
    routing_table.clear()
    dead_chats.clear() # Reset dead chats on routing update

    subs = db.get_all_subs()

    print("\n--- 🔍 ROUTING TABLE UPDATED ---")
    for tg_id, kw_json, chats_json in subs:
        keywords = json.loads(kw_json)
        chats = json.loads(chats_json)

        for c in chats:
            cid = c.get("chat_id")
            if cid:
                routing_table.setdefault(cid, []).append({
                    "tg_id": tg_id,
                    "keywords": keywords
                })

    print(f"Monitoring {len(routing_table)} chats.\n")

# --- PAYLOAD ---
class SubPayload(BaseModel):
    tg_id: int
    title: str
    keywords: str
    chats: str

# --- CORE MESSAGE PROCESSOR ---
async def process_message(message):
    chat_id = message.chat.id

    if chat_id not in routing_table:
        return

    # Anti-duplicate check
    if chat_id in last_processed and message.id <= last_processed[chat_id]:
        return

    # Update processed ID immediately to prevent race conditions
    last_processed[chat_id] = message.id

    text = message.text or message.caption
    if not text:
        return

    text_lower = text.lower()

    if any(stop in text_lower for stop in GLOBAL_STOP_WORDS):
        return

    clean_text = " ".join(re.findall(r'\w+', text_lower))

    alerted_users = set()

    for rule in routing_table[chat_id]:
        user_id = rule["tg_id"]
        if user_id in alerted_users:
            continue

        found_match = None

        for pattern in rule["keywords"]:
            if isinstance(pattern, list):
                if all(word in clean_text for word in pattern):
                    found_match = " + ".join(pattern)
                    break
            else:
                if pattern in clean_text:
                    found_match = pattern
                    break

        if found_match:
            alerted_users.add(user_id)

            link = f"https://t.me/c/{str(chat_id).replace('-100', '')}/{message.id}"
            if message.chat.username:
                link = f"https://t.me/{message.chat.username}/{message.id}"

            try:
                await bot.send_message(
                    user_id,
                    f"🎯 Found: {found_match}\n"
                    f"💬 Chat: {message.chat.title}\n\n"
                    f"{text[:400]}...\n\n"
                    f"🔗 {link}",
                    disable_web_page_preview=True
                )
                print(f"✅ Sent to {user_id}")
            except Exception as e:
                print(f"❌ Send error: {e}")

# --- EVENT HANDLER ---
@userbot.on_message(filters.group | filters.channel)
async def handler(client, message):
    asyncio.create_task(process_message(message))

# --- POLLING FALLBACK ---
async def poll_messages():
    await asyncio.sleep(5)

    while True:
        for chat_id in list(routing_table.keys()):
            if chat_id in dead_chats:
                continue

            try:
                # Fetch up to 20 latest messages
                new_messages = []
                async for msg in userbot.get_chat_history(chat_id, limit=20):
                    if chat_id in last_processed and msg.id <= last_processed[chat_id]:
                        break # Stop fetching if we hit a known message
                    new_messages.append(msg)

                # Process from oldest to newest to maintain chronological order
                for msg in reversed(new_messages):
                    await process_message(msg)

            except Exception as e:
                error_str = str(e).upper()
                if "CHANNEL_PRIVATE" in error_str or "CHAT_WRITE_FORBIDDEN" in error_str:
                    print(f"🚫 Access lost to {chat_id}. Chat marked as dead. Please check your access.")
                    dead_chats.add(chat_id)
                else:
                    print(f"Polling error {chat_id}: {e}")

            await asyncio.sleep(1) # Prevent flooding Telegram API

        await asyncio.sleep(15) # Main polling interval

# --- STARTUP ---
@app.on_event("startup")
async def startup():
    db.init_db()
    build_routing_table()

    await userbot.start()
    await bot.start()

    me = await userbot.get_me()
    print(f"🔥 Userbot: {me.first_name}")

    print("🔄 Initializing chat history pointers...")

    for chat_id in routing_table:
        try:
            # Get the very last message just to set the initial pointer
            async for m in userbot.get_chat_history(chat_id, limit=1):
                last_processed[chat_id] = m.id
                print(f"✅ Active: {chat_id} (Pointer set to {m.id})")
                break
        except Exception as e:
            error_str = str(e).upper()
            if "CHANNEL_PRIVATE" in error_str:
                print(f"🚫 Init: Access denied for {chat_id}. Marked as dead.")
                dead_chats.add(chat_id)
            else:
                print(f"❌ Access error {chat_id}: {e}")

    asyncio.create_task(poll_messages())

    print("🚀 System started")

# --- SHUTDOWN ---
@app.on_event("shutdown")
async def shutdown():
    await userbot.stop()
    await bot.stop()

# --- API ---
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/subs")
async def get_subs(tg_id: int):
    return db.get_user_subs(tg_id)

@app.delete("/api/subs/{sub_id}")
async def delete_sub(sub_id: int, tg_id: int):
    db.delete_sub(sub_id, tg_id)
    build_routing_table()
    return {"status": "ok"}

@app.post("/api/subs")
async def save_sub(payload: SubPayload):
    keywords = [k.strip().lower() for k in payload.keywords.split(",") if k.strip()]
    chat_links = [c.strip() for c in payload.chats.split("\n") if c.strip()]

    saved_chats = []
    errors = []

    for link in chat_links:
        target = link.replace("https://t.me/", "").replace("@", "").strip()

        try:
            chat = await userbot.join_chat(target)
            saved_chats.append({"link": link, "chat_id": chat.id})
            await asyncio.sleep(1)
        except Exception as e:
            if "USER_ALREADY_PARTICIPANT" in str(e).upper():
                try:
                    chat = await userbot.get_chat(target)
                    saved_chats.append({"link": link, "chat_id": chat.id})
                except Exception as inner_e:
                    errors.append(link)
            else:
                errors.append(link)

    db.add_sub(payload.tg_id, payload.title, keywords, saved_chats)
    build_routing_table()

    return {"status": "ok", "errors": errors}

# --- BOT ---
@bot.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("⚙️ Panel", web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True
    )

    await message.reply(
        "Welcome!\nOpen the panel to create subscriptions.",
        reply_markup=keyboard
    )