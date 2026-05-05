"""
Configuration module for Telegram File Bot.

Loads settings from environment variables with sensible defaults.
Uses python-dotenv to load from a .env file if present.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _parse_int(value: str | None, default: int) -> int:
    """Parse an integer from an env var, returning *default* on failure."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _parse_csv(value: str | None) -> List[int]:
    """Parse a comma-separated list of Telegram user IDs."""
    if not value:
        return []
    ids: List[int] = []
    for chunk in value.split(","):
        chunk = chunk.strip()
        if chunk:
            try:
                ids.append(int(chunk))
            except ValueError:
                pass  # silently skip malformed entries
    return ids


# ── Bot ─────────────────────────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
"""Telegram bot token from @BotFather."""

# ── Access control ──────────────────────────────────────────────────────
ALLOWED_USERS: List[int] = _parse_csv(os.getenv("ALLOWED_USERS"))
"""Telegram user IDs authorised to use the bot.  Empty = no-one."""

ADMIN_IDS: List[int] = _parse_csv(os.getenv("ADMIN_IDS"))
"""User IDs allowed to run /allow and /revoke commands."""

# ── Storage ─────────────────────────────────────────────────────────────
UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", "/var/bot_uploads"))
"""Directory where uploaded files are stored. Created on startup if missing."""

ALLOWED_EXTENSIONS: set = {
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".doc", ".docx",
    ".xls", ".xlsx", ".txt", ".csv", ".zip", ".gz", ".7z",
    ".mp4", ".mp3", ".wav", ".ogg",
}
"""File extensions permitted for upload."""

MAX_FILE_SIZE: int = _parse_int(os.getenv("MAX_FILE_SIZE"), 50 * 1024 * 1024)
"""Maximum upload size in bytes (default 50 MB — Telegram bot limit)."""

# ── Rate limiting ───────────────────────────────────────────────────────
RATE_LIMIT_UPLOADS: int = _parse_int(os.getenv("RATE_LIMIT_UPLOADS"), 5)
"""Max uploads per time window."""

RATE_LIMIT_WINDOW: int = _parse_int(os.getenv("RATE_LIMIT_WINDOW"), 60)
"""Rate-limit window in seconds (default 60)."""

# ── Logging ─────────────────────────────────────────────────────────────
LOG_DIR: Path = Path(os.getenv("LOG_DIR", "/var/log/telegram-file-bot"))
"""Directory for log files."""

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
"""Logging level: DEBUG, INFO, WARNING, ERROR."""

# ── Paths ───────────────────────────────────────────────────────────────
WHITELIST_FILE: Path = Path(os.getenv("WHITELIST_FILE", ""))
"""Optional path to a JSON file for persistent whitelist storage.
If empty, the whitelist is ephemeral (memory-only)."""
