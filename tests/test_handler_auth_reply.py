"""Integration tests for auth + reply handlers (Group 1).

Pattern: _is_command_for_me + _is_authorized + bot.send_message
No I/O, no subprocess, no state mutation.
"""
from unittest.mock import MagicMock, patch


class TestHelp:
    def test_help_sends_command_list(self, init_state):
        from core.bot_handlers import handle_help
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/help"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                handle_help(bot, msg)
        bot.send_message.assert_called_once()
        assert "/help" in str(bot.send_message.call_args[0][1])

    def test_help_not_authorized(self, init_state):
        from core.bot_handlers import handle_help
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.from_user.id = 99999
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=False):
                handle_help(bot, msg)
        bot.send_message.assert_called_once_with(1, "Unauthorized.")


class TestProjects:
    def test_projects_empty_shows_no_projects(self, init_state):
        from core.bot_handlers import handle_projects
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._load_projects", return_value={}):
                    handle_projects(bot, msg)
        args = bot.send_message.call_args[0][1]
        assert "projects.json" in args


class TestCron:
    def test_cron_calls_check_and_wake(self, init_state):
        from core.bot_handlers import handle_cron
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.loops.check_and_wake", return_value=True):
                    handle_cron(bot, msg)
        assert "seeded" in str(bot.send_message.call_args[0][1]).lower()


class TestExperts:
    def test_experts_delegates_to_panel(self, init_state):
        from core.bot_handlers import handle_experts
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._show_experts_panel") as mock_panel:
                    handle_experts(bot, msg)
        mock_panel.assert_called_once_with(bot, msg.chat.id)
