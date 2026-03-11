# paw

Telegram proxy for Claude Code CLI. Your messages go to Claude Code, its responses come back to you.

## Prerequisites

- Python 3.11+
- Claude Code CLI installed and authenticated (`claude` must work in your terminal)
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- Your Telegram user ID (from [@userinfobot](https://t.me/userinfobot))

## Quick start (VPS)

```bash
git clone <your-repo-url> && cd paw
./setup.sh
```

The setup script will:
1. Install the bot to `/opt/paw`
2. Create a Python venv and install dependencies
3. Prompt you for your Telegram bot token and user ID
4. Install and start a systemd service

The bot survives terminal closes, crashes (auto-restarts in 5s), and VPS reboots (auto-starts on boot).

## Manual setup (without systemd)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit with your values
python bot.py
```

## Managing the service

```bash
# View live logs
sudo journalctl -u paw -f

# Restart
sudo systemctl restart paw

# Stop
sudo systemctl stop paw

# Check status
sudo systemctl status paw
```

## Stop and remove completely

```bash
sudo systemctl stop paw
sudo systemctl disable paw
sudo rm /etc/systemd/system/paw.service
sudo systemctl daemon-reload
sudo rm -rf /opt/paw
```

## Configuration

All config is in `/opt/paw/.env` (or `.env` locally):

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from @BotFather |
| `ALLOWED_USER_IDS` | Yes | Comma-separated Telegram user IDs allowed to use the bot |
| `WORK_DIR` | No | Working directory for Claude Code (default: `/opt/paw/workspace`) |

## Running tests

```bash
source .venv/bin/activate
pytest tests/ -v
```
