import asyncio
from dotenv import load_dotenv

# Load env variables before importing any module that uses them
load_dotenv()

import database
import scanner
import manager

async def main():
    print("Initializing Database...")
    await database.init_db()
    
    print("Starting Pyrogram Clients...")
    await scanner.start_all_active_clients()
    
    print("Starting Manager Bot...")
    # This blocks and runs the bot
    await manager.dp.start_polling(manager.bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")
