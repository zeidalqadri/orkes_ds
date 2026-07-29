# Harga CLI Project Readiness Checklist

Use this checklist to verify that the project is ready for development with the expert team.

## Infrastructure (Setup Complete ✅)

- [x] **CLAUDE.md** — Architecture, verification tables, named mistakes
- [x] **PROMPT.md** — Mission, constraints, expert definitions
- [x] **experts.json** — 5 experts registered with system prompts & model routing
  - [x] cli-builder (opus)
  - [x] cli-tester (sonnet)
  - [x] cli-reviewer (opus)
  - [x] cli-deployer (sonnet)
  - [x] cli-conductor (sonnet)
- [x] **pyproject.toml** — Package config, entry point, test config, coverage rules

## Documentation (Setup Complete ✅)

- [x] **HARGA_CLI_README.md** — Command spec, data model, examples, implementation checklist
- [x] **DEVELOP.md** — Setup, workflow, patterns, verification, release procedure
- [x] **PROJECT_CHECKLIST.md** — This file

## Project Scaffolding (Setup Complete ✅)

### Source Code Structure
- [x] `tools/harga_cli/__init__.py` — Version management
- [x] `tools/harga_cli/__main__.py` — Entry point, argument parsing (stubbed)
- [x] `tools/harga_cli/errors.py` — Custom exceptions
- [x] `tools/harga_cli/db.py` — Database connections & query templates (stubbed)
- [x] `tools/harga_cli/formatters.py` — Output formatting (stubbed)
- [x] `tools/harga_cli/commands/__init__.py` — Command package
- [x] `tools/harga_cli/commands/tenders.py` — Tenders command (stubbed)
- [x] `tools/harga_cli/commands/bids.py` — Bids command (stubbed)
- [x] `tools/harga_cli/commands/entities.py` — Entities command (stubbed)

### Test Infrastructure
- [x] `tests/conftest.py` — Pytest fixtures (test DBs, sample data)
- [x] `tests/test_harga_cli_example.py` — Example test patterns

## Implementation Tasks (Ready for Assignment ➜)

### Builders (cli-builder)
- [ ] **db.py — query_tenders()** — Query tenders.db with filters & pagination
- [ ] **db.py — query_bids()** — Query harga_v8.db with filters & pagination
- [ ] **db.py — query_entities()** — List entities from harga_v8.db
- [ ] **db.py — set_entity_notification()** — Update entity notification channel
- [ ] **commands/tenders.py — handle_tenders()** — Call query_tenders & format output
- [ ] **commands/bids.py — handle_bids()** — Call query_bids & format output
- [ ] **commands/entities.py — handle_entities_list()** — Call query_entities & format
- [ ] **commands/entities.py — handle_entities_config()** — Call set_entity_notification
- [ ] **formatters.py — format_tenders_text()** — Human-readable table output
- [ ] **formatters.py — format_bids_text()** — Human-readable table output
- [ ] **formatters.py — format_entities_text()** — Human-readable table output
- [ ] **__main__.py — dispatch handlers** — Wire up handle_* functions to subcommands

### Testers (cli-tester)
- [ ] **tests/test_harga_cli_tenders.py** — Unit & integration tests for tenders command
- [ ] **tests/test_harga_cli_bids.py** — Unit & integration tests for bids command
- [ ] **tests/test_harga_cli_entities.py** — Unit & integration tests for entities command
- [ ] **tests/test_harga_cli_args.py** — Argument parsing validation & edge cases
- [ ] **tests/test_harga_cli_errors.py** — Database error handling, missing DBs, bad queries
- [ ] **Coverage Report** — Generate coverage report, target >= 80% for critical paths

### Reviewers (cli-reviewer)
- [ ] **Code Audit** — Check all implementations for SQL injection, parameterized queries
- [ ] **Performance Audit** — Verify queries use indexes, no N+1 patterns, memory efficient
- [ ] **Maintainability Review** — Check naming, DRY principle, modularity
- [ ] **Test Coverage** — Verify all code paths tested, edge cases handled
- [ ] **Backward Compatibility** — Ensure API contracts stable, breaking changes documented

### Deployers (cli-deployer)
- [ ] **Installation Test** — Verify `pip install -e .` works
- [ ] **Entry Point Test** — Verify `harga-cli --version` and `harga-cli --help` work
- [ ] **Package Build** — Build sdist and wheel: `python -m build`
- [ ] **Release Documentation** — Write changelog, usage examples, installation guide
- [ ] **Version Bump** — Update version in __init__.py and pyproject.toml

## Pre-Development Checks

### Database Setup
```bash
# Verify databases exist
ls -la /home/the_bomb/orkes_ds2/data/harga_v8.db
ls -la /home/the_bomb/orkes_ds2/data/tenders.db

# Check schema (example)
sqlite3 /home/the_bomb/orkes_ds2/data/harga_v8.db ".schema bids"
sqlite3 /home/the_bomb/orkes_ds2/data/tenders.db ".schema tenders"
```

### Python Environment
```bash
cd /home/the_bomb/orkes_ds2
python --version  # Should be >= 3.10
python -m pip install -e .  # Install in development mode
harga-cli --version  # Should show "harga-cli 0.1.0"
harga-cli --help     # Should show all subcommands
```

### Test Infrastructure
```bash
cd /home/the_bomb/orkes_ds2
python -m pytest tests/ --collect-only  # List all tests
python -m pytest tests/conftest.py -v   # Test fixtures work
```

## Sign-Off Checklist (After All Tasks Complete)

- [ ] All 12 builder tasks complete (no NotImplementedError)
- [ ] All tests pass: `python -m pytest tests/ -v`
- [ ] Coverage >= 80%: `python -m pytest tests/ --cov=tools/harga_cli`
- [ ] No security issues found in code review
- [ ] Installation works: `pip install -e .` + `harga-cli --version`
- [ ] Example commands work:
  - [ ] `harga-cli tenders --entity ePerolehan --limit 5 --text`
  - [ ] `harga-cli bids --status active`
  - [ ] `harga-cli entities list`
- [ ] Documentation updated (API changes, new flags, examples)
- [ ] Version bumped and tagged

---

## Operator Notes

**Project Status**: Ready for assignment to expert team

**Setup Time**: 2 hours (all scaffolding, docs, fixtures in place)

**Development Estimate**: 5 days (assuming 1 builder, 1 tester, 1 reviewer working in parallel)

**Key Dependencies**:
- `data/harga_v8.db` must exist with bids/entities/audit_log tables
- `data/tenders.db` must exist with tenders table
- Python >= 3.10, pytest, sqlite3 (stdlib)

**Next Steps**:
1. Verify databases exist and have expected schema
2. Assign tasks to expert team via context/GOAL.md
3. Track progress in STATE.md
4. Each expert writes learnings to context/<handle>/learnings.md
