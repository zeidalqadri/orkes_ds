"""
Authentication & access-control module for Telegram File Bot.

Manages a user whitelist (Telegram user IDs) with optional JSON-backed
persistence and simple admin commands to add/remove users.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Set

import config

logger = logging.getLogger(__name__)


class AuthManager:
    """Whitelist-based access control with optional disk persistence."""

    def __init__(self) -> None:
        self._whitelist: Set[int] = set(config.ALLOWED_USERS)
        self._admin_ids: Set[int] = set(config.ADMIN_IDS)
        self._persist_path: Path | None = (
            config.WHITELIST_FILE if config.WHITELIST_FILE else None
        )
        self._load()

    # ── public API ──────────────────────────────────────────────────────

    def is_authorised(self, user_id: int) -> bool:
        """Return *True* if *user_id* is allowed to use the bot."""
        return user_id in self._whitelist or user_id in self._admin_ids

    def is_admin(self, user_id: int) -> bool:
        """Return *True* if *user_id* has admin privileges."""
        return user_id in self._admin_ids

    def allow(self, user_id: int, actor_id: int) -> str:
        """Add *user_id* to the whitelist (admin-only)."""
        if not self.is_admin(actor_id):
            return "Permission denied — you are not an admin."
        self._whitelist.add(user_id)
        self._save()
        return f"User `{user_id}` added to the whitelist."

    def revoke(self, user_id: int, actor_id: int) -> str:
        """Remove *user_id* from the whitelist (admin-only)."""
        if not self.is_admin(actor_id):
            return "Permission denied — you are not an admin."
        self._whitelist.discard(user_id)
        self._save()
        return f"User `{user_id}` removed from the whitelist."

    def whitelisted_users(self) -> Dict[str, str]:
        """Return the current whitelist as a dict ``{user_id → status}``."""
        return {
            str(uid): "admin" if uid in self._admin_ids else "user"
            for uid in sorted(self._whitelist | self._admin_ids)
        }

    # ── persistence ─────────────────────────────────────────────────────

    def _load(self) -> None:
        if self._persist_path is None or not self._persist_path.exists():
            return
        try:
            data = json.loads(self._persist_path.read_text())
            self._whitelist = set(data.get("whitelist", [])) | set(
                config.ALLOWED_USERS
            )
            self._admin_ids = set(data.get("admins", [])) | set(config.ADMIN_IDS)
            logger.info(
                "Loaded whitelist: %d users, %d admins",
                len(self._whitelist),
                len(self._admin_ids),
            )
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load whitelist from %s: %s", self._persist_path, exc)

    def _save(self) -> None:
        if self._persist_path is None:
            return
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(
                json.dumps(
                    {
                        "whitelist": sorted(self._whitelist),
                        "admins": sorted(self._admin_ids),
                    },
                    indent=2,
                )
            )
        except OSError as exc:
            logger.error("Failed to persist whitelist: %s", exc)


# Singleton for the application
auth_manager = AuthManager()
