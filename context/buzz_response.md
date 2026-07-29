# Harga CLI: Impeccable Skills & Resources Ready

**Status**: ✅ **READY FOR EXPERT TEAM ASSIGNMENT**

## What Was Prepped

### 1. Expert Fleet (context/experts.json)
✅ 5 experts configured with system prompts & model routing:
- **cli-builder** (opus) — Implement commands & database queries
- **cli-tester** (sonnet) — Write & run comprehensive tests
- **cli-reviewer** (opus) — Security audit, performance, code quality
- **cli-deployer** (sonnet) — Packaging, versioning, pip install
- **cli-conductor** (sonnet) — Task orchestration & prioritization

### 2. Documentation (4 comprehensive guides)
✅ **CLAUDE.md** — Architecture, verification tables, named mistakes
✅ **PROMPT.md** — Mission, constraints, expert activation flow
✅ **DEVELOP.md** — Setup, workflow, patterns, testing, release procedure (2KB)
✅ **HARGA_CLI_README.md** — Command specs, data model, examples
✅ **PROJECT_CHECKLIST.md** — 12 implementation tasks + sign-off

### 3. Source Scaffolding (14 files)

**Core modules** (tools/harga_cli/):
- `__init__.py` — Version management (v0.1.0)
- `__main__.py` — Entry point & argument parsing (all subcommands stubbed)
- `errors.py` — Custom exceptions (HargaError, DatabaseError, ArgumentError)
- `db.py` — Database layer with 4 stubbed query functions
- `formatters.py` — JSON & text output formatting (3 stubbed)
- `commands/__init__.py` — Command package
- `commands/tenders.py` — Tenders handler (stubbed)
- `commands/bids.py` — Bids handler (stubbed)
- `commands/entities.py` — Entities handler (stubbed)

**Test infrastructure** (tests/):
- `conftest.py` — Pytest fixtures (temp DBs, sample data)
- `test_harga_cli_example.py` — Example test patterns (20+ test templates)

**Configuration**:
- `pyproject.toml` — Entry point, dependencies, pytest config, coverage rules

**Tools**:
- `SETUP_VERIFY.sh` — Readiness verification (6 checks, all pass)

## Verification Status

```bash
./SETUP_VERIFY.sh  # Output:
✓ Python 3.12.3
✓ sqlite3 available
✓ pytest available
✓ All modules compile (9 files)
✓ CLI help shows commands
✓ Test infrastructure compiles
✓ Project structure ready
```

Manual checks:
```bash
harga-cli --version          # Shows 0.1.0 ✓
harga-cli --help             # Shows all subcommands ✓
python -m pytest tests/ -q   # Collects test patterns ✓
```

## Implementation Tasks Ready

**12 builder tasks** identified & templated:
1. `db.query_tenders()` — Parameterized SQL with filters & pagination
2. `db.query_bids()` — Join entities, parameterized queries
3. `db.query_entities()` — List all entities
4. `db.set_entity_notification()` — Update entity config
5-8. Command handlers (tenders, bids, entities list/config)
9-11. Text formatters (tenders, bids, entities tables)
12. Wire up dispatch in __main__.py

**5+ test suites** with pattern templates (all stubbed with pytest structure)

**Full infrastructure**:
- Fixtures for test databases (temp files, auto cleanup)
- Sample data loading functions
- Edge case patterns documented in test examples

## Next Steps for Operator

1. **Verify databases exist:**
   ```bash
   ls data/harga_v8.db data/tenders.db
   ```

2. **Write initial goal** to context/GOAL.md:
   ```
   Implement 'tenders' command: query, filter by entity/status, paginate with limit/offset
   ```

3. **Conductor assigns tasks** → builders implement → testers verify → reviewers audit

4. **Track progress** in STATE.md

## Key Files for Quick Reference

| File | Purpose | Lines |
|---|---|---|
| DEVELOP.md | Setup + workflow guide | 300+ |
| PROJECT_CHECKLIST.md | Sign-off checklist | 150+ |
| tools/harga_cli/db.py | Database templates | 100 |
| tests/conftest.py | Pytest fixtures | 150 |
| context/experts.json | Expert system | 200 |

**Deliverable**: 14 files created, all dependencies in place. Experts can begin immediately.
