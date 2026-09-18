import os
import json
import asyncio
import shutil
import database

OLD_JSON_PATH = "../main/words.json"
OLD_SESSION_PATH = "../main/my_account.session"

async def migrate():
    print("Начало миграции старых данных (words.json) в SQLite...")
    
    if not os.path.exists(OLD_JSON_PATH):
        print(f"Файл {OLD_JSON_PATH} не найден. Пропуск.")
        return
        
    await database.init_db()
    
    with open(OLD_JSON_PATH, "r", encoding="utf-8") as f:
        # Load the LAST JSON object if there are multiple in the file 
        # (the file seems to have multiple JSON objects appended, we take the last valid one or parse cleanly)
        content = f.read()
        try:
            # The user's words.json had two objects. We can try to wrap it in an array
            # or just take the last block.
            blocks = content.split("}\n{")
            if len(blocks) > 1:
                # Reconstruct the last block
                last_block = "{" + blocks[-1]
                data = json.loads(last_block)
            else:
                data = json.loads(content)
        except Exception as e:
            print(f"Ошибка парсинга JSON: {e}")
            return

    system = data.get("system", {})
    api_id = system.get("api_id")
    api_hash = system.get("api_hash")
    notify_id = system.get("notify_id")
    session_name = system.get("session_name", "my_account")
    phone = "+10000000000" # Phone is unknown from old config, adding placeholder
    
    # Check if user already exists
    users = await database.get_all_users()
    if any(u['session_name'] == session_name for u in users):
        print("Пользователь my_account уже существует в БД.")
        return
        
    user_id = await database.add_user(session_name, api_id, api_hash, phone, notify_id)
    print(f"Добавлен пользователь: {session_name} (ID: {user_id})")
    
    # Global stop words
    for gsw in data.get("global_stop_words", []):
        await database.add_global_stop_word(user_id, gsw)
        
    # Folders
    for folder_data in data.get("folders", []):
        folder_name = folder_data.get("folder_name")
        if not folder_name:
            continue
            
        folder_id = await database.add_folder(user_id, folder_name)
        
        for k in folder_data.get("keywords", []):
            if isinstance(k, list):
                await database.add_keyword(folder_id, " + ".join(k))
            else:
                await database.add_keyword(folder_id, k)
                
        for s in folder_data.get("stop_words", []):
            await database.add_stop_word(folder_id, s)
            
        print(f"Мигрирована папка: {folder_name}")
        
    # Copy session file
    os.makedirs("sessions", exist_ok=True)
    if os.path.exists(OLD_SESSION_PATH):
        shutil.copy(OLD_SESSION_PATH, f"sessions/{session_name}.session")
        print("Файл сессии скопирован.")
    else:
        print("ВНИМАНИЕ: Файл сессии my_account.session не найден.")
        
    print("Миграция завершена успешно!")

if __name__ == "__main__":
    asyncio.run(migrate())
