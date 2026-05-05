"""Integration tests for expert management handlers (Group 6).

Pattern: _is_command_for_me + _is_authorized + ExpertContext + _loop_manager + CRUD file I/O.
Tests: handle_expert_cmd, handle_expert_callback.
"""
from unittest.mock import MagicMock, patch

from core import state as core_state


class TestExpertCmd:
    def test_expert_add_creates_expert(self, init_state):
        core_state._loop_manager = MagicMock()
        from core.bot_handlers import handle_expert_cmd
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/expert add builder build things fast"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._get_expert", return_value=None):
                    with patch("core.bot_handlers._set_expert") as mock_set:
                        handle_expert_cmd(bot, msg)
        mock_set.assert_called_once()
        args = bot.send_message.call_args[0][1]
        assert "created" in args.lower()

    def test_expert_remove(self, init_state):
        core_state._loop_manager = MagicMock()
        from core.bot_handlers import handle_expert_cmd
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/expert remove builder"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._get_expert", return_value={"active": True}):
                    with patch("core.bot_handlers._remove_expert", return_value=True):
                        handle_expert_cmd(bot, msg)
        core_state._loop_manager.stop_expert.assert_called_once_with("builder")
        bot.send_message.assert_called_once()

    def test_expert_start(self, init_state):
        core_state._loop_manager = MagicMock()
        core_state._loop_manager.start_expert.return_value = True
        from core.bot_handlers import handle_expert_cmd
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/expert start builder"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._get_expert", return_value={"active": True}):
                    handle_expert_cmd(bot, msg)
        core_state._loop_manager.start_expert.assert_called_once_with("builder")
        bot.send_message.assert_called_once()

    def test_expert_goal_sets_goal_file(self, init_state):
        core_state._loop_manager = MagicMock()
        core_state._loop_manager.is_running.return_value = False
        from core.bot_handlers import handle_expert_cmd
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/expert goal builder deploy to prod"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._get_expert", return_value={"active": True}):
                    handle_expert_cmd(bot, msg)
        core_state._loop_manager.start_expert.assert_called_once_with("builder")
        core_state._loop_manager.wake_expert.assert_called_once_with("builder")
        bot.send_message.assert_called_once()


class TestExpertCallback:
    def test_callback_start(self, init_state):
        core_state._loop_manager = MagicMock()
        core_state._loop_manager.is_running.return_value = False
        from core.bot_handlers import handle_expert_callback
        bot = MagicMock()
        call = MagicMock()
        call.from_user = MagicMock()
        call.from_user.id = 12345
        call.id = "cb1"
        call.data = "exp:start:builder"
        call.message = MagicMock()
        call.message.chat.id = 1
        call.message.message_id = 10
        with patch("core.bot_handlers._is_owner", return_value=True):
            with patch("core.bot_handlers._get_expert", return_value={"active": True}):
                # Create goal file so the handler doesn't bail with "no goal"
                from core.context import ExpertContext
                ec = ExpertContext("builder")
                ec.ensure_dirs()
                ec.goal_file.write_text("deploy")
                handle_expert_callback(bot, call)
        core_state._loop_manager.start_expert.assert_called_once_with("builder")

    def test_callback_stop(self, init_state):
        core_state._loop_manager = MagicMock()
        from core.bot_handlers import handle_expert_callback
        bot = MagicMock()
        call = MagicMock()
        call.from_user = MagicMock()
        call.from_user.id = 12345
        call.id = "cb2"
        call.data = "exp:stop:builder"
        call.message = MagicMock()
        call.message.chat.id = 1
        call.message.message_id = 10
        with patch("core.bot_handlers._is_owner", return_value=True):
            handle_expert_callback(bot, call)
        core_state._loop_manager.stop_expert.assert_called_once_with("builder")
