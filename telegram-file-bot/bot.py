"""
Main bot module for Telegram File Bot.

Wires together auth, file handling, rate limiting, and all command
handlers into a single ``Application`` that can be run directly or
imported for testing.
"""

from __future__ import annotations

import logging
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from time import time
from typing import DefaultDict, List, Set

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
from auth import auth_manager
from file_handler import (
    delete_file,
    extract_file_info,
    list_files,
    save_upload,
    send_download,
)

# ── Logging setup ───────────────────────────────────────────────────────


def _setup_logging() -> None:
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = config.LOG_DIR / "bot.log"

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    root.addHandler(stream)

    logging.getLogger("httpx").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)

# ── Rate limiter ────────────────────────────────────────────────────────


class RateLimiter:
    """Simple in-memory sliding-window rate limiter."""

    def __init__(self, max_actions: int, window_secs: int) -> None:
        self._max = max_actions
        self._window = window_secs
        self._buckets: DefaultDict[int, List[float]] = defaultdict(list)

    def is_limited(self, user_id: int) -> bool:
        now = time()
        bucket = self._buckets[user_id]
        # Prune expired entries
        cutoff = now - self._window
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)
        if len(bucket) >= self._max:
            return True
        bucket.append(now)
        return False


rate_limiter = RateLimiter(config.RATE_LIMIT_UPLOADS, config.RATE_LIMIT_WINDOW)

# ── Decorator helpers ───────────────────────────────────────────────────


def _auth_required(func):
    """Decorator: reject unauthenticated users before calling the handler."""

    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if user is None:
            return
        if not auth_manager.is_authorised(user.id):
            logger.warning("Unauthorised access attempt by user %s", user.id)
            await update.message.reply_text(
                "Access denied. You are not on the whitelist."
            )
            return
        return await func(update, context)

    return wrapper


# ── Command handlers ────────────────────────────────────────────────────


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome message."""
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}!\n\n"
        "I'm a file-transfer bot. Send me a file to upload it to the server, "
        "or use /help to see available commands."
    )


@_auth_required
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show available commands."""
    text = (
        "*Available Commands*\n\n"
        "📤 *Upload* — Send any file (document, photo, video, audio)\n"
        "📥 `/download <filename>` — Download a file\n"
        "📋 `/list` — List all files\n"
        "❌ `/delete <filename>` — Delete a file (admin only)\n"
        "ℹ️ `/help` — Show this message\n\n"
        "━━━ *Admin Commands* ━━━\n"
        "➕ `/allow <user_id>` — Add user to whitelist\n"
        "➖ `/revoke <user_id>` — Remove user from whitelist\n"
        "👥 `/whitelist` — Show current whitelist\n\n"
        f"Allowed extensions: {', '.join(sorted(config.ALLOWED_EXTENSIONS))}\n"
        f"Max file size: {config.MAX_FILE_SIZE // (1024*1024)} MB"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


@_auth_required
async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all files in the upload directory."""
    files = list_files()
    if not files:
        await update.message.reply_text("No files uploaded yet.")
        return

    lines = [f"*{f['name']}* — {f['size_human']} (modified {f['modified'][:10]})" for f in files]
    # Telegram has a 4096-char limit per message — chunk if needed
    chunks = []
    current = []
    char_count = 0
    for line in lines:
        if char_count + len(line) + 1 > 3900:
            chunks.append("\n".join(current))
            current = [line]
            char_count = len(line) + 1
        else:
            current.append(line)
            char_count += len(line) + 1
    if current:
        chunks.append("\n".join(current))

    header = f"*{len(files)} file(s) in storage:*\n\n"
    for i, chunk in enumerate(chunks):
        payload = header + chunk if i == 0 else chunk
        await update.message.reply_text(payload, parse_mode=ParseMode.MARKDOWN)


@_auth_required
async def cmd_download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download a file by name."""
    if not context.args:
        await update.message.reply_text("Usage: `/download <filename>`", parse_mode=ParseMode.MARKDOWN)
        return
    filename = " ".join(context.args)
    msg = await send_download(context, update.effective_chat.id, filename)
    if msg.startswith("Sent"):
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


@_auth_required
async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a file (admin only, with confirmation)."""
    user = update.effective_user
    if not auth_manager.is_admin(user.id):
        await update.message.reply_text("Permission denied — admin only.")
        return

    if not context.args:
        await update.message.reply_text("Usage: `/delete <filename>`", parse_mode=ParseMode.MARKDOWN)
        return

    filename = " ".join(context.args)
    result = delete_file(filename, update.effective_chat.id, user.id)
    await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)


# ── Admin commands ──────────────────────────────────────────────────────


@_auth_required
async def cmd_allow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a user to the whitelist (admin only)."""
    user = update.effective_user
    if not auth_manager.is_admin(user.id):
        await update.message.reply_text("Permission denied.")
        return
    if not context.args:
        await update.message.reply_text("Usage: `/allow <user_id>`")
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID. Must be an integer.")
        return
    msg = auth_manager.allow(target_id, user.id)
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


@_auth_required
async def cmd_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove a user from the whitelist (admin only)."""
    user = update.effective_user
    if not auth_manager.is_admin(user.id):
        await update.message.reply_text("Permission denied.")
        return
    if not context.args:
        await update.message.reply_text("Usage: `/revoke <user_id>`")
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID. Must be an integer.")
        return
    msg = auth_manager.revoke(target_id, user.id)
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


@_auth_required
async def cmd_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the current whitelist (admin only)."""
    user = update.effective_user
    if not auth_manager.is_admin(user.id):
        await update.message.reply_text("Permission denied.")
        return
    users = auth_manager.whitelisted_users()
    if not users:
        await update.message.reply_text("Whitelist is empty.")
        return
    lines = [f"• `{uid}` ({role})" for uid, role in users.items()]
    await update.message.reply_text(
        f"*Whitelisted users ({len(users)}):*\n" + "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
    )


# ── File upload handler ────────────────────────────────────────────────


@_auth_required
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming documents, photos, videos, audio, and voice messages."""
    user = update.effective_user

    # Rate-limit check
    if rate_limiter.is_limited(user.id):
        await update.message.reply_text(
            f"Rate limit exceeded. Max {config.RATE_LIMIT_UPLOADS} uploads "
            f"per {config.RATE_LIMIT_WINDOW} seconds."
        )
        return

    msg = update.message
    info = extract_file_info(
        document=msg.document,
        photo=msg.photo,
        video=msg.video,
        audio=msg.audio,
        voice=msg.voice,
    )

    if info is None:
        await update.message.reply_text(
            "Unsupported file type. Send a document, photo, video, or audio file."
        )
        return

    file_id, filename, file_size = info

    # Size check
    if file_size > config.MAX_FILE_SIZE:
        await update.message.reply_text(
            f"File too large ({file_size // (1024*1024)} MB). "
            f"Maximum allowed: {config.MAX_FILE_SIZE // (1024*1024)} MB."
        )
        return

    try:
        path, size = await save_upload(context, file_id, filename)
        await update.message.reply_text(
            f"Uploaded `{path.name}` ({_human_size(size)}).",
            parse_mode=ParseMode.MARKDOWN,
        )
    except ValueError as exc:
        await update.message.reply_text(str(exc))
    except OSError as exc:
        logger.error("Upload failed: %s", exc)
        await update.message.reply_text(f"Storage error: {exc}")
    except Exception as exc:
        logger.exception("Unexpected upload error")
        await update.message.reply_text(f"Unexpected error: {exc}")


# ── Helpers ─────────────────────────────────────────────────────────────


def _human_size(bytes_: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if bytes_ < 1024:
            return f"{bytes_:.1f} {unit}" if unit != "B" else f"{bytes_} B"
        bytes_ /= 1024
    return f"{bytes_:.1f} TB"


# ── Application factory ─────────────────────────────────────────────────


def build_application() -> Application:
    """Create and configure the bot ``Application``.

    Call ``application.run_polling()`` to start.
    """
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set — check your .env file.")

    application = Application.builder().token(config.BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("list", cmd_list))
    application.add_handler(CommandHandler("download", cmd_download))
    application.add_handler(CommandHandler("delete", cmd_delete))
    application.add_handler(CommandHandler("allow", cmd_allow))
    application.add_handler(CommandHandler("revoke", cmd_revoke))
    application.add_handler(CommandHandler("whitelist", cmd_whitelist))

    # Catch-all for file uploads (must come after command handlers)
    application.add_handler(
        MessageHandler(
            filters.Document.ALL
            | filters.PHOTO
            | filters.VIDEO
            | filters.AUDIO
            | filters.VOICE,
            handle_file,
        )
    )

    return application


# ── Entry point ─────────────────────────────────────────────────────────


def main() -> None:
    _setup_logging()
    logger.info("Starting Telegram File Bot ...")
    application = build_application()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
