"""Phase 1.2: STATE.md Integrity Tests.

Verifies STATE.md is well-formed across all lifecycle transitions.
"""



from core.engine import _auto_resume_on_boot, _freshen_state_on_boot, _is_generic_restart_goal
from core.loops import _write_completion_state


def test_write_completion_state_creates_valid_markdown(init_state):
    """_write_completion_state must produce parseable STATE.md with required fields."""
    _write_completion_state(
        goal="Build feature X",
        steps=3,
        outcome="completed",
        runs_dir=init_state.RUNS_DIR,
        state_file=init_state.STATE_FILE,
    )
    assert init_state.STATE_FILE.exists()
    text = init_state.STATE_FILE.read_text()

    assert "Updated:" in text
    assert "## Status: IDLE" in text
    assert "completed after 3 steps" in text
    assert "Build feature X" in text


def test_write_completion_state_with_rollout_summary(init_state):
    """When rollout exists, STATE.md should include a ### Summary section."""
    run_dir = init_state.RUNS_DIR / "20260428_150000"
    run_dir.mkdir(parents=True)
    rollout = run_dir / "rollout.md"
    rollout.write_text("Generated the feature flag module.\n\nAll tests pass.")

    _write_completion_state(
        goal="Generate feature flag module",
        steps=2,
        outcome="completed",
        runs_dir=init_state.RUNS_DIR,
        state_file=init_state.STATE_FILE,
    )
    text = init_state.STATE_FILE.read_text()
    assert "### Summary" in text
    assert "Generated the feature flag module" in text


def test_write_completion_state_empty_runs_dir(init_state):
    """STATE.md should still be well-formed even with no rollout dirs."""
    _write_completion_state(
        goal="Short task",
        steps=1,
        outcome="completed",
        runs_dir=init_state.RUNS_DIR,
        state_file=init_state.STATE_FILE,
    )
    text = init_state.STATE_FILE.read_text()
    assert "Short task" in text
    assert "### Summary" not in text


def test_required_fields_present_after_goal_clear(init_state):
    """Simulate the full goal-clear lifecycle: STATE.md must have all 3 fields."""
    _write_completion_state(
        goal="Fix pagination bug",
        steps=2,
        outcome="completed",
        runs_dir=init_state.RUNS_DIR,
        state_file=init_state.STATE_FILE,
    )
    text = init_state.STATE_FILE.read_text()

    assert text.startswith("# Arbos State")
    assert "Updated:" in text
    assert "## Status: IDLE" in text
    assert "completed after 2 steps" in text
    assert "Fix pagination bug" in text


def test_freshen_state_on_boot_populates_empty(init_state):
    """When STATE.md is empty but run_dir with rollout exists, _freshen_state_on_boot writes it."""
    run_dir = init_state.RUNS_DIR / "20260428_120000"
    run_dir.mkdir(parents=True)
    (run_dir / "rollout.md").write_text("Fixed the timeout issue in worker.py\n\nAll good.")

    init_state.STATE_FILE.write_text("")
    _freshen_state_on_boot()
    text = init_state.STATE_FILE.read_text()
    assert "recovered from last run" in text


def test_freshen_state_on_boot_preserves_existing(init_state):
    """When STATE.md already has content, _freshen_state_on_boot leaves it alone."""
    init_state.STATE_FILE.write_text("Existing content")
    _freshen_state_on_boot()
    assert init_state.STATE_FILE.read_text() == "Existing content"


def test_freshen_state_on_boot_noop_when_no_runs(init_state):
    """No rollout dirs = no state population, file should not exist."""
    init_state.STATE_FILE.unlink(missing_ok=True)
    _freshen_state_on_boot()
    assert not init_state.STATE_FILE.exists()


def test_is_generic_restart_goal_detects_markers():
    """_is_generic_restart_goal should catch all restart marker patterns."""
    assert _is_generic_restart_goal("Bot restarted. Act immediately.")
    assert _is_generic_restart_goal("self-restart completed")
    assert _is_generic_restart_goal("do not wait for operator")
    assert not _is_generic_restart_goal("Build the new dashboard UI")
    assert not _is_generic_restart_goal("")


def test_is_generic_restart_goal_case_insensitive():
    """Marker detection should be case-insensitive."""
    assert _is_generic_restart_goal("BOT RESTARTED")


def test_auto_resume_on_boot_skips_when_idle(init_state):
    """When state is IDLE, auto-resume should not seed a goal."""
    init_state.STATE_FILE.write_text("# Arbos State\n## Status: IDLE\n")
    _auto_resume_on_boot()
    goal = init_state.GOAL_FILE.read_text().strip() if init_state.GOAL_FILE.exists() else ""
    assert goal == ""


def test_auto_resume_on_boot_seeds_when_active(init_state):
    """When state shows active work, auto-resume seeds a continuation goal."""
    init_state.STATE_FILE.write_text(
        "# Arbos State\n## Status: In progress — building feature X\n"
    )
    _auto_resume_on_boot()
    assert init_state.GOAL_FILE.exists()
    text = init_state.GOAL_FILE.read_text()
    assert "Act immediately" in text
    assert "building feature X" in text


def test_auto_resume_on_boot_preserves_user_goal(init_state):
    """A non-generic goal set by the operator should not be overwritten."""
    init_state.GOAL_FILE.write_text("Build the dashboard")
    init_state.STATE_FILE.write_text("# Arbos State\n## Status: In progress\n")
    _auto_resume_on_boot()
    assert init_state.GOAL_FILE.read_text() == "Build the dashboard"


def test_auto_resume_on_boot_skips_empty_state(init_state):
    """When STATE.md is empty, auto-resume should skip."""
    init_state.STATE_FILE.write_text("")
    _auto_resume_on_boot()
    goal = init_state.GOAL_FILE.read_text().strip() if init_state.GOAL_FILE.exists() else ""
    assert goal == ""


def test_state_file_tracks_across_goal_boundaries(init_state):
    """Simulate two goal cycles and verify STATE.md updates correctly between them."""
    _write_completion_state(
        goal="Cycle 1: Fix timeout",
        steps=2,
        outcome="completed",
        runs_dir=init_state.RUNS_DIR,
        state_file=init_state.STATE_FILE,
    )
    text1 = init_state.STATE_FILE.read_text()
    assert "Cycle 1: Fix timeout" in text1
    assert "completed after 2 steps" in text1

    _write_completion_state(
        goal="Cycle 2: Add logging",
        steps=1,
        outcome="completed",
        runs_dir=init_state.RUNS_DIR,
        state_file=init_state.STATE_FILE,
    )
    text2 = init_state.STATE_FILE.read_text()
    assert "Cycle 2: Add logging" in text2
    assert "completed after 1 step" in text2
    assert "Cycle 1: Fix timeout" not in text2


def test_phase_from_state_parsing(init_state):
    """_parse_phase_from_state should extract the phase: field."""
    from core.loops import _parse_phase_from_state

    assert _parse_phase_from_state() is None

    init_state.STATE_FILE.write_text("# Arbos State\nphase: plan\n")
    assert _parse_phase_from_state() == "plan"
    init_state.STATE_FILE.write_text("phase: act\n")
    assert _parse_phase_from_state() == "act"
    init_state.STATE_FILE.write_text("phase: bypass\n")
    assert _parse_phase_from_state() is None
