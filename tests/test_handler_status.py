"""Integration tests for status display handlers (Group 4).

Pattern: _is_command_for_me + _is_authorized + multi-state read + formatted text output.
"""
from unittest.mock import MagicMock, patch

from core import state as core_state


class TestStatus:
    def test_status_shows_goal(self, init_state):
        core_state.GOAL_FILE.write_text("build feature X")
        from core.bot_handlers import handle_status
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                handle_status(bot, msg)
        args = bot.send_message.call_args[0][1]
        assert "build feature X" in args

    def test_status_shows_experts(self, init_state):
        core_state._loop_manager = MagicMock()
        core_state._loop_manager.is_running.return_value = False
        from core.bot_handlers import handle_status
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                handle_status(bot, msg)
        args = bot.send_message.call_args[0][1]
        assert "Default Loop" in args

class TestPeerStatus:
    def test_peer_status_queries_pm2(self, init_state):
        core_state.MY_PM2_NAME = "arbos-orkes_ds"
        from core.bot_handlers import handle_peer_status
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        sample_peers = [
            {"name": "arbos-orkes_ds", "status": "online", "pid": 123, "uptime": 0},
        ]
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._pm2_peer_list", return_value=sample_peers):
                    handle_peer_status(bot, msg)
        args = bot.send_message.call_args[0][1]
        assert "arbos-orkes_ds" in args

    def test_peer_status_no_peers(self, init_state):
        from core.bot_handlers import handle_peer_status
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._pm2_peer_list", return_value=[]):
                    handle_peer_status(bot, msg)
        args = bot.send_message.call_args[0][1]
        assert "No arbos" in args
