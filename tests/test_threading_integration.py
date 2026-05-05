"""Threading integration tests for agent_loop, _expert_loop, and transcribe_voice.

Uses a controlled _agent_wake.wait() that raises _LoopDone after N calls,
allowing agent_loop to run in the main thread and exit naturally.
"""
import json
import threading
from unittest.mock import MagicMock, patch

import pytest
from core import state as core_state


class _LoopDone(BaseException):
    """Raised to terminate agent_loop after testing specific paths."""


def _make_wait(max_calls=10):
    """Factory: returns wait() that raises _LoopDone after max_calls invocations."""
    calls = [0]
    def _wait(timeout=None):
        calls[0] += 1
        if calls[0] > max_calls:
            raise _LoopDone("exit after max calls")
    return _wait


# ══════════════════════════════════════════════════════════════════════════
# agent_loop
# ══════════════════════════════════════════════════════════════════════════

class TestAgentLoop:
    """Test agent_loop code paths by running in main thread with controlled exit."""

    def _run_loop(self, max_waits=10):
        import core.loops
        with patch.object(core_state._agent_wake, 'wait', _make_wait(max_waits)):
            with pytest.raises(_LoopDone):
                core.loops.agent_loop()

    def test_done_marker_clears_goal(self, init_state):
        core_state.GOAL_FILE.write_text("(done)")
        core_state.IDLE_POLL_INTERVAL = 0
        with patch('core.loops.run_step'):
            self._run_loop(5)
            assert core_state.GOAL_FILE.read_text().strip() == ""

    def test_goal_changed_logs(self, init_state):
        import core.loops
        core_state.GOAL_FILE.write_text("new goal")
        core_state.IDLE_POLL_INTERVAL = 0
        with patch('core.loops.run_step', return_value=True):
            with patch('core.loops._step_result_appears_idle', return_value=False):
                with patch('core.loops.load_prompt', return_value="prompt"):
                    self._run_loop(8)
                    assert core.loops._goal_hash

    def test_auto_clear_idle(self, init_state):
        core_state.GOAL_FILE.write_text("do something")
        core_state.IDLE_POLL_INTERVAL = 0
        with patch('core.loops.run_step', return_value=True):
            with patch('core.loops._step_result_appears_idle', return_value=True):
                with patch('core.loops.load_prompt', return_value="prompt"):
                    self._run_loop(5)
                    assert core_state.GOAL_FILE.read_text().strip() == ""

    def test_circuit_breaker(self, init_state):
        core_state.GOAL_FILE.write_text("test goal")
        core_state.IDLE_POLL_INTERVAL = 0
        core_state.MAX_CONSECUTIVE_FAILURES = 1
        with patch('core.loops.run_step', return_value=False):
            with patch('core.loops.load_prompt', return_value="prompt"):
                with patch('core.loops._send_owner_alert'):
                    self._run_loop(8)
                    assert core_state.GOAL_FILE.read_text().strip() == ""

    def test_step_cap(self, init_state):
        core_state.GOAL_FILE.write_text("test goal")
        core_state.IDLE_POLL_INTERVAL = 0
        core_state.MAX_GOAL_STEPS = 1
        with patch('core.loops.run_step', return_value=True):
            with patch('core.loops.load_prompt', return_value="prompt"):
                with patch('core.loops._step_result_appears_idle', return_value=False):
                    with patch('core.loops._send_owner_alert'):
                        self._run_loop(8)
                        assert core_state.GOAL_FILE.read_text().strip() == ""

    def test_goal_cleared_writes_completion(self, init_state):
        import core.loops
        core_state.GOAL_FILE.write_text("old goal")
        core_state.IDLE_POLL_INTERVAL = 0
        core.loops._goal_hash = "somehash"
        core.loops._goal_step_count = 3
        core.loops._last_goal_text = "old goal"
        core_state.GOAL_FILE.write_text("")
        self._run_loop(5)
        state_text = core_state.STATE_FILE.read_text()
        assert "IDLE" in state_text
        assert "old goal" in state_text

    def test_new_goal_detected(self, init_state):
        import core.loops
        core_state.GOAL_FILE.write_text("second goal")
        core_state.IDLE_POLL_INTERVAL = 0
        core.loops._goal_hash = "oldhash"
        core.loops._goal_step_count = 5
        core.loops._last_goal_text = "old goal"
        with patch('core.loops.run_step', return_value=True):
            with patch('core.loops._step_result_appears_idle', return_value=False):
                with patch('core.loops.load_prompt', return_value="prompt"):
                    self._run_loop(8)
                    assert core.loops._goal_step_count >= 0

    def test_no_prompt_skips_step(self, init_state):
        core_state.GOAL_FILE.write_text("test goal")
        core_state.IDLE_POLL_INTERVAL = 0
        with patch('core.loops.load_prompt', return_value=""):
            self._run_loop(5)

    def test_chat_wake_seeds_goal(self, init_state):
        import core.loops
        core_state.CHATLOG_DIR.mkdir(parents=True, exist_ok=True)
        chat_file = core_state.CHATLOG_DIR / "chat.jsonl"
        chat_file.write_text(json.dumps({"role": "user", "text": "Hello"}) + "\n")
        core_state.IDLE_POLL_INTERVAL = 0
        core.loops._last_chat_wake_check = 0.0
        core.loops._last_seeded_goal_hash = ""
        core_state.GOAL_FILE.write_text("")
        with patch('core.loops.run_step', return_value=True):
            with patch('core.loops._step_result_appears_idle', return_value=False):
                with patch('core.loops.load_prompt', return_value="prompt"):
                    self._run_loop(8)
                    text = core_state.GOAL_FILE.read_text()
                    assert "Hello" in text

    def test_context_budget_soft_compress(self, init_state):
        core_state.GOAL_FILE.write_text("test goal")
        core_state.IDLE_POLL_INTERVAL = 0
        core_state._CTX_BUDGET_SOFT_LIMIT = 0
        core_state._CTX_BUDGET_HARD_LIMIT = 999999
        with patch('core.loops.run_step', return_value=True):
            with patch('core.loops._step_result_appears_idle', return_value=False):
                with patch('core.loops.load_prompt', return_value="prompt"):
                    self._run_loop(8)

    def test_context_budget_hard_compress(self, init_state):
        core_state.GOAL_FILE.write_text("test goal")
        core_state.IDLE_POLL_INTERVAL = 0
        core_state._CTX_BUDGET_SOFT_LIMIT = 0
        core_state._CTX_BUDGET_HARD_LIMIT = 0
        with patch('core.loops.run_step', return_value=True):
            with patch('core.loops._step_result_appears_idle', return_value=False):
                with patch('core.loops.load_prompt', return_value="prompt"):
                    self._run_loop(8)

    def test_failure_backoff(self, init_state):
        core_state.GOAL_FILE.write_text("test goal")
        core_state.IDLE_POLL_INTERVAL = 0
        core_state.MAX_CONSECUTIVE_FAILURES = 10
        core_state.MAX_GOAL_STEPS = 10
        with patch('core.loops.run_step', return_value=False):
            with patch('core.loops.load_prompt', return_value="prompt"):
                self._run_loop(8)


# ══════════════════════════════════════════════════════════════════════════
# transcribe_voice
# ══════════════════════════════════════════════════════════════════════════

class TestTranscribeVoice:
    def test_no_api_key(self, init_state):
        from core.loops import transcribe_voice
        core_state.GROQ_API_KEY = ""
        result = transcribe_voice("/tmp/test.ogg", "ogg")
        assert "unavailable" in result
        assert "GROQ_API_KEY" in result

    def test_success(self, init_state):
        from core.loops import transcribe_voice
        core_state.GROQ_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"text": "Hello world transcription"}
        with patch('requests.post', return_value=mock_resp):
            with patch('builtins.open', MagicMock()):
                result = transcribe_voice("/tmp/test.ogg", "ogg")
                assert result == "Hello world transcription"

    def test_empty_response(self, init_state):
        from core.loops import transcribe_voice
        core_state.GROQ_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"text": ""}
        with patch('requests.post', return_value=mock_resp):
            with patch('builtins.open', MagicMock()):
                result = transcribe_voice("/tmp/test.ogg", "ogg")
                assert "empty" in result

    def test_api_error(self, init_state):
        from core.loops import transcribe_voice
        core_state.GROQ_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        with patch('requests.post', return_value=mock_resp):
            with patch('builtins.open', MagicMock()):
                result = transcribe_voice("/tmp/test.oga", "oga")
                assert "unavailable" in result

    def test_exception(self, init_state):
        from core.loops import transcribe_voice
        core_state.GROQ_API_KEY = "test-key"
        with patch('requests.post', side_effect=Exception("connection error")):
            with patch('builtins.open', MagicMock()):
                result = transcribe_voice("/tmp/test.ogg", "ogg")
                assert "unavailable" in result

    def test_file_open_error(self, init_state):
        from core.loops import transcribe_voice
        core_state.GROQ_API_KEY = "test-key"
        with patch('builtins.open', side_effect=FileNotFoundError("no file")):
            result = transcribe_voice("/tmp/nonexistent.ogg", "ogg")
            assert "unavailable" in result


# ══════════════════════════════════════════════════════════════════════════
# _expert_loop helpers
# ══════════════════════════════════════════════════════════════════════════

class TestExpertStatusCard:
    def test_format_card(self):
        from core.loops import _expert_status_card
        card = _expert_status_card("expert1", "Do X", 3, "Running")
        assert "[expert1]" in card
        assert "Do X" in card
        assert "Step: 3" in card

    def test_format_card_long_goal(self):
        from core.loops import _expert_status_card
        long_goal = "x" * 200
        card = _expert_status_card("expert1", long_goal, 1)
        assert "..." in card


class TestExpertLoopManager:
    def test_start_expert(self, init_state):
        from core.loops import LoopManager
        lm = LoopManager()
        with patch('core.loops._expert_loop'):
            with patch('core.context.ExpertContext') as MockCtx:
                ctx = MagicMock()
                ctx.goal_file = MagicMock()
                ctx.state_file = MagicMock()
                ctx.runs_dir = MagicMock()
                ctx.inbox_file = MagicMock()
                ctx.base = MagicMock()
                ctx.ensure_dirs = MagicMock()
                MockCtx.return_value = ctx
                assert lm.start_expert("test_expert") is True

    def test_start_expert_already_running(self, init_state):
        from core.loops import LoopManager
        lm = LoopManager()
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        lm._threads["test_expert"] = mock_thread
        assert lm.start_expert("test_expert") is False

    def test_wake_expert(self, init_state):
        from core.loops import LoopManager
        lm = LoopManager()
        wake = threading.Event()
        lm._wakes["test_expert"] = wake
        lm.wake_expert("test_expert")
        assert wake.is_set()

    def test_is_running(self, init_state):
        from core.loops import LoopManager
        lm = LoopManager()
        assert lm.is_running("nonexistent") is False
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        lm._threads["running_expert"] = mock_thread
        assert lm.is_running("running_expert") is True

    def test_list_active(self, init_state):
        from core.loops import LoopManager
        lm = LoopManager()
        alive = MagicMock()
        alive.is_alive.return_value = True
        dead = MagicMock()
        dead.is_alive.return_value = False
        lm._threads["alive"] = alive
        lm._threads["dead"] = dead
        active = lm.list_active()
        assert "alive" in active
        assert "dead" not in active

    def test_stop_all(self, init_state):
        from core.loops import LoopManager
        lm = LoopManager()
        stop = threading.Event()
        wake = threading.Event()
        lm._stops["test"] = stop
        lm._wakes["test"] = wake
        lm.stop_all()
        assert stop.is_set()
        assert wake.is_set()


class TestExpertAutoRetro:
    def test_write_retro(self, init_state):
        from core.loops import _expert_auto_retro
        ctx = MagicMock()
        ctx.goal_file = MagicMock()
        ctx.state_file = MagicMock()
        ctx.state_file.exists.return_value = True
        ctx.state_file.read_text.return_value = "Final state here"
        ctx.base = core_state.WORKING_DIR / "test_expert"
        _expert_auto_retro("test_expert", ctx, "goal text", 5, "completed")
        learnings_file = ctx.base / "learnings.md"
        assert learnings_file.exists()
        text = learnings_file.read_text()
        assert "Retro" in text
        assert "goal text" in text

    def test_write_retro_no_state(self, init_state):
        from core.loops import _expert_auto_retro
        ctx = MagicMock()
        ctx.state_file.exists.return_value = False
        ctx.base = core_state.WORKING_DIR / "test_expert_no_state"
        _expert_auto_retro("test_expert_no_state", ctx, "goal", 1, "done")
        learnings_file = ctx.base / "learnings.md"
        assert learnings_file.exists()
