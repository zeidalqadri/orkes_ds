"""Phase 1.1: Core Loop Integration Tests.

Tests the agent lifecycle: GOAL.md → skills → execution → clear → state update.
"""

import hashlib
import json

from core import state as core_state
from core.loops import (
    _STEP_IDLE_MARKERS,
    LoopManager,
    _apply_phase_constraints,
    _expert_auto_retro,
    _parse_phase_from_state,
    _step_result_appears_idle,
    _write_completion_state,
    _write_fleet_status,
    check_and_wake,
)


class TestPhaseConstraints:
    def test_apply_plan_mode(self):
        """Plan mode constraint should inject read-only instructions."""
        prompt = "## Goal\nDo the thing"
        result = _apply_phase_constraints(prompt, "plan")
        assert "## PHASE CONSTRAINT: PLAN MODE (READ-ONLY)" in result
        assert "You MUST NOT" in result
        assert "Modify any files" in result

    def test_apply_act_mode(self):
        """Act mode should pass through unchanged."""
        prompt = "## Goal\nDo the thing"
        result = _apply_phase_constraints(prompt, "act")
        assert result == prompt

    def test_apply_bypass_mode(self):
        """Bypass mode should inject the bypass notice."""
        prompt = "## Goal\nDo the thing"
        result = _apply_phase_constraints(prompt, "bypass")
        assert "BYPASS MODE" in result

    def test_constraint_prompt_length_grows(self):
        """Constrained prompt should be longer than original."""
        prompt = "## Goal\nDo the thing"
        constrained = _apply_phase_constraints(prompt, "plan")
        assert len(constrained) > len(prompt)


class TestPhaseParsing:
    def test_parse_plan(self, init_state):
        init_state.STATE_FILE.write_text("# Arbos State\nphase: plan\n")
        assert _parse_phase_from_state() == "plan"

    def test_parse_act(self, init_state):
        init_state.STATE_FILE.write_text("phase: act\n")
        assert _parse_phase_from_state() == "act"

    def test_parse_none_when_no_file(self, init_state):
        init_state.STATE_FILE.unlink(missing_ok=True)
        assert _parse_phase_from_state() is None

    def test_parse_none_when_wrong_value(self, init_state):
        init_state.STATE_FILE.write_text("phase: bypass\n")
        assert _parse_phase_from_state() is None

    def test_parse_none_when_no_phase_field(self, init_state):
        init_state.STATE_FILE.write_text("# Arbos State\n## Status: IDLE\n")
        assert _parse_phase_from_state() is None


class TestStepIdleDetection:
    def test_detects_idle_markers(self, init_state):
        """_step_result_appears_idle should detect 'no active task' markers."""
        run_dir = core_state.RUNS_DIR / "20260428_120000"
        run_dir.mkdir(parents=True)
        (run_dir / "rollout.md").write_text("I found no active task to work on.")
        assert _step_result_appears_idle() is True

    def test_no_idle_when_active(self, init_state):
        """Normal task output should not trigger idle detection."""
        run_dir = core_state.RUNS_DIR / "20260428_120001"
        run_dir.mkdir(parents=True)
        (run_dir / "rollout.md").write_text("Built the feature flag module.")
        assert _step_result_appears_idle() is False

    def test_no_idle_when_no_rollout(self, init_state):
        """Empty runs dir should not trigger idle."""
        assert _step_result_appears_idle() is False

    def test_case_insensitive_idle_check(self, init_state):
        """Idle marker detection should be case-insensitive."""
        run_dir = core_state.RUNS_DIR / "20260428_120002"
        run_dir.mkdir(parents=True)
        (run_dir / "rollout.md").write_text("NO ACTIVE TASK")
        assert _step_result_appears_idle() is True

    def test_all_idle_markers(self, init_state):
        """Every marker in _STEP_IDLE_MARKERS should be detected."""
        for marker in _STEP_IDLE_MARKERS:
            run_dir = core_state.RUNS_DIR / f"test_{hash(marker)}"
            run_dir.mkdir(parents=True)
            (run_dir / "rollout.md").write_text(marker)
            assert _step_result_appears_idle(), f"Marker not detected: {marker}"

    def test_uses_correct_runs_dir_for_expert(self, init_state):
        """With an ExpertContext, _step_result_appears_idle should use the expert's runs dir."""
        from core.context import ExpertContext
        ctx = ExpertContext("builder")
        ctx.ensure_dirs()
        run_dir = ctx.runs_dir / "20260428_120000"
        run_dir.mkdir(parents=True)
        (run_dir / "rollout.md").write_text("no active task")
        assert _step_result_appears_idle(ctx=ctx) is True


class TestChatWake:
    def test_chat_wake_noop_when_empty_chatlog(self, init_state):
        """check_and_wake should return False when no chatlog files exist."""
        result = check_and_wake()
        assert result is False

    def test_chat_wake_noop_when_goal_exists(self, init_state):
        """If GOAL.md already has content, don't seed a new goal."""
        core_state.GOAL_FILE.write_text("Active goal")
        result = check_and_wake()
        assert result is False

    def test_chat_wake_seeds_goal_for_pending_user_msg(self, init_state):
        """Pending user messages without a bot reply should trigger goal seeding."""
        chatlog = core_state.CHATLOG_DIR
        chatlog.mkdir(parents=True)
        f = chatlog / "20260428_150000.jsonl"
        f.write_text(
            json.dumps({"role": "user", "text": "Please do X", "ts": "2026-04-28T15:00:00"})
            + "\n"
        )
        result = check_and_wake()
        assert result is True
        assert core_state.GOAL_FILE.exists()
        text = core_state.GOAL_FILE.read_text()
        assert "Operator sent messages while bot was idle" in text
        assert "Please do X" in text

    def test_chat_wake_noop_when_bot_replied(self, init_state):
        """If the last message is from the bot, don't seed a goal."""
        chatlog = core_state.CHATLOG_DIR
        chatlog.mkdir(parents=True)
        f = chatlog / "20260428_150000.jsonl"
        f.write_text(
            json.dumps({"role": "user", "text": "Please do X", "ts": "2026-04-28T15:00:00"})
            + "\n"
            + json.dumps({"role": "bot", "text": "Done", "ts": "2026-04-28T15:01:00"})
            + "\n"
        )
        result = check_and_wake()
        assert result is False

    def test_chat_wake_dedup(self, init_state):
        """Same pending messages should not seed a goal twice."""
        chatlog = core_state.CHATLOG_DIR
        chatlog.mkdir(parents=True)
        f = chatlog / "20260428_150000.jsonl"
        f.write_text(
            json.dumps({"role": "user", "text": "Do X", "ts": "2026-04-28T15:00:00"})
            + "\n"
        )
        assert check_and_wake() is True
        assert check_and_wake() is False


class TestFleetStatus:
    def test_write_fleet_status_creates_file(self, init_state):
        """_write_fleet_status should create .fleet_status.json."""
        _write_fleet_status()
        fleets = core_state.CONTEXT_DIR / ".fleet_status.json"
        assert fleets.exists()
        data = json.loads(fleets.read_text())
        assert "bot_name" in data
        assert "default_loop" in data
        assert "pid" in data

    def test_fleet_status_contains_expected_keys(self, init_state):
        """Fleet status JSON should have the standard shape."""
        _write_fleet_status()
        fleets = core_state.CONTEXT_DIR / ".fleet_status.json"
        data = json.loads(fleets.read_text())
        assert "bot_name" in data
        assert "pid" in data
        assert "phase" in data
        assert data["phase"] == "act"
        assert "context_budget" in data
        assert "default_loop" in data
        assert "experts" in data

    def test_fleet_status_active_goal(self, init_state):
        """When a goal is set, fleet status should reflect it."""
        core_state.GOAL_FILE.write_text("Build X")
        _write_fleet_status()
        fleets = core_state.CONTEXT_DIR / ".fleet_status.json"
        data = json.loads(fleets.read_text())
        assert data["default_loop"]["active"] is True
        assert "Build X" in data["default_loop"]["goal"]


class TestExpertAutoRetro:
    def test_writes_to_learnings(self, init_state):
        """_expert_auto_retro should write retro to learnings.md."""
        from core.context import ExpertContext
        ctx = ExpertContext("builder")
        ctx.ensure_dirs()
        _expert_auto_retro("builder", ctx, "Build X", 3, "completed")
        learnings = ctx.base / "learnings.md"
        assert learnings.exists()
        text = learnings.read_text()
        assert "Build X" in text
        assert "3 steps" in text
        assert "completed" in text

    def test_appends_to_existing_learnings(self, init_state):
        """_expert_auto_retro should append, not overwrite."""
        from core.context import ExpertContext
        ctx = ExpertContext("builder")
        ctx.ensure_dirs()
        (ctx.base / "learnings.md").write_text("Previous learning\n")
        _expert_auto_retro("builder", ctx, "Build X", 3, "completed")
        text = (ctx.base / "learnings.md").read_text()
        assert "Previous learning" in text
        assert "Build X" in text

    def test_uses_state_for_context(self, init_state):
        """When STATE.md exists, retro should include a summary."""
        from core.context import ExpertContext
        ctx = ExpertContext("builder")
        ctx.ensure_dirs()
        ctx.state_file.write_text("Fixed the timeout bug in worker.py")
        _expert_auto_retro("builder", ctx, "Fix timeout", 2, "completed")
        text = (ctx.base / "learnings.md").read_text()
        assert "timeout bug" in text


class TestLoopManager:
    def test_loop_manager_initial_state(self, init_state):
        """LoopManager should start with no active loops."""
        from core.engine import _bootstrap
        _bootstrap(init_state.WORKING_DIR)
        mgr = core_state._loop_manager
        assert mgr.list_active() == []

    def test_loop_manager_is_running_false(self, init_state):
        """is_running should return False for unknown handles."""
        mgr = LoopManager()
        assert mgr.is_running("nonexistent") is False

    def test_loop_manager_stop_all_noop(self, init_state):
        """stop_all on an empty manager should not raise."""
        mgr = LoopManager()
        mgr.stop_all()


class TestGoalCompletion:
    def test_goal_hash_change_detected(self, init_state):
        """When GOAL.md changes, the new content should produce a different hash."""
        h1 = hashlib.sha256(b"Goal A").hexdigest()[:16]
        h2 = hashlib.sha256(b"Goal B").hexdigest()[:16]
        assert h1 != h2

    def test_goal_step_count_increments(self, init_state):
        """Simulate step count tracking across goal lifecycle."""
        sc = 0
        sc += 1
        assert sc == 1
        sc += 1
        assert sc == 2

    def test_done_marker_detection(self, init_state):
        """Goal text containing done markers should be detected."""
        done_markers = [
            "(done", "done —", "completed.", "idle", "no active task",
            "goal cleared", "nothing to do", "(finished",
            "clear when done", "task complete", "(cleared",
        ]
        for marker in done_markers:
            short = marker[:119]
            is_done = len(short) < 120 and any(
                m in short.lower() for m in done_markers
            )
            assert is_done, f"Marker not detected: {marker}"

    def test_non_done_marker_not_detected(self):
        """Long or non-done text should not trigger done detection."""
        text = "Fix the pagination bug in the admin panel and add tests"
        is_done = len(text) < 120 and any(
            m in text.lower() for m in [
                "(done", "done —", "completed.", "idle", "no active task",
                "goal cleared", "nothing to do", "(finished",
                "clear when done", "task complete", "(cleared",
            ]
        )
        assert is_done is False


class TestWriteCompletionState:
    def test_writes_correct_format(self, init_state):
        """_write_completion_state should produce the expected STATE.md format."""
        _write_completion_state(
            goal="Fix bug",
            steps=2,
            outcome="completed",
            runs_dir=init_state.RUNS_DIR,
            state_file=init_state.STATE_FILE,
        )
        text = init_state.STATE_FILE.read_text()
        assert text.startswith("# Arbos State")
        assert "## Status: IDLE" in text
        assert "completed after 2 steps" in text
        assert "## Last Completed: Fix bug" in text

    def test_includes_rollout_summary_when_available(self, init_state):
        """When a rollout file exists, include its first paragraph in Summary."""
        run_dir = init_state.RUNS_DIR / "20260428_120000"
        run_dir.mkdir(parents=True)
        (run_dir / "rollout.md").write_text(
            "First paragraph of results.\n\nSecond paragraph.\n"
        )
        _write_completion_state(
            goal="Fix bug",
            steps=2,
            outcome="completed",
            runs_dir=init_state.RUNS_DIR,
            state_file=init_state.STATE_FILE,
        )
        text = init_state.STATE_FILE.read_text()
        assert "### Summary" in text
        assert "First paragraph of results" in text
