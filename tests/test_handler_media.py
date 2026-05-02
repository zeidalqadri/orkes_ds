"""Integration tests for content ingestion handlers (Group 5)."""
from unittest.mock import MagicMock, patch

from core import state as core_state


def _ensure_uploads():
    core_state.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


class TestVoice:
    def test_voice_downloads_and_transcribes(self, init_state):
        _ensure_uploads()
        from core.bot_handlers import handle_voice
        bot = MagicMock()
        bot.get_file.return_value = MagicMock(file_path="voice/1.oga")
        bot.download_file.return_value = b"audio data"
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.message_id = 10
        msg.voice = MagicMock(file_id="v1")
        msg.audio = None
        msg.caption = None
        with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.loops.transcribe_voice", return_value="hello world"):
                    with patch("core.runner.run_agent_streaming", return_value="ok"):
                        with patch("core.prompt.log_chat"):
                            with patch("threading.Thread") as mt:
                                handle_voice(bot, msg)
        mt.assert_called_once()

    def test_voice_transcription_unavailable(self, init_state):
        from core.bot_handlers import handle_voice
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.voice = MagicMock(file_id="v1")
        msg.audio = None
        msg.caption = None
        with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                import builtins
                real_import = builtins.__import__
                def blocking_import(name, *args, **kwargs):
                    if name == "core.loops" or "core.loops.transcribe_voice" in name:
                        raise ImportError("No transcribe_voice")
                    return real_import(name, *args, **kwargs)
                with patch("builtins.__import__", side_effect=blocking_import):
                    handle_voice(bot, msg)
        assert "not supported" in bot.send_message.call_args[0][1].lower()


class TestDocument:
    def test_document_text_file_processed(self, init_state):
        _ensure_uploads()
        from core.bot_handlers import handle_document
        bot = MagicMock()
        bot.get_file.return_value = MagicMock(file_path="docs/config.json")
        bot.download_file.return_value = b'{"key":"value"}'
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.message_id = 10
        msg.document = MagicMock(file_name="config.json", file_unique_id="abc", file_size=100, mime_type="application/json")
        msg.caption = None
        with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.runner.run_agent_streaming", return_value="ok"):
                    with patch("core.prompt.log_chat"):
                        with patch("threading.Thread") as mt:
                            handle_document(bot, msg)
        bot.send_message.assert_called()
        mt.assert_called_once()

    def test_document_too_large(self, init_state):
        from core.bot_handlers import handle_document
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.document = MagicMock(file_name="big.bin", file_unique_id="abc", file_size=30*1024*1024, mime_type="application/octet-stream")
        msg.caption = None
        with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                handle_document(bot, msg)
        assert "too large" in bot.send_message.call_args[0][1].lower()


class TestPhoto:
    def test_photo_kodak_keyword_detected(self, init_state):
        _ensure_uploads()
        from core.bot_handlers import handle_photo
        bot = MagicMock()
        bot.get_file.return_value = MagicMock(file_path="photos/1.jpg")
        bot.download_file.return_value = b"fake"
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.message_id = 10
        msg.photo = [MagicMock(file_id="ph1")]
        msg.caption = "kodak this button"
        with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._codex_photo_audit") as mk:
                    handle_photo(bot, msg)
        mk.assert_called_once()

    def test_photo_normal_processed(self, init_state):
        _ensure_uploads()
        from core.bot_handlers import handle_photo
        bot = MagicMock()
        bot.get_file.return_value = MagicMock(file_path="photos/1.jpg")
        bot.download_file.return_value = b"fake"
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.message_id = 10
        msg.photo = [MagicMock(file_id="ph1")]
        msg.caption = "look at this"
        with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.runner.run_agent_streaming", return_value="ok"):
                    with patch("core.prompt.log_chat"):
                        with patch("threading.Thread") as mt:
                            handle_photo(bot, msg)
        mt.assert_called_once()
