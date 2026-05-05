"""Integration tests for handle_message — exercises the full catch-all message flow.

Unlike the unit tests in test_bot_handlers.py (which mock every internal function),
these tests exercise the real _is_authorized, _route_message, _build_operator_prompt,
etc. with only external deps (opencode, openai, network) mocked.

Goal: catch regressions like the 17-missing-handlers fiasco where the bot silently
failed every message without the test suite noticing.
"""
from unittest.mock import MagicMock, patch

from core import state as core_state


def make_msg(chat_type="private", text="hello", from_user_id=12345, msg_id=1):
    """Factory for a telegram message mock."""
    msg = MagicMock()
    msg.chat.type = chat_type
    msg.chat.id = 1
    msg.text = text
    msg.from_user.id = from_user_id
    msg.message_id = msg_id
    msg.reply_to_message = None
    return msg


class TestHandleMessageIntegration:
    """Behavior-driven integration tests for the catch-all message handler.

    These tests verify what the operator actually sees when they message the bot,
    not just that internal calls were made. They use real state setup (init_state
    fixture) and mock only the LLM boundary.
    """

    def test_owner_text_triggers_operator_prompt(self, init_state, monkeypatch):
        """Owner sends text in private chat → operator prompt built and worker spawned."""
        monkeypatch.setenv("TELEGRAM_OWNER_ID", "12345")
        monkeypatch.setenv("BOT_USERNAME", "test_bot")
        core_state.WORKING_DIR.mkdir(parents=True, exist_ok=True)
        core_state.CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
        core_state.GOAL_FILE.write_text("test goal")
        core_state.STATE_FILE.write_text("# Idle")
        core_state.CHAT_ID_FILE = core_state.WORKING_DIR / "chat_id.txt"
        core_state.CHATLOG_DIR.mkdir(parents=True, exist_ok=True)
        core_state._loop_manager = MagicMock()

        bot = MagicMock()
        msg = make_msg(chat_type="private", text="what's the status?")
        msg.from_user.id = 12345

        with patch("core.bot_handlers.run_agent_streaming", return_value="ok"):
            with patch("core.bot_handlers.log_chat"):
                with patch("threading.Thread") as mock_thread_class:
                    from core.bot_handlers import handle_message
                    handle_message(bot, msg)

        # Must set the handling flag
        assert core_state.handling_message.is_set()

        # Must spawn a worker thread
        mock_thread_class.assert_called_once()

    def test_handling_message_cleared_after_worker_completes(self, init_state, monkeypatch):
        """After the worker thread finishes, handling_message must be cleared."""
        monkeypatch.setenv("TELEGRAM_OWNER_ID", "12345")
        core_state.WORKING_DIR.mkdir(parents=True, exist_ok=True)
        core_state.CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
        core_state.GOAL_FILE.write_text("test goal")
        core_state.STATE_FILE.write_text("# Idle")
        core_state.CHAT_ID_FILE = core_state.WORKING_DIR / "chat_id.txt"
        core_state.CHATLOG_DIR.mkdir(parents=True, exist_ok=True)
        core_state._loop_manager = MagicMock()

        bot = MagicMock()
        msg = make_msg(chat_type="private", text="hello")
        msg.from_user.id = 12345

        captured_run = []

        def fake_run_worker(bot, prompt, chat_id, **kw):
            captured_run.append(1)
            return "response text"

        with patch("core.bot_handlers.run_agent_streaming", side_effect=fake_run_worker):
            with patch("core.bot_handlers.log_chat"):
                from core.bot_handlers import handle_message
                handle_message(bot, msg)

        # Wait for daemon thread to finish
        import time
        deadline = time.monotonic() + 3.0
        while not captured_run and time.monotonic() < deadline:
            time.sleep(0.05)

        assert captured_run, "Worker thread never ran"
        # handling_message should be cleared by the worker's finally block
        assert not core_state.handling_message.is_set(), "handling_message was not cleared after worker"

    def test_reply_to_set_on_operator_response(self, init_state, monkeypatch):
        """Operator message → agent response is a reply to the original message."""
        monkeypatch.setenv("TELEGRAM_OWNER_ID", "12345")
        core_state.WORKING_DIR.mkdir(parents=True, exist_ok=True)
        core_state.CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
        core_state.GOAL_FILE.write_text("test goal")
        core_state.STATE_FILE.write_text("# Idle")
        core_state.CHAT_ID_FILE = core_state.WORKING_DIR / "chat_id.txt"
        core_state.CHATLOG_DIR.mkdir(parents=True, exist_ok=True)
        core_state._loop_manager = MagicMock()

        bot = MagicMock()
        msg = make_msg(chat_type="private", text="status", msg_id=42)
        msg.from_user.id = 12345

        run_kwargs = {}

        def capture_kwargs(bot, prompt, chat_id, **kw):
            nonlocal run_kwargs
            run_kwargs = kw
            return "ok"

        with patch("core.bot_handlers.run_agent_streaming", side_effect=capture_kwargs):
            with patch("core.bot_handlers.log_chat"):
                from core.bot_handlers import handle_message
                handle_message(bot, msg)

        import time
        deadline = time.monotonic() + 3.0
        while not run_kwargs and time.monotonic() < deadline:
            time.sleep(0.05)

        assert run_kwargs.get("reply_to_message_id") == 42

    def test_unauthorized_user_gets_rejected(self, init_state, monkeypatch):
        """Non-owner sending a private message should be rejected."""
        monkeypatch.setenv("TELEGRAM_OWNER_ID", "99999")
        core_state._loop_manager = MagicMock()

        bot = MagicMock()
        msg = make_msg(chat_type="private", text="spam", from_user_id=12345)

        from core.bot_handlers import handle_message
        handle_message(bot, msg)

        bot.send_message.assert_called_with(1, "Unauthorized.")

    def test_handler_registration_is_complete(self):
        """register_handlers must reference only functions that exist in the module."""
        from core.bot_handlers import register_handlers
        fn = register_handlers
        names = {n for n in fn.__code__.co_names if n.startswith("handle_")}

        import core.bot_handlers as bh
        missing = [n for n in sorted(names) if not callable(getattr(bh, n, None))]
        assert not missing, (
            "Handler functions referenced in register_handlers() but not defined:\n  "
            + "\n  ".join(missing) + "\n\n"
            "This is the exact bug that made the bot silently unresponsive. "
            "Add the missing function implementations to bot_handlers.py."
        )
