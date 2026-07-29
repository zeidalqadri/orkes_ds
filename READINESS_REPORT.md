# Harga CLI Readiness Report

**Date**: 2026-07-28
**Status**: ✅ **READY FOR DEVELOPMENT**

---

## Executive Summary

The orkes_ds2 project infrastructure is **fully prepared** for expert team harga-cli development. All documentation, database connections, expert definitions, and verification procedures are in place and tested.

**Setup Status**: 7/7 checks passing ✅

---

## Infrastructure Checklist

### ✅ Project Documentation
- [x] **CLAUDE.md** — Architecture, verification procedures, named mistakes (M1-M3)
- [x] **PROMPT.md** — Mission, constraints, operator communication
- [x] **EXPERT_ACTIVATION.md** — How to invoke each expert, communication channels, escalation
- [x] **DEVELOPER_QUICKSTART.md** — 5-minute setup guide with patterns and examples
- [x] **HARGA_CLI_REFERENCE.md** — Complete DB schemas, module APIs, CLI surface area
- [x] **context/shared_learnings.md** — Fleet-wide patterns, recurring mistakes (M1-M3), CLI patterns
- [x] **context/experts.json** — 4 experts with detailed system prompts and model routing

### ✅ Python Environment
- [x] **Python 3.12.3** installed
- [x] **Venv**: `/home/the_bomb/orkes/.venv/` (shared orkes environment)
- [x] **Orkes packages** (all installed editable):
  - orkes-core 0.2.0
  - orkes-pricing 0.2.0
  - orkes-tender 0.2.0
- [x] **Testing tools** installed:
  - pytest 8.3.3
  - pytest-cov 5.0.0
  - pytest-xdist 3.8.0
- [x] **Code quality tools**:
  - ruff (configured in pyproject.toml)
  - py_compile (stdlib)

### ✅ Databases
All three required databases exist with current data:
- [x] **harga_v8.db** (126 KB) — bids, entities, assignments, submissions, audit_log
- [x] **price_memory.db** (37 MB) — price history with FTS5 full-text search
- [x] **supplier_index.db** (6 MB) — supplier catalog with FTS5 + embeddings
- Location: `/home/the_bomb/orkes/harga/data/`

### ✅ Package Structure
- [x] **tools/harga_cli/__init__.py** — Version 0.1.0, metadata
- [x] **tools/harga_cli/__main__.py** — Entry point, argument parsing (stubbed, ready for builder)
- [x] **tools/harga_cli/db.py** — Database connections & queries (stubbed)
- [x] **tools/harga_cli/formatters.py** — JSON & table output (stubbed)
- [x] **tools/harga_cli/errors.py** — Custom exceptions
- [x] **tools/harga_cli/commands/** — Subcommand package
  - tenders.py (stubbed)
  - bids.py (stubbed)
  - entities.py (stubbed)

### ✅ Configuration
- [x] **pyproject.toml** — Complete project config:
  - Entry point: `harga-cli = "tools.harga_cli.__main__:main"`
  - Python 3.10+, zero dependencies
  - pytest configuration
  - Coverage configuration
  - ruff linting rules
- [x] **SETUP_VERIFY.sh** — Automated verification script (7 checks, all passing)

### ✅ Testing Infrastructure
- [x] **conftest.py** — Pytest fixtures for temp SQLite DBs
- [x] **test_harga_cli_example.py** — Example test patterns (ready for tester to extend)
- [x] **Coverage config** — Target 80% on critical paths

### ✅ Context Files
- [x] **context/GOAL.md** — Current objective (ready for operator to set)
- [x] **context/STATE.md** — Working memory (phase, approach, blockers)
- [x] **context/INBOX.md** — Task queue for experts (consumed each step)
- [x] **context/experts.json** — Expert fleet definitions
- [x] **context/shared_learnings.md** — Fleet-wide patterns & mistakes

---

## Expert Team Ready

### Conductor (Sonnet)
- **Role**: Orchestration, subcommand prioritization, sequencing
- **System Prompt**: Detailed, references HARGA_CLI_REFERENCE.md, knows expert responsibilities
- **Invocation**: `python arbos.py inbox conductor "<task>"`
- **Outputs**: Sequences tasks, writes to context/conductor/GOAL.md

### Builder (Opus)
- **Role**: Implementation, argparse, SQLite queries, output formatting
- **System Prompt**: Detailed, includes entity list, bid statuses, reusable module list
- **Verification**: py_compile + smoke test (specified in prompt)
- **Invocation**: `python arbos.py inbox builder "<task>"`
- **Outputs**: Implementation in `/home/the_bomb/orkes/harga/`, learnings to context/builder/learnings.md

### Reviewer (Opus)
- **Role**: Code review, security audit (SQL injection, input validation), performance audit
- **System Prompt**: Detailed review checklist, performance patterns (FTS5, indexes)
- **Verification**: Grep for SQL injection patterns, check module boundaries
- **Invocation**: `python arbos.py inbox reviewer "<task>"`
- **Outputs**: Review findings to context/reviewer/findings.md

### Tester (Sonnet)
- **Role**: pytest fixtures, CLI output capture, edge cases (unicode, large datasets, NULL fields)
- **System Prompt**: Detailed test patterns, subprocess.run() CLI invocation, fixture examples
- **Verification**: All tests pass, <5s total, no network calls
- **Invocation**: `python arbos.py inbox tester "<task>"`
- **Outputs**: Tests in `/home/the_bomb/orkes/harga/tests/`, learnings to context/tester/learnings.md

---

## Verification Procedures

### Pre-Development (✅ Passing)

```bash
cd /home/the_bomb/orkes_ds2 && bash SETUP_VERIFY.sh
# Output: 7/7 checks passing
```

### Post-Implementation (Builder)

```bash
# Syntax check
python -c "import py_compile; py_compile.compile('/home/the_bomb/orkes/harga/harga_cli.py', doraise=True)"

# Help works
/home/the_bomb/orkes/.venv/bin/python /home/the_bomb/orkes/harga/harga_cli.py --help

# Smoke test
harga-cli entities list  # Should return JSON or error (DB OK if FileNotFoundError is because DB doesn't exist)
harga-cli bids list      # Should return JSON or error
```

### Post-Testing (Tester)

```bash
cd /home/the_bomb/orkes/harga
/home/the_bomb/orkes/.venv/bin/python -m pytest tests/test_harga_cli.py -v
/home/the_bomb/orkes/.venv/bin/python -m pytest tests/ --cov=tools/harga_cli --cov-report=term-missing
# Target: 0 failed, >= 80% coverage
```

### Post-Review (Reviewer)

```bash
# SQL injection check
grep -n "f\".*{" /home/the_bomb/orkes/harga/harga_cli.py  # Should be empty

# Flask imports check (should not exist)
grep -n "from flask\|import flask" /home/the_bomb/orkes/harga/harga_cli.py  # Should be empty

# Module boundaries (only orkes_*, modules/)
grep -n "^from tools\|^import tools" /home/the_bomb/orkes/harga/harga_cli.py | grep -v "tools.harga_cli"  # Should be empty

# Index usage verified by code review (cross-ref HARGA_CLI_REFERENCE.md)
```

---

## Resource Files

| File | Purpose | Status |
|------|---------|--------|
| CLAUDE.md | Architecture, verification, named mistakes | ✅ Complete |
| PROMPT.md | Mission, constraints, expert definitions | ✅ Complete |
| EXPERT_ACTIVATION.md | How to invoke experts, communication | ✅ Created |
| DEVELOPER_QUICKSTART.md | 5-minute setup, patterns, troubleshooting | ✅ Created |
| HARGA_CLI_REFERENCE.md | DB schemas, module APIs, CLI surface | ✅ Complete |
| context/shared_learnings.md | Fleet-wide patterns, recurring mistakes | ✅ Updated with CLI patterns |
| context/experts.json | Expert fleet definitions | ✅ Complete |
| SETUP_VERIFY.sh | Automated verification script | ✅ Created |
| READINESS_REPORT.md | This file | ✅ Complete |

---

## Next Steps

### For Operator

1. **Set first goal** in `context/GOAL.md`:
   ```markdown
   # Harga CLI Development

   Implement tenders subcommand: list, filter by entity, paginate with limit/offset.
   ```

2. **Invoke conductor**:
   ```bash
   python arbos.py inbox conductor "Plan the tenders subcommand implementation"
   ```

3. **Monitor progress**:
   - Read `context/STATE.md` for working memory
   - Read `context/<expert>/findings.md` for work output
   - Check expert learnings in `context/<expert>/learnings.md`

### For Experts

1. **Read core docs** (takes 10 min):
   - DEVELOPER_QUICKSTART.md
   - context/HARGA_CLI_REFERENCE.md
   - context/shared_learnings.md

2. **Implement your role**:
   - Conductor: prioritize subcommands
   - Builder: implement features, test locally
   - Tester: write comprehensive tests
   - Reviewer: audit for security, performance

3. **Document learnings**:
   - Update `context/shared_learnings.md` with new patterns
   - Write personal learnings to `context/<handle>/learnings.md`

### For CI/CD (if applicable)

- Entry point is `harga-cli` (configured in pyproject.toml)
- Tests: `python -m pytest tests/test_harga_cli.py -v`
- Coverage target: >= 80%
- No new dependencies (zero pip installs, use argparse + reusable modules)

---

## Known Constraints

- **Zero new dependencies** — argparse is stdlib; use orkes_*, modules/bid_crud.py for logic
- **Absolute paths only** — cwd is ~/orkes_ds2, target is ~/orkes/harga/
- **SQLite direct** — parameterized queries with ? placeholders (never f-strings)
- **No Flask imports** — CLI is standalone; don't import from tools/harga_v8_*.py
- **Workdir split** — cwd is ~/orkes_ds2 (for arbos), but code goes in ~/orkes/harga/
- **Venv shared** — `/home/the_bomb/orkes/.venv/` is shared by all orkes projects

---

## Troubleshooting

### If SETUP_VERIFY.sh fails
- Check venv exists: `ls -la /home/the_bomb/orkes/.venv/`
- Check databases exist: `ls -la /home/the_bomb/orkes/harga/data/`
- Check packages installed: `pip list | grep orkes`
- Run verification again: `bash SETUP_VERIFY.sh`

### If import errors occur
- Ensure venv is activated: `source /home/the_bomb/orkes/.venv/bin/activate`
- Check orkes packages are editable: `pip show orkes-core` (should show local path)
- Re-install if needed: `cd /home/the_bomb/orkes && pip install -e ./packages/orkes_core ./packages/orkes_pricing ./packages/orkes_tender`

### If tests fail
- Run with verbose output: `pytest tests/ -vv -s`
- Check conftest.py fixtures: `pytest tests/conftest.py -v`
- Check for absolute paths in test file paths

---

## Sign-Off

**Project**: harga-cli
**Date Prepared**: 2026-07-28
**Prepared By**: Arbos (pre-flight check)
**Status**: ✅ Ready for expert team assignment
**Infrastructure**: 7/7 checks passing
**Documentation**: Complete
**Expert Team**: Conductor, Builder, Reviewer, Tester (all system prompts prepared)

**Next**: Operator sets GOAL.md and invokes conductor.
