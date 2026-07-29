# Harga CLI: Preparation Complete ✅

**Status**: Ready for expert team assignment
**Date**: 2026-07-28 21:40 UTC
**Setup Verification**: 7/7 checks passing

---

## What Was Prepared

The orkes_ds2 project now has **impeccable skills and resources** for harga-cli development by the expert team.

### Infrastructure (Verified ✅)

```
✅ Python 3.12.3 + shared venv /home/the_bomb/orkes/.venv/
✅ Orkes packages: core, pricing, tender (all installed editable)
✅ Databases: harga_v8.db, price_memory.db, supplier_index.db (all present, current data)
✅ Package: tools/harga_cli/ (scaffolded, syntax-valid)
✅ Testing: pytest 8.3.3, conftest.py with fixtures, coverage config
✅ Documentation: CLAUDE.md, PROMPT.md, HARGA_CLI_REFERENCE.md, shared_learnings.md
✅ Expert team: 4 experts (conductor, builder, reviewer, tester) with detailed system prompts
```

### New Resources Created

| Resource | Purpose | Audience |
|----------|---------|----------|
| **EXPERT_ACTIVATION.md** | How to invoke each expert, communication channels, escalation | Conductor, Builder, Reviewer, Tester |
| **DEVELOPER_QUICKSTART.md** | 5-minute setup guide, implementation patterns, common commands | Builder, Tester |
| **SETUP_VERIFY.sh** | Automated verification script (7 checks) | All experts, CI/CD |
| **READINESS_REPORT.md** | Comprehensive readiness assessment, checklist, next steps | Operator |
| **shared_learnings.md** (updated) | CLI patterns (parameterized queries, pagination, formatting), recurring mistakes (M1-M3) | All experts |

### Expert Team Capabilities

**Conductor (Sonnet)** — Orchestration, subcommand prioritization
- Reads GOAL.md + HARGA_CLI_REFERENCE.md
- Sequences tasks for builder, tester, reviewer
- Writes scoped goals to context/conductor/GOAL.md

**Builder (Opus)** — Implementation, argparse, SQLite queries
- Knows reusable modules: bid_crud.py, orkes_pricing, orkes_tender
- Implements with argparse + parameterized queries
- Verifies syntax + smoke test before each handoff
- Outputs to /home/the_bomb/orkes/harga/

**Reviewer (Opus)** — Security audit, performance review, API contracts
- Checks SQL injection (? placeholders, no f-strings)
- Verifies index usage (v8_bids indexes, FTS5 in price_memory)
- Audits module boundaries (no Flask imports)
- Reviews error handling, output contracts, no secrets

**Tester (Sonnet)** — pytest fixtures, CLI output capture, edge cases
- Writes unit tests with conftest.py fixtures (temp SQLite DBs)
- Captures CLI subprocess.run() for output validation
- Tests edge cases: empty results, unicode, NULL fields, malformed JSON
- Targets >= 80% coverage on critical paths

---

## How to Start

### Step 1: Set Goal (Operator)

Write the first task to `context/GOAL.md`:

```markdown
# Harga CLI Development

## Objective
Implement tenders subcommand: list, filter by entity/status, paginate with limit/offset

## Expected CLI
  harga-cli tenders list [--entity SLUG] [--status open] [--limit 50] [--offset 0]
  harga-cli tenders list --text  # human-readable output

## Success Criteria
- Default JSON output: {"rows": [...], "total": N, "limit": L, "offset": O}
- --text flag for human-readable table
- Exit codes: 0=success, 1=DB error, 2=user error
- Tests pass: pytest tests/ -v >= 80% coverage
```

### Step 2: Invoke Conductor

```bash
cd /home/the_bomb/orkes_ds2
python arbos.py inbox conductor "Plan the tenders subcommand implementation"
```

Conductor will:
1. Read GOAL.md + HARGA_CLI_REFERENCE.md
2. Sequence tasks for builder → tester → reviewer
3. Write to context/conductor/GOAL.md
4. Each expert reads their scoped goal and works independently

### Step 3: Monitor Progress

Check working memory:
```bash
cat context/STATE.md      # Overall state
cat context/conductor/GOAL.md  # Conductor's task breakdown
cat context/builder/findings.md  # Builder's work output
```

Verify at any time:
```bash
bash SETUP_VERIFY.sh
```

---

## Resources for Each Expert

### All Experts Read First
1. DEVELOPER_QUICKSTART.md (5 min) — setup, patterns, troubleshooting
2. context/HARGA_CLI_REFERENCE.md (10 min) — DB schemas, module APIs, CLI surface
3. context/shared_learnings.md (5 min) — patterns, recurring mistakes (M1-M3)

### Conductor
- EXPERT_ACTIVATION.md — expert responsibilities, sequencing, communication
- CLAUDE.md § Named Mistakes — M1 (stale edit), M2 (SQL injection), M3 (wrong cwd)

### Builder
- DEVELOPER_QUICKSTART.md § Implementation Patterns — query, formatter, argparse templates
- context/HARGA_CLI_REFERENCE.md § Reusable Modules — BidManager, price_memory, tender_db
- context/shared_learnings.md § CLI Implementation Patterns — parameterized queries, row_factory, pagination

### Tester
- DEVELOPER_QUICKSTART.md § Test section — unit test, CLI test, edge cases
- context/HARGA_CLI_REFERENCE.md § Database Schemas — key data shapes to test (bid items, entity, price_memory)
- EXPERT_ACTIVATION.md § Verification Checklist — what to verify after build

### Reviewer
- EXPERT_ACTIVATION.md § Verification Checklist — SQL injection, index usage, module boundaries, error handling
- context/HARGA_CLI_REFERENCE.md § Database Schemas — FTS5 usage, index names, JSON field parsing
- CLAUDE.md § Named Mistakes — M2 (SQL injection), module boundaries

---

## Verification

### Pre-Development ✅
```bash
cd /home/the_bomb/orkes_ds2 && bash SETUP_VERIFY.sh
# Output: 7/7 checks passing
```

### Post-Builder (Syntax + Smoke Test)
```bash
python -c "import py_compile; py_compile.compile('/home/the_bomb/orkes/harga/harga_cli.py', doraise=True)"
/home/the_bomb/orkes/.venv/bin/python /home/the_bomb/orkes/harga/harga_cli.py --help
harga-cli entities list  # Should return JSON or error
```

### Post-Tester (Tests + Coverage)
```bash
cd /home/the_bomb/orkes/harga
/home/the_bomb/orkes/.venv/bin/python -m pytest tests/test_harga_cli.py -v
/home/the_bomb/orkes/.venv/bin/python -m pytest tests/ --cov=tools/harga_cli --cov-report=term-missing
# Target: 0 failed, >= 80% coverage
```

### Post-Reviewer (Security Audit)
```bash
# SQL injection check (should be empty)
grep -n "f\".*{" /home/the_bomb/orkes/harga/harga_cli.py

# Flask imports (should be empty)
grep -n "from flask\|import flask" /home/the_bomb/orkes/harga/harga_cli.py

# Module boundaries (only orkes_*, modules/)
grep -n "^from tools\|^import tools" /home/the_bomb/orkes/harga/harga_cli.py | grep -v "tools.harga_cli"
```

---

## Files Created/Updated

### Created (New Resources)
- ✅ EXPERT_ACTIVATION.md
- ✅ DEVELOPER_QUICKSTART.md
- ✅ SETUP_VERIFY.sh
- ✅ READINESS_REPORT.md
- ✅ PREP_COMPLETE.md (this file)

### Updated
- ✅ context/shared_learnings.md (added CLI patterns + M1-M3 mistakes)

### Verified Unchanged (Ready)
- ✅ CLAUDE.md
- ✅ PROMPT.md
- ✅ context/HARGA_CLI_REFERENCE.md
- ✅ context/experts.json
- ✅ pyproject.toml
- ✅ tools/harga_cli/ (package structure)
- ✅ /home/the_bomb/orkes/harga/data/ (databases)

---

## Constraints & Conventions

**Zero Dependencies**: argparse only (stdlib). Reuse modules: bid_crud.py, orkes_pricing, orkes_tender.

**Absolute Paths Always**: cwd is ~/orkes_ds2, target is ~/orkes/harga/. Never use relative paths or ~.

**SQL Injection Prevention**: Parameterized queries only (? placeholders, never f-strings).

**Output Format**: JSON default, --text for humans. Keys are stable snake_case.

**Exit Codes**: 0=success, 1=DB error, 2=user error.

**Named Mistakes**:
- M1 Relative paths → use absolute /home/the_bomb/...
- M2 Missing row_factory → set at connection time
- M3 SQL f-strings → use ? placeholders always

---

## Contact & Escalation

**Operator Communication**:
- `python arbos.py send "message"` — Telegram
- `context/buzz_response.md` — Buzz channel (auto-sent)
- `context/buzz_alert.md` — #alerts channel (urgent)

**Blocker Escalation**:
1. Write to `context/STATE.md` ## Blocker section
2. Send: `python arbos.py send "blocker: <issue>"`
3. Operator responds via `context/INBOX.md`

---

## Sign-Off

✅ **Harga CLI project is ready for expert team development.**

All infrastructure, documentation, experts, and resources are in place.

**Next**: Operator sets GOAL.md and invokes conductor.

---

*Prepared: 2026-07-28 21:40 UTC*
*Setup Status: 7/7 checks passing*
*Expert Team: Conductor (Sonnet), Builder (Opus), Reviewer (Opus), Tester (Sonnet)*
