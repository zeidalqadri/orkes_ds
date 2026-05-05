"""Integration tests for agent lifecycle handlers (Group 3).

Pattern: _is_command_for_me + _is_authorized + mutate GOAL_FILE + _kill_child_procs / _loop_manager.
Tests: handle_cancel, handle_stop, handle_goal, handle_restart, handle_update.
"""
from unittest.mock import MagicMock, patch

from core import state as core_state


class TestStop:
    def test_stop_clears_default_goal(self, init_state):
        core_state.GOAL_FILE.write_text("active task")
        from core.bot_handlers import handle_stop
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/stop"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                handle_stop(bot, msg)
        assert core_state.GOAL_FILE.read_text().strip() == ""
        bot.send_message.assert_called_once()

    def test_stop_expert(self, init_state):
        from core.bot_handlers import handle_stop
        core_state._loop_manager = MagicMock()
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/stop builder"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._get_expert", return_value={"active": True}):
                    handle_stop(bot, msg)
        core_state._loop_manager.stop_expert.assert_called_once_with("builder")


class TestGoal:
    def test_goal_sets_default_goal(self, init_state):
        from core.bot_handlers import handle_goal
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/goal do the thing"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                handle_goal(bot, msg)
        assert "do the thing" in core_state.GOAL_FILE.read_text()
        bot.send_message.assert_called_once()

    def test_goal_sets_expert_goal(self, init_state):
        from core.bot_handlers import handle_goal
        core_state._loop_manager = MagicMock()
        core_state._loop_manager.is_running.return_value = False
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/goal builder deploy to prod"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._get_expert", return_value={"active": True}):
                    handle_goal(bot, msg)
        core_state._loop_manager.start_expert.assert_called_once_with("builder")
        core_state._loop_manager.wake_expert.assert_called_once_with("builder")
        bot.send_message.assert_called_once()

    def test_goal_no_args_shows_usage(self, init_state):
        from core.bot_handlers import handle_goal
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/goal"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                handle_goal(bot, msg)
        args = bot.send_message.call_args[0][1]
        assert "Usage" in args


class TestCancel:
    def test_cancel_kills_procs_and_clears(self, init_state):
        core_state.GOAL_FILE.write_text("active goal")
        from core.bot_handlers import handle_cancel
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/cancel"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._kill_child_procs") as mock_kill:
                    handle_cancel(bot, msg)
        mock_kill.assert_called_once()
        assert core_state.GOAL_FILE.read_text().strip() == ""
        bot.send_message.assert_called_once()


class TestRestart:
    def test_restart_touches_flag(self, init_state):
        from core.bot_handlers import handle_restart
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/restart"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._kill_child_procs") as mock_kill:
                    handle_restart(bot, msg)
        mock_kill.assert_called_once()
        assert core_state.RESTART_FLAG.exists()
        bot.send_message.assert_called_once()
        core_state.RESTART_FLAG.unlink(missing_ok=True)


class TestUpdate:
    def test_update_pulls_and_restarts(self, init_state):
        from core.bot_handlers import handle_update
        bot = MagicMock()
        sent_msg = MagicMock()
        sent_msg.message_id = 10
        bot.send_message.return_value = sent_msg
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.message_id = 10
        msg.text = "/update"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value.returncode = 0
                    mock_run.return_value.stdout = "Already up to date."
                    mock_run.return_value.stderr = ""
                    with patch("core.bot_handlers._kill_child_procs") as mock_kill:
                        handle_update(bot, msg)
        mock_kill.assert_called_once()
        mock_run.assert_called()
        args = mock_run.call_args[0][0]
        assert args[0] == "git"
        assert args[1] == "pull"
        assert core_state.RESTART_FLAG.exists()
        core_state.RESTART_FLAG.unlink(missing_ok=True)
