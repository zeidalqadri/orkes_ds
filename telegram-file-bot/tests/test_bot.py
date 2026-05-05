"""
Functional test suite for Telegram File Bot.

Run::

    cd telegram-file-bot
    python -m pytest tests/ -v

Or with a real bot token::

    BOT_TOKEN="..." python tests/test_bot.py --live
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Ensure the package root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

# ── Patch config before importing application code ───────────────────

import config

config.BOT_TOKEN = "test:token"
config.ALLOWED_USERS = [111, 222]
config.ADMIN_IDS = [111]
config.UPLOAD_DIR = Path(tempfile.mkdtemp(prefix="bot_test_"))
config.LOG_DIR = Path(tempfile.mkdtemp(prefix="bot_test_log_"))
config.WHITELIST_FILE = config.LOG_DIR / "whitelist.json"
config.MAX_FILE_SIZE = 50 * 1024 * 1024

# Re-initialise auth with patched config
from auth import AuthManager, auth_manager
auth_manager.__init__()

from file_handler import (
    delete_file,
    extract_file_info,
    _sanitise_filename,
    _unique_path,
    _human_size,
    list_files,
)


# ── Tests ────────────────────────────────────────────────────────────


class TestFilenameSanitisation:
    def test_removes_path_traversal(self):
        assert _sanitise_filename("../../etc/passwd") == "passwd"

    def test_removes_backslash_paths(self):
        assert _sanitise_filename("..\\windows\\system32\\evil.exe") == "evil.exe"

    def test_removes_null_bytes(self):
        assert _sanitise_filename("good.txt\0evil.exe") == "good.txt_evil.exe"

    def test_basename_only(self):
        assert _sanitise_filename("/var/bot_uploads/foo/bar.pdf") == "bar.pdf"

    def test_empty_falls_back(self):
        name = _sanitise_filename(".")
        assert name.startswith("unnamed_")

    def test_keeps_good_name(self):
        assert _sanitise_filename("report_2024.pdf") == "report_2024.pdf"


class TestHumanSize:
    def test_bytes(self):
        assert _human_size(500) == "500 B"

    def test_kilobytes(self):
        result = _human_size(2048)
        assert "KB" in result

    def test_megabytes(self):
        result = _human_size(5 * 1024 * 1024)
        assert "MB" in result

    def test_gigabytes(self):
        result = _human_size(3 * 1024 * 1024 * 1024)
        assert "GB" in result


class TestUniquePath:
    def test_first_use(self):
        d = Path(tempfile.mkdtemp())
        p = _unique_path(d, "foo.txt")
        assert p == d / "foo.txt"

    def test_collision(self):
        d = Path(tempfile.mkdtemp())
        (d / "foo.txt").write_text("a")
        p = _unique_path(d, "foo.txt")
        assert p.name.startswith("foo_") and p.suffix == ".txt"


class TestAuth:
    def test_admin_is_authorised(self):
        assert auth_manager.is_authorised(111)

    def test_whitelisted_user_is_authorised(self):
        assert auth_manager.is_authorised(222)

    def test_unknown_user_is_not_authorised(self):
        assert not auth_manager.is_authorised(999)

    def test_admin_check(self):
        assert auth_manager.is_admin(111)
        assert not auth_manager.is_admin(222)

    def test_allow(self):
        auth_manager.allow(333, 111)
        assert auth_manager.is_authorised(333)

    def test_allow_non_admin(self):
        result = auth_manager.allow(444, 222)
        assert "denied" in result.lower()
        assert not auth_manager.is_authorised(444)

    def test_revoke(self):
        auth_manager.allow(555, 111)
        assert auth_manager.is_authorised(555)
        auth_manager.revoke(555, 111)
        assert not auth_manager.is_authorised(555)


class TestListFiles:
    def test_empty_directory(self):
        assert list_files() == []

    def test_lists_files(self):
        (config.UPLOAD_DIR / "test.txt").write_text("hello")
        files = list_files()
        names = [f["name"] for f in files]
        assert "test.txt" in names


class TestDelete:
    def test_delete_existing(self):
        (config.UPLOAD_DIR / "delete_me.txt").write_text("bye")
        result = delete_file("delete_me.txt", chat_id=1, user_id=111)
        assert "Deleted" in result
        assert not (config.UPLOAD_DIR / "delete_me.txt").exists()

    def test_delete_nonexistent(self):
        result = delete_file("nope.txt", chat_id=1, user_id=111)
        assert "not found" in result


class TestExtractFileInfo:
    """Uses real Telegram object shapes — checks dict-like access patterns."""

    def test_no_media_returns_none(self):
        assert extract_file_info() is None

    def test_document(self):
        class FakeDocument:
            file_id = "doc123"
            file_name = "report.pdf"
            file_size = 42_000
        info = extract_file_info(document=FakeDocument())
        assert info is not None
        fid, name, size = info
        assert fid == "doc123"
        assert name == "report.pdf"
        assert size == 42_000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
