"""Integration tests for deep operations handlers (Group 8).

Pattern: _is_command_for_me + _is_authorized + complex multi-step with subprocess + file I/O.
Tests: handle_project, handle_clear, handle_deepfix, handle_kodak.
"""
import time
from unittest.mock import MagicMock, patch


class TestProject:
    def test_project_start_restarts_pm2(self, init_state):
        from core.bot_handlers import handle_project
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/project start testproj"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._load_projects", return_value={
                    "testproj": {"path": "/tmp/testproj", "description": "test"}
                }):
                    with patch("subprocess.run") as mock_run:
                        mock_run.return_value.returncode = 0
                        handle_project(bot, msg)
        mock_run.assert_called()
        args = mock_run.call_args[0][0]
        assert args[0] == "pm2"
        assert args[1] == "restart"
        assert "arbos-testproj" in args

    def test_project_list_delegates(self, init_state):
        from core.bot_handlers import handle_project
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/project list"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._load_projects", return_value={}):
                    handle_project(bot, msg)
        bot.send_message.assert_called_once()

    def test_project_start_unknown(self, init_state):
        from core.bot_handlers import handle_project
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/project start nobody"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._load_projects", return_value={}):
                    handle_project(bot, msg)
        args = bot.send_message.call_args[0][1]
        assert "Unknown" in args


class TestClear:
    def test_clear_runs_git_cleanup(self, init_state):
        from core.bot_handlers import handle_clear
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/clear"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value.returncode = 0
                    mock_run.return_value.stdout = "Removed x"
                    handle_clear(bot, msg)
        bot.send_message.assert_called_once()
        args = bot.send_message.call_args[0][1]
        assert "Cleared" in args


class TestDeepfix:
    def test_deepfix_github_issue(self, init_state):
        from core.bot_handlers import handle_deepfix
        bot = MagicMock()
        sent_msg = MagicMock()
        sent_msg.message_id = 10
        bot.send_message.return_value = sent_msg
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/deepfix https://github.com/o/r/issues/42"
        msg.message_id = 10
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._is_github_issue_url", return_value=True):
                    with patch("core.bot_handlers._fetch_github_issue", return_value=("#42 title", None)):
                        with patch("core.bot_handlers.run_agent_streaming", return_value="ok") as mock_run:
                            handle_deepfix(bot, msg)
        time.sleep(0.05)
        bot.send_message.assert_any_call(1, "Project: (current working directory)")
        bot.send_message.assert_any_call(1, "Fetching GitHub issue...")
        bot.edit_message_text.assert_called_with(
            "Fetched. Running deep analysis with full repo context...",
            1, 10,
        )
        call_args = mock_run.call_args
        assert call_args is not None
        prompt = call_args.kwargs.get("prompt") or call_args[0][1]
        assert "#42 title" in prompt

    def test_deepfix_no_args_shows_usage(self, init_state):
        from core.bot_handlers import handle_deepfix
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/deepfix"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._load_projects", return_value={}):
                    handle_deepfix(bot, msg)
        args = bot.send_message.call_args[0][1]
        assert "Usage" in args


class TestKodak:
    def test_kodak_reply_to_photo(self, init_state):
        from core.bot_handlers import handle_kodak
        bot = MagicMock()
        photo = MagicMock()
        photo.file_id = "ph1"
        reply_msg = MagicMock()
        reply_msg.photo = [photo]
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/kodak"
        msg.reply_to_message = reply_msg
        file_info = MagicMock()
        file_info.file_path = "photos/1.jpg"
        bot.get_file.return_value = file_info
        bot.download_file.return_value = b"fake_jpg"
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._codex_photo_audit") as mock_kodak:
                    handle_kodak(bot, msg)
        mock_kodak.assert_called_once()

    def test_kodak_no_args_or_reply(self, init_state):
        from core.bot_handlers import handle_kodak
        bot = MagicMock()
        msg = MagicMock()
        msg.chat.type = "private"
        msg.chat.id = 1
        msg.text = "/kodak"
        msg.reply_to_message = None
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                handle_kodak(bot, msg)
        args = bot.send_message.call_args[0][1]
        assert "Usage" in args
