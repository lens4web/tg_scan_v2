import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "scanner.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_name TEXT UNIQUE NOT NULL,
                api_id INTEGER NOT NULL,
                api_hash TEXT NOT NULL,
                phone TEXT NOT NULL,
                notify_id INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                FOREIGN KEY(folder_id) REFERENCES folders(id) ON DELETE CASCADE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stop_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                FOREIGN KEY(folder_id) REFERENCES folders(id) ON DELETE CASCADE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS global_stop_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        await db.commit()

# --- Users ---
async def add_user(session_name, api_id, api_hash, phone, notify_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO users (session_name, api_id, api_hash, phone, notify_id) VALUES (?, ?, ?, ?, ?)",
            (session_name, api_id, api_hash, phone, notify_id)
        )
        await db.commit()
        return cursor.lastrowid

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users")
        return await cursor.fetchall()

async def get_user_by_id(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return await cursor.fetchone()

async def delete_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await db.commit()

# --- Folders ---
async def add_folder(user_id, name):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO folders (user_id, name) VALUES (?, ?)", (user_id, name)
        )
        await db.commit()
        return cursor.lastrowid

async def get_folders_by_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM folders WHERE user_id = ?", (user_id,))
        return await cursor.fetchall()

async def delete_folder(folder_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
        await db.commit()

# --- Keywords ---
async def add_keyword(folder_id, word):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO keywords (folder_id, word) VALUES (?, ?)", (folder_id, word))
        await db.commit()

async def get_keywords_by_folder(folder_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT word FROM keywords WHERE folder_id = ?", (folder_id,))
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
        
async def delete_keyword(folder_id, word):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM keywords WHERE folder_id = ? AND word = ?", (folder_id, word))
        await db.commit()

# --- Stop Words ---
async def add_stop_word(folder_id, word):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO stop_words (folder_id, word) VALUES (?, ?)", (folder_id, word))
        await db.commit()

async def get_stop_words_by_folder(folder_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT word FROM stop_words WHERE folder_id = ?", (folder_id,))
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
        
async def delete_stop_word(folder_id, word):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM stop_words WHERE folder_id = ? AND word = ?", (folder_id, word))
        await db.commit()

# --- Global Stop Words ---
async def add_global_stop_word(user_id, word):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO global_stop_words (user_id, word) VALUES (?, ?)", (user_id, word))
        await db.commit()

async def get_global_stop_words_by_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT word FROM global_stop_words WHERE user_id = ?", (user_id,))
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
        
async def delete_global_stop_word(user_id, word):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM global_stop_words WHERE user_id = ? AND word = ?", (user_id, word))
        await db.commit()
