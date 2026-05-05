"""Integration tests for peer ops handlers (Group 7).

Pattern: _is_command_for_me + _is_authorized + _pm2_peer_list + subprocess.run(["pm2", ...]).
"""
from unittest.mock import MagicMock, patch

from core import state as core_state


class TestPeerWake:
    def test_peer_wake_restarts_pm2(self, init_state):
        core_state.MY_PM2_NAME = "arbos-orkes_ds"
        from core.bot_handlers import handle_peer_wake
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/wake arbos-other"
        sample_peers = [
            {"name": "arbos-orkes_ds", "status": "online"},
            {"name": "arbos-other", "status": "stopped"},
        ]
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._pm2_peer_list", return_value=sample_peers):
                    with patch("subprocess.run") as mock_run:
                        mock_run.return_value.returncode = 0
                        handle_peer_wake(bot, msg)
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0][1] == "restart"

    def test_peer_wake_unknown_peer(self, init_state):
        from core.bot_handlers import handle_peer_wake
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/wake arbos-nobody"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._pm2_peer_list", return_value=[]):
                    handle_peer_wake(bot, msg)
        args = bot.send_message.call_args[0][1]
        assert "Unknown" in args

    def test_peer_wake_no_args(self, init_state):
        from core.bot_handlers import handle_peer_wake
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/wake"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                handle_peer_wake(bot, msg)
        args = bot.send_message.call_args[0][1]
        assert "Usage" in args


class TestPeerKill:
    def test_peer_kill_stops_pm2(self, init_state):
        core_state.MY_PM2_NAME = "arbos-orkes_ds"
        from core.bot_handlers import handle_peer_kill
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/kill arbos-other"
        sample_peers = [
            {"name": "arbos-orkes_ds", "status": "online"},
            {"name": "arbos-other", "status": "online"},
        ]
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._pm2_peer_list", return_value=sample_peers):
                    with patch("subprocess.run") as mock_run:
                        mock_run.return_value.returncode = 0
                        handle_peer_kill(bot, msg)
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0][1] == "stop"

    def test_peer_kill_cannot_kill_self(self, init_state):
        core_state.MY_PM2_NAME = "arbos-orkes_ds"
        from core.bot_handlers import handle_peer_kill
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/kill arbos-orkes_ds"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                handle_peer_kill(bot, msg)
        args = bot.send_message.call_args[0][1]
        assert "Cannot kill myself" in args
