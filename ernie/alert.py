"""Telegram alerting for Ernie guardian.

Thin wrapper around the bot's existing Telegram infra.
"""
import os
from pathlib import Path

import requests

PROJECT_DIR = Path(__file__).resolve().parent.parent
CHAT_ID_FILE = PROJECT_DIR / "chat_id.txt"


def _load_chat_id() -> str | None:
    if not CHAT_ID_FILE.exists():
        return None
    raw = CHAT_ID_FILE.read_text().strip()
    return raw if raw else None


def _bot_token() -> str | None:
    return os.getenv("TAU_BOT_TOKEN") or os.getenv("BOT_TOKEN")


def send_alert(message: str) -> bool:
    token = _bot_token()
    chat_id = _load_chat_id()
    if not token or not chat_id:
        return False
    try:
        icon = "\U0001f36a\U0001f43b"
        payload = {"chat_id": chat_id, "text": f"{icon} Ernie: {message}", "parse_mode": "HTML"}
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=payload, timeout=15,
        )
        return resp.status_code == 200
    except Exception:
        return False
