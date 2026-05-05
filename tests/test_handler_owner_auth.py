"""Integration tests for owner-auth handlers (Group 2).

Pattern: _is_command_for_me + _is_owner + enrollment/group registration.
"""
from unittest.mock import MagicMock, patch


class TestStart:
    def test_start_enrolls_first_owner(self, init_state, monkeypatch):
        monkeypatch.delenv("TELEGRAM_OWNER_ID", raising=False)
        from core.bot_handlers import handle_start
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.from_user = MagicMock()
        msg.from_user.id = 42
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            handle_start(bot, msg)
        args = bot.send_message.call_args[0][1]
        assert "goal" in args.lower()

    def test_start_rejects_wrong_owner(self, init_state, monkeypatch):
        monkeypatch.setenv("TELEGRAM_OWNER_ID", "12345")
        from core.bot_handlers import handle_start
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.from_user = MagicMock()
        msg.from_user.id = 99999
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            handle_start(bot, msg)
        bot.send_message.assert_called_with(1, "Unauthorized.")


class TestGroup:
    def test_group_register_persists(self, init_state):
        from core.bot_handlers import handle_group
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "group"
        msg.chat.id = -100123
        msg.text = "/group register"
        msg.from_user = MagicMock()
        msg.from_user.id = 12345
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_owner", return_value=True):
                handle_group(bot, msg)
        bot.send_message.assert_called_once()
        assert "registered" in str(bot.send_message.call_args[0][1])

    def test_group_unregister_persists(self, init_state):
        from core.bot_handlers import handle_group
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "group"
        msg.chat.id = -100123
        msg.text = "/group unregister"
        msg.from_user = MagicMock()
        msg.from_user.id = 12345
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_owner", return_value=True):
                handle_group(bot, msg)
        bot.send_message.assert_called_once()
        assert "unregistered" in str(bot.send_message.call_args[0][1])

    def test_group_not_in_group_chat(self, init_state):
        from core.bot_handlers import handle_group
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/group register"
        msg.from_user = MagicMock()
        msg.from_user.id = 12345
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_owner", return_value=True):
                handle_group(bot, msg)
        args = bot.send_message.call_args[0][1]
        assert "only works in group" in args.lower()
