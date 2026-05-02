"""Coverage phase 2: _expert_loop, health, logger, alerter, plus engine/runner edge cases."""
import json
import os
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from core import state as core_state

# ══════════════════════════════════════════════════════════════════════════
# _expert_loop
# ══════════════════════════════════════════════════════════════════════════

def _expert_patches(extra=None):
    """Default patch dict for _expert_loop tests."""
    p = {
        '_send_owner_alert': MagicMock(),
        '_write_fleet_status': MagicMock(),
        '_send_expert_status': MagicMock(),
        '_write_completion_state': MagicMock(),
        '_expert_auto_retro': MagicMock(),
        'load_prompt': MagicMock(return_value="prompt"),
        'run_step': MagicMock(return_value=True),
        '_step_result_appears_idle': MagicMock(return_value=False),
    }
    if extra:
        p.update(extra)
    return p


def _run_expert_thread(handle, ctx, patches=None, runtime=0.3, expert_cfg=None):
    """Run _expert_loop in a daemon thread with stop event after `runtime` seconds."""
    import core.loops
    wake = threading.Event()
    stop = threading.Event()
    all_patches = _expert_patches(patches)
    cfg = expert_cfg or {}
    with patch('core.loops._STEP_MIN_INTERVAL', 0):
        with patch('core.loops._get_expert', return_value=cfg):
            with patch.multiple('core.loops', **all_patches):
                t = threading.Thread(target=core.loops._expert_loop, args=(handle, ctx, wake, stop))
                t.daemon = True
                t.start()
                time.sleep(runtime)
                stop.set()
                from core import state as core_state
                core_state._agent_wake.set()
                t.join(timeout=5)


def _make_expert_ctx(goal_text="", inbox_text="", handle="test"):
    """Build a MagicMock ctx with optional file interactions."""
    ctx = MagicMock()
    goal_file = MagicMock()
    goal_file.exists.return_value = bool(goal_text)
    goal_file.read_text.return_value = goal_text
    ctx.goal_file = goal_file
    state_file = MagicMock()
    state_file.exists.return_value = True
    state_file.read_text.return_value = "state content"
    ctx.state_file = state_file
    runs_dir = MagicMock()
    runs_dir.exists.return_value = False
    ctx.runs_dir = runs_dir
    inbox_file = MagicMock()
    inbox_file.exists.return_value = bool(inbox_text)
    inbox_file.read_text.return_value = inbox_text
    ctx.inbox_file = inbox_file
    ctx.base = MagicMock()
    ctx.step_msg_file = MagicMock()
    ctx.handle = handle
    return ctx


class TestExpertLoop:
    def test_idle_timeout_exit(self, init_state):
        core_state.IDLE_POLL_INTERVAL = 0
        ctx = _make_expert_ctx(goal_text="")
        import core.loops
        with patch('core.loops._STEP_MIN_INTERVAL', 0):
            with patch('core.loops._get_expert', return_value={"idle_timeout": 0}):
                with patch.multiple('core.loops', **_expert_patches()):
                    core.loops._expert_loop("idle_test", ctx, threading.Event(), threading.Event())

    def test_done_marker(self, init_state):
        core_state.IDLE_POLL_INTERVAL = 0
        ctx = _make_expert_ctx(goal_text="(done)")
        _run_expert_thread("done_test", ctx, expert_cfg={"idle_timeout": 0})

    def test_step_execution(self, init_state):
        core_state.IDLE_POLL_INTERVAL = 0
        ctx = _make_expert_ctx(goal_text="do something")
        _run_expert_thread("step_test", ctx, expert_cfg={"idle_timeout": 0})

    def test_goal_changed(self, init_state):
        core_state.IDLE_POLL_INTERVAL = 0
        core_state._expert_loop_state["changed_test"] = {
            "step_count": 2, "goal_hash": "oldhash", "goal_step_count": 1,
            "consecutive_failures": 0,
        }
        ctx = _make_expert_ctx(goal_text="new different goal")
        _run_expert_thread("changed_test", ctx, expert_cfg={"idle_timeout": 0})

    def test_auto_clear_idle(self, init_state):
        core_state.IDLE_POLL_INTERVAL = 0
        ctx = _make_expert_ctx(goal_text="idle prone")
        _run_expert_thread("auto_clear", ctx,
                           patches={'_step_result_appears_idle': MagicMock(return_value=True)},
                           expert_cfg={"idle_timeout": 0})

    def test_circuit_breaker(self, init_state):
        core_state.IDLE_POLL_INTERVAL = 0
        ctx = _make_expert_ctx(goal_text="fail goal")
        _run_expert_thread("breaker", ctx,
                           patches={'run_step': MagicMock(return_value=False)},
                           expert_cfg={"idle_timeout": 0, "max_consecutive_failures": 1})

    def test_step_cap(self, init_state):
        core_state.IDLE_POLL_INTERVAL = 0
        ctx = _make_expert_ctx(goal_text="cap goal")
        _run_expert_thread("step_cap", ctx,
                           expert_cfg={"idle_timeout": 0, "max_goal_steps": 1})

    def test_failure_backoff(self, init_state):
        core_state.IDLE_POLL_INTERVAL = 0
        ctx = _make_expert_ctx(goal_text="backoff goal")
        _run_expert_thread("backoff", ctx,
                           patches={'run_step': MagicMock(return_value=False)},
                           expert_cfg={"idle_timeout": 0, "max_consecutive_failures": 3},
                           runtime=0.1)

    def test_inbox_processing(self, init_state):
        core_state.IDLE_POLL_INTERVAL = 0
        ctx = _make_expert_ctx(goal_text="", inbox_text="pending inbox")
        _run_expert_thread("inbox_test", ctx, expert_cfg={"idle_timeout": 0})


# ══════════════════════════════════════════════════════════════════════════
# health.py
# ══════════════════════════════════════════════════════════════════════════

class TestHealth:
    def test_write_heartbeat(self, init_state):
        from core.health import HEARTBEAT_FILE, write_heartbeat
        write_heartbeat(step_number=5, status="running", goal="test goal", duration_ms=100)
        path = core_state.CONTEXT_DIR / HEARTBEAT_FILE
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["step"] == 5
        assert data["status"] == "running"
        assert data["goal"] == "test goal"

    def test_write_heartbeat_exception(self, init_state):
        from core.health import write_heartbeat
        core_state.CONTEXT_DIR = Path("/nonexistent_dir_xyz123")
        write_heartbeat()  # should not raise

    def test_read_heartbeat_normal(self, init_state):
        from core.health import read_heartbeat, write_heartbeat
        write_heartbeat(step_number=3)
        result = read_heartbeat()
        assert result is not None
        assert result["step"] == 3

    def test_read_heartbeat_missing(self, init_state):
        from core.health import HEARTBEAT_FILE, read_heartbeat
        path = core_state.CONTEXT_DIR / HEARTBEAT_FILE
        if path.exists():
            path.unlink()
        assert read_heartbeat() is None

    def test_read_heartbeat_corrupt(self, init_state):
        from core.health import HEARTBEAT_FILE, read_heartbeat
        path = core_state.CONTEXT_DIR / HEARTBEAT_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not valid json")
        assert read_heartbeat() is None

    def test_start_health_server_disabled(self, init_state):
        from core.health import start_health_server
        with patch.dict(os.environ, {}, clear=True):
            start_health_server()  # HEALTH_PORT not set, should log and return

    def test_start_health_server_invalid_port(self, init_state):
        from core.health import start_health_server
        with patch.dict(os.environ, {"HEALTH_PORT": "not-a-number"}, clear=True):
            start_health_server()  # invalid port, should log and return

    def test_stop_health_server(self, init_state):
        from core.health import stop_health_server
        stop_health_server()  # no server running, should be safe

    def test_stop_health_server_with_server(self, init_state):
        from core.health import stop_health_server
        mock_server = MagicMock()
        import core.health
        core.health._http_server = mock_server
        stop_health_server()
        mock_server.shutdown.assert_called_once()
        assert core.health._http_server is None


# ══════════════════════════════════════════════════════════════════════════
# logger.py
# ══════════════════════════════════════════════════════════════════════════

class TestLogger:
    def test_log_level_default(self):
        from core.logger import _log_level
        with patch.dict(os.environ, {}, clear=True):
            assert _log_level() == 1  # INFO = 1

    def test_log_level_from_env(self):
        from core.logger import _log_level
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}, clear=True):
            assert _log_level() == 0

    def test_level_enabled(self):
        from core.logger import _level_enabled
        with patch.dict(os.environ, {"LOG_LEVEL": "WARN"}, clear=True):
            assert _level_enabled("ERROR") is True
            assert _level_enabled("INFO") is False

    def test_log_step_with_run_dir(self, init_state):
        from core.logger import log_step
        run_dir = core_state.RUNS_DIR / "20260428_120000"
        run_dir.mkdir(parents=True, exist_ok=True)
        log_step(step_number=1, goal_step=1, goal_id="abc123", status="success",
                 duration_ms=500, tokens_in=100, tokens_out=50, run_dir=run_dir)
        step_file = run_dir / "step-1.json"
        assert step_file.exists()
        data = json.loads(step_file.read_text())
        assert data["step"] == 1

    def test_log_step_no_run_dir(self, init_state):
        from core.logger import log_step
        log_step(step_number=2, goal_step=1, goal_id="def456", status="failed",
                 duration_ms=300, error="something broke")
        assert core_state.RUNS_DIR.exists()

    def test_log_function(self, init_state):
        from core.logger import log
        core_state.RUNS_DIR.mkdir(parents=True, exist_ok=True)
        with patch.dict(os.environ, {"LOG_LEVEL": "INFO"}, clear=True):
            log("INFO", "test message")
        log_file = core_state.RUNS_DIR / "step_log.jsonl"
        assert log_file.exists()
        lines = log_file.read_text().strip().split("\n")
        assert any("test message" in line for line in lines)

    def test_log_function_warn(self, init_state):
        from core.logger import log
        core_state.RUNS_DIR.mkdir(parents=True, exist_ok=True)
        with patch.dict(os.environ, {"LOG_LEVEL": "INFO"}, clear=True):
            log("WARN", "warning message")
        log_file = core_state.RUNS_DIR / "step_log.jsonl"
        assert log_file.exists()

    def test_log_level_filtered(self, init_state):
        from core.logger import log
        with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}, clear=True):
            log("INFO", "should not appear")
        log_file = core_state.RUNS_DIR / "step_log.jsonl"
        if log_file.exists():
            content = log_file.read_text()
            assert "should not appear" not in content

    def test_step_label(self):
        from core.logger import step_label
        assert "Step 5" in step_label(5)
        assert "[bot1]" in step_label(1, bot_short="bot1")
        assert "[expert1]" in step_label(1, bot_short="", expert_tag="expert1")


# ══════════════════════════════════════════════════════════════════════════
# alerter.py
# ══════════════════════════════════════════════════════════════════════════

class TestAlerter:
    def test_summarize_error_empty(self):
        from core.alerter import _summarize_error
        assert _summarize_error("") == "(empty error)"

    def test_summarize_error_traceback(self):
        from core.alerter import _summarize_error
        text = "Traceback (most recent call last):\n  File \"/path/to/file.py\", line 10, in func\n    raise ValueError(\"bad\")\nValueError: bad"
        result = _summarize_error(text)
        assert "ValueError: bad" in result
        assert "Traceback" not in result

    def test_summarize_error_dedup(self):
        from core.alerter import _summarize_error
        text = "Error: timeout\nError: timeout\nError: timeout"
        result = _summarize_error(text)
        assert result.count("Error: timeout") == 1

    def test_summarize_error_no_key_lines(self):
        from core.alerter import _summarize_error
        text = "Traceback\n  File \"x.py\"\n  File \"y.py\"\n  raise ValueError"
        result = _summarize_error(text)
        assert len(result) > 0

    def test_summarize_error_truncation(self):
        from core.alerter import _summarize_error
        long_text = "x" * 1000
        result = _summarize_error(long_text, max_len=100)
        assert len(result) <= 100 + 3  # +3 for "..."

    def test_send_alert_disabled(self):
        from core.alerter import send_alert
        with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}, clear=True):
            result = send_alert("test message", level="INFO")
            assert result is False

    def test_send_alert_rate_limited(self, init_state):
        from core.alerter import _last_alert, send_alert
        with patch.dict(os.environ, {}, clear=True):
            _last_alert = time.monotonic()
            with patch('core.alerter._alert_enabled', return_value=True):
                result = send_alert("rate limited test")
                assert result is False

    def test_send_alert_exception(self, init_state):
        from core import alerter as core_alerter
        from core.alerter import send_alert
        core_alerter._last_alert = 0.0
        with patch.dict(os.environ, {}, clear=True):
            with patch('core.alerter._alert_enabled', return_value=True):
                with patch('core.alerter._rate_limited', return_value=False):
                    with patch('core.telegram._send_owner_alert', side_effect=Exception("network error")):
                        result = send_alert("exception test")
                        assert result is False

    def test_send_alert_success(self, init_state):
        from core import alerter as core_alerter
        from core.alerter import send_alert
        core_alerter._last_alert = 0.0
        with patch.dict(os.environ, {}, clear=True):
            with patch('core.alerter._alert_enabled', return_value=True):
                with patch('core.alerter._rate_limited', return_value=False):
                    with patch('core.telegram._send_owner_alert', return_value=True):
                        result = send_alert("successful test")
                        assert result is True

    def test_send_step_alert(self, init_state):
        from core import alerter as core_alerter
        from core.alerter import send_step_alert
        core_alerter._last_alert = 0.0
        with patch.dict(os.environ, {}, clear=True):
            with patch('core.alerter._alert_enabled', return_value=True):
                with patch('core.alerter._rate_limited', return_value=False):
                    with patch('core.telegram._send_owner_alert', return_value=True):
                        result = send_step_alert(5, "my goal", "error occurred")
                        assert result is True


# ══════════════════════════════════════════════════════════════════════════
# engine.py additional
# ══════════════════════════════════════════════════════════════════════════

class TestEngine_RunBot:
    def test_run_bot_no_token(self, init_state):
        from core.engine import run_bot
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit):
                run_bot()

    def test_run_bot_normal(self, init_state):
        from core.engine import run_bot
        mock_bot = MagicMock()
        with patch.dict(os.environ, {"TAU_BOT_TOKEN": "test:token"}, clear=True):
            mock_telebot = MagicMock()
            mock_telebot.TeleBot.return_value = mock_bot
            with patch.dict('sys.modules', {'telebot': mock_telebot, 'telebot.types': MagicMock()}):
                with patch('core.bot_handlers.register_handlers'):
                    with patch('core.bot_handlers._load_chat_ids'):
                        with patch('core.engine._load_expert_registry'):
                            core_state._shutdown.set()
                            run_bot()
                            mock_bot.polling.assert_not_called()

    def test_signal_handler(self, init_state):
        from core.engine import main
        core_state._shutdown.clear()
        core_state._loop_manager = MagicMock()
        with patch.object(sys, 'argv', ['engine.py']):
            with patch('core.engine._acquire_bot_lock', return_value=True):
                with patch('core.engine._release_bot_lock'):
                    with patch('core.engine._load_expert_registry'):
                        with patch('core.bot_handlers._load_chat_ids'):
                            with patch('core.context._list_experts', return_value={}):
                                with patch('core.telegram._send_owner_alert'):
                                    with patch('threading.Thread'):
                                        with patch('atexit.register'):
                                            with patch('core.engine.CONTEXT_DIR', core_state.CONTEXT_DIR):
                                                with patch('core.engine.UPLOADS_DIR', core_state.UPLOADS_DIR):
                                                    with patch('core.engine.WORKING_DIR', core_state.WORKING_DIR):
                                                        with patch('os.kill', side_effect=ProcessLookupError):
                                                            with patch('core.engine.signal'):
                                                                with patch.object(sys, 'exit'):
                                                                    with patch.object(core_state._shutdown, 'is_set', side_effect=[False, True]):
                                                                        with patch('core.engine.RESTART_FLAG', PropertyMock(return_value=core_state.WORKING_DIR / ".restart")):
                                                                            (core_state.WORKING_DIR / ".restart").write_text("restart")
                                                                            main()

    def test_freshen_state_preserve_already_set(self, init_state):
        from core.engine import _freshen_state_on_boot
        core_state.STATE_FILE.write_text("existing content")
        core_state.RUNS_DIR.mkdir(parents=True, exist_ok=True)
        _freshen_state_on_boot()
        assert core_state.STATE_FILE.read_text() == "existing content"


# ══════════════════════════════════════════════════════════════════════════
# runner.py additional
# ══════════════════════════════════════════════════════════════════════════

class TestRunner_Additional:
    def test_format_opencode_tool_none_input(self):
        from core.runner import _format_opencode_tool
        result = _format_opencode_tool({"name": "Bash", "input": None})
        assert "running" in result

    def test_run_agent_semaphore_release(self, init_state):
        from core.runner import run_agent
        core_state.RUNS_DIR.mkdir(parents=True, exist_ok=True)
        with patch('core.runner._run_opencode_once', side_effect=Exception("crash")):
            core_state._opencode_semaphore = threading.Semaphore(1)
            sem = core_state._opencode_semaphore
            with pytest.raises(Exception):
                run_agent(["test"], "phase", core_state.RUNS_DIR / "out.txt")
            assert sem._value == 1

    def test_run_opencode_once_json_decode_error(self, init_state):
        from core.runner import _run_opencode_once
        mock_proc = MagicMock()
        mock_proc.pid = 99999
        mock_proc.stdout.readline.side_effect = ["not json\n", ""]
        mock_proc.poll.return_value = 0
        mock_proc.wait.return_value = 0
        mock_proc.stderr.read.return_value = ""
        with patch('subprocess.Popen', return_value=mock_proc):
            sel = MagicMock()
            sel.select.side_effect = [[(None, MagicMock())], []]
            with patch('selectors.DefaultSelector', return_value=sel):
                rc, result, raw, _ = _run_opencode_once(["echo", "hi"], {})
                assert rc == 0

    def test_run_opencode_once_proc_dead_with_output(self, init_state):
        from core.runner import _run_opencode_once
        mock_proc = MagicMock()
        mock_proc.pid = 99999
        mock_proc.stdout.readline.side_effect = ["", ""]
        mock_proc.poll.return_value = 0
        mock_proc.wait.return_value = 0
        mock_proc.stderr.read.return_value = ""
        with patch('subprocess.Popen', return_value=mock_proc):
            sel = MagicMock()
            sel.select.side_effect = [[], [(None, MagicMock())]]
            with patch('selectors.DefaultSelector', return_value=sel):
                rc, result, raw, _ = _run_opencode_once(["echo", "hi"], {})
                assert rc == 0
