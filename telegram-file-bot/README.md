# Telegram File Bot

A production-ready Telegram bot for secure file upload and download between Telegram users and a Linux VPS. Built with `python-telegram-bot` v20.x and Python 3.9+.

## Overview

Users send files (documents, photos, videos, audio) to the bot, which stores them on the server. Authorised users can download, list, and (admins) delete files. Access is controlled by a Telegram user-ID whitelist with optional JSON-backed persistence.

### Features

- **Whitelist access control** — only approved Telegram user IDs can interact
- **Admin commands** — `/allow`, `/revoke`, `/delete`, `/whitelist`
- **Sanitised uploads** — path-traversal prevention, extension whitelist, unique filenames
- **Rate limiting** — configurable sliding-window per user
- **Comprehensive logging** — timestamped operations, errors, and access attempts
- **Disk-space checks** — rejects uploads when free space falls below a threshold
- **Systemd integration** — service file included for production auto-restart

## Prerequisites

- **Python 3.9+** and `pip`
- **Ubuntu 22.04 LTS** (or any modern Linux)
- A **Telegram bot token** from [@BotFather](https://t.me/BotFather)
- Your **Telegram user ID** (use [@userinfobot](https://t.me/userinfobot))

## Installation

### 1. Clone and set up

```bash
# Create the directory
sudo mkdir -p /opt/telegram-file-bot
sudo chown $USER:$USER /opt/telegram-file-bot

# Copy files
cp -r telegram-file-bot/* /opt/telegram-file-bot/

# Create upload directories
sudo mkdir -p /var/bot_uploads /var/log/telegram-file-bot
sudo chown $USER:$USER /var/bot_uploads /var/log/telegram-file-bot
```

### 2. Virtual environment

```bash
cd /opt/telegram-file-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration

```bash
cp .env.example .env
nano .env
```

Fill in at minimum:
```
BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
ALLOWED_USERS="12345678,87654321"
ADMIN_IDS="12345678"
```

### 4. Test-run

```bash
source .venv/bin/activate
python bot.py
```

Send `/start` to your bot on Telegram. Press `Ctrl+C` to stop.

### 5. Systemd service (production)

```bash
sudo cp telegram-file-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable telegram-file-bot
sudo systemctl start telegram-file-bot
sudo systemctl status telegram-file-bot
```

## Usage

### Commands

| Command | Description | Access |
|---|---|---|
| `/start` | Welcome message | All whitelisted |
| `/help` | Show available commands | All whitelisted |
| `/list` | List all stored files | All whitelisted |
| `/download <filename>` | Download a file | All whitelisted |
| `/delete <filename>` | Delete a file | Admin only |
| `/allow <user_id>` | Add user to whitelist | Admin only |
| `/revoke <user_id>` | Remove user from whitelist | Admin only |
| `/whitelist` | Show whitelist | Admin only |

### Upload

Simply send any file (document, photo, video, or audio) to the bot chat. The bot replies with the saved filename and size.

## Project Structure

```
telegram-file-bot/
├── bot.py              # Main bot logic and command handlers
├── config.py           # Environment-variable configuration
├── auth.py             # User whitelist and access control
├── file_handler.py     # File upload/download/management operations
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── telegram-file-bot.service  # Systemd service unit
├── pytest.ini          # Test configuration
├── README.md           # This file
└── tests/
    └── test_bot.py     # Functional test suite
```

## Running Tests

```bash
cd telegram-file-bot
source .venv/bin/activate
pip install pytest
python -m pytest tests/ -v
```

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `BOT_TOKEN` | _(required)_ | Telegram bot token from @BotFather |
| `ALLOWED_USERS` | _(required)_ | Comma-separated Telegram user IDs |
| `ADMIN_IDS` | _(required)_ | Comma-separated admin user IDs |
| `UPLOAD_DIR` | `/var/bot_uploads` | Upload storage directory |
| `MAX_FILE_SIZE` | `52428800` (50 MB) | Maximum upload size in bytes |
| `RATE_LIMIT_UPLOADS` | `5` | Max uploads per time window |
| `RATE_LIMIT_WINDOW` | `60` | Rate-limit window in seconds |
| `LOG_DIR` | `/var/log/telegram-file-bot` | Log file directory |
| `LOG_LEVEL` | `INFO` | Logging level |
| `WHITELIST_FILE` | _(empty)_ | Path for persistent whitelist JSON |

## Security

- **Path-traversal prevention**: filenames are sanitised via `os.path.basename()` and regex stripping of dangerous characters
- **Extension whitelist**: only explicitly allowed extensions are accepted
- **Rate limiting**: sliding-window per-user throttle on uploads
- **Disk space guard**: uploads rejected if free space drops below 500 MB
- **Systemd hardening**: `ProtectSystem=strict`, `PrivateDevices=true`, `PrivateTmp=true`, `NoNewPrivileges=true`
