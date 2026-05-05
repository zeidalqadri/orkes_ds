"""
File upload / download / management operations for Telegram File Bot.

Handles:
  - Unique filename generation
  - Extension validation & path-traversal sanitisation
  - Upload from Telegram's file system
  - Download to Telegram user
  - Listing, deleting, and size / date queries
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from telegram import Document, File, PhotoSize, Video, Audio, Voice
from telegram.ext import ContextTypes

import config

logger = logging.getLogger(__name__)

# ── Helpers ─────────────────────────────────────────────────────────────


def _sanitise_filename(name: str) -> str:
    """Strip path separators and dangerous characters from *name*.

    Removes any ``../``, ``..\\``, leading slashes, and null bytes.
    Returns a plain filename safe for use as a filesystem leaf.
    """
    # Null-byte → underscore (prevents malicious concatenation)
    name = name.replace("\0", "_")
    # Strip directory components
    name = name.replace("\\", "/")
    name = name.rstrip("/")
    # Remove any remaining path prefixes
    name = os.path.basename(name)
    # Collapse runs of non-alphanumeric (except . - _) into single _
    name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    # Avoid empty / dot-only names
    if not name or set(name) in ({".", ".."}, {"."}, {".."}):
        name = f"unnamed_{int(time.time())}"
    return name


def _unique_path(directory: Path, filename: str) -> Path:
    """Return a Path inside *directory* that does not already exist.

    If *filename* is taken, appends a numeric suffix before the extension.
    """
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    candidate = directory / filename
    counter = 1
    while candidate.exists():
        candidate = directory / f"{stem}_{counter}{suffix}"
        counter += 1
    return candidate


def _human_size(bytes_: int) -> str:
    """Return a human-readable string for *bytes_* (e.g. ``"4.2 MB"``)."""
    for unit in ("B", "KB", "MB", "GB"):
        if bytes_ < 1024:
            return f"{bytes_:.1f} {unit}" if unit != "B" else f"{bytes_} B"
        bytes_ /= 1024
    return f"{bytes_:.1f} TB"


# ── Public API ──────────────────────────────────────────────────────────


async def save_upload(
    context: ContextTypes.DEFAULT_TYPE,
    file_id: str,
    original_filename: str,
) -> Tuple[Path, int]:
    """Download a file from Telegram and save it to the upload directory.

    Returns ``(path, size_in_bytes)``.

    Raises
    ------
    FileExistsError
        If disk space is critically low.
    ValueError
        If the extension is not in the whitelist.
    """
    ext = Path(original_filename).suffix.lower()
    if ext not in config.ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Extension `{ext}` is not allowed. "
            f"Permitted: {', '.join(sorted(config.ALLOWED_EXTENSIONS))}"
        )

    safe_name = _sanitise_filename(original_filename)
    if not safe_name:
        safe_name = f"unnamed_{int(time.time())}{ext or '.bin'}"

    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Disk-space check
    _check_disk_space()

    dest = _unique_path(config.UPLOAD_DIR, safe_name)

    # Download via Telegram file API
    tg_file: File = await context.bot.get_file(file_id)
    await tg_file.download_to_drive(dest)

    size = dest.stat().st_size
    logger.info("Uploaded: %s (%s bytes)", dest.name, size)
    return dest, size


async def send_download(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    filename: str,
) -> str:
    """Send a file from the upload directory to *chat_id*.

    Returns a user-facing message string (success or error).
    """
    safe_name = _sanitise_filename(filename)
    path = config.UPLOAD_DIR / safe_name

    if not path.exists() or not path.is_file():
        return (
            f"File `{safe_name}` not found.\n"
            f"Use /list to see available files."
        )

    try:
        with open(path, "rb") as fh:
            await context.bot.send_document(chat_id=chat_id, document=fh)
        logger.info("Downloaded: %s to chat %s", path.name, chat_id)
        return f"Sent `{path.name}`."
    except Exception as exc:
        logger.error("Download failed for %s: %s", path.name, exc)
        return f"Failed to send file: {exc}"


def list_files() -> List[dict]:
    """Return sorted list of file info dicts from the upload directory.

    Each dict has keys: ``name``, ``size``, ``size_human``, ``modified``.
    """
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    entries: List[dict] = []
    for child in sorted(config.UPLOAD_DIR.iterdir()):
        if child.is_file():
            stat = child.stat()
            entries.append(
                {
                    "name": child.name,
                    "size": stat.st_size,
                    "size_human": _human_size(stat.st_size),
                    "modified": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                }
            )
    return entries


def delete_file(filename: str, chat_id: int, user_id: int) -> str:
    """Remove a file from the upload directory.

    Authorisation (admin-only) is expected to be handled *before* calling
    this function — the caller is responsible for that check.
    """
    safe_name = _sanitise_filename(filename)
    path = config.UPLOAD_DIR / safe_name

    if not path.exists() or not path.is_file():
        return f"File `{safe_name}` not found."

    try:
        path.unlink()
        logger.info("Deleted: %s (by user %s, chat %s)", safe_name, user_id, chat_id)
        return f"Deleted `{safe_name}`."
    except OSError as exc:
        logger.error("Delete failed for %s: %s", safe_name, exc)
        return f"Failed to delete `{safe_name}`: {exc}"


# ── Internal ────────────────────────────────────────────────────────────


def _check_disk_space(min_free_mb: int = 500) -> None:
    """Raise ``OSError`` if free disk space is below *min_free_mb*."""
    try:
        usage = shutil.disk_usage(config.UPLOAD_DIR)
        free_mb = usage.free / (1024 * 1024)
        if free_mb < min_free_mb:
            raise OSError(
                f"Low disk space: {free_mb:.0f} MB free "
                f"(minimum {min_free_mb} MB required)."
            )
    except FileNotFoundError:
        pass  # directory doesn't exist yet — will be created later


# ── Extract filename from Telegram message ──────────────────────────────


def extract_file_info(
    document: Optional[Document] = None,
    photo: Optional[List[PhotoSize]] = None,
    video: Optional[Video] = None,
    audio: Optional[Audio] = None,
    voice: Optional[Voice] = None,
) -> Optional[Tuple[str, str, int]]:
    """Extract ``(file_id, filename, file_size)`` from a Telegram message.

    Returns *None* if no supported media is present.
    """
    if document is not None:
        return (
            document.file_id,
            document.file_name or f"document_{int(time.time())}.bin",
            document.file_size or 0,
        )
    if video is not None:
        return (
            video.file_id,
            f"video_{int(time.time())}.mp4",
            video.file_size or 0,
        )
    if audio is not None:
        ext = ".ogg" if audio.mime_type and "ogg" in audio.mime_type else ".mp3"
        return (
            audio.file_id,
            f"audio_{int(time.time())}{ext}",
            audio.file_size or 0,
        )
    if voice is not None:
        return (
            voice.file_id,
            f"voice_{int(time.time())}.ogg",
            voice.file_size or 0,
        )
    if photo:
        # Use the largest photo size
        largest = max(photo, key=lambda p: p.file_size or 0)
        return (
            largest.file_id,
            f"photo_{int(time.time())}.jpg",
            largest.file_size or 0,
        )
    return None
