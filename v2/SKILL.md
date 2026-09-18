---
name: "TG Scanner V2 Agent Help"
description: "Instructions for AI agents modifying or understanding the TG Scanner V2 architecture."
---

# TG Scanner V2 Architecture

## Overview
This is a multi-tenant Telegram monitoring system. It allows an admin to manage multiple user accounts (Pyrogram clients) via a Telegram Bot Manager (Aiogram). The scanner listens to messages in real-time (event-driven) instead of polling history to prevent Telegram `FloodWait` limits.

## Directory Structure
- `database.py`: Handles all SQLite operations (using `aiosqlite`). Tables: `users`, `folders`, `keywords`, `stop_words`, `global_stop_words`.
- `scanner.py`: The Pyrogram engine. Dynamically loads user configurations from the database and spawns clients in the same async event loop. Uses `@app.on_message` for event-driven monitoring.
- `manager.py`: Aiogram 3 bot. Provides an inline keyboard interface for the Admin to add user accounts, folders, and keywords.
- `main.py`: Entry point. Starts the database, the Pyrogram clients, and the Aiogram polling.
- `deploy.sh`: Script to setup venv, install deps, ask for `.env` vars, and create a systemd service.

## Adding a User Flow
1. Admin triggers `/start` in the Manager Bot.
2. Clicks "Add Account".
3. Provides `API ID`, `API HASH`, and `Phone`.
4. Aiogram creates a temporary `Client` and calls `send_code()`.
5. Admin inputs code. Aiogram calls `sign_in()`.
6. Session is saved to `sessions/session_<phone>.session`.
7. Account is inserted into `users` table.
8. `scanner.start_client()` is triggered to launch the Pyrogram monitor for this account.

## Modifying Keyword Matching Logic
The text matching logic is inside `scanner.py` -> `handle_message()`.
- Content is parsed and converted to lowercase.
- Global stop words are checked.
- Chat ID is resolved to a folder.
- Local folder stop words are checked.
- Keywords are checked. Compound keywords (e.g. `rent + wifi`) are split into lists `["rent", "wifi"]` and matched using `all(word in text)`.

## Known Caveats
- Adding Two-Factor Authentication (2FA) support is currently not fully implemented. If an account has a cloud password, the bot will throw `SessionPasswordNeeded`.
- When adding a folder via the Manager Bot, the folder MUST exist in the user's Telegram client (Dialog Filters) exactly with the same name.
