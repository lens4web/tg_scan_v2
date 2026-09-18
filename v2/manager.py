import os
import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram import Client

import database
import scanner

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

from aiogram import BaseMiddleware

# --- Auth Middleware ---
class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = None
        if isinstance(event, types.Message):
            user_id = event.from_user.id
        elif isinstance(event, types.CallbackQuery):
            user_id = event.from_user.id
            
        if user_id != ADMIN_ID:
            return
            
        return await handler(event, data)

dp.message.middleware(AuthMiddleware())
dp.callback_query.middleware(AuthMiddleware())

# --- FSM States ---
class AddUserState(StatesGroup):
    wait_api_id = State()
    wait_api_hash = State()
    wait_phone = State()
    wait_code = State()

class AddFolderState(StatesGroup):
    wait_user_id = State()
    wait_folder_name = State()

class AddKeywordState(StatesGroup):
    wait_folder_id = State()
    wait_keyword = State()

class DelKeywordState(StatesGroup):
    wait_folder_id = State()
    wait_keyword = State()

class AddStopWordState(StatesGroup):
    wait_folder_id = State()
    wait_stop_word = State()

class DelStopWordState(StatesGroup):
    wait_folder_id = State()
    wait_stop_word = State()

# Temp storage for pyrogram auth
auth_temp = {}

# --- Keyboards ---
def main_menu_kb():
    kb = [
        [InlineKeyboardButton(text="👥 Управление аккаунтами", callback_data="manage_users")],
        [InlineKeyboardButton(text="➕ Добавить аккаунт", callback_data="add_user")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def user_menu_kb(user_id: int):
    kb = [
        [InlineKeyboardButton(text="📁 Папки", callback_data=f"user_folders:{user_id}")],
        [InlineKeyboardButton(text="🔄 Перезапустить сканер", callback_data=f"user_restart:{user_id}")],
        [InlineKeyboardButton(text="🗑 Удалить аккаунт", callback_data=f"user_delete:{user_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

async def clean_edit(message: types.Message, state: FSMContext, text: str, reply_markup=None):
    try:
        await message.delete()
    except:
        pass
    data = await state.get_data()
    msg_id = data.get('msg_id')
    if msg_id:
        try:
            await bot.edit_message_text(text, chat_id=message.chat.id, message_id=msg_id, reply_markup=reply_markup)
            return
        except:
            pass
    await message.answer(text, reply_markup=reply_markup)

# --- Handlers ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    await message.answer("🤖 **Панель управления TG Scanner**", reply_markup=main_menu_kb())

@dp.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🤖 **Панель управления TG Scanner**", reply_markup=main_menu_kb())

# --- Add User Flow ---
@dp.callback_query(F.data == "add_user")
async def cb_add_user(callback: CallbackQuery, state: FSMContext):
    await state.update_data(msg_id=callback.message.message_id)
    await callback.message.edit_text("Введите **API ID**:")
    await state.set_state(AddUserState.wait_api_id)

@dp.message(AddUserState.wait_api_id)
async def state_api_id(message: types.Message, state: FSMContext):
    await state.update_data(api_id=int(message.text))
    await clean_edit(message, state, "Введите **API HASH**:")
    await state.set_state(AddUserState.wait_api_hash)

@dp.message(AddUserState.wait_api_hash)
async def state_api_hash(message: types.Message, state: FSMContext):
    await state.update_data(api_hash=message.text)
    await clean_edit(message, state, "Введите номер телефона (с плюсом, например +123456789):")
    await state.set_state(AddUserState.wait_phone)

@dp.message(AddUserState.wait_phone)
async def state_phone(message: types.Message, state: FSMContext):
    phone = message.text
    await state.update_data(phone=phone)
    data = await state.get_data()
    
    session_name = f"session_{phone.replace('+', '')}"
    await state.update_data(session_name=session_name)
    
    os.makedirs("sessions", exist_ok=True)
    workdir = os.path.join(os.getcwd(), "sessions")
    
    client = Client(session_name, api_id=data['api_id'], api_hash=data['api_hash'], workdir=workdir)
    await client.connect()
    
    try:
        sent_code = await client.send_code(phone)
        auth_temp[message.from_user.id] = {
            "client": client,
            "phone_code_hash": sent_code.phone_code_hash
        }
        await clean_edit(message, state, "Код отправлен. Введите его (если в коде есть пробелы или тире - уберите их):")
        await state.set_state(AddUserState.wait_code)
    except Exception as e:
        await clean_edit(message, state, f"Ошибка отправки кода: {e}", reply_markup=main_menu_kb())
        await state.clear()

@dp.message(AddUserState.wait_code)
async def state_code(message: types.Message, state: FSMContext):
    code = message.text
    data = await state.get_data()
    temp = auth_temp.get(message.from_user.id)
    
    if not temp:
        await clean_edit(message, state, "Сессия устарела, начните заново.", reply_markup=main_menu_kb())
        return
        
    client: Client = temp["client"]
    try:
        await client.sign_in(data["phone"], temp["phone_code_hash"], code)
        await client.disconnect()
        
        notify_id = message.chat.id
        user_id = await database.add_user(
            data["session_name"], data["api_id"], data["api_hash"], data["phone"], notify_id
        )
        
        await clean_edit(message, state, f"✅ Аккаунт успешно добавлен!\nВсе уведомления будут приходить в этот чат.", reply_markup=main_menu_kb())
        
        user = await database.get_user_by_id(user_id)
        asyncio.create_task(scanner.start_client(dict(user)))
        
    except Exception as e:
        await clean_edit(message, state, f"Ошибка авторизации: {e}", reply_markup=main_menu_kb())
    finally:
        await state.clear()
        if message.from_user.id in auth_temp:
            del auth_temp[message.from_user.id]

# --- Manage Users ---
@dp.callback_query(F.data == "manage_users")
async def cb_manage_users(callback: CallbackQuery):
    users = await database.get_all_users()
    if not users:
        await callback.message.edit_text("Аккаунты не найдены.", reply_markup=main_menu_kb())
        return
        
    kb = []
    for u in users:
        kb.append([InlineKeyboardButton(text=f"📱 {u['phone']}", callback_data=f"user_menu:{u['id']}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    
    await callback.message.edit_text("Выберите аккаунт:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("user_menu:"))
async def cb_user_menu(callback: CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    user = await database.get_user_by_id(user_id)
    if not user:
        await callback.answer("Пользователь не найден")
        return
        
    await callback.message.edit_text(f"Аккаунт: **{user['phone']}**", reply_markup=user_menu_kb(user_id))

@dp.callback_query(F.data.startswith("user_restart:"))
async def cb_user_restart(callback: CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.answer("Перезапуск...")
    await scanner.stop_client(user_id)
    user = await database.get_user_by_id(user_id)
    asyncio.create_task(scanner.start_client(dict(user)))
    await callback.message.answer("✅ Клиент перезапущен и папки синхронизированы.")

@dp.callback_query(F.data.startswith("user_delete:"))
async def cb_user_delete(callback: CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await scanner.stop_client(user_id)
    await database.delete_user(user_id)
    await callback.message.edit_text("Аккаунт удален.", reply_markup=main_menu_kb())

# --- Folders ---
@dp.callback_query(F.data.startswith("user_folders:"))
async def cb_user_folders(callback: CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    folders = await database.get_folders_by_user(user_id)
    
    kb = []
    for f in folders:
        kb.append([InlineKeyboardButton(text=f"📁 {f['name']}", callback_data=f"folder_view:{f['id']}")])
    kb.append([InlineKeyboardButton(text="➕ Добавить папку", callback_data=f"add_folder:{user_id}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад к аккаунту", callback_data=f"user_menu:{user_id}")])
    
    await callback.message.edit_text("Папки сканирования:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("add_folder:"))
async def cb_add_folder(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    await state.update_data(user_id=user_id, msg_id=callback.message.message_id)
    await callback.message.edit_text("Введите точное название папки в Telegram:")
    await state.set_state(AddFolderState.wait_folder_name)

@dp.message(AddFolderState.wait_folder_name)
async def state_folder_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data['user_id']
    await database.add_folder(user_id, message.text)
    
    await clean_edit(message, state, f"Папка {message.text} добавлена! Не забудьте перезапустить сканер, чтобы подтянуть новые настройки.", reply_markup=main_menu_kb())
    await state.clear()
    await scanner.reload_user(user_id)

@dp.callback_query(F.data.startswith("folder_view:"))
async def cb_folder_view(callback: CallbackQuery):
    folder_id = int(callback.data.split(":")[1])
    
    keywords = await database.get_keywords_by_folder(folder_id)
    stops = await database.get_stop_words_by_folder(folder_id)
    
    text = f"**Настройки папки**\n\n"
    text += "**Ключевые слова:**\n" + (", ".join(keywords) if keywords else "Нет") + "\n\n"
    text += "**Стоп-слова:**\n" + (", ".join(stops) if stops else "Нет")
    
    kb = [
        [InlineKeyboardButton(text="➕ Добавить ключи", callback_data=f"add_kw:{folder_id}"),
         InlineKeyboardButton(text="➖ Удалить ключ", callback_data=f"del_kw:{folder_id}")],
        [InlineKeyboardButton(text="➕ Добавить стоп-слово", callback_data=f"add_sw:{folder_id}"),
         InlineKeyboardButton(text="➖ Удалить стоп-слово", callback_data=f"del_sw:{folder_id}")],
        [InlineKeyboardButton(text="❌ Удалить папку", callback_data=f"del_folder:{folder_id}")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("add_kw:"))
async def cb_add_kw(callback: CallbackQuery, state: FSMContext):
    folder_id = int(callback.data.split(":")[1])
    await state.update_data(folder_id=folder_id, msg_id=callback.message.message_id)
    await callback.message.edit_text("Введите ключевые слова через запятую (можно использовать + для связок, например: rent, wifi + adapter):")
    await state.set_state(AddKeywordState.wait_keyword)

@dp.message(AddKeywordState.wait_keyword)
async def state_add_kw(message: types.Message, state: FSMContext):
    data = await state.get_data()
    folder_id = data['folder_id']
    
    words = [w.strip() for w in message.text.split(",") if w.strip()]
    for w in words:
        await database.add_keyword(folder_id, w)
        
    await clean_edit(message, state, "Ключевые слова добавлены! Настройки обновлены.", reply_markup=main_menu_kb())
    await state.clear()
    
    async with aiosqlite.connect(database.DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM folders WHERE id = ?", (folder_id,))
        row = await cursor.fetchone()
        if row:
            await scanner.reload_user(row[0])


@dp.callback_query(F.data.startswith("del_kw:"))
async def cb_del_kw(callback: CallbackQuery, state: FSMContext):
    folder_id = int(callback.data.split(":")[1])
    await state.update_data(folder_id=folder_id, msg_id=callback.message.message_id)
    await callback.message.edit_text("Введите ключевое слово для удаления (точно как в списке):")
    await state.set_state(DelKeywordState.wait_keyword)

@dp.message(DelKeywordState.wait_keyword)
async def state_del_kw(message: types.Message, state: FSMContext):
    data = await state.get_data()
    folder_id = data['folder_id']
    await database.delete_keyword(folder_id, message.text.strip())
    
    await clean_edit(message, state, "Удалено! Настройки обновлены.", reply_markup=main_menu_kb())
    await state.clear()
    
    async with aiosqlite.connect(database.DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM folders WHERE id = ?", (folder_id,))
        row = await cursor.fetchone()
        if row:
            await scanner.reload_user(row[0])

@dp.callback_query(F.data.startswith("add_sw:"))
async def cb_add_sw(callback: CallbackQuery, state: FSMContext):
    folder_id = int(callback.data.split(":")[1])
    await state.update_data(folder_id=folder_id, msg_id=callback.message.message_id)
    await callback.message.edit_text("Введите стоп-слова через запятую:")
    await state.set_state(AddStopWordState.wait_stop_word)

@dp.message(AddStopWordState.wait_stop_word)
async def state_add_sw(message: types.Message, state: FSMContext):
    data = await state.get_data()
    folder_id = data['folder_id']
    words = [w.strip() for w in message.text.split(",") if w.strip()]
    for w in words:
        await database.add_stop_word(folder_id, w)
        
    await clean_edit(message, state, "Стоп-слова добавлены! Настройки обновлены.", reply_markup=main_menu_kb())
    await state.clear()
    
    async with aiosqlite.connect(database.DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM folders WHERE id = ?", (folder_id,))
        row = await cursor.fetchone()
        if row:
            await scanner.reload_user(row[0])

@dp.callback_query(F.data.startswith("del_sw:"))
async def cb_del_sw(callback: CallbackQuery, state: FSMContext):
    folder_id = int(callback.data.split(":")[1])
    await state.update_data(folder_id=folder_id, msg_id=callback.message.message_id)
    await callback.message.edit_text("Введите стоп-слово для удаления (точно как в списке):")
    await state.set_state(DelStopWordState.wait_stop_word)

@dp.message(DelStopWordState.wait_stop_word)
async def state_del_sw(message: types.Message, state: FSMContext):
    data = await state.get_data()
    folder_id = data['folder_id']
    await database.delete_stop_word(folder_id, message.text.strip())
    
    await clean_edit(message, state, "Удалено! Настройки обновлены.", reply_markup=main_menu_kb())
    await state.clear()
    
    async with aiosqlite.connect(database.DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM folders WHERE id = ?", (folder_id,))
        row = await cursor.fetchone()
        if row:
            await scanner.reload_user(row[0])

@dp.callback_query(F.data.startswith("del_folder:"))
async def cb_del_folder(callback: CallbackQuery):
    folder_id = int(callback.data.split(":")[1])
    
    async with aiosqlite.connect(database.DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM folders WHERE id = ?", (folder_id,))
        row = await cursor.fetchone()
        user_id = row[0] if row else None
        
    await database.delete_folder(folder_id)
    await callback.answer("Папка удалена")
    if user_id:
        await scanner.reload_user(user_id)
    await callback.message.edit_text("Удалено.", reply_markup=main_menu_kb())
