"""Tests for ernie.alert — Telegram alerting."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ernie.alert import _bot_token, _load_chat_id, send_alert


class TestLoadChatId:
    def test_no_file(self, tmp_path):
        with patch("ernie.alert.CHAT_ID_FILE", tmp_path / "nonexistent.txt"):
            assert _load_chat_id() is None

    def test_empty_file(self, tmp_path):
        p = tmp_path / "chat_id.txt"
        p.write_text("")
        with patch("ernie.alert.CHAT_ID_FILE", p):
            assert _load_chat_id() is None

    def test_valid(self, tmp_path):
        p = tmp_path / "chat_id.txt"
        p.write_text("123456")
        with patch("ernie.alert.CHAT_ID_FILE", p):
            assert _load_chat_id() == "123456"

    def test_with_whitespace(self, tmp_path):
        p = tmp_path / "chat_id.txt"
        p.write_text("  123456  \n")
        with patch("ernie.alert.CHAT_ID_FILE", p):
            assert _load_chat_id() == "123456"


class TestBotToken:
    @patch.dict("os.environ", {"TAU_BOT_TOKEN": "tok123"}, clear=True)
    def test_tau_token(self):
        assert _bot_token() == "tok123"

    @patch.dict("os.environ", {"BOT_TOKEN": "tok456"}, clear=True)
    def test_bot_token(self):
        assert _bot_token() == "tok456"

    @patch.dict("os.environ", {}, clear=True)
    def test_no_token(self):
        assert _bot_token() is None

    @patch.dict("os.environ", {"TAU_BOT_TOKEN": "tau", "BOT_TOKEN": "bot"}, clear=True)
    def test_tau_preferred(self):
        assert _bot_token() == "tau"


class TestSendAlert:
    @patch("ernie.alert._load_chat_id", return_value="123456")
    @patch("ernie.alert._bot_token", return_value="tok123")
    @patch("ernie.alert.requests.post")
    def test_sends_message(self, mock_post, mock_token, mock_chat):
        mock_post.return_value.status_code = 200
        result = send_alert("Test message")
        assert result is True
        mock_post.assert_called_once()
        args = mock_post.call_args[0]
        assert "tok123" in args[0]
        kwargs = mock_post.call_args[1]
        assert kwargs["json"]["chat_id"] == "123456"
        assert "Test message" in kwargs["json"]["text"]
        assert kwargs["timeout"] == 15

    @patch("ernie.alert._load_chat_id", return_value="123456")
    @patch("ernie.alert._bot_token", return_value="tok123")
    @patch("ernie.alert.requests.post")
    def test_api_failure(self, mock_post, mock_token, mock_chat):
        mock_post.return_value.status_code = 403
        result = send_alert("Fail")
        assert result is False

    @patch("ernie.alert._load_chat_id", return_value=None)
    @patch("ernie.alert._bot_token", return_value="tok123")
    def test_no_chat_id(self, mock_token, mock_chat):
        assert send_alert("noop") is False

    @patch("ernie.alert._load_chat_id", return_value="123456")
    @patch("ernie.alert._bot_token", return_value=None)
    def test_no_token(self, mock_token, mock_chat):
        assert send_alert("noop") is False

    @patch("ernie.alert._load_chat_id", return_value="123456")
    @patch("ernie.alert._bot_token", return_value="tok123")
    @patch("ernie.alert.requests.post", side_effect=Exception("Network error"))
    def test_exception_handling(self, mock_post, mock_token, mock_chat):
        assert send_alert("crash") is False
