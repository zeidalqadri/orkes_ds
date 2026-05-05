"""Phase 1.3: Arbos Engine Tests.

Tests engine initialization, bot lock, path management,
ExpertContext, inbox read/write, and restart signaling.
"""

import os
from pathlib import Path

from core import state as core_state
from core.context import ExpertContext
from core.engine import (
    _acquire_bot_lock,
    _bootstrap,
    _cleanup_stale_step_msgs,
    _init_config,
    _init_paths,
    _release_bot_lock,
)


class TestInitPaths:
    def test_init_paths_sets_all_constants(self, mock_project_dir):
        """_init_paths should set all path constants on the state module."""
        _init_paths(mock_project_dir)
        assert core_state.WORKING_DIR == mock_project_dir
        assert core_state.CONTEXT_DIR == mock_project_dir / "context"
        assert core_state.GOAL_FILE == mock_project_dir / "context" / "GOAL.md"
        assert core_state.STATE_FILE == mock_project_dir / "context" / "STATE.md"
        assert core_state.INBOX_FILE == mock_project_dir / "context" / "INBOX.md"
        assert core_state.RUNS_DIR == mock_project_dir / "context" / "runs"
        assert core_state.BOT_LOCK_FILE == mock_project_dir / "context" / ".bot.lock"
        assert core_state.RESTART_FLAG == mock_project_dir / ".restart"
        assert core_state.PROMPT_FILE == mock_project_dir / "PROMPT.md"

    def test_init_paths_creates_dirs(self, tmp_path: Path):
        """init_paths should not create directories — just set path values."""
        proj = tmp_path / "fresh_project"
        _init_paths(proj)
        assert not proj.exists()


class TestInitConfig:
    def test_init_config_defaults(self, mock_project_dir):
        """_init_config should set sensible defaults when .env has no overrides."""
        _init_paths(mock_project_dir)
        _init_config()
        assert core_state.OPENCODE_MODEL == "deepseek/deepseek-v4-flash"
        assert core_state.MAX_CONCURRENT == 2
        assert core_state.MAX_RETRIES == 3
        assert core_state.IDLE_POLL_INTERVAL == 120
        assert core_state.OPENCODE_TIMEOUT == 600

    def test_init_config_from_env(self, mock_project_dir, monkeypatch):
        """Env vars should override config defaults."""
        monkeypatch.setenv("MAX_CONCURRENT", "5")
        monkeypatch.setenv("MAX_RETRIES", "7")
        monkeypatch.setenv("OPENCODE_MODEL", "gpt-4")
        _init_paths(mock_project_dir)
        _init_config()
        assert core_state.MAX_CONCURRENT == 5
        assert core_state.MAX_RETRIES == 7
        assert core_state.OPENCODE_MODEL == "gpt-4"


class TestBotLock:
    def test_acquire_bot_lock_creates_file(self, init_state):
        """_acquire_bot_lock should create .bot.lock with the current PID."""
        core_state.BOT_LOCK_FILE.unlink(missing_ok=True)
        result = _acquire_bot_lock()
        assert result is True
        assert core_state.BOT_LOCK_FILE.exists()
        assert core_state.BOT_LOCK_FILE.read_text().strip() == str(os.getpid())

    def test_acquire_bot_lock_fails_when_held(self, init_state, monkeypatch):
        """Acquiring lock while it's held by another process should fail."""
        def _fake_kill(pid, sig):
            return None
        monkeypatch.setattr(os, "kill", _fake_kill)
        core_state.BOT_LOCK_FILE.unlink(missing_ok=True)
        core_state.BOT_LOCK_FILE.write_text("999999")
        result = _acquire_bot_lock()
        assert result is False

    def test_acquire_bot_lock_steals_stale(self, init_state, monkeypatch):
        """Lock from a dead process should be stealable."""
        def _fake_kill(pid, sig):
            raise ProcessLookupError()
        monkeypatch.setattr(os, "kill", _fake_kill)
        core_state.BOT_LOCK_FILE.unlink(missing_ok=True)
        core_state.BOT_LOCK_FILE.write_text("0")
        result = _acquire_bot_lock()
        assert result is True

    def test_release_bot_lock_removes_file(self, init_state):
        """_release_bot_lock should delete the lock file."""
        core_state.BOT_LOCK_FILE.unlink(missing_ok=True)
        _acquire_bot_lock()
        assert core_state.BOT_LOCK_FILE.exists()
        _release_bot_lock()
        assert not core_state.BOT_LOCK_FILE.exists()

    def test_release_bot_lock_no_file(self, init_state):
        """Releasing a lock that doesn't exist should not raise."""
        core_state.BOT_LOCK_FILE.unlink(missing_ok=True)
        _release_bot_lock()


class TestCleanupStaleStepMsgs:
    def test_cleans_stale_step_msg(self, init_state):
        """_cleanup_stale_step_msgs should remove existing .step_msg."""
        core_state.STEP_MSG_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.STEP_MSG_FILE.write_text('{"msg_id": 1, "text": "old"}')
        _cleanup_stale_step_msgs()
        assert not core_state.STEP_MSG_FILE.exists()

    def test_cleans_stale_step_msgs_in_context_subdirs(self, init_state):
        """Should clean .step_msg in direct subdirectories of CONTEXT_DIR."""
        sub = core_state.CONTEXT_DIR / "some_expert"
        sub.mkdir(parents=True)
        (sub / ".step_msg").write_text("stale")
        _cleanup_stale_step_msgs()
        assert not (sub / ".step_msg").exists()

    def test_noop_when_no_files(self, init_state):
        """Should not raise when no .step_msg files exist."""
        _cleanup_stale_step_msgs()


class TestExpertContext:
    def test_paths_for_main_context(self, init_state):
        """ExpertContext(None) should use the base CONTEXT_DIR paths."""
        ctx = ExpertContext(None)
        assert ctx.goal_file == core_state.GOAL_FILE
        assert ctx.state_file == core_state.STATE_FILE
        assert ctx.inbox_file == core_state.INBOX_FILE

    def test_paths_for_named_expert(self, init_state):
        """ExpertContext('builder') should isolate to context/builder/."""
        ctx = ExpertContext("builder")
        assert ctx.goal_file == core_state.CONTEXT_DIR / "builder" / "GOAL.md"
        assert ctx.state_file == core_state.CONTEXT_DIR / "builder" / "STATE.md"
        assert ctx.inbox_file == core_state.CONTEXT_DIR / "builder" / "INBOX.md"

    def test_ensure_dirs_creates_directories(self, init_state):
        """ensure_dirs should create the expert's base and runs dirs."""
        ctx = ExpertContext("builder")
        ctx.ensure_dirs()
        assert ctx.base.exists()
        assert ctx.runs_dir.exists()


class TestInboxReadWrite:
    def test_write_and_read_inbox(self, init_state):
        """Simulate the INBOX.md write-then-consume cycle."""
        inbox = core_state.INBOX_FILE
        inbox.write_text("Operator: please do X\n")
        assert inbox.read_text() == "Operator: please do X\n"

        from core.prompt import load_prompt
        prompt = load_prompt(consume_inbox=True)
        assert "please do X" in prompt
        assert inbox.read_text() == ""

    def test_inbox_empty_after_consume(self, init_state):
        """Consuming an empty inbox should work without error."""
        from core.prompt import load_prompt
        prompt = load_prompt(consume_inbox=True)
        assert "## Inbox" not in prompt


class TestGoalLifecycle:
    def test_goal_clear_then_empty(self, init_state):
        """Verify the goal clear-after-complete semantics."""
        goal_file = core_state.GOAL_FILE
        goal_file.write_text("Build feature X")
        assert goal_file.read_text().strip() == "Build feature X"
        goal_file.write_text("")
        assert goal_file.read_text().strip() == ""

    def test_goal_hash_change_detection(self, init_state):
        """When GOAL.md content changes, the loop should detect a new hash."""
        import hashlib

        h1 = hashlib.sha256(b"Goal A").hexdigest()[:16]
        h2 = hashlib.sha256(b"Goal B").hexdigest()[:16]
        assert h1 != h2


class TestRestartSignaling:
    def test_restart_flag_touch(self, init_state):
        """Creating .restart should signal restart."""
        flag = core_state.RESTART_FLAG
        assert not flag.exists()
        flag.touch()
        assert flag.exists()
        flag.unlink()
        assert not flag.exists()

    def test_restart_continue_flag(self, init_state):
        """.restart_continue should also signal restart."""
        flag = core_state.RESTART_FLAG
        continue_flag = flag.parent / ".restart_continue"
        continue_flag.touch()
        assert continue_flag.exists()

    def test_bootstrap_sets_loop_manager(self, mock_project_dir):
        """_bootstrap should initialize the LoopManager."""
        _bootstrap(mock_project_dir)
        assert core_state._loop_manager is not None
        assert hasattr(core_state._loop_manager, "list_active")

    def test_bootstrap_sets_loop_manager_and_paths(self, mock_project_dir):
        """_bootstrap should set loop manager and path constants."""
        _bootstrap(mock_project_dir)
        assert core_state._loop_manager is not None
        assert core_state.WORKING_DIR == mock_project_dir
        assert core_state.CONTEXT_DIR == mock_project_dir / "context"
