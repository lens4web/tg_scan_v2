#!/bin/bash
set -e

# Go to script directory
cd "$(dirname "$0")"

echo "Setting up Telegram Scanner V2..."

# Setup Virtual Environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

# Request .env variables if not exist
if [ ! -f ".env" ]; then
    echo "Создание конфигурации .env..."
    read -p "Введите токен вашего бота-менеджера (BotFather): " BOT_TOKEN
    read -p "Введите ваш Telegram User ID (для доступа к админке): " ADMIN_ID
    
    echo "BOT_TOKEN=$BOT_TOKEN" > .env
    echo "ADMIN_ID=$ADMIN_ID" >> .env
    echo "✅ .env файл создан."
fi

# Setup Systemd Service
SERVICE_FILE="/etc/systemd/system/tg_scanner_v2.service"
CURRENT_DIR=$(pwd)
CURRENT_USER=$USER

echo "Создание systemd сервиса (потребуются права root)..."
sudo bash -c "cat > $SERVICE_FILE <<EOF
[Unit]
Description=Telegram Scanner V2
After=network.target

[Service]
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/venv/bin/python3 $CURRENT_DIR/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable tg_scanner_v2
sudo systemctl restart tg_scanner_v2

echo "✅ Установка завершена!"
echo "Статус сервиса: sudo systemctl status tg_scanner_v2"
echo "Логи: journalctl -u tg_scanner_v2 -n 50 -f"
