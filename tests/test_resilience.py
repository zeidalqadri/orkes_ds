"""Tests for Phase 4 resilience modules: skill_runner, state_writer, graceful degradation."""


# ══════════════════════════════════════════════════════════════════════════
# skill_runner.py
# ══════════════════════════════════════════════════════════════════════════


class TestSkillRunner_RunnerConfig:
    def test_default_config(self):
        from core.skill_runner import RunnerConfig
        cfg = RunnerConfig()
        assert cfg.timeout == 120
        assert cfg.retries == 0
        assert cfg.retry_delay == 2.0
        assert cfg.label == ""

    def test_custom_config(self):
        from core.skill_runner import RunnerConfig
        cfg = RunnerConfig(timeout=30, retries=2, retry_delay=1.0, label="test")
        assert cfg.timeout == 30
        assert cfg.retries == 2
        assert cfg.retry_delay == 1.0
        assert cfg.label == "test"


class TestSkillRunner_RunnerResult:
    def test_default_result(self):
        from core.skill_runner import RunnerResult
        r = RunnerResult()
        assert r.success is False
        assert r.result is None
        assert r.error == ""
        assert r.duration_ms == 0
        assert r.timed_out is False
        assert r.signal_killed is False


class TestSkillRunner_SafeRun:
    def test_success(self):
        from core.skill_runner import RunnerConfig, _safe_run
        def ok_fn():
            return 42
        result = _safe_run(ok_fn, config=RunnerConfig(label="test"))
        assert result.success is True
        assert result.result == 42
        assert result.duration_ms >= 0

    def test_failure_single_attempt(self):
        from core.skill_runner import RunnerConfig, _safe_run
        def bad_fn():
            raise ValueError("boom")
        result = _safe_run(bad_fn, config=RunnerConfig(label="test"))
        assert result.success is False
        assert "boom" in result.error

    def test_success_on_retry(self):
        from core.skill_runner import RunnerConfig, _safe_run
        call_count = [0]
        def flaky_fn():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("not yet")
            return "ok"
        result = _safe_run(flaky_fn, config=RunnerConfig(retries=1, retry_delay=0.01, label="flaky"))
        assert result.success is True
        assert result.result == "ok"

    def test_all_retries_exhausted(self):
        from core.skill_runner import RunnerConfig, _safe_run
        call_count = [0]
        def always_bad():
            call_count[0] += 1
            raise ValueError("always")
        result = _safe_run(always_bad, config=RunnerConfig(retries=2, retry_delay=0.01, label="bad"))
        assert result.success is False
        assert call_count[0] == 3

    def test_with_args_kwargs(self):
        from core.skill_runner import RunnerConfig, _safe_run
        def adder(a, b=0):
            return a + b
        result = _safe_run(adder, 10, b=20, config=RunnerConfig(label="adder"))
        assert result.success is True
        assert result.result == 30


class TestSkillRunner_WithRetry:
    def test_success_first_try(self):
        from core.skill_runner import with_retry
        result = with_retry(lambda: "ok", label="test")
        assert result.success is True
        assert result.result == "ok"

    def test_retry_with_backoff(self):
        from core.skill_runner import with_retry
        call_count = [0]
        def flaky():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ConnectionError("timeout")
            return "data"
        result = with_retry(flaky, retries=2, delay=0.01, label="flaky")
        assert result.success is True
        assert result.result == "data"
        assert call_count[0] == 2

    def test_retry_exhausted(self):
        from core.skill_runner import with_retry
        def always_fail():
            raise RuntimeError("fail")
        result = with_retry(always_fail, retries=1, delay=0.01, label="fail")
        assert result.success is False
        assert "fail" in result.error


class TestSkillRunner_RunIsolated:
    def test_success(self):
        from core.skill_runner import RunnerConfig, run_isolated
        def ok_fn():
            return "result"
        result = run_isolated(ok_fn, config=RunnerConfig(label="test"))
        assert result.success is True
        assert result.result == "result"

    def test_crash(self):
        from core.skill_runner import RunnerConfig, run_isolated
        def crash_fn():
            raise ValueError("crashed")
        result = run_isolated(crash_fn, config=RunnerConfig(label="crash"))
        assert result.success is False
        assert "crashed" in result.error

    def test_timeout(self):
        from core.skill_runner import RunnerConfig, run_isolated
        def slow_fn():
            import time
            time.sleep(10)
            return "never"
        result = run_isolated(slow_fn, config=RunnerConfig(timeout=1, label="slow"))
        assert result.success is False
        assert result.timed_out is True

    def test_with_args(self):
        from core.skill_runner import RunnerConfig, run_isolated
        def add(a, b):
            return a + b
        result = run_isolated(add, 3, 4, config=RunnerConfig(label="add"))
        assert result.success is True
        assert result.result == 7


class TestSkillRunner_RunIsolatedThread:
    def test_success_thread(self):
        from core.skill_runner import RunnerConfig, run_isolated_thread
        def ok_fn():
            return "threaded"
        result = run_isolated_thread(ok_fn, config=RunnerConfig(label="thread"))
        assert result.success is True
        assert result.result == "threaded"

    def test_crash_thread(self):
        from core.skill_runner import RunnerConfig, run_isolated_thread
        def crash_fn():
            raise RuntimeError("thread crash")
        result = run_isolated_thread(crash_fn, config=RunnerConfig(label="thread_crash"))
        assert result.success is False
        assert "thread crash" in result.error

    def test_timeout_thread(self):
        from core.skill_runner import RunnerConfig, run_isolated_thread
        def slow_fn():
            import time
            time.sleep(10)
            return "never"
        result = run_isolated_thread(slow_fn, config=RunnerConfig(timeout=1, label="thread_slow"))
        assert result.success is False
        assert result.timed_out is True


# ══════════════════════════════════════════════════════════════════════════
# state_writer.py
# ══════════════════════════════════════════════════════════════════════════


class TestStateWriter_Validation:
    def test_valid_state(self):
        from core.state_writer import is_state_valid, validate_state_text
        text = (
            "# State\n"
            "Updated: 2026-04-28T16:00 UTC\n\n"
            "## Status\n"
            "IDLE\n\n"
            "## Summary\n"
            "All tasks complete."
        )
        assert is_state_valid(text) is True
        assert len(validate_state_text(text)) == 0

    def test_empty_state_invalid(self):
        from core.state_writer import is_state_valid, validate_state_text
        assert is_state_valid("") is False
        issues = validate_state_text("")
        assert "empty" in issues[0]

    def test_missing_updated_field(self):
        from core.state_writer import validate_state_text
        text = (
            "# State\n\n"
            "## Status\n"
            "IDLE\n\n"
            "## Summary\n"
            "All done."
        )
        issues = validate_state_text(text)
        assert len(issues) > 0

    def test_internal_monologue_detected(self):
        from core.state_writer import validate_state_text
        text = (
            "# State\n"
            "Updated: 2026-04-28\n\n"
            "**Internal thinking**: I need to check the error.\n"
            "## Status\n"
            "BUSY\n\n"
            "## Summary\n"
            "Working."
        )
        issues = validate_state_text(text)
        assert any("internal monologue" in i for i in issues)

    def test_tool_output_detected(self):
        from core.state_writer import validate_state_text
        text = (
            "# State\n"
            "Updated: 2026-04-28\n\n"
            "## Status\n"
            "BUSY\n\n"
            "```bash\n"
            "ls -la\n"
            "```\n\n"
            "## Summary\n"
            "Working."
        )
        issues = validate_state_text(text)
        assert any("tool output" in i for i in issues)

    def test_long_lines_detected(self):
        from core.state_writer import validate_state_text
        text = (
            "# State\n"
            "Updated: 2026-04-28\n\n"
            "## Status\n"
            "BUSY\n\n"
            "## Summary\n"
            + "x" * 300 + "\n"
        )
        issues = validate_state_text(text)
        assert any("long lines" in i for i in issues)

    def test_raw_llm_output_detected(self):
        from core.state_writer import validate_state_text
        text = (
            "I think the issue is in the database layer. Let me trace through "
            "the code path to find the root cause. The error occurs when..."
        )
        issues = validate_state_text(text)
        assert any("raw LLM output" in i for i in issues)


class TestStateWriter_Sanitize:
    def test_strip_internal_monologue(self):
        from core.state_writer import strip_internal_monologue
        text = (
            "# State\n"
            "## Status\n"
            "let me think about this problem\n"
            "## Summary\n"
            "Done."
        )
        cleaned = strip_internal_monologue(text)
        assert "let me think about" not in cleaned
        assert "## Summary" in cleaned

    def test_sanitize_truncates_long_lines(self):
        from core.state_writer import sanitize_state
        text = (
            "# State\n"
            "Updated: now\n\n"
            "## Status\n"
            "BUSY\n\n"
            "## Summary\n"
            + "x" * 300 + "\n"
        )
        cleaned = sanitize_state(text)
        assert "..." in cleaned

    def test_sanitize_truncates_oversized(self):
        from core.state_writer import sanitize_state
        lines = ["line " + str(i) for i in range(300)]
        lines.insert(0, "# State")
        lines.insert(1, "Updated: now")
        text = "\n".join(lines)
        cleaned = sanitize_state(text, max_lines=10)
        assert len(cleaned.splitlines()) <= 12


class TestStateWriter_BuildMinimal:
    def test_minimal_state(self):
        from core.state_writer import build_minimal_state
        text = build_minimal_state("BUSY", "Working on Phase 4")
        assert "# State" in text
        assert "Updated:" in text
        assert "## Status" in text
        assert "BUSY" in text
        assert "## Summary" in text
        assert "Working on Phase 4" in text

    def test_minimal_state_with_goal(self):
        from core.state_writer import build_minimal_state
        text = build_minimal_state("IDLE", "Done", goal="Phase 4")
        assert "Goal:" in text
        assert "Phase 4" in text

    def test_minimal_state_empty_summary(self):
        from core.state_writer import build_minimal_state
        text = build_minimal_state("IDLE", "")
        assert "(no summary)" in text


class TestStateWriter_SafeWrite:
    def test_safe_write_valid_content(self, tmp_path):
        from core.state_writer import safe_write_state
        state_file = tmp_path / "STATE.md"
        text = (
            "# State\n"
            "Updated: 2026-04-28\n\n"
            "## Status\n"
            "IDLE\n\n"
            "## Summary\n"
            "Done."
        )
        result = safe_write_state(state_file, text)
        assert result is True
        assert state_file.exists()
        assert "## Summary" in state_file.read_text()

    def test_safe_write_rejects_empty(self, tmp_path):
        from core.state_writer import safe_write_state
        state_file = tmp_path / "STATE.md"
        result = safe_write_state(state_file, "")
        assert result is False
        assert not state_file.exists()

    def test_safe_write_sanitizes_bad_content(self, tmp_path):
        from core.state_writer import safe_write_state
        state_file = tmp_path / "STATE.md"
        text = (
            "## Some garbage content with no proper format\n"
            "let me think about what to do next\n"
            "I should check the error..."
        )
        result = safe_write_state(state_file, text)
        assert result is True
        assert state_file.exists()
        content = state_file.read_text()
        assert "Status" in content

    def test_safe_write_creates_minimal_on_bad_sanitize(self, tmp_path):
        from core.state_writer import safe_write_state
        state_file = tmp_path / "STATE.md"
        text = "```json\nraw tool output\n```\n" * 50
        result = safe_write_state(state_file, text)
        assert result is True
        content = state_file.read_text()
        assert "Status" in content


class TestStateWriter_IsStateValid:
    def test_minimal_valid(self):
        from core.state_writer import is_state_valid
        text = (
            "# State\n"
            "Updated: now\n\n"
            "## Status\n"
            "IDLE\n\n"
            "## Summary\n"
            "Done."
        )
        assert is_state_valid(text) is True

    def test_invalid_empty(self):
        from core.state_writer import is_state_valid
        assert is_state_valid("") is False


# ══════════════════════════════════════════════════════════════════════════
# Graceful degradation — skill_runner integration
# ══════════════════════════════════════════════════════════════════════════


class TestGracefulDegradation:
    def test_safe_run_never_crashes_caller(self):
        from core.skill_runner import RunnerConfig, _safe_run
        def crash():
            raise Exception("this should be contained")
        result = _safe_run(crash, config=RunnerConfig(label="safe"))
        assert result.success is False
        # Caller should never see the exception

    def test_safe_run_preserves_loop(self):
        from core.skill_runner import RunnerConfig, _safe_run
        results = []
        for i in range(3):
            def maybe_fail(n=i):
                if n == 1:
                    raise ValueError(f"fail {n}")
                return f"ok {n}"
            result = _safe_run(maybe_fail, config=RunnerConfig(label=f"step_{i}"))
            results.append(result.success)
        assert results == [True, False, True]

    def test_with_retry_preserves_loop_on_failure(self):
        from core.skill_runner import with_retry
        def fail():
            raise RuntimeError("persistent")
        result = with_retry(fail, retries=1, delay=0.01, label="persistent_fail")
        assert result.success is False
        assert result.error == "persistent"

    def test_nested_safe_calls(self):
        from core.skill_runner import RunnerConfig, _safe_run
        def inner():
            raise ValueError("inner crash")
        def outer():
            r = _safe_run(inner, config=RunnerConfig(label="inner"))
            assert r.success is False
            return "outer ok"
        result = _safe_run(outer, config=RunnerConfig(label="outer"))
        assert result.success is True
        assert result.result == "outer ok"
