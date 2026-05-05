"""Tests for permauth.py — logging formatter and mood icons."""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from permauth import PermauthEmojiFormatter


class TestPermauthEmojiFormatter:
    def setup_method(self):
        self.fmt = PermauthEmojiFormatter(fmt="%(message)s", datefmt="%H:%M:%S")

    def _make_record(self, msg, level=logging.INFO):
        return logging.LogRecord("test", level, "", 0, msg, (), None)

    def test_debug_adds_cookie(self):
        rec = self._make_record("debug msg", logging.DEBUG)
        out = self.fmt.format(rec)
        assert "\U0001f36a" in out  # 🍪

    def test_info_adds_smiley_cookie(self):
        rec = self._make_record("info msg", logging.INFO)
        out = self.fmt.format(rec)
        assert "\U0001f60a" in out  # 😊
        assert "\U0001f36a" in out  # 🍪

    def test_warning_adds_worried_cookie(self):
        rec = self._make_record("warn msg", logging.WARNING)
        out = self.fmt.format(rec)
        assert "\U0001f61f" in out  # 😟
        assert "\U0001f36a" in out  # 🍪

    def test_error_adds_dead_cookie(self):
        rec = self._make_record("err msg", logging.ERROR)
        out = self.fmt.format(rec)
        assert "\U0001f480" in out  # 💀
        assert "\U0001f36a" in out  # 🍪

    def test_critical_adds_dead_cookie(self):
        rec = self._make_record("crit msg", logging.CRITICAL)
        out = self.fmt.format(rec)
        assert "\U0001f480" in out  # 💀

    def test_preserves_original_message(self):
        rec = self._make_record("original text", logging.INFO)
        self.fmt.format(rec)
        assert rec.msg == "original text"

    def test_includes_emoji_before_message(self):
        rec = self._make_record("hello", logging.WARNING)
        out = self.fmt.format(rec)
        assert out.startswith("\U0001f61f\U0001f36a")  # 😟🍪 prefix

    def test_preserves_record_levelname(self):
        rec = self._make_record("level test", logging.WARNING)
        out = self.fmt.format(rec)
        assert "WARNING" not in out  # custom format with %(message)s only
