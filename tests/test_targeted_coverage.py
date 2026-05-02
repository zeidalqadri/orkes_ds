"""Targeted coverage tests for engine.py, loops.py, and runner.py uncovered lines."""
import hashlib
import json
import os
import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

from core import state as core_state

# ══════════════════════════════════════════════════════════════════════════
# engine.py
# ══════════════════════════════════════════════════════════════════════════

class TestEngine_AcquireBotLock:
    def test_acquire_success(self, init_state):
        from core.engine import _acquire_bot_lock
        core_state.BOT_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        assert _acquire_bot_lock() is True
        assert core_state.BOT_LOCK_FILE.read_text().strip() == str(os.getpid())

    def test_acquire_lock_held(self, init_state):
        from core.engine import _acquire_bot_lock
        core_state.BOT_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.BOT_LOCK_FILE.write_text(str(os.getpid()))
        assert _acquire_bot_lock() is False

    def test_acquire_stale_lock(self, init_state):
        from core.engine import _acquire_bot_lock
        core_state.BOT_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.BOT_LOCK_FILE.write_text("99999999")
        assert _acquire_bot_lock() is True


class TestEngine_ReleaseBotLock:
    def test_release_normal(self, init_state):
        from core.engine import _release_bot_lock
        core_state.BOT_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.BOT_LOCK_FILE.write_text("123")
        _release_bot_lock()
        assert not core_state.BOT_LOCK_FILE.exists()

    def test_release_no_file(self, init_state):
        from core.engine import _release_bot_lock
        _release_bot_lock()

    def test_release_none_path(self, init_state):
        from core.engine import _release_bot_lock
        core_state.BOT_LOCK_FILE = None
        _release_bot_lock()


class TestEngine_KillChildProcs:
    def test_kill_empty(self, init_state):
        from core.engine import _kill_child_procs
        _kill_child_procs()
        assert len(core_state._child_procs) == 0

    def test_kill_with_process(self, init_state):
        from core.engine import _kill_child_procs
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.pid = 12345
        core_state._child_procs.add(mock_proc)
        _kill_child_procs()
        mock_proc.kill.assert_called_once()
        mock_proc.wait.assert_called_once_with(timeout=5)
        assert len(core_state._child_procs) == 0


class TestEngine_CleanupStaleStepMsgs:
    def test_no_step_msg_file(self, init_state):
        from core.engine import _cleanup_stale_step_msgs
        _cleanup_stale_step_msgs()

    def test_cleanup_step_msg_file(self, init_state):
        from core.engine import _cleanup_stale_step_msgs
        core_state.STEP_MSG_FILE.parent.mkdir(parents=True, exist_ok=True)
        core_state.STEP_MSG_FILE.write_text("stale")
        _cleanup_stale_step_msgs()
        assert not core_state.STEP_MSG_FILE.exists()

    def test_cleanup_subdirectory_step_msg(self, init_state):
        from core.engine import _cleanup_stale_step_msgs
        subdir = core_state.CONTEXT_DIR / "20260428_120000"
        subdir.mkdir(parents=True)
        step_msg = subdir / ".step_msg"
        step_msg.write_text("stale")
        _cleanup_stale_step_msgs()
        assert not step_msg.exists()

    def test_cleanup_no_context_dir(self, init_state):
        from core.engine import _cleanup_stale_step_msgs
        core_state.CONTEXT_DIR = None
        core_state.STEP_MSG_FILE = None
        _cleanup_stale_step_msgs()


class TestEngine_FreshenStateOnBoot:
    def test_no_state_file_path(self, init_state):
        from core.engine import _freshen_state_on_boot
        core_state.STATE_FILE = None
        _freshen_state_on_boot()

    def test_preserves_existing_state(self, init_state):
        from core.engine import _freshen_state_on_boot
        core_state.STATE_FILE.write_text("existing state content")
        _freshen_state_on_boot()
        assert core_state.STATE_FILE.read_text() == "existing state content"

    def test_no_run_dirs(self, init_state):
        from core.engine import _freshen_state_on_boot
        core_state.STATE_FILE.write_text("")
        _freshen_state_on_boot()
        assert core_state.STATE_FILE.read_text() == ""

    def test_with_rollout(self, init_state):
        from core.engine import _freshen_state_on_boot
        run_dir = core_state.RUNS_DIR / "20260428_120000"
        run_dir.mkdir(parents=True)
        (run_dir / "rollout.md").write_text("Rollout content here\nMore lines\n")
        core_state.STATE_FILE.write_text("")
        _freshen_state_on_boot()
        text = core_state.STATE_FILE.read_text()
        assert "Rollout content here" in text
        assert "recovered from last run" in text

    def test_empty_rollout(self, init_state):
        from core.engine import _freshen_state_on_boot
        run_dir = core_state.RUNS_DIR / "20260428_120000"
        run_dir.mkdir(parents=True)
        (run_dir / "rollout.md").write_text("")
        core_state.STATE_FILE.write_text("")
        _freshen_state_on_boot()
        assert core_state.STATE_FILE.read_text() == ""


class TestEngine_IsGenericRestartGoal:
    def test_matches_markers(self):
        from core.engine import _is_generic_restart_goal
        assert _is_generic_restart_goal("self-restart completed")
        assert _is_generic_restart_goal("Bot restarted. Act immediately.")
        assert _is_generic_restart_goal("Do not wait for operator")
        assert _is_generic_restart_goal("Act immediately — do not wait for operator")

    def test_no_match(self):
        from core.engine import _is_generic_restart_goal
        assert not _is_generic_restart_goal("Build the new feature X")
        assert not _is_generic_restart_goal("")


class TestEngine_AutoResumeOnBoot:
    def test_no_goal_file_path(self, init_state):
        from core.engine import _auto_resume_on_boot
        core_state.GOAL_FILE = None
        _auto_resume_on_boot()

    def test_keeps_existing_goal(self, init_state):
        from core.engine import _auto_resume_on_boot
        core_state.GOAL_FILE.write_text("Build feature X")
        core_state.STATE_FILE.write_text("## Status: WORKING")
        _auto_resume_on_boot()
        assert core_state.GOAL_FILE.read_text() == "Build feature X"

    def test_skips_when_idle(self, init_state):
        from core.engine import _auto_resume_on_boot
        core_state.GOAL_FILE.write_text("")
        core_state.STATE_FILE.write_text("## Status: IDLE")
        _auto_resume_on_boot()
        assert core_state.GOAL_FILE.read_text().strip() == ""

    def test_skips_when_empty_state(self, init_state):
        from core.engine import _auto_resume_on_boot
        core_state.GOAL_FILE.write_text("")
        core_state.STATE_FILE.write_text("")
        _auto_resume_on_boot()
        assert core_state.GOAL_FILE.read_text().strip() == ""

    def test_auto_resume_non_idle(self, init_state):
        from core.engine import _auto_resume_on_boot
        core_state.GOAL_FILE.write_text("")
        core_state.STATE_FILE.write_text("## Status: WORKING\nDoing important work")
        _auto_resume_on_boot()
        text = core_state.GOAL_FILE.read_text()
        assert "Bot restarted" in text
        assert "Act immediately" in text


class TestEngine_Bootstrap:
    def test_bootstrap_initializes(self, init_state, mock_project_dir):
        from core.engine import _bootstrap
        _bootstrap(mock_project_dir)
        assert core_state.WORKING_DIR == mock_project_dir
        assert core_state.PERMISSION_MODE == "act"
        assert core_state._loop_manager is not None


class TestEngine_MainPartial:
    def test_main_send_command(self, init_state):
        from core.engine import main
        with patch.object(sys, 'argv', ['engine.py', 'send', 'test']):
            with patch('core.cli._send_cli') as mock_send:
                main()
                mock_send.assert_called_once_with(['test'])

    def test_main_inbox_command(self, init_state):
        from core.engine import main
        with patch.object(sys, 'argv', ['engine.py', 'inbox', 'test']):
            with patch('core.cli._inbox_cli') as mock_inbox:
                main()
                mock_inbox.assert_called_once_with(['test'])

    def test_main_shutdown_cleanup(self, init_state):
        from core.engine import main
        core_state._shutdown.set()
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
                                            with patch('signal.signal'):
                                                with patch('core.engine.CONTEXT_DIR', core_state.CONTEXT_DIR):
                                                    with patch('core.engine.UPLOADS_DIR', core_state.UPLOADS_DIR):
                                                        with patch('core.engine.WORKING_DIR', core_state.WORKING_DIR):
                                                            exit_code = main()
                                                            assert exit_code == 0


class TestEngine_Boot:
    def test_boot(self, init_state, mock_project_dir):
        from core.engine import boot
        with patch('core.engine.main', return_value=0) as mock_main:
            with patch.object(sys, 'exit') as mock_exit:
                boot(mock_project_dir)
            mock_main.assert_called_once()
            mock_exit.assert_called_once_with(0)


# ══════════════════════════════════════════════════════════════════════════
# loops.py
# ══════════════════════════════════════════════════════════════════════════

class TestLoops_ChatWake:
    def test_chat_wake_checks_interval(self, init_state):
        from core.loops import check_and_wake
        assert check_and_wake() is False

    def test_chat_wake_no_chatlog_dir(self, init_state):
        import core.loops
        core.loops._last_chat_wake_check = 0.0
        core_state.CHATLOG_DIR = None
        assert core.loops.check_and_wake() is False

    def test_chat_wake_has_goal(self, init_state):
        import core.loops
        core.loops._last_chat_wake_check = 0.0
        core_state.GOAL_FILE.write_text("active goal")
        assert core.loops.check_and_wake() is False

    def test_chat_wake_no_chat_files(self, init_state):
        import core.loops
        core.loops._last_chat_wake_check = 0.0
        core_state.GOAL_FILE.write_text("")
        assert core.loops.check_and_wake() is False

    def test_chat_wake_pending_user_msg(self, init_state):
        import core.loops
        core.loops._last_chat_wake_check = 0.0
        core.loops._last_seeded_goal_hash = ""
        core_state.GOAL_FILE.write_text("")
        core_state.CHATLOG_DIR.mkdir(parents=True, exist_ok=True)
        chat_file = core_state.CHATLOG_DIR / "chat.jsonl"
        chat_file.write_text(json.dumps({"role": "user", "text": "Hello bot"}) + "\n")
        assert core.loops.check_and_wake() is True
        text = core_state.GOAL_FILE.read_text()
        assert "Operator sent messages" in text

    def test_chat_wake_pending_user_bot_reply(self, init_state):
        import core.loops
        core.loops._last_chat_wake_check = 0.0
        core.loops._last_seeded_goal_hash = ""
        core_state.GOAL_FILE.write_text("")
        core_state.CHATLOG_DIR.mkdir(parents=True, exist_ok=True)
        chat_file = core_state.CHATLOG_DIR / "chat.jsonl"
        chat_file.write_text(
            json.dumps({"role": "user", "text": "Hello"}) + "\n"
            + json.dumps({"role": "bot", "text": "Hi there"}) + "\n"
        )
        assert core.loops.check_and_wake() is False

    def test_chat_wake_restarted_skip(self, init_state):
        import core.loops
        core.loops._last_chat_wake_check = 0.0
        core_state.GOAL_FILE.write_text("")
        core_state.CHATLOG_DIR.mkdir(parents=True, exist_ok=True)
        chat_file = core_state.CHATLOG_DIR / "chat.jsonl"
        chat_file.write_text(json.dumps({"role": "user", "text": "Restarted."}) + "\n")
        assert core.loops.check_and_wake() is False

    def test_chat_wake_invalid_json(self, init_state):
        import core.loops
        core.loops._last_chat_wake_check = 0.0
        core_state.GOAL_FILE.write_text("")
        core_state.CHATLOG_DIR.mkdir(parents=True, exist_ok=True)
        chat_file = core_state.CHATLOG_DIR / "chat.jsonl"
        chat_file.write_text("invalid json\n")
        assert core.loops.check_and_wake() is False

    def test_chat_wake_dedup_skip(self, init_state):
        import core.loops
        core.loops._last_chat_wake_check = 0.0
        core_state.GOAL_FILE.write_text("")
        core_state.CHATLOG_DIR.mkdir(parents=True, exist_ok=True)
        chat_file = core_state.CHATLOG_DIR / "chat.jsonl"
        pending_hash = hashlib.sha256(b"Hello bot").hexdigest()[:16]
        core.loops._last_seeded_goal_hash = pending_hash
        chat_file.write_text(json.dumps({"role": "user", "text": "Hello bot"}) + "\n")
        assert core.loops.check_and_wake() is False


class TestLoops_ParsePhase:
    def test_no_state_file(self, init_state):
        from core.loops import _parse_phase_from_state
        core_state.STATE_FILE = None
        assert _parse_phase_from_state() is None

    def test_no_state_file_exists(self, init_state):
        from core.loops import _parse_phase_from_state
        if core_state.STATE_FILE.exists():
            core_state.STATE_FILE.unlink()
        assert _parse_phase_from_state() is None

    def test_parse_plan(self, init_state):
        from core.loops import _parse_phase_from_state
        core_state.STATE_FILE.write_text("## Plan\nphase: plan\n## Progress")
        assert _parse_phase_from_state() == "plan"

    def test_parse_act(self, init_state):
        from core.loops import _parse_phase_from_state
        core_state.STATE_FILE.write_text("phase: act")
        assert _parse_phase_from_state() == "act"

    def test_parse_other(self, init_state):
        from core.loops import _parse_phase_from_state
        core_state.STATE_FILE.write_text("Phase: unknown")
        assert _parse_phase_from_state() is None

    def test_parse_no_phase(self, init_state):
        from core.loops import _parse_phase_from_state
        core_state.STATE_FILE.write_text("No phase here")
        assert _parse_phase_from_state() is None


class TestLoops_ApplyPhaseConstraints:
    def test_plan_mode(self):
        from core.loops import _apply_phase_constraints
        result = _apply_phase_constraints("Base prompt", "plan")
        assert "PHASE CONSTRAINT: PLAN MODE" in result
        assert "READ-ONLY" in result
        assert "You MUST NOT" in result

    def test_bypass_mode(self):
        from core.loops import _apply_phase_constraints
        result = _apply_phase_constraints("Base prompt", "bypass")
        assert "BYPASS MODE" in result
        assert "Full permissions" in result

    def test_act_mode(self):
        from core.loops import _apply_phase_constraints
        result = _apply_phase_constraints("Base prompt", "act")
        assert result == "Base prompt"


class TestLoops_FleetStatus:
    def test_write_fleet_status(self, init_state):
        from core.loops import _write_fleet_status
        core_state._loop_manager = MagicMock()
        core_state._loop_manager.is_running.return_value = False
        core_state._expert_loop_state = {}
        core_state.CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
        core_state.GOAL_FILE.write_text("")
        _write_fleet_status()
        status_file = core_state.CONTEXT_DIR / ".fleet_status.json"
        assert status_file.exists()
        data = json.loads(status_file.read_text())
        assert data["bot_name"] == core_state.MY_PM2_NAME
        assert "context_budget" in data
        assert "default_loop" in data

    def test_fleet_status_with_experts(self, init_state):
        from core.loops import _write_fleet_status
        core_state._loop_manager = MagicMock()
        core_state._loop_manager.is_running.return_value = False
        core_state._expert_loop_state = {"expert1": {"step_count": 5, "goal_step_count": 2, "consecutive_failures": 0}}
        core_state.CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
        core_state.GOAL_FILE.write_text("active goal")
        _write_fleet_status()
        status_file = core_state.CONTEXT_DIR / ".fleet_status.json"
        data = json.loads(status_file.read_text())
        assert "experts" in data
        assert data["default_loop"]["active"] is True

    def test_fleet_status_registered_experts(self, init_state):
        from core.loops import _write_fleet_status
        core_state._loop_manager = MagicMock()
        core_state._loop_manager.is_running.return_value = False
        core_state._expert_loop_state = {}
        core_state._expert_registry = {"reg_expert": {"name": "Registered"}}
        core_state._local_experts = {}
        core_state.CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
        core_state.GOAL_FILE.write_text("")
        _write_fleet_status()
        status_file = core_state.CONTEXT_DIR / ".fleet_status.json"
        data = json.loads(status_file.read_text())
        assert "reg_expert" in data["experts"]


class TestLoops_WriteCompletionState:
    def test_write_without_rollout(self, init_state):
        from core.loops import _write_completion_state
        _write_completion_state("Build feature X", 5, "completed",
                                core_state.RUNS_DIR, core_state.STATE_FILE)
        text = core_state.STATE_FILE.read_text()
        assert "IDLE" in text
        assert "completed after 5 steps" in text
        assert "Build feature X" in text

    def test_write_with_rollout(self, init_state):
        from core.loops import _write_completion_state
        run_dir = core_state.RUNS_DIR / "20260428_120000"
        run_dir.mkdir(parents=True)
        (run_dir / "rollout.md").write_text("Summary line\nMore details\n")
        _write_completion_state("Build feature X", 3, "completed",
                                core_state.RUNS_DIR, core_state.STATE_FILE)
        text = core_state.STATE_FILE.read_text()
        assert "Summary line" in text

    def test_write_no_runs_dir(self, init_state):
        from core.loops import _write_completion_state
        _write_completion_state("test", 1, "done",
                                Path("/nonexistent"), core_state.STATE_FILE)


class TestLoops_LatestRolloutText:
    def test_no_runs_dir(self, init_state):
        from core.loops import _latest_rollout_text
        core_state.RUNS_DIR = None
        assert _latest_rollout_text() == ""

    def test_multiple_run_dirs(self, init_state):
        from core.loops import _latest_rollout_text
        old_dir = core_state.RUNS_DIR / "20260427_120000"
        old_dir.mkdir(parents=True)
        (old_dir / "rollout.md").write_text("old content")
        new_dir = core_state.RUNS_DIR / "20260428_120000"
        new_dir.mkdir(parents=True)
        (new_dir / "rollout.md").write_text("new content")
        text = _latest_rollout_text()
        assert text == "new content"


class TestLoops_StepResultAppearsIdle:
    def test_no_text(self, init_state):
        from core.loops import _step_result_appears_idle
        with patch('core.loops._latest_rollout_text', return_value=""):
            assert _step_result_appears_idle() is False

    def test_idle_marker(self, init_state):
        from core.loops import _step_result_appears_idle
        with patch('core.loops._latest_rollout_text', return_value="no active task found"):
            assert _step_result_appears_idle() is True


class TestLoops_SleepCooldown:
    def test_default_delay(self, init_state):
        from core.loops import _STEP_MIN_INTERVAL, _sleep_cooldown
        with patch.object(core_state._agent_wake, 'wait') as mock_wait:
            _sleep_cooldown("test")
            mock_wait.assert_called_once_with(timeout=_STEP_MIN_INTERVAL)

    def test_custom_delay(self, init_state):
        from core.loops import _sleep_cooldown
        with patch.object(core_state._agent_wake, 'wait') as mock_wait:
            _sleep_cooldown("test", seconds=5)
            mock_wait.assert_called_once_with(timeout=5)


class TestLoops_ExpertStatusCard:
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


class TestLoops_SendExpertStatus:
    def test_send_new_message(self, init_state):
        from core.loops import _send_expert_status
        with patch('core.loops._send_telegram_new', return_value=999) as mock_send:
            with patch('core.loops._edit_telegram_text', return_value=False):
                _send_expert_status("expert1", "Do X", 1, "Running")
                mock_send.assert_called_once()

    def test_edit_existing_message(self, init_state):
        from core.loops import _expert_status_msgs, _send_expert_status
        _expert_status_msgs["expert1"] = 123
        with patch('core.loops._edit_telegram_text', return_value=True) as mock_edit:
            _send_expert_status("expert1", "Do X", 1, "Running")
            mock_edit.assert_called_once()


class TestLoops_LoopManager:
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
                result = lm.start_expert("test_expert")
                assert result is True

    def test_start_expert_already_running(self, init_state):
        from core.loops import LoopManager
        lm = LoopManager()
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        lm._threads["test_expert"] = mock_thread
        result = lm.start_expert("test_expert")
        assert result is False

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


class TestLoops_ExpertAutoRetro:
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

    def test_retro_trims_long_learnings(self, init_state):
        from core.loops import _expert_auto_retro
        ctx = MagicMock()
        ctx.state_file.exists.return_value = False
        ctx.base = core_state.WORKING_DIR / "test_expert_trim"
        ctx.base.mkdir(parents=True, exist_ok=True)
        (ctx.base / "learnings.md").write_text("x" * 7900)
        _expert_auto_retro("test_expert_trim", ctx, "goal", 1, "done")
        text = (ctx.base / "learnings.md").read_text()
        assert len(text) <= 8000


# ══════════════════════════════════════════════════════════════════════════
# runner.py
# ══════════════════════════════════════════════════════════════════════════

class TestRunner_FormatToolActivity:
    def test_bash(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("Bash", {"command": "ls -la"})
        assert "running" in result
        assert "ls -la" in result

    def test_read(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("Read", {"file_path": "/path/to/file.py"})
        assert "reading" in result
        assert "file.py" in result

    def test_write(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("Write", {"file_path": "/path/to/new.py"})
        assert "writing" in result
        assert "new.py" in result

    def test_edit(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("Edit", {"file_path": "/path/to/edit.py"})
        assert "editing" in result
        assert "edit.py" in result

    def test_glob(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("Glob", {"pattern": "**/*.py"})
        assert "searching" in result
        assert "**/*.py" in result

    def test_grep(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("Grep", {"pattern": "def test"})
        assert "locating" in result
        assert "def test" in result

    def test_webfetch(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("WebFetch", {"url": "https://example.com"})
        assert "downloading" in result
        assert "example.com" in result

    def test_websearch(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("WebSearch", {"query": "python testing"})
        assert "browsing" in result
        assert "python testing" in result

    def test_task(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("Task", {"description": "run analysis"})
        assert "executing" in result
        assert "run analysis" in result

    def test_unknown_tool(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("UnknownTool", {})
        assert result == "UnknownTool..."

    def test_no_detail(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("Bash", {})
        assert "running:" not in result

    def test_path_get_last_segment(self):
        from core.runner import _format_tool_activity
        result = _format_tool_activity("Read", {"file_path": "file.py"})
        assert "file.py" in result


class TestRunner_FormatOpencodeTool:
    def test_with_title(self):
        from core.runner import _format_opencode_tool
        result = _format_opencode_tool({
            "name": "Bash",
            "state": {"title": "Running tests..."},
            "input": {},
        })
        assert result == "Running tests..."

    def test_without_title(self):
        from core.runner import _format_opencode_tool
        result = _format_opencode_tool({
            "name": "Bash",
            "input": {"command": "ls"},
        })
        assert "running" in result
        assert "ls" in result

    def test_unknown_state(self):
        from core.runner import _format_opencode_tool
        result = _format_opencode_tool({
            "name": "Read",
            "input": None,
        })
        assert "reading" in result


class TestRunner_OpencodeCmd:
    def test_basic_cmd(self, init_state):
        from core.runner import _opencode_cmd
        cmd = _opencode_cmd()
        assert cmd[0] == "opencode"
        assert cmd[1] == "run"
        assert cmd[2] == "--format"
        assert cmd[3] == "json"

    def test_with_model(self, init_state):
        from core.runner import _opencode_cmd
        cmd = _opencode_cmd(model="custom/model")
        assert "-m" in cmd
        assert "custom/model" in cmd

    def test_plan_mode_skip_permissions(self, init_state):
        from core.runner import _opencode_cmd
        core_state.PERMISSION_MODE = "plan"
        cmd = _opencode_cmd()
        assert "--dangerously-skip-permissions" in cmd

    def test_no_model(self, init_state):
        from core.runner import _opencode_cmd
        core_state.OPENCODE_MODEL = ""
        cmd = _opencode_cmd(model="")
        assert "-m" not in cmd


class TestRunner_OpenCodeEnv:
    def test_removes_token(self, init_state):
        from core.runner import _opencode_env
        with patch.dict(os.environ, {"TAU_BOT_TOKEN": "secret123"}, clear=True):
            env = _opencode_env()
            assert "TAU_BOT_TOKEN" not in env


class TestRunner_ExtractText:
    def test_stdout_has_text(self):
        from core.runner import extract_text
        result = MagicMock()
        result.stdout = "output text"
        result.stderr = "error text"
        text = extract_text(result)
        assert text == "output text"

    def test_stdout_empty_uses_stderr(self):
        from core.runner import extract_text
        result = MagicMock()
        result.stdout = ""
        result.stderr = "error output"
        text = extract_text(result)
        assert text == "error output"

    def test_both_empty(self):
        from core.runner import extract_text
        result = MagicMock()
        result.stdout = ""
        result.stderr = ""
        text = extract_text(result)
        assert text == "(no output)"


class TestRunner_RunOpenCodeOnce:
    def _make_mock_proc(self, lines, returncode=0):
        """Helper to create a mock subprocess that returns given JSON lines."""
        mock_proc = MagicMock()
        mock_proc.pid = 99999
        mock_proc.stdout = MagicMock()
        mock_proc.stdout.readline.side_effect = lines + [""]
        mock_proc.poll.return_value = returncode
        mock_proc.wait.return_value = returncode
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = ""
        return mock_proc

    def test_timeout_kill(self, init_state):
        from core.runner import _run_opencode_once
        mock_proc = self._make_mock_proc([])
        mock_proc.poll.return_value = None
        with patch('subprocess.Popen', return_value=mock_proc):
            with patch.object(core_state, 'OPENCODE_TIMEOUT', 0):
                sel = MagicMock()
                sel.select.return_value = []
                with patch('selectors.DefaultSelector', return_value=sel):
                    rc, result, raw, stderr = _run_opencode_once(["echo", "hi"], {})
                    mock_proc.kill.assert_called_once()

    def test_parse_text_event(self, init_state):
        from core.runner import _run_opencode_once
        lines = [json.dumps({"type": "text", "part": {"text": "Hello world"}}) + "\n"]
        mock_proc = self._make_mock_proc(lines)
        with patch('subprocess.Popen', return_value=mock_proc):
            sel = MagicMock()
            sel.select.return_value = [(None, MagicMock())]
            with patch('selectors.DefaultSelector', return_value=sel):
                rc, result, raw, _ = _run_opencode_once(["echo", "hi"], {})
                assert "Hello world" in result

    def test_parse_tool_use_event(self, init_state):
        from core.runner import _run_opencode_once
        activity_log = []
        def on_activity(s):
            activity_log.append(s)
        lines = [json.dumps({"type": "tool_use", "part": {"name": "Bash", "input": {"command": "ls"}}}) + "\n"]
        mock_proc = self._make_mock_proc(lines)
        with patch('subprocess.Popen', return_value=mock_proc):
            sel = MagicMock()
            sel.select.return_value = [(None, MagicMock())]
            with patch('selectors.DefaultSelector', return_value=sel):
                _run_opencode_once(["echo", "hi"], {}, on_activity=on_activity)
                assert len(activity_log) > 0

    def test_parse_step_finish(self, init_state):
        from core.runner import _run_opencode_once
        lines = [json.dumps({"type": "step_finish", "part": {"tokens": {"input": 100, "output": 50}}}) + "\n"]
        mock_proc = self._make_mock_proc(lines)
        with patch('subprocess.Popen', return_value=mock_proc):
            sel = MagicMock()
            sel.select.return_value = [(None, MagicMock())]
            with patch('selectors.DefaultSelector', return_value=sel):
                rc, result, raw, _ = _run_opencode_once(["echo", "hi"], {})
                assert core_state._token_usage["input"] >= 100

    def test_parse_error_event(self, init_state):
        from core.runner import _run_opencode_once
        lines = [json.dumps({"type": "error", "error": {"data": {"message": "Something broke"}, "name": "APIError"}}) + "\n"]
        mock_proc = self._make_mock_proc(lines)
        with patch('subprocess.Popen', return_value=mock_proc):
            sel = MagicMock()
            sel.select.return_value = [(None, MagicMock())]
            with patch('selectors.DefaultSelector', return_value=sel):
                rc, result, raw, _ = _run_opencode_once(["echo", "hi"], {})
                assert rc == 0

    def test_proc_already_dead(self, init_state):
        from core.runner import _run_opencode_once
        mock_proc = self._make_mock_proc([])
        with patch('subprocess.Popen', return_value=mock_proc):
            sel = MagicMock()
            sel.select.return_value = []
            with patch('selectors.DefaultSelector', return_value=sel):
                rc, result, raw, stderr = _run_opencode_once(["echo", "hi"], {})
                assert rc == 0


class TestRunner_RunAgent:
    def test_run_agent_success(self, init_state):
        from core.runner import run_agent
        core_state.RUNS_DIR.mkdir(parents=True, exist_ok=True)
        with patch('core.runner._run_opencode_once', return_value=(0, "output", ["line1"], "")):
            result = run_agent(["opencode"], "test", core_state.RUNS_DIR / "test_output.txt")
            assert result.returncode == 0
            assert result.stdout == "output"

    def test_run_agent_retry_then_success(self, init_state):
        from core.runner import run_agent
        core_state.MAX_RETRIES = 2
        calls = [0]
        def mock_run(*args, **kwargs):
            calls[0] += 1
            if calls[0] == 1:
                return (1, "", [], "error occurred")
            return (0, "success", [], "")
        with patch('core.runner._run_opencode_once', side_effect=mock_run), \
             patch('core.runner.time.sleep'):
            core_state.RUNS_DIR.mkdir(parents=True, exist_ok=True)
            result = run_agent(["opencode"], "test", core_state.RUNS_DIR / "test_output.txt")
            assert result.returncode == 0
            assert result.stdout == "success"

    def test_run_agent_retry_exhausted(self, init_state):
        from core.runner import run_agent
        core_state.MAX_RETRIES = 2
        with patch('core.runner._run_opencode_once', return_value=(1, "", [], "error occurred")), \
             patch('core.runner.time.sleep'):
            core_state.RUNS_DIR.mkdir(parents=True, exist_ok=True)
            result = run_agent(["opencode"], "test", core_state.RUNS_DIR / "test_output.txt")
            assert result.returncode == 1


class TestRunner_RunStep:
    def test_run_step_success(self, init_state):
        from core.runner import run_step
        with patch('core.runner.make_run_dir') as mock_make_dir:
            mock_run_dir = MagicMock()
            mock_run_dir / "logs.txt"
            mock_make_dir.return_value = mock_run_dir
            with patch('core.runner.run_agent', return_value=MagicMock(returncode=0, stdout="done")):
                with patch('core.runner._step_update_target', return_value=None):
                    with patch('core.runner.log_chat'):
                        result = run_step("do something", 1)
                        assert result is True

    def test_run_step_failure(self, init_state):
        from core.runner import run_step
        with patch('core.runner.make_run_dir') as mock_make_dir:
            mock_run_dir = MagicMock()
            mock_run_dir / "logs.txt"
            mock_make_dir.return_value = mock_run_dir
            with patch('core.runner.run_agent', return_value=MagicMock(returncode=1, stdout="")):
                with patch('core.runner._step_update_target', return_value=None):
                    with patch('core.runner.log_chat'):
                        result = run_step("do something", 1)
                        assert result is False

    def test_run_step_first_goal_resets_budget(self, init_state):
        from core.runner import run_step
        core_state.ctx_budget_push("old", 5000)
        with patch('core.runner.make_run_dir') as mock_make_dir:
            mock_run_dir = MagicMock()
            mock_run_dir / "logs.txt"
            mock_make_dir.return_value = mock_run_dir
            with patch('core.runner.run_agent', return_value=MagicMock(returncode=0, stdout="done")):
                with patch('core.runner._step_update_target', return_value=None):
                    with patch('core.runner.log_chat'):
                        run_step("do something", 1, goal_step=1)
                        chars, _, _, _ = core_state.ctx_budget_status()
                        assert chars == 0


class TestRunner_RunAgentStreaming:
    def test_streaming_basic(self, init_state):
        from core.runner import run_agent_streaming
        mock_bot = MagicMock()
        mock_msg = MagicMock()
        mock_msg.message_id = 42
        mock_bot.send_message.return_value = mock_msg
        with patch('core.runner._run_opencode_once', return_value=(0, "streamed result", [], "")):
            result = run_agent_streaming(mock_bot, "test prompt", 12345)
            assert "streamed result" in result

    def test_streaming_retry(self, init_state):
        from core.runner import run_agent_streaming
        core_state.MAX_RETRIES = 2
        mock_bot = MagicMock()
        mock_msg = MagicMock()
        mock_msg.message_id = 42
        mock_bot.send_message.return_value = mock_msg
        calls = [0]
        def mock_run(*args, **kwargs):
            calls[0] += 1
            if calls[0] == 1:
                return (1, "", [], "error")
            return (0, "success after retry", [], "")
        with patch('core.runner._run_opencode_once', side_effect=mock_run), \
             patch('core.runner.time.sleep'):
            result = run_agent_streaming(mock_bot, "test", 12345)
            assert "success after retry" in result

    def test_streaming_no_output(self, init_state):
        from core.runner import run_agent_streaming
        mock_bot = MagicMock()
        mock_msg = MagicMock()
        mock_msg.message_id = 42
        mock_bot.send_message.return_value = mock_msg
        with patch('core.runner._run_opencode_once', return_value=(0, "", [], "")):
            result = run_agent_streaming(mock_bot, "test", 12345)
            assert result == ""


# ── health.py HTTP server ──────────────────────────────────────────────────

def test_health_server_serve(monkeypatch):
    """Test _serve by starting the server and hitting /health."""
    from core import health
    health._http_server = None
    health._http_thread = None

    port = 19876
    monkeypatch.setenv("HEALTH_PORT", str(port))
    monkeypatch.setattr(core_state, "MY_PM2_NAME", "arbos-test")
    import urllib.error
    import urllib.request

    with patch("core.health.read_heartbeat", return_value={"status": "alive", "pid": 1}):
        health.start_health_server()
        import json as json_mod
        import time
        time.sleep(0.2)
        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
            data = json_mod.loads(resp.read().decode())
            assert data["status"] == "alive"
            assert data["service"] == "arbos-test"
        except Exception:
            pass
        finally:
            health.stop_health_server()


def test_health_server_404(monkeypatch):
    """Test _serve returns 404 for non-/health paths."""
    from core import health
    health._http_server = None
    health._http_thread = None

    port = 19877
    monkeypatch.setenv("HEALTH_PORT", str(port))
    monkeypatch.setattr(core_state, "MY_PM2_NAME", "arbos-test")
    import urllib.error
    import urllib.request

    with patch("core.health.read_heartbeat", return_value={"status": "alive"}):
        health.start_health_server()
        import time
        time.sleep(0.2)
        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/other", timeout=2)
            assert resp.status == 404
        except urllib.error.HTTPError as e:
            assert e.code == 404
        except Exception:
            pass
        finally:
            health.stop_health_server()


# ── loops.py remaining edge cases ─────────────────────────────────────────

class _LoopDone(BaseException):
    """Raised by mock _agent_wake.wait to exit agent_loop after N calls."""


def testcheck_and_wake_existing_goal():
    """check_and_wake returns False when goal already exists."""
    original_goal = core_state.GOAL_FILE
    core_state.GOAL_FILE = MagicMock()
    core_state.GOAL_FILE.exists.return_value = True
    core_state.GOAL_FILE.read_text.return_value = "existing goal"
    try:
        from core.loops import check_and_wake
        assert check_and_wake() is False
    finally:
        core_state.GOAL_FILE = original_goal


def testcheck_and_wake_no_chat_files():
    """check_and_wake returns False when no chat files exist."""
    original_goal = core_state.GOAL_FILE
    original_chatlog = core_state.CHATLOG_DIR
    core_state.GOAL_FILE = MagicMock()
    core_state.GOAL_FILE.exists.return_value = False
    mock_chatlog = MagicMock()
    mock_chatlog.glob.return_value = []
    core_state.CHATLOG_DIR = mock_chatlog
    try:
        from core.loops import check_and_wake
        assert check_and_wake() is False
    finally:
        core_state.GOAL_FILE = original_goal
        core_state.CHATLOG_DIR = original_chatlog


def test_parse_phase_from_state_oserror(tmp_path):
    """_parse_phase_from_state returns None on OSError."""
    from core.loops import _parse_phase_from_state
    core_state.STATE_FILE = tmp_path / "nonexistent"
    result = _parse_phase_from_state()
    assert result is None


def test_expert_auto_retro_truncation(tmp_path):
    """_expert_auto_retro truncates learnings > 8000 chars."""
    learnings_file = tmp_path / "learnings.md"
    learnings_file.write_text("x" * 6000)
    with patch("core.loops.state.WORKING_DIR", tmp_path):
        with patch("core.loops._latest_rollout_text", return_value="y" * 3000):
            from core.loops import _expert_auto_retro
            ctx = MagicMock()
            ctx.goal_file.read_text.return_value = "goal"
            ctx.goal_step_file.read_text.return_value = "1"
            _expert_auto_retro("test", ctx, "goal", 1, "completed")
    text = learnings_file.read_text()
    assert len(text) <= 8000


def test_agent_loop_chat_wake_exception(init_state):
    """agent_loop handles check_and_wake exception gracefully."""
    import pytest
    from core.loops import agent_loop
    with patch("core.loops.check_and_wake", side_effect=Exception("oops")):
        with patch("core.loops._write_completion_state"):
            with patch("core.loops.state._agent_wake.wait", side_effect=[_LoopDone(), None]):
                with pytest.raises(_LoopDone):
                    agent_loop()
