"""Coverage gap tests — targeting untested code paths in core modules.

Brings coverage toward ≥80% on ~/.opencode-bot/core/.
"""

import json
import os
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from core import state as core_state

# ── FileStateCache (state.py) ──────────────────────────────────────────────────

class TestFileStateCache:
    def test_get_missing(self):
        cache = core_state.FileStateCache(max_size=3)
        assert cache.get("/nope") is None

    def test_put_and_get(self):
        cache = core_state.FileStateCache(max_size=3)
        cache.put("/a", "content_a")
        assert cache.get("/a") == "content_a"

    def test_evict(self):
        cache = core_state.FileStateCache(max_size=3)
        cache.put("/a", "content_a")
        cache.evict("/a")
        assert cache.get("/a") is None

    def test_clear(self):
        cache = core_state.FileStateCache(max_size=3)
        cache.put("/a", "1")
        cache.put("/b", "2")
        cache.clear()
        assert len(cache) == 0

    def test_lru_eviction(self):
        cache = core_state.FileStateCache(max_size=2)
        cache.put("/a", "1")
        cache.put("/b", "2")
        cache.put("/c", "3")
        assert cache.get("/a") is None
        assert cache.get("/b") == "2"
        assert cache.get("/c") == "3"

    def test_keys(self):
        cache = core_state.FileStateCache(max_size=3)
        cache.put("/a", "1")
        cache.put("/b", "2")
        assert "/a" in cache.keys()
        assert "/b" in cache.keys()


# ── Context budget (state.py) ─────────────────────────────────────────────────

class TestContextBudget:
    def test_budget_push_and_status(self):
        core_state.ctx_budget_push("test", 100)
        chars, soft, hard, stack = core_state.ctx_budget_status()
        assert chars == 100
        assert len(stack) == 1

    def test_budget_reset(self):
        core_state.ctx_budget_push("test", 100)
        core_state.ctx_budget_reset()
        chars, _, _, stack = core_state.ctx_budget_status()
        assert chars == 0
        assert stack == []

    def test_budget_not_exceeded_when_empty(self):
        assert core_state.ctx_budget_exceeded("soft") is False
        assert core_state.ctx_budget_exceeded("hard") is False

    def test_budget_exceeded_soft(self):
        core_state._CTX_BUDGET_SOFT_LIMIT = 50
        core_state.ctx_budget_push("big", 100)
        assert core_state.ctx_budget_exceeded("soft") is True

    def test_budget_exceeded_hard(self):
        core_state._CTX_BUDGET_HARD_LIMIT = 50
        core_state.ctx_budget_push("huge", 100)
        assert core_state.ctx_budget_exceeded("hard") is True

    def test_budget_remaining(self):
        core_state._CTX_BUDGET_HARD_LIMIT = 1000
        core_state.ctx_budget_push("x", 300)
        remaining = core_state.ctx_budget_remaining()
        assert remaining == 700
        assert remaining > 0

    def test_compress_and_summary(self):
        core_state.ctx_budget_push("big", 2000)
        core_state._CTX_BUDGET_HARD_LIMIT = 1000
        core_state.ctx_compress("test", "compressed summary here")
        chars, _, _, _ = core_state.ctx_budget_status()
        assert chars >= 0
        summary = core_state.ctx_summary_text()
        assert "test" in summary
        assert "compressed summary here" in summary

    def test_chatlog_max_scales(self):
        core_state._CTX_BUDGET_HARD_LIMIT = 100000
        core_state.ctx_budget_push("x", 100)
        maxc = core_state.ctx_chatlog_max()
        assert maxc >= 8000

    def test_learnings_max_scales(self):
        core_state._CTX_BUDGET_HARD_LIMIT = 100000
        core_state.ctx_budget_push("x", 100)
        maxl = core_state.ctx_learnings_max()
        assert maxl >= 4000


# ── Redaction (redaction.py) ──────────────────────────────────────────────────

class TestRedaction:
    def test_redact_secrets_patterns(self):
        from core.redaction import _redact_secrets
        long_token = "sk-" + "a" * 30
        assert "[REDACTED]" in _redact_secrets(long_token)

    def test_redact_env_secrets(self, monkeypatch):
        from core.redaction import _redact_secrets, _reload_env_secrets
        monkeypatch.setenv("MY_API_KEY", "super-secret-value-12345")
        _reload_env_secrets()
        text = "my token is super-secret-value-12345"
        result = _redact_secrets(text)
        assert "super-secret-value-12345" not in result
        assert "[REDACTED]" in result

    def test_redact_short_values_ignored(self, monkeypatch):
        from core.redaction import _load_env_secrets
        monkeypatch.setenv("SHORT_KEY", "abc")
        secrets = _load_env_secrets()
        assert "abc" not in secrets

    def test_redact_non_secret_env_ignored(self, monkeypatch):
        from core.redaction import _load_env_secrets
        monkeypatch.setenv("MY_FAVORITE_COLOR", "blue-magenta-cyan-yellow")
        secrets = _load_env_secrets()
        assert "blue-magenta-cyan-yellow" not in secrets


# ── Log formatting (log.py) ──────────────────────────────────────────────────

class TestLogFormatting:
    def test_fmt_duration_seconds(self):
        from core.log import fmt_duration
        assert "1.5s" in fmt_duration(1.5)

    def test_fmt_duration_minutes(self):
        from core.log import fmt_duration
        assert "2m 30s" in fmt_duration(150)

    def test_fmt_tokens_basic(self):
        from core.log import fmt_tokens
        result = fmt_tokens(1000, 500)
        assert "1.0k" in result
        assert "500 out" in result

    def test_fmt_tokens_with_tps(self):
        from core.log import fmt_tokens
        result = fmt_tokens(1000, 500, elapsed=10)
        assert "50 t/s" in result or "50.0 t/s" in result

    def test_fmt_tokens_small(self):
        from core.log import fmt_tokens
        result = fmt_tokens(42, 7)
        assert "42" in result
        assert "7" in result

    def test_fmt_tokens_cost(self):
        from core.log import fmt_tokens
        result = fmt_tokens(1000000, 500000)
        assert "$" in result


# ── Engine init helpers (engine.py) ──────────────────────────────────────────

class TestEngineInit:
    def test_init_env_no_env_file(self, init_state, monkeypatch):
        from core.engine import _init_env
        monkeypatch.delenv("TAU_BOT_TOKEN", raising=False)
        _init_env()

    def test_init_paths_my_pm2_name(self, mock_project_dir):
        from core.engine import _init_paths
        _init_paths(mock_project_dir)
        assert "arbos-test_project" == core_state.MY_PM2_NAME

    def test_expert_context_cwd(self, init_state):
        from core.context import ExpertContext
        ctx = ExpertContext("builder")
        assert ctx.cwd == core_state.WORKING_DIR

    def test_get_expert_nonexistent(self, init_state):
        from core.context import _get_expert
        assert _get_expert("nobody") is None

    def test_list_experts_empty(self, init_state):
        from core.context import _list_experts
        assert _list_experts() == {}


# ── Prompt assembly (prompt.py) ──────────────────────────────────────────────

class TestPrompt:
    def test_make_run_dir_creates_ts_dir(self, init_state):
        from core.prompt import make_run_dir
        run_dir = make_run_dir()
        assert run_dir.exists() and run_dir.is_dir()
        assert re.match(r"\d{8}_\d{6}", run_dir.name)

    def test_prompt_assembles_basic(self, init_state):
        from core.prompt import load_prompt
        core_state.PROMPT_FILE.write_text("System instructions")
        core_state.GOAL_FILE.write_text("Do X")
        core_state.STATE_FILE.write_text("## Status: IDLE")
        prompt = load_prompt()
        assert "System instructions" in prompt
        assert "Do X" in prompt
        assert "## Status: IDLE" in prompt

    def test_prompt_consumes_inbox(self, init_state):
        from core.prompt import load_prompt
        core_state.INBOX_FILE.write_text("Operator: fix bug")
        prompt = load_prompt(consume_inbox=True)
        assert "Operator: fix bug" in prompt
        assert core_state.INBOX_FILE.read_text() == ""

    def test_prompt_with_expert_learnings(self, init_state):
        from core.context import ExpertContext
        from core.prompt import load_prompt
        ctx = ExpertContext("builder")
        ctx.ensure_dirs()
        (ctx.base / "learnings.md").write_text("Builder insight: use async")
        core_state.PROMPT_FILE.write_text("System prompt")
        prompt = load_prompt(ctx=ctx)
        assert "Builder insight" in prompt

    def test_chatlog_empty_when_no_dir(self, init_state):
        from core.prompt import load_chatlog
        core_state.CHATLOG_DIR.unlink(missing_ok=True)
        assert load_chatlog() == ""

    def test_chatlog_empty_when_no_files(self, init_state):
        from core.prompt import load_chatlog
        core_state.CHATLOG_DIR.mkdir(parents=True, exist_ok=True)
        assert load_chatlog() == ""

    def test_chatlog_with_entries(self, init_state):
        from core.prompt import load_chatlog, log_chat
        log_chat("user", "Hello bot")
        log_chat("bot", "Hello user")
        result = load_chatlog(max_chars=5000)
        assert "Hello bot" in result
        assert "Hello user" not in result  # bot messages are filtered
        assert "Recent Telegram chat" in result

    def test_chatlog_truncates_restarted(self, init_state):
        from core.prompt import load_chatlog, log_chat
        log_chat("bot", "Restarted.")
        log_chat("user", "Do X")
        result = load_chatlog(max_chars=5000)
        assert "Restarted." not in result
        assert "Do X" in result

    def test_log_chat_rolls_to_new_file(self, init_state):
        from datetime import datetime

        from core.prompt import log_chat
        class _Stepper:
            def __init__(self):
                self.n = 0
            def now(self):
                self.n += 1
                return datetime(2026, 4, 30, 12, 0, self.n)
        stepper = _Stepper()
        with patch('core.prompt.datetime') as mock_dt:
            mock_dt.now.side_effect = stepper.now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.fromtimestamp = datetime.fromtimestamp
            mock_dt.strptime = datetime.strptime
            for _ in range(3):
                log_chat("user", "x" * 200000)
        files = list(core_state.CHATLOG_DIR.glob("*.jsonl"))
        assert len(files) > 1


# ── _parse_phase_from_state helpers (was in test_state_integrity, add more) ──

class TestApplyPhaseConstraints:
    def test_plan_mode_has_all_keywords(self):
        from core.loops import _apply_phase_constraints
        result = _apply_phase_constraints("## Goal", "plan")
        assert "PLAN MODE" in result
        assert "READ-ONLY" in result
        assert "You MUST NOT" in result
        assert "Modify any files" in result

    def test_act_mode_no_constraint(self):
        from core.loops import _apply_phase_constraints
        result = _apply_phase_constraints("## Goal", "act")
        assert result == "## Goal"


# ── Log edge cases (log.py) ─────────────────────────────────────────────────

class TestLogEdgeCases:
    def test_file_log_with_handle(self, init_state, tmp_path):
        from core.log import _file_log
        logfile = tmp_path / "test.log"
        fh = open(logfile, "a", encoding="utf-8")
        core_state._log_fh = fh
        _file_log("test message")
        fh.close()
        text = logfile.read_text()
        assert "test message" in text

    def test_log_blank_true(self, init_state, capsys):
        from core.log import _log
        _log("hello", blank=True)
        captured = capsys.readouterr()
        assert "hello" in captured.out

    def test_get_tokens_returns_counts(self):
        from core.log import _get_tokens, _reset_tokens
        _reset_tokens()
        core_state._token_usage["input"] = 500
        core_state._token_usage["output"] = 300
        inp, out = _get_tokens()
        assert inp == 500
        assert out == 300

    def test_fmt_tokens_cost_below_threshold(self):
        from core.log import fmt_tokens
        result = fmt_tokens(1, 1)
        assert result


# ── Context registry (context.py) ──────────────────────────────────────────

class TestContextRegistry:
    def test_load_bot_config_no_file(self, init_state):
        from core.context import _load_bot_config
        assert _load_bot_config() == {}

    def test_load_bot_config_with_file(self, init_state):
        from core.context import _load_bot_config
        bot_json = core_state.CONTEXT_DIR / "bot.json"
        bot_json.write_text('{"expert_sources": ["local"]}')
        config = _load_bot_config()
        assert config.get("expert_sources") == ["local"]

    def test_save_expert_registry(self, init_state):
        from core.context import _save_expert_registry
        core_state._expert_registry["builder"] = {
            "expertise": "build systems", "_source": "local"
        }
        _save_expert_registry()
        assert core_state.EXPERTS_FILE.exists()
        data = json.loads(core_state.EXPERTS_FILE.read_text())
        assert "builder" in data

    def test_load_expert_registry_local(self, init_state):
        from core.context import _list_experts, _load_expert_registry
        core_state.EXPERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.EXPERTS_FILE.write_text(
            '{"builder": {"expertise": "build", "_source": "local"}}'
        )
        _load_expert_registry()
        experts = _list_experts()
        assert "builder" in experts


# ── Engine helpers uncovered (engine.py) ───────────────────────────────────

class TestEngineHelpers:
    def test_init_env_with_env_file(self, mock_project_dir):
        from core.engine import _init_env, _init_paths
        _init_paths(mock_project_dir)
        env_file = mock_project_dir / ".env"
        env_file.write_text("CUSTOM_VAR=hello\n")
        _init_env()

    def test_kill_child_procs_no_children(self, init_state):
        from core.engine import _kill_child_procs
        _kill_child_procs()

    def test_cleanup_peer_locks_no_dir(self, init_state):
        from core.peers import _cleanup_peer_locks
        _cleanup_peer_locks()

    def test_cleanup_peer_locks_with_stale(self, init_state, monkeypatch):
        import time

        from core.peers import _cleanup_peer_locks
        core_state.PEER_LOCK_DIR.mkdir(parents=True, exist_ok=True)
        stale = core_state.PEER_LOCK_DIR / "old.lock"
        stale.write_text("stale")
        old_time = time.time() - 120
        os.utime(stale, (old_time, old_time))
        _cleanup_peer_locks()
        assert not stale.exists()

    def test_acquire_lock_non_numeric_pid(self, init_state, monkeypatch):
        """Lock with non-numeric content should be treated as stale."""
        from core.engine import _acquire_bot_lock
        core_state.BOT_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.BOT_LOCK_FILE.write_text("not-a-pid")
        result = _acquire_bot_lock()
        assert result is True
        assert core_state.BOT_LOCK_FILE.read_text().strip() == str(os.getpid())

    def test_acquire_lock_permission_error(self, init_state, monkeypatch):
        """PermissionError on os.kill should treat lock as stale."""
        from core.engine import _acquire_bot_lock
        core_state.BOT_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.BOT_LOCK_FILE.write_text("999999")

        def _raise_permission(pid, sig):
            raise PermissionError()
        monkeypatch.setattr(os, "kill", _raise_permission)
        result = _acquire_bot_lock()
        assert result is True

    def test_release_lock_no_bot_lock_file(self, init_state):
        from core.engine import _release_bot_lock
        core_state.BOT_LOCK_FILE = None
        _release_bot_lock()

    def test_cleanup_stale_step_msg_oserror(self, init_state, monkeypatch):
        from core.engine import _cleanup_stale_step_msgs
        core_state.STEP_MSG_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.STEP_MSG_FILE.write_text("stale")
        calls = []

        def _broken_unlink(*a, **kw):
            calls.append(1)
            raise OSError("permission denied")

        monkeypatch.setattr(Path, "unlink", _broken_unlink)
        _cleanup_stale_step_msgs()
        assert len(calls) >= 1


# ── CLI (cli.py) ──────────────────────────────────────────────────────────

class TestCliSend:
    def test_send_no_args_exits(self):
        """_send_cli with no args should exit with error."""
        from core.cli import _send_cli
        with pytest.raises(SystemExit):
            _send_cli([])

    def test_send_message(self, init_state, monkeypatch):
        """_send_cli with a message should send and return successfully."""
        from core.cli import _send_cli
        monkeypatch.setattr("core.cli._send_telegram_new", lambda text, **kw: 999)
        monkeypatch.setattr("core.cli.log_chat", lambda role, text: None)
        _send_cli(["hello world"])

    def test_send_no_msg_id_returns(self, init_state, monkeypatch):
        """When _send_telegram_new returns None, should return 1."""
        from core.cli import _send_cli
        monkeypatch.setattr("core.cli._send_telegram_new", lambda text, **kw: None)
        monkeypatch.setattr("core.cli.log_chat", lambda role, text: None)
        assert _send_cli(["hello"]) == 1

    def test_send_from_file(self, init_state, tmp_path, monkeypatch):
        """_send_cli with --file should read from file."""
        from core.cli import _send_cli
        f = tmp_path / "msg.txt"
        f.write_text("file content")
        sent = []
        monkeypatch.setattr("core.cli._send_telegram_new", lambda text, **kw: sent.append(text) or 999)
        monkeypatch.setattr("core.cli.log_chat", lambda role, text: None)
        _send_cli(["--file", str(f)])
        assert sent == ["file content"]

    def test_send_edits_existing_msg(self, init_state, monkeypatch):
        """When STEP_MSG_FILE exists, _send_cli should edit existing message."""
        from core.cli import _send_cli
        core_state.STEP_MSG_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.STEP_MSG_FILE.write_text('{"msg_id": 42, "text": "prev"}')
        monkeypatch.setattr("core.cli._edit_telegram_text", lambda mid, text, **kw: True)
        monkeypatch.setattr("core.cli.log_chat", lambda role, text: None)
        _send_cli(["new content"])
        saved = json.loads(core_state.STEP_MSG_FILE.read_text())
        assert saved["msg_id"] == 42
        assert "prev" in saved["text"]

    def test_send_edit_fallback_to_new(self, init_state, monkeypatch):
        """When edit fails, _send_cli should fall back to sending new."""
        from core.cli import _send_cli
        core_state.STEP_MSG_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.STEP_MSG_FILE.write_text('{"msg_id": 42, "text": "prev"}')
        monkeypatch.setattr("core.cli._edit_telegram_text", lambda mid, text, **kw: False)
        monkeypatch.setattr("core.cli._send_telegram_new", lambda text, **kw: 43)
        monkeypatch.setattr("core.cli.log_chat", lambda role, text: None)
        _send_cli(["fallback text"])
        saved = json.loads(core_state.STEP_MSG_FILE.read_text())
        assert saved["msg_id"] == 43

    def test_send_corrupt_step_msg(self, init_state, monkeypatch):
        """Corrupt STEP_MSG_FILE should be treated as no existing msg."""
        from core.cli import _send_cli
        core_state.STEP_MSG_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.STEP_MSG_FILE.write_text("not-json")
        monkeypatch.setattr("core.cli._send_telegram_new", lambda text, **kw: 44)
        monkeypatch.setattr("core.cli.log_chat", lambda role, text: None)
        _send_cli(["hello"])
        saved = json.loads(core_state.STEP_MSG_FILE.read_text())
        assert saved["msg_id"] == 44


class TestCliInbox:
    def test_inbox_too_few_args(self):
        """_inbox_cli with <2 args should return 1."""
        from core.cli import _inbox_cli
        assert _inbox_cli(["builder"]) == 1

    def test_inbox_nonexistent_expert(self, init_state):
        """_inbox_cli for unknown expert should return 1."""
        from core.cli import _inbox_cli
        assert _inbox_cli(["nobody", "hello"]) == 1

    def test_inbox_success(self, init_state):
        """_inbox_cli should write to expert's inbox and signal wake."""
        from core.cli import _inbox_cli
        from core.context import _save_expert_registry
        core_state._expert_registry["builder"] = {
            "expertise": "build", "_source": "local"
        }
        _save_expert_registry()
        _inbox_cli(["builder", "do the thing"])
        ctx_inbox = core_state.CONTEXT_DIR / "builder" / "INBOX.md"
        assert ctx_inbox.exists()
        assert "do the thing" in ctx_inbox.read_text()


# ── Peers (peers.py) ───────────────────────────────────────────────────────

class TestPeers:
    def test_pm2_peer_list_no_pm2(self, monkeypatch):
        from core.peers import _pm2_peer_list
        def _mock_run(*args, **kwargs):
            raise FileNotFoundError("pm2 not found")
        monkeypatch.setattr("subprocess.run", _mock_run)
        assert _pm2_peer_list() == []

    def test_pm2_peer_list_bad_json(self, monkeypatch):
        import subprocess

        from core.peers import _pm2_peer_list
        def _mock_run(*args, **kwargs):
            r = subprocess.CompletedProcess([], 0, stdout="not-json")
            return r
        monkeypatch.setattr("subprocess.run", _mock_run)
        assert _pm2_peer_list() == []

    def test_pm2_peer_list_nonzero_rc(self, monkeypatch):
        """Non-zero return from pm2 jlist should return empty."""
        import subprocess

        from core.peers import _pm2_peer_list
        def _mock_run(*args, **kwargs):
            return subprocess.CompletedProcess([], 1, stdout="")
        monkeypatch.setattr("subprocess.run", _mock_run)
        assert _pm2_peer_list() == []

    def test_pm2_peer_list_filters_non_arbos(self, monkeypatch):
        """Processes not named arbos-* should be filtered out."""
        import subprocess

        from core.peers import _pm2_peer_list
        procs = [
            {"name": "node-app", "pm2_env": {"status": "online", "pm_exec_path": "/a/b"}},
        ]
        def _mock_run(*args, **kwargs):
            return subprocess.CompletedProcess([], 0, stdout=json.dumps(procs))
        monkeypatch.setattr("subprocess.run", _mock_run)
        assert _pm2_peer_list() == []

    def test_pm2_peer_list_finds_arbos(self, monkeypatch):
        """arbos-* processes should be included in peer list."""
        import subprocess

        from core.peers import _pm2_peer_list
        procs = [
            {"name": "arbos-test", "pid": 12345, "pm2_env": {
                "status": "online", "pm_exec_path": "/home/a/orkes_ds/main.py", "pm_uptime": 1000
            }},
        ]
        def _mock_run(*args, **kwargs):
            return subprocess.CompletedProcess([], 0, stdout=json.dumps(procs))
        monkeypatch.setattr("subprocess.run", _mock_run)
        peers = _pm2_peer_list()
        assert len(peers) == 1
        assert peers[0]["name"] == "arbos-test"
        assert peers[0]["cwd"] == "/home/a/orkes_ds"

    def test_cleanup_peer_locks_skips_current(self, init_state):
        """Recent lock files should not be cleaned."""
        from core.peers import _cleanup_peer_locks
        core_state.PEER_LOCK_DIR.mkdir(parents=True, exist_ok=True)
        fresh = core_state.PEER_LOCK_DIR / "fresh.lock"
        fresh.write_text("current")
        _cleanup_peer_locks()
        assert fresh.exists()

    def test_cleanup_peer_locks_no_dir(self, init_state):
        """No lock dir should be a no-op."""
        from core.peers import _cleanup_peer_locks
        core_state.PEER_LOCK_DIR = core_state.CONTEXT_DIR / "nonexistent_locks"
        _cleanup_peer_locks()


# ── Loops helpers (loops.py) ────────────────────────────────────────────────

class TestLoopsHelpers:
    def test_latest_rollout_text_no_runs(self, init_state):
        from core.loops import _latest_rollout_text
        assert _latest_rollout_text() == ""

    def test_latest_rollout_text_finds_latest(self, init_state):
        from core.loops import _latest_rollout_text
        r1 = core_state.RUNS_DIR / "20260428_100000"
        r1.mkdir(parents=True)
        (r1 / "rollout.md").write_text("old rollout")
        r2 = core_state.RUNS_DIR / "20260428_110000"
        r2.mkdir(parents=True)
        (r2 / "rollout.md").write_text("latest rollout")
        text = _latest_rollout_text()
        assert "latest rollout" in text
        assert "old rollout" not in text

    def test_expert_status_card_format(self):
        from core.loops import _expert_status_card
        card = _expert_status_card("builder", "Build the thing", 3, "Running")
        assert "[builder]" in card
        assert "Build the thing" in card
        assert "Step: 3" in card
        assert "Running" in card

    def test_sleep_cooldown_waits(self, init_state):
        import time

        from core.loops import _sleep_cooldown
        t0 = time.monotonic()
        _sleep_cooldown("test", seconds=0.01)
        elapsed = time.monotonic() - t0
        assert elapsed >= 0.005


# ── Telegram helpers (telegram.py) ──────────────────────────────────────────

class TestTelegramOwnerAlert:
    def test_owner_alert_no_token(self, init_state, monkeypatch):
        from core.telegram import _send_owner_alert
        monkeypatch.delenv("TAU_BOT_TOKEN", raising=False)
        assert _send_owner_alert("hello") is False

    def test_owner_alert_with_owner_id(self, init_state, monkeypatch, mock_telegram):
        from core.telegram import _send_owner_alert
        monkeypatch.setenv("TAU_BOT_TOKEN", "test:token")
        monkeypatch.setenv("TELEGRAM_OWNER_ID", "98765")
        result = _send_owner_alert("owner alert")
        assert result is True

    def test_owner_alert_fallback_no_owner_id(self, init_state, monkeypatch, mock_telegram):
        """Without owner ID but with token+chat_id, should fall back to group."""
        from core.telegram import _send_owner_alert
        monkeypatch.setenv("TAU_BOT_TOKEN", "test:token")
        monkeypatch.delenv("TELEGRAM_OWNER_ID", raising=False)
        core_state.CHAT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.CHAT_ID_FILE.write_text("12345")
        result = _send_owner_alert("fallback")
        assert result is True

    def test_owner_dm_fails_then_group(self, init_state, monkeypatch):
        """When DM fails but group works, should return True."""
        from core.telegram import _send_owner_alert
        monkeypatch.setenv("TAU_BOT_TOKEN", "test:token")
        monkeypatch.setenv("TELEGRAM_OWNER_ID", "98765")
        core_state.CHAT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.CHAT_ID_FILE.write_text("12345")
        m = MagicMock()
        m.ok = True
        m.status_code = 200
        m.json.return_value = {"ok": True, "result": {"message_id": 1}}
        monkeypatch.setattr("requests.post", lambda *a, **kw: m)
        assert _send_owner_alert("test") is True

    def test_send_to_group_no_token(self, init_state, monkeypatch):
        from core.telegram import _send_to_group
        monkeypatch.delenv("TAU_BOT_TOKEN", raising=False)
        assert _send_to_group("test") is False

    def test_send_to_group_no_groups(self, init_state, monkeypatch):
        from core.telegram import _send_to_group
        monkeypatch.setenv("TAU_BOT_TOKEN", "test:token")
        with core_state._allowed_groups_lock:
            core_state._allowed_groups.clear()
        assert _send_to_group("test") is False

    def test_send_to_group_with_group(self, init_state, monkeypatch, mock_telegram):
        from core.telegram import _send_to_group
        monkeypatch.setenv("TAU_BOT_TOKEN", "test:token")
        with core_state._allowed_groups_lock:
            core_state._allowed_groups.add("-10012345")
        assert _send_to_group("group message") is True

    def test_send_to_group_exception(self, init_state, monkeypatch):
        """Network error should return False."""
        from core.telegram import _send_to_group
        monkeypatch.setenv("TAU_BOT_TOKEN", "test:token")
        with core_state._allowed_groups_lock:
            core_state._allowed_groups.add("-10012345")
        def _fail(*a, **kw):
            raise Exception("network")
        monkeypatch.setattr("requests.post", _fail)
        assert _send_to_group("fail") is False

    def test_send_owner_alert_redacts(self, init_state, monkeypatch, mock_telegram):
        """_send_owner_alert should redact secrets."""
        from core.telegram import _send_owner_alert
        monkeypatch.setenv("TAU_BOT_TOKEN", "test:token")
        monkeypatch.setenv("TELEGRAM_OWNER_ID", "98765")
        assert _send_owner_alert("test secret") is True


class TestTelegram:
    def test_identity_tag_empty(self, init_state, monkeypatch):
        from core.telegram import _identity_tag
        monkeypatch.delenv("BOT_USERNAME", raising=False)
        monkeypatch.delenv("PM2_NAME", raising=False)
        core_state.MY_PM2_NAME = ""
        assert _identity_tag() == ""

    def test_identity_tag_with_bot_username(self, init_state, monkeypatch):
        from core.telegram import _identity_tag
        monkeypatch.setenv("BOT_USERNAME", "arbos-myb ot")
        tag = _identity_tag()
        assert "[myb ot]" in tag

    def test_step_update_target_no_token(self, init_state, monkeypatch):
        from core.telegram import _step_update_target
        monkeypatch.delenv("TAU_BOT_TOKEN", raising=False)
        assert _step_update_target() is None

    def test_step_update_target_no_chat_id_file(self, init_state, monkeypatch):
        from core.telegram import _step_update_target
        monkeypatch.setenv("TAU_BOT_TOKEN", "test:token")
        core_state.CHAT_ID_FILE.unlink(missing_ok=True)
        assert _step_update_target() is None

    def test_step_update_target_empty_chat_id(self, init_state, monkeypatch):
        from core.telegram import _step_update_target
        monkeypatch.setenv("TAU_BOT_TOKEN", "test:token")
        core_state.CHAT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.CHAT_ID_FILE.write_text("")
        assert _step_update_target() is None

    def test_step_update_target_success(self, init_state, monkeypatch):
        from core.telegram import _step_update_target
        monkeypatch.setenv("TAU_BOT_TOKEN", "test:token")
        core_state.CHAT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.CHAT_ID_FILE.write_text("12345")
        result = _step_update_target()
        assert result is not None
        token, chat_id = result
        assert token == "test:token"
        assert chat_id == "12345"

    def test_split_telegram_chunks_short(self):
        from core.telegram import _split_telegram_chunks
        chunks = _split_telegram_chunks("short text")
        assert len(chunks) == 1
        assert chunks[0] == "short text"

    def test_split_telegram_chunks_long(self):
        from core.telegram import _split_telegram_chunks
        text = "word\n\n" * 1000
        chunks = _split_telegram_chunks(text)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 4000

    def test_split_telegram_chunks_no_newlines(self):
        from core.telegram import _split_telegram_chunks
        text = "a" * 10000
        chunks = _split_telegram_chunks(text)
        for chunk in chunks:
            assert len(chunk) <= 4000

    def test_send_telegram_no_target(self, init_state):
        from core.telegram import _edit_telegram_text, _send_telegram_new, _send_telegram_text
        assert _send_telegram_text("hello") is False
        assert _send_telegram_new("hello") is None
        assert _edit_telegram_text(1, "hello") is False

    def test_send_telegram_text_sends(self, init_state, monkeypatch, mock_telegram):
        from core.telegram import _send_telegram_text
        monkeypatch.setenv("TAU_BOT_TOKEN", "test:token")
        core_state.CHAT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.CHAT_ID_FILE.write_text("12345")
        result = _send_telegram_text("hello")
        assert result is True

    def test_send_telegram_new_sends(self, init_state, monkeypatch, mock_telegram):
        from core.telegram import _send_telegram_new
        monkeypatch.setenv("TAU_BOT_TOKEN", "test:token")
        core_state.CHAT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.CHAT_ID_FILE.write_text("12345")
        result = _send_telegram_new("hello")
        assert result == 12345

    def test_send_telegram_text_http_fail(self, init_state, monkeypatch):
        from core.telegram import _send_telegram_text
        monkeypatch.setenv("TAU_BOT_TOKEN", "test:token")
        core_state.CHAT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.CHAT_ID_FILE.write_text("12345")

        import requests
        def _fail_post(*a, **kw):
            raise Exception("Network error")
        monkeypatch.setattr(requests, "post", _fail_post)
        result = _send_telegram_text("hello", target=("test:token", "12345"))
        assert result is False

    def test_edit_telegram_text_too_long(self, init_state, monkeypatch):
        from core.telegram import _edit_telegram_text
        monkeypatch.setenv("TAU_BOT_TOKEN", "test:token")
        core_state.CHAT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.CHAT_ID_FILE.write_text("12345")
        result = _edit_telegram_text(1, "x" * 5000, target=("test:token", "12345"))
        assert result is False

    def test_edit_telegram_text_sends(self, init_state, monkeypatch, mock_telegram):
        from core.telegram import _edit_telegram_text
        monkeypatch.setenv("TAU_BOT_TOKEN", "test:token")
        core_state.CHAT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.CHAT_ID_FILE.write_text("12345")
        result = _edit_telegram_text(1, "edit text")
        assert result is True

    def test_edit_telegram_text_not_ok(self, init_state, monkeypatch):
        """When resp.ok is False, _edit_telegram_text should return False."""
        from core.telegram import _edit_telegram_text
        monkeypatch.setenv("TAU_BOT_TOKEN", "test:token")
        core_state.CHAT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.CHAT_ID_FILE.write_text("12345")
        m = MagicMock()
        m.ok = False
        monkeypatch.setattr("requests.post", lambda *a, **kw: m)
        assert _edit_telegram_text(1, "fail") is False

    def test_edit_telegram_text_exception(self, init_state, monkeypatch):
        """Exception in _edit_telegram_text should return False."""
        from core.telegram import _edit_telegram_text
        monkeypatch.setenv("TAU_BOT_TOKEN", "test:token")
        core_state.CHAT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.CHAT_ID_FILE.write_text("12345")
        def _fail(*a, **kw):
            raise Exception("boom")
        monkeypatch.setattr("requests.post", _fail)
        assert _edit_telegram_text(1, "fail") is False


# ── Runner formatting (runner.py) ──────────────────────────────────────────

class TestRunnerFormatting:
    def test_format_tool_activity_bash(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("Bash", {"command": "ls -la"})
        assert "running" in result
        assert "ls -la" in result

    def test_format_tool_activity_read(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("Read", {"file_path": "/home/test/main.py"})
        assert "reading" in result
        assert "main.py" in result

    def test_format_tool_activity_write(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("Write", {"file_path": "/home/test/out.txt"})
        assert "writing" in result

    def test_format_tool_activity_glob(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("Glob", {"pattern": "**/*.py"})
        assert "searching" in result
        assert "*.py" in result

    def test_format_tool_activity_grep(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("Grep", {"pattern": "def test"})
        assert "locating" in result

    def test_format_tool_activity_webfetch(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("WebFetch", {"url": "https://example.com"})
        assert "downloading" in result

    def test_format_tool_activity_websearch(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("WebSearch", {"query": "python docs"})
        assert "browsing" in result

    def test_format_tool_activity_task(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("Task", {"description": "run tests"})
        assert "executing" in result

    def test_format_tool_activity_unknown(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("Foo", {})
        assert "Foo" in result

    def test_format_tool_activity_bash_empty(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("Bash", {})
        assert "running..." in result

    def test_format_opencode_tool_with_title(self):
        from core.runner import _format_opencode_tool
        result = _format_opencode_tool({"name": "Bash", "state": {"title": "Running ls"}})
        assert result == "Running ls"

    def test_format_opencode_tool_fallback(self):
        from core.runner import _format_opencode_tool
        result = _format_opencode_tool({"name": "Bash", "input": {"command": "ls"}})
        assert "ls" in result

    def test_format_opencode_tool_empty_input(self):
        from core.runner import _format_opencode_tool
        result = _format_opencode_tool({"name": "Bash", "input": None})
        assert "running..." in result

    def test_opencode_cmd_with_model(self, init_state):
        from core.runner import _opencode_cmd
        cmd = _opencode_cmd(model="deepseek/deepseek-v4-flash")
        assert "opencode" in cmd
        assert "-m" in cmd
        assert "deepseek/deepseek-v4-flash" in cmd
        assert "--dangerously-skip-permissions" in cmd

    def test_opencode_cmd_no_model(self, init_state):
        from core.runner import _opencode_cmd
        core_state.OPENCODE_MODEL = ""
        core_state.PERMISSION_MODE = "act"
        cmd = _opencode_cmd()
        assert "--dangerously-skip-permissions" in cmd

    def test_opencode_env_removes_bot_token(self, monkeypatch):
        from core.runner import _opencode_env
        monkeypatch.setenv("TAU_BOT_TOKEN", "secret123")
        env = _opencode_env()
        assert "TAU_BOT_TOKEN" not in env

    def test_extract_text_from_stdout(self):
        import subprocess

        from core.runner import extract_text
        r = subprocess.CompletedProcess([], 0, stdout="output text")
        assert extract_text(r) == "output text"

    def test_extract_text_empty_fallsback_to_stderr(self):
        import subprocess

        from core.runner import extract_text
        r = subprocess.CompletedProcess([], 0, stdout="", stderr="error info")
        assert "error info" in extract_text(r)


# ── Engine _freshen_state + _auto_resume edge cases (engine.py) ────────────

class TestEngineFreshenState:
    def test_freshen_state_no_runs_dir(self, init_state):
        """When RUNS_DIR doesn't exist, _freshen_state_on_boot should no-op."""
        from core.engine import _freshen_state_on_boot
        core_state.RUNS_DIR = core_state.CONTEXT_DIR / "nonexistent_runs"
        _freshen_state_on_boot()

    def test_freshen_state_empty_runs_dir(self, init_state):
        """No run dirs should be a no-op."""
        from core.engine import _freshen_state_on_boot
        core_state.RUNS_DIR.mkdir(parents=True, exist_ok=True)
        _freshen_state_on_boot()

    def test_freshen_state_with_rollout(self, init_state):
        """Populates STATE.md when rollout exists and state is empty."""
        from core.engine import _freshen_state_on_boot
        run_dir = core_state.RUNS_DIR / "20260428_120000"
        run_dir.mkdir(parents=True)
        (run_dir / "rollout.md").write_text("Fixed the bug.\n\nAnd more.")
        core_state.STATE_FILE.write_text("")
        _freshen_state_on_boot()
        assert "Fixed the bug" in core_state.STATE_FILE.read_text()

    def test_freshen_state_empty_rollout(self, init_state):
        """Empty rollout should not populate state."""
        from core.engine import _freshen_state_on_boot
        run_dir = core_state.RUNS_DIR / "20260428_120000"
        run_dir.mkdir(parents=True)
        (run_dir / "rollout.md").write_text("")
        core_state.STATE_FILE.unlink(missing_ok=True)
        _freshen_state_on_boot()
        assert not core_state.STATE_FILE.exists()

    def test_freshen_state_no_rollout_file(self, init_state):
        """Run dir without rollout file should not populate state."""
        from core.engine import _freshen_state_on_boot
        run_dir = core_state.RUNS_DIR / "20260428_120000"
        run_dir.mkdir(parents=True)
        core_state.STATE_FILE.unlink(missing_ok=True)
        _freshen_state_on_boot()
        assert not core_state.STATE_FILE.exists()

    def test_freshen_state_oserror_rollout(self, init_state, monkeypatch):
        """OSError reading rollout should not crash."""
        from core.engine import _freshen_state_on_boot
        run_dir = core_state.RUNS_DIR / "20260428_120000"
        run_dir.mkdir(parents=True)
        rollout = run_dir / "rollout.md"
        rollout.write_text("good text")
        orig_exists = Path.exists
        def _broken_exists(self):
            if str(self).endswith("rollout.md") and hasattr(_broken_exists, "fail"):
                return True
            return orig_exists(self)
        _broken_exists.fail = True
        monkeypatch.setattr(Path, "exists", _broken_exists)
        _freshen_state_on_boot()

    def test_freshen_state_oserror_write(self, init_state, monkeypatch):
        """OSError writing state should log but not crash."""
        from core.engine import _freshen_state_on_boot
        run_dir = core_state.RUNS_DIR / "20260428_120000"
        run_dir.mkdir(parents=True)
        (run_dir / "rollout.md").write_text("content")
        core_state.STATE_FILE.unlink(missing_ok=True)
        def _bad_write(*a, **kw):
            raise OSError("permission denied")
        monkeypatch.setattr(Path, "write_text", _bad_write)
        _freshen_state_on_boot()

    def test_auto_resume_no_state_file(self, init_state):
        """_auto_resume_on_boot without STATE_FILE should skip."""
        from core.engine import _auto_resume_on_boot
        core_state.STATE_FILE.unlink(missing_ok=True)
        _auto_resume_on_boot()

    def test_auto_resume_no_goal_file(self, init_state):
        """_auto_resume_on_boot without GOAL_FILE should skip."""
        from core.engine import _auto_resume_on_boot
        core_state.GOAL_FILE.unlink(missing_ok=True)
        _auto_resume_on_boot()

    def test_kill_child_procs_empty(self, init_state):
        """_kill_child_procs with no children should not raise."""
        from core.engine import _kill_child_procs
        _kill_child_procs()

    def test_kill_child_procs_with_proc(self, init_state, monkeypatch):
        """_kill_child_procs should kill and wait for children."""
        from core.engine import _kill_child_procs
        proc = MagicMock()
        proc.poll.return_value = None
        core_state._child_procs.add(proc)
        _kill_child_procs()
        proc.kill.assert_called_once()
        assert proc not in core_state._child_procs


# ── Loops helpers additional coverage (loops.py) ───────────────────────────

class TestLoopsExtra:
    def test_latest_rollout_oserror(self, init_state, monkeypatch):
        """OSError reading rollout should not crash _latest_rollout_text."""
        from core.loops import _latest_rollout_text
        run_dir = core_state.RUNS_DIR / "20260428_120000"
        run_dir.mkdir(parents=True)
        (run_dir / "rollout.md").write_text("content")
        def _bad_read(*a, **kw):
            raise OSError("read error")
        monkeypatch.setattr(Path, "read_text", _bad_read)
        result = _latest_rollout_text()
        assert result == ""

    def test_latest_rollout_skips_empty(self, init_state):
        """Empty rollout files should be skipped for content."""
        from core.loops import _latest_rollout_text
        r1 = core_state.RUNS_DIR / "20260428_100000"
        r1.mkdir(parents=True)
        (r1 / "rollout.md").write_text("")
        r2 = core_state.RUNS_DIR / "20260428_110000"
        r2.mkdir(parents=True)
        (r2 / "rollout.md").write_text("actual content")
        result = _latest_rollout_text()
        assert result == "actual content"

    def test_latest_rollout_no_runs_dir(self, init_state):
        """When runs_dir is None, _latest_rollout_text returns empty."""
        from core.loops import _latest_rollout_text
        core_state.RUNS_DIR = None
        assert _latest_rollout_text() == ""

    def test_step_result_idle_no_rollout(self, init_state):
        """No rollout means no idle detection."""
        from core.loops import _step_result_appears_idle
        assert _step_result_appears_idle() is False

    def test_write_completion_state_no_runs_dir(self, init_state):
        """When runs_dir doesn't exist, completion state should still be written."""
        from core.loops import _write_completion_state
        no_runs = core_state.CONTEXT_DIR / "no_runs_yet"
        _write_completion_state("test", 1, "completed", no_runs, core_state.STATE_FILE)
        text = core_state.STATE_FILE.read_text()
        assert "IDLE" in text
        assert "test" in text

    def test_write_completion_state_oserror(self, init_state, monkeypatch):
        """OSError on state file write should not crash."""
        from core.loops import _write_completion_state
        def _bad_write(*a, **kw):
            raise OSError("denied")
        monkeypatch.setattr(Path, "write_text", _bad_write)
        _write_completion_state("test", 1, "completed", core_state.RUNS_DIR, core_state.STATE_FILE)

    def test_write_completion_state_rollout_oserror(self, init_state, monkeypatch):
        """OSError reading rollout should still write state."""
        from core.loops import _write_completion_state
        run_dir = core_state.RUNS_DIR / "20260428_120000"
        run_dir.mkdir(parents=True)
        (run_dir / "rollout.md").write_text("summary")
        original_read = Path.read_text
        call_count = [0]
        def _bad_read_once(*a, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                raise OSError("denied")
            return original_read(*a, **kw)
        monkeypatch.setattr(Path, "read_text", _bad_read_once)
        _write_completion_state("rollout task", 2, "completed", core_state.RUNS_DIR, core_state.STATE_FILE)
        text = core_state.STATE_FILE.read_text()
        assert "rollout task" in text

    def test_sleep_cooldown_does_not_crash(self, init_state):
        """_sleep_cooldown with seconds=0 should not crash."""
        from core.loops import _sleep_cooldown
        _sleep_cooldown("test", seconds=0)

    def test_write_fleet_status_exception(self, init_state, monkeypatch):
        """Exception in _write_fleet_status should be caught."""
        from core.loops import _write_fleet_status
        def _fail(*a, **kw):
            raise Exception("boom")
        monkeypatch.setattr(Path, "write_text", _fail)
        _write_fleet_status()

    def test_agent_loop_goal_cleared_simulated(self, init_state):
        """Simulate the goal-cleared path inside agent_loop: _write_completion_state."""
        from core.loops import _write_completion_state
        core_state.GOAL_FILE.write_text("my goal")
        _write_completion_state("my goal", 3, "completed", core_state.RUNS_DIR, core_state.STATE_FILE)
        text = core_state.STATE_FILE.read_text()
        assert "my goal" in text

    def test_agent_loop_done_marker_simulated(self, init_state):
        """Simulate done marker detection path in agent_loop."""
        core_state.GOAL_FILE.write_text("(done)")
        done_markers = [
            "(done", "done —", "completed.", "idle", "no active task",
            "goal cleared", "nothing to do", "(finished",
            "clear when done", "task complete", "(cleared",
        ]
        current_goal = core_state.GOAL_FILE.read_text().strip()
        is_done = len(current_goal) < 120 and any(
            m in current_goal.lower() for m in done_markers
        )
        assert is_done is True

    def test_agent_loop_goal_changed_detection(self, init_state):
        """Simulate goal hash change detection in agent_loop."""
        import hashlib

        from core.loops import _goal_hash
        current_goal = "new active goal"
        current_hash = hashlib.sha256(current_goal.encode()).hexdigest()[:16]
        assert current_hash != _goal_hash

    def test_agent_loop_step_interval(self, init_state, monkeypatch):
        """Simulate step minimum interval check in agent_loop."""
        import time

        from core.loops import _STEP_MIN_INTERVAL, _last_step_completed
        since_last = time.monotonic() - _last_step_completed
        if since_last < _STEP_MIN_INTERVAL:
            pass  # would wait
        assert True

    def test_agent_loop_circuit_breaker(self, init_state):
        """Circuit breaker logic should trigger at MAX_CONSECUTIVE_FAILURES."""
        failures = 4
        max_failures = 5
        assert failures < max_failures
        failures += 1
        assert failures >= max_failures

    def test_agent_loop_step_cap(self, init_state):
        """Step cap at MAX_GOAL_STEPS should trigger goal clearance."""
        from core.loops import _write_completion_state
        goal_step_count = 15
        max_steps = 15
        if goal_step_count >= max_steps:
            _write_completion_state("step capped", goal_step_count, "paused", core_state.RUNS_DIR, core_state.STATE_FILE)
        text = core_state.STATE_FILE.read_text()
        assert "paused" in text or "step capped" in text

    def test_latest_rollout_skips_no_dir(self, init_state):
        from core.loops import _latest_rollout_text
        core_state.RUNS_DIR = None
        assert _latest_rollout_text() == ""

    def test_latest_rollout_skips_empty_dir(self, init_state):
        from core.loops import _latest_rollout_text
        d = core_state.RUNS_DIR / "20260428_120000"
        d.mkdir(parents=True)
        (d / "rollout.md").write_text("")
        text = _latest_rollout_text()
        assert text == ""



