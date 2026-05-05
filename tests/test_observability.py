"""Tests for Phase 3 observability modules: logger, alerter, health."""
import json
import os
import time
from unittest.mock import patch

from core import state as core_state

# ══════════════════════════════════════════════════════════════════════════
# logger.py
# ══════════════════════════════════════════════════════════════════════════

class TestLogger_LevelEnabled:
    def test_info_by_default(self):
        from core.logger import _level_enabled
        assert _level_enabled("INFO") is True
        assert _level_enabled("DEBUG") is False

    def test_debug_when_configured(self):
        from core.logger import _level_enabled
        os.environ["LOG_LEVEL"] = "DEBUG"
        assert _level_enabled("DEBUG") is True
        del os.environ["LOG_LEVEL"]

    def test_warn_enabled(self):
        from core.logger import _level_enabled
        os.environ["LOG_LEVEL"] = "WARN"
        assert _level_enabled("ERROR") is True
        assert _level_enabled("INFO") is False
        del os.environ["LOG_LEVEL"]

    def test_error_only(self):
        from core.logger import _level_enabled
        os.environ["LOG_LEVEL"] = "ERROR"
        assert _level_enabled("ERROR") is True
        assert _level_enabled("WARN") is False
        assert _level_enabled("INFO") is False
        del os.environ["LOG_LEVEL"]


class TestLogger_LogLevel:
    def test_log_level_default(self):
        from core.logger import _log_level
        assert _log_level() == 1

    def test_log_level_debug(self):
        from core.logger import _log_level
        os.environ["LOG_LEVEL"] = "DEBUG"
        assert _log_level() == 0
        del os.environ["LOG_LEVEL"]

    def test_log_level_error(self):
        from core.logger import _log_level
        os.environ["LOG_LEVEL"] = "ERROR"
        assert _log_level() == 3
        del os.environ["LOG_LEVEL"]

    def test_log_level_invalid(self):
        from core.logger import _log_level
        os.environ["LOG_LEVEL"] = "INVALID"
        assert _log_level() == 1
        del os.environ["LOG_LEVEL"]


class TestLogger_StepLabel:
    def test_step_label_basic(self):
        from core.logger import step_label
        assert step_label(1) == "Step 1"

    def test_step_label_with_goal_step(self):
        from core.logger import step_label
        assert step_label(5, goal_step=3) == "Step 3"

    def test_step_label_with_bot_short(self):
        from core.logger import step_label
        lbl = step_label(1, 0, bot_short="orkes_ds")
        assert "[orkes_ds]" in lbl
        assert "Step 1" in lbl

    def test_step_label_with_expert_tag(self):
        from core.logger import step_label
        lbl = step_label(1, 0, expert_tag="helper")
        assert "[helper]" in lbl

    def test_step_label_expert_not_main(self):
        from core.logger import step_label
        lbl = step_label(1, 0, expert_tag="helper")
        assert "[helper]" in lbl
        lbl2 = step_label(1, 0, expert_tag="main")
        assert "[main]" not in lbl2


class TestLogger_LogStep:
    def test_log_step_creates_json_file(self, init_state, tmp_path):
        from core.logger import log_step
        run_dir = tmp_path / "runs" / "20260428_120000"
        run_dir.mkdir(parents=True)
        core_state.RUNS_DIR = tmp_path / "runs"
        log_step(1, 1, "abc123", "success", 1500, run_dir=run_dir)
        step_file = run_dir / "step-1.json"
        assert step_file.exists()
        data = json.loads(step_file.read_text())
        assert data["step"] == 1
        assert data["goal_step"] == 1
        assert data["goal_id"] == "abc123"
        assert data["status"] == "success"
        assert data["duration_ms"] == 1500
        assert data["level"] == "INFO"

    def test_log_step_with_error(self, init_state, tmp_path):
        from core.logger import log_step
        run_dir = tmp_path / "runs" / "20260428_120001"
        core_state.RUNS_DIR = tmp_path / "runs"
        log_step(2, 1, "def456", "failed", 3000, error="Something broke",
                 run_dir=run_dir)
        data = json.loads((run_dir / "step-2.json").read_text())
        assert data["level"] == "ERROR"
        assert "Something broke" in data["error"]

    def test_log_step_tokens(self, init_state, tmp_path):
        from core.logger import log_step
        run_dir = tmp_path / "runs" / "20260428_120002"
        core_state.RUNS_DIR = tmp_path / "runs"
        log_step(3, 2, "ghi789", "success", 2000, tokens_in=5000, tokens_out=1200,
                 run_dir=run_dir)
        data = json.loads((run_dir / "step-3.json").read_text())
        assert data["tokens_in"] == 5000
        assert data["tokens_out"] == 1200

    def test_log_step_appends_to_combined_log(self, init_state, tmp_path):
        from core.logger import log_step
        core_state.RUNS_DIR = tmp_path / "runs"
        core_state.RUNS_DIR.mkdir(parents=True)
        log_step(1, 1, "aaa", "success", 100, run_dir=tmp_path / "runs" / "d1")
        log_step(2, 2, "bbb", "success", 200, run_dir=tmp_path / "runs" / "d2")
        combined = core_state.RUNS_DIR / "step_log.jsonl"
        assert combined.exists()
        lines = combined.read_text().strip().splitlines()
        assert len(lines) == 2

    def test_log_step_no_run_dir_creates_one(self, init_state, tmp_path):
        from core.logger import log_step
        core_state.RUNS_DIR = tmp_path / "runs"
        core_state.RUNS_DIR.mkdir(parents=True)
        log_step(1, 1, "ccc", "success", 100)
        combined = core_state.RUNS_DIR / "step_log.jsonl"
        assert combined.exists()


class TestLogger_Log:
    def test_log_info(self, init_state, tmp_path):
        from core.logger import log
        core_state.RUNS_DIR = tmp_path / "runs"
        core_state.RUNS_DIR.mkdir(parents=True)
        log("INFO", "test message", extra_field="value")
        combined = core_state.RUNS_DIR / "step_log.jsonl"
        assert combined.exists()
        data = json.loads(combined.read_text().strip().splitlines()[-1])
        assert data["message"] == "test message"
        assert data["extra_field"] == "value"

    def test_log_debug_suppressed(self, init_state, tmp_path):
        from core.logger import log
        core_state.RUNS_DIR = tmp_path / "runs"
        core_state.RUNS_DIR.mkdir(parents=True)
        log("DEBUG", "debug message")
        combined = core_state.RUNS_DIR / "step_log.jsonl"
        if combined.exists():
            lines = combined.read_text().strip().splitlines()
            debug_lines = [x for x in lines if '"debug message"' in x]
            assert len(debug_lines) == 0


# ══════════════════════════════════════════════════════════════════════════
# alerter.py
# ══════════════════════════════════════════════════════════════════════════

class TestAlerter_SummarizeError:
    def test_empty(self):
        from core.alerter import _summarize_error
        assert _summarize_error("") == "(empty error)"

    def test_simple_message(self):
        from core.alerter import _summarize_error
        result = _summarize_error("Connection refused")
        assert result == "Connection refused"

    def test_strips_traceback(self):
        from core.alerter import _summarize_error
        error = (
            "Traceback (most recent call last):\n"
            '  File "/usr/lib/python3/foo.py", line 42, in bar\n'
            "    do_something()\n"
            "  File \"/home/user/project/code.py\", line 10, in run\n"
            "    raise ValueError(\"something broke\")\n"
            "ValueError: something broke"
        )
        result = _summarize_error(error)
        assert "Traceback" not in result
        assert 'File "' not in result
        assert "ValueError: something broke" in result

    def test_truncates_long_error(self):
        from core.alerter import _summarize_error
        long_msg = "x" * 2000
        result = _summarize_error(long_msg, max_len=100)
        assert len(result) <= 103

    def test_dedup_repeated_lines(self):
        from core.alerter import _summarize_error
        error = "same error\nsame error\nsame error\ndifferent"
        result = _summarize_error(error)
        count_same = result.count("same error")
        assert count_same == 1


class TestAlerter_AlertEnabled:
    def test_default_info_level(self):
        from core.alerter import _alert_enabled
        assert _alert_enabled("ERROR") is True
        assert _alert_enabled("INFO") is True

    def test_warn_level_suppresses_info(self):
        from core.alerter import _alert_enabled
        os.environ["LOG_LEVEL"] = "WARN"
        assert _alert_enabled("INFO") is False
        assert _alert_enabled("ERROR") is True
        del os.environ["LOG_LEVEL"]

    def test_error_level_only(self):
        from core.alerter import _alert_enabled
        os.environ["LOG_LEVEL"] = "ERROR"
        assert _alert_enabled("WARN") is False
        assert _alert_enabled("ERROR") is True
        del os.environ["LOG_LEVEL"]


class TestAlerter_RateLimited:
    def test_first_call_not_limited(self):
        import core.alerter
        core.alerter._last_alert = 0.0
        assert core.alerter._rate_limited() is False

    def test_consecutive_call_limited(self):
        import core.alerter
        core.alerter._last_alert = 0.0
        core.alerter._rate_limited()
        assert core.alerter._rate_limited() is True


class TestAlerter_SendAlert:
    def test_alert_not_sent_when_disabled(self):
        from core.alerter import send_alert
        os.environ["LOG_LEVEL"] = "ERROR"
        result = send_alert("test message", level="INFO")
        assert result is False
        del os.environ["LOG_LEVEL"]

    def test_alert_rate_limited(self):
        import core.alerter
        core.alerter._last_alert = time.monotonic()
        with patch("core.telegram._send_owner_alert", return_value=True):
            result = core.alerter.send_alert("rate limit test")
            assert result is False

    def test_alert_sends(self):
        import core.alerter
        core.alerter._last_alert = 0.0
        with patch("core.telegram._send_owner_alert", return_value=True) as mock:
            result = core.alerter.send_alert("something failed")
            assert result is True
            mock.assert_called_once()

    def test_step_alert_format(self):
        import core.alerter
        core.alerter._last_alert = 0.0
        with patch("core.telegram._send_owner_alert", return_value=True) as mock:
            result = core.alerter.send_step_alert(5, "build feature", "compiler error")
            assert result is True
            call_arg = mock.call_args[0][0]
            assert "Step 5 failed" in call_arg
            assert "build feature" in call_arg
            assert "compiler error" in call_arg

    def test_alert_exception_handled(self):
        import core.alerter
        core.alerter._last_alert = 0.0
        with patch("core.telegram._send_owner_alert", side_effect=Exception("no network")):
            result = core.alerter.send_alert("test")
            assert result is False


# ══════════════════════════════════════════════════════════════════════════
# health.py
# ══════════════════════════════════════════════════════════════════════════

class TestHealth_HeartbeatFile:
    def test_write_heartbeat_creates_file(self, init_state):
        from core.health import write_heartbeat
        write_heartbeat(step_number=1, status="running", goal="test goal")
        hb_path = core_state.CONTEXT_DIR / ".heartbeat"
        assert hb_path.exists()
        data = json.loads(hb_path.read_text())
        assert data["step"] == 1
        assert data["status"] == "running"
        assert data["goal"] == "test goal"

    def test_write_heartbeat_with_duration(self, init_state):
        from core.health import write_heartbeat
        write_heartbeat(step_number=5, status="success", duration_ms=2500)
        data = json.loads((core_state.CONTEXT_DIR / ".heartbeat").read_text())
        assert data["duration_ms"] == 2500
        assert data["step"] == 5

    def test_read_heartbeat(self, init_state):
        from core.health import read_heartbeat, write_heartbeat
        write_heartbeat(step_number=3, status="running")
        read = read_heartbeat()
        assert read is not None
        assert read["step"] == 3
        assert read["status"] == "running"

    def test_read_heartbeat_missing(self, init_state):
        from core.health import read_heartbeat
        hb_file = core_state.CONTEXT_DIR / ".heartbeat"
        if hb_file.exists():
            hb_file.unlink()
        assert read_heartbeat() is None

    def test_read_heartbeat_corrupt(self, init_state):
        from core.health import read_heartbeat
        hb_file = core_state.CONTEXT_DIR / ".heartbeat"
        hb_file.write_text("not json")
        assert read_heartbeat() is None

    def test_write_no_context_dir(self):
        from core.health import write_heartbeat
        core_state.CONTEXT_DIR = None
        write_heartbeat(step_number=1, status="running")
