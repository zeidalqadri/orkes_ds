"""Final coverage gap tests — targeting specific uncovered lines."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from core import state as core_state

# ── context.py uncovered lines: 34, 39-40, 51-52, 62-78 ───────────────────

class TestContextGaps:
    def test_load_bot_config_no_working_dir(self, init_state):
        from core.context import _load_bot_config
        core_state.WORKING_DIR = None
        assert _load_bot_config() == {}

    def test_load_bot_config_oserror(self, init_state):
        from core.context import _load_bot_config
        bot_json = core_state.CONTEXT_DIR / "bot.json"
        bot_json.write_text("{}")
        bot_json.chmod(0o000)
        try:
            result = _load_bot_config()
            assert result == {}
        finally:
            bot_json.chmod(0o644)

    def test_load_expert_registry_global_bad_json(self, init_state):
        from core.context import _load_expert_registry
        core_state.EXPERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.EXPERTS_FILE.write_text('{"builder": {"expertise": "build"}}')
        core_state._GLOBAL_EXPERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state._GLOBAL_EXPERTS_FILE.write_text("not-json")
        bot_json = core_state.CONTEXT_DIR / "bot.json"
        bot_json.write_text('{"expert_sources": ["global"]}')
        _load_expert_registry()


# ── prompt.py uncovered lines: 25, 32-33, 86-89, 98, 116, 136, 178, 206-207, 214, 218-219, 225

class TestPromptGaps:
    def test_cached_read_hit(self, init_state):
        from core.prompt import _cached_read
        f = core_state.CONTEXT_DIR / "test.txt"
        f.write_text("content")
        first = _cached_read(f)
        assert first == "content"
        second = _cached_read(f)
        assert second == "content"

    def test_cached_read_oserror(self, init_state, monkeypatch):
        from core.prompt import _cached_read
        f = core_state.CONTEXT_DIR / "test_os.txt"
        f.write_text("content")
        def _bad_read(*a, **kw):
            raise OSError("denied")
        monkeypatch.setattr(Path, "read_text", _bad_read)
        core_state.FILE_CACHE.evict(str(f))
        result = _cached_read(f)
        assert result is None

    def test_load_prompt_with_system_prompt(self, init_state):
        from core.context import ExpertContext
        from core.prompt import load_prompt
        core_state._expert_registry["builder"] = {
            "expertise": "build", "_source": "local",
            "system_prompt": "You are a builder",
            "name": "BuilderBot",
        }
        ctx = ExpertContext("builder")
        ctx.ensure_dirs()
        ctx.goal_file.write_text("build it")
        prompt = load_prompt(ctx=ctx, consume_inbox=True)
        assert "BuilderBot" in prompt
        assert "You are a builder" in prompt

    def test_load_prompt_learnings_truncated(self, init_state):
        from core.context import ExpertContext
        from core.prompt import load_prompt
        ctx = ExpertContext("builder")
        ctx.ensure_dirs()
        learnings = ctx.base / "learnings.md"
        learnings.write_text("x" * 50000)
        ctx.goal_file.write_text("do it")
        prompt = load_prompt(ctx=ctx)
        assert "Prior Knowledge" in prompt

    def test_load_prompt_with_summary(self, init_state):
        from datetime import datetime

        from core.prompt import load_prompt
        core_state._ctx_summaries.append(("test", "compressed summary text", datetime.now().isoformat()))
        core_state.GOAL_FILE.write_text("goal")
        prompt = load_prompt()
        assert "compressed summary text" in prompt

    def test_load_prompt_with_chatlog(self, init_state):
        from core.prompt import load_prompt, log_chat
        log_chat("user", "previous message")
        log_chat("bot", "previous reply")
        core_state.GOAL_FILE.write_text("goal")
        prompt = load_prompt()
        assert "Recent Telegram chat" in prompt
        assert "previous message" in prompt

    def test_log_chat_rotation(self, init_state):
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
            for _ in range(5):
                log_chat("user", "x" * 200000)
        files = list(core_state.CHATLOG_DIR.glob("*.jsonl"))
        assert len(files) <= 3

    def test_load_chatlog_json_decode_error(self, init_state):
        from core.prompt import load_chatlog
        core_state.CHATLOG_DIR.mkdir(parents=True, exist_ok=True)
        (core_state.CHATLOG_DIR / "20260428_150000.jsonl").write_text(
            '{"role": "user", "text": "valid"}\nnot-json\n'
        )
        result = load_chatlog(max_chars=10000)
        assert "valid" in result

    def test_load_chatlog_dedup(self, init_state):
        from core.prompt import load_chatlog, log_chat
        log_chat("user", "duplicate message")
        log_chat("user", "duplicate message")
        result = load_chatlog(max_chars=10000)
        assert result.count("duplicate message") == 1

    def test_load_chatlog_truncation(self, init_state):
        from core.prompt import load_chatlog, log_chat
        log_chat("user", "A" * 1000)
        result = load_chatlog(max_chars=50)
        assert len(result) < 100

    def test_load_chatlog_empty(self, init_state):
        from core.prompt import load_chatlog
        core_state.CHATLOG_DIR.mkdir(parents=True, exist_ok=True)
        (core_state.CHATLOG_DIR / "20260428_150000.jsonl").write_text(
            '{"role": "user", "text": ""}\n'
        )
        result = load_chatlog(max_chars=10000)
        assert result == ""

    def test_cached_read_not_exists(self, init_state):
        from core.prompt import _cached_read
        result = _cached_read(core_state.CONTEXT_DIR / "nonexistent.txt")
        assert result is None


# ── engine.py uncovered lines: 194-195, 216-217, 224-225, 245-246, 258-259, 270-271, 300, 364-432, 437-438

class TestEngineGaps:
    def test_init_config_all_env_overrides(self, mock_project_dir, monkeypatch):
        from core.engine import _init_config, _init_paths
        _init_paths(mock_project_dir)
        monkeypatch.setenv("MAX_CONCURRENT", "10")
        monkeypatch.setenv("MAX_RETRIES", "5")
        monkeypatch.setenv("OPENCODE_MODEL", "custom-model")
        monkeypatch.setenv("OPENCODE_TIMEOUT", "300")
        monkeypatch.setenv("IDLE_POLL_INTERVAL", "30")
        monkeypatch.setenv("COST_PER_M_INPUT", "0.01")
        monkeypatch.setenv("COST_PER_M_OUTPUT", "0.05")
        _init_config()
        assert core_state.MAX_CONCURRENT == 10
        assert core_state.MAX_RETRIES == 5
        assert core_state.OPENCODE_MODEL == "custom-model"
        assert core_state.IDLE_POLL_INTERVAL == 30

    def test_release_bot_lock_exception(self, init_state, monkeypatch):
        from core.engine import _release_bot_lock
        core_state.BOT_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.BOT_LOCK_FILE.write_text("123")
        def _bad_unlink(*a, **kw):
            raise Exception("boom")
        monkeypatch.setattr(Path, "unlink", _bad_unlink)
        _release_bot_lock()

    def test_freshen_state_preserves_existing(self, init_state):
        from core.engine import _freshen_state_on_boot
        core_state.STATE_FILE.write_text("Existing state")
        _freshen_state_on_boot()
        assert core_state.STATE_FILE.read_text() == "Existing state"

    def test_freshen_state_oserror_on_read(self, init_state, monkeypatch):
        from core.engine import _freshen_state_on_boot
        run_dir = core_state.RUNS_DIR / "20260428_120000"
        run_dir.mkdir(parents=True)
        (run_dir / "rollout.md").write_text("content")
        core_state.STATE_FILE.unlink(missing_ok=True)
        def _bad_read(*a, **kw):
            raise OSError("denied")
        monkeypatch.setattr(Path, "read_text", _bad_read)
        _freshen_state_on_boot()

    def test_freshen_state_oserror_on_write(self, init_state, monkeypatch):
        from core.engine import _freshen_state_on_boot
        run_dir = core_state.RUNS_DIR / "20260428_120000"
        run_dir.mkdir(parents=True)
        (run_dir / "rollout.md").write_text("rollout content")
        core_state.STATE_FILE.unlink(missing_ok=True)
        original_write = Path.write_text
        calls = []
        def _bad_write(self, *a, **kw):
            calls.append(str(self))
            if "STATE" in str(self):
                raise OSError("denied")
            return original_write(self, *a, **kw)
        monkeypatch.setattr(Path, "write_text", _bad_write)
        _freshen_state_on_boot()
        assert any("STATE" in c for c in calls)

    def test_auto_resume_no_goal_or_state(self, init_state):
        from core.engine import _auto_resume_on_boot
        core_state.GOAL_FILE = None
        core_state.STATE_FILE = None
        _auto_resume_on_boot()

    def test_auto_resume_no_goal_file_sentinel(self, init_state):
        from core.engine import _auto_resume_on_boot
        core_state.GOAL_FILE = core_state.CONTEXT_DIR / "GOAL.md"
        core_state.GOAL_FILE.write_text("")
        _auto_resume_on_boot()

    def test_cleanup_stale_step_oserror_in_context(self, init_state, monkeypatch):
        from core.engine import _cleanup_stale_step_msgs
        sub = core_state.CONTEXT_DIR / "builder"
        sub.mkdir(parents=True)
        (sub / ".step_msg").write_text("stale")
        calls = []
        original_unlink = Path.unlink
        def _unlink_check(self, *a, **kw):
            calls.append(str(self))
            if ".step_msg" in str(self):
                raise OSError("denied")
            return original_unlink(self, *a, **kw)
        monkeypatch.setattr(Path, "unlink", _unlink_check)
        _cleanup_stale_step_msgs()
        assert any(".step_msg" in c for c in calls)

    def test_acquire_lock_exception(self, init_state, monkeypatch):
        from core.engine import _acquire_bot_lock
        def _bad_mkdir(*a, **kw):
            raise Exception("disk full")
        monkeypatch.setattr(Path, "mkdir", _bad_mkdir)
        assert _acquire_bot_lock() is False

    def test_kill_child_procs_with_running(self, init_state):
        import subprocess

        from core.engine import _kill_child_procs
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(0.5)"],
        )
        core_state._child_procs.add(proc)
        _kill_child_procs()
        assert proc not in core_state._child_procs

    def test_kill_child_procs_kill_exception(self, init_state, monkeypatch):
        from core.engine import _kill_child_procs
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.kill.side_effect = Exception("kill denied")
        core_state._child_procs.add(mock_proc)
        _kill_child_procs()


# ── telegram.py uncovered: 78-79, 106-107, 116-118, 167-168

class TestTelegramGaps:
    def test_send_telegram_text_with_reply_to(self, init_state, monkeypatch, mock_telegram):
        from core.telegram import _send_telegram_text
        monkeypatch.setenv("TAU_BOT_TOKEN", "test:token")
        core_state.CHAT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.CHAT_ID_FILE.write_text("12345")
        result = _send_telegram_text("reply", reply_to=42)
        assert result is True

    def test_send_telegram_new_with_reply_to(self, init_state, monkeypatch, mock_telegram):
        from core.telegram import _send_telegram_new
        monkeypatch.setenv("TAU_BOT_TOKEN", "test:token")
        core_state.CHAT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.CHAT_ID_FILE.write_text("12345")
        result = _send_telegram_new("new reply", reply_to=42)
        assert result == 12345

    def test_send_telegram_new_exception(self, init_state, monkeypatch):
        from core.telegram import _send_telegram_new
        monkeypatch.setenv("TAU_BOT_TOKEN", "test:token")
        core_state.CHAT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.CHAT_ID_FILE.write_text("12345")
        def _fail(*a, **kw):
            raise Exception("network err")
        monkeypatch.setattr("requests.post", _fail)
        result = _send_telegram_new("fail")
        assert result is None

    def test_send_owner_alert_dm_fails_fallback(self, init_state, monkeypatch):
        from core.telegram import _send_owner_alert
        monkeypatch.setenv("TAU_BOT_TOKEN", "test:token")
        monkeypatch.setenv("TELEGRAM_OWNER_ID", "98765")
        core_state.CHAT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.CHAT_ID_FILE.write_text("12345")
        call_count = [0]
        def _post(*a, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("DM failed")
            m = MagicMock()
            m.ok = True
            m.status_code = 200
            m.json.return_value = {"ok": True, "result": {"message_id": 1}}
            return m
        monkeypatch.setattr("requests.post", _post)
        assert _send_owner_alert("dm fail") is True


# ── peers.py uncovered: 49-50 (exception handler)

class TestPeersGaps:
    def test_cleanup_peer_locks_exception(self, init_state, monkeypatch):
        from core.peers import _cleanup_peer_locks
        core_state.PEER_LOCK_DIR.mkdir(parents=True, exist_ok=True)
        (core_state.PEER_LOCK_DIR / "test.lock").write_text("stale")
        def _bad_iterdir(*a, **kw):
            raise Exception("boom")
        monkeypatch.setattr(Path, "iterdir", _bad_iterdir)
        _cleanup_peer_locks()


# ── loops.py uncovered priority lines

class TestLoopsGaps:
    def test_expert_loop_agent_not_yet_implemented(self):
        pass  # _expert_loop_agent doesn't exist in current loops.py
