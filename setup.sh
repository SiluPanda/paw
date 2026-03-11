#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/paw"
SERVICE_NAME="paw"

echo "==> Installing paw to $INSTALL_DIR"

# Copy files
sudo mkdir -p "$INSTALL_DIR"
sudo cp bot.py requirements.txt "$INSTALL_DIR/"

# Create venv and install deps
sudo python3 -m venv "$INSTALL_DIR/.venv"
sudo "$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# Prompt for .env if missing
if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo ""
    echo "==> No .env found. Creating one..."
    read -rp "TELEGRAM_BOT_TOKEN: " token
    read -rp "ALLOWED_USER_IDS (comma-separated): " user_ids

    sudo tee "$INSTALL_DIR/.env" > /dev/null <<EOF
TELEGRAM_BOT_TOKEN=$token
ALLOWED_USER_IDS=$user_ids
WORK_DIR=$INSTALL_DIR/workspace
CLAUDE_TIMEOUT=300
EOF
    sudo chmod 600 "$INSTALL_DIR/.env"
    sudo mkdir -p "$INSTALL_DIR/workspace"
    echo "==> .env created at $INSTALL_DIR/.env"
fi

# Install systemd service
sudo cp paw.service /etc/systemd/system/"$SERVICE_NAME".service

# Set ownership to current user
sudo chown -R "$(whoami)":"$(id -gn)" "$INSTALL_DIR"

# Update service to use current user
sudo sed -i "s|User=%i|User=$(whoami)|" /etc/systemd/system/"$SERVICE_NAME".service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"

echo ""
echo "==> Done! Bot is running."
echo "    Logs:    sudo journalctl -u $SERVICE_NAME -f"
echo "    Stop:    sudo systemctl stop $SERVICE_NAME"
echo "    Restart: sudo systemctl restart $SERVICE_NAME"
