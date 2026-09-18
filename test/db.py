import sqlite3
import json

DB_FILE = "scanner.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER,
                title TEXT,
                keywords TEXT,
                chats TEXT
            )
        """)

def get_user_subs(tg_id: int) -> list:
    with sqlite3.connect(DB_FILE) as conn:
        res = conn.execute("SELECT id, title, keywords, chats FROM subscriptions WHERE tg_id = ?", (tg_id,)).fetchall()
        subs = []
        for r in res:
            subs.append({
                "id": r[0],
                "title": r[1],
                "keywords": json.loads(r[2]),
                "chats": json.loads(r[3])
            })
        return subs

def add_sub(tg_id: int, title: str, keywords: list, chats: list):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            INSERT INTO subscriptions (tg_id, title, keywords, chats)
            VALUES (?, ?, ?, ?)
        """, (tg_id, title, json.dumps(keywords), json.dumps(chats)))

def delete_sub(sub_id: int, tg_id: int):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM subscriptions WHERE id = ? AND tg_id = ?", (sub_id, tg_id))

def get_all_subs() -> list:
    with sqlite3.connect(DB_FILE) as conn:
        return conn.execute("SELECT tg_id, keywords, chats FROM subscriptions").fetchall()