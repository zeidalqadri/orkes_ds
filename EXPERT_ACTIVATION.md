# Expert Activation Guide

How to invoke each expert for harga-cli development.

## Overview

The harga-cli project uses a 4-person expert team coordinated via `context/GOAL.md` and `context/INBOX.md`. Each expert runs in isolation with dedicated system prompt and model routing.

**Expert Fleet**:
- **@conductor** (Sonnet) — orchestration, subcommand prioritization
- **@builder** (Opus) — implementation, argparse, SQLite
- **@reviewer** (Opus) — code review, security audit
- **@tester** (Sonnet) — pytest fixtures, CLI testing

---

## Activation Flow

### 1. Operator writes GOAL.md

```markdown
# Harga CLI Development

Implement tenders subcommand: list, filter by entity, paginate with limit/offset.

Expected CLI:
  harga-cli tenders list [--entity SLUG] [--status open] [--limit 50]
```

### 2. Conductor reads + sequences

```bash
cd /home/the_bomb/orkes_ds2
python arbos.py inbox conductor "Plan the tenders subcommand implementation"
```

Conductor outputs to `context/conductor/GOAL.md`:
```
Sequence for tenders subcommand (3 tasks):
1. @builder: Implement query_tenders() in db.py + handle_tenders() in commands/tenders.py
2. @tester: Write unit & integration tests for tenders command
3. @reviewer: Audit code for SQL injection, performance, API stability
```

### 3. Builder implements

```bash
python arbos.py inbox builder "Implement tenders subcommand per conductor's sequence (task 1/3)"
```

Builder reads:
- `context/HARGA_CLI_REFERENCE.md` (DB schemas, module APIs)
- `context/conductor/GOAL.md` (scoped task)
- `context/shared_learnings.md` (patterns, mistakes to avoid)
- `/home/the_bomb/orkes/harga/` target codebase

Builder outputs:
- Implementation in `/home/the_bomb/orkes/harga/` (absolute paths, never symlink)
- Learnings to `context/builder/learnings.md`
- Status update to `context/STATE.md`

### 4. Tester writes tests

```bash
python arbos.py inbox tester "Write tests for tenders command (task 2/3)"
```

Tester writes:
- Tests in `/home/the_bomb/orkes/harga/tests/test_harga_cli.py`
- Uses conftest.py fixtures (temp SQLite DBs, sample data)
- Capture subprocess.run() for CLI output validation
- Learnings to `context/tester/learnings.md`

### 5. Reviewer audits

```bash
python arbos.py inbox reviewer "Review tenders implementation for security & performance (task 3/3)"
```

Reviewer checks:
- SQL injection (parameterized queries only)
- Index usage (leveraging v8_bids indexes, FTS5 in price_memory)
- JSON field parsing (items/levers/confirmed_prices from SQLite)
- Output contract (stable JSON schema, --table column alignment)
- Error handling (FileNotFoundError, sqlite3.OperationalError)
- Module boundaries (no Flask deps, use orkes_* packages only)

Reviewer outputs:
- Code review findings to `context/reviewer/GOAL.md`
- Suggested fixes to builder
- Learnings to `context/reviewer/learnings.md`

---

## Communication Channels

### Within Task (Expert → Expert)

- **Write findings to**: `context/<handle>/findings.md`
- **Request follow-up**: Add item to `context/INBOX.md`
- **Escalate blocker**: Write to `context/STATE.md` ## Blocker section

### To Operator

- **Telegram**: `python arbos.py send "message"`
- **Buzz channel**: Write to `context/buzz_response.md` (auto-sent)
- **Urgent alert**: Write to `context/buzz_alert.md` (sent to #alerts)

---

## Context Files Reference

| File | Ownership | Purpose |
|------|-----------|---------|
| `GOAL.md` | Operator | Top-level mission, current task |
| `STATE.md` | All experts | Working memory, phase (PLAN/ACT), approach, blockers |
| `INBOX.md` | Operator → Experts | Task queue, consumed each step |
| `context/<handle>/GOAL.md` | Conductor | Sequenced subgoals for each expert |
| `context/shared_learnings.md` | All | Fleet-wide patterns, recurring mistakes |
| `context/<handle>/learnings.md` | Each expert | Personal learnings (patterns, gotchas, solutions) |
| `context/<handle>/findings.md` | Each expert | Work output (findings, diffs, suggestions) |

---

## File Manifest

**Read-only** (experts must not modify):
- `CLAUDE.md` — Architecture, verification, named mistakes
- `PROMPT.md` — Mission, constraints
- `HARGA_CLI_REFERENCE.md` — DB schemas, module APIs
- `pyproject.toml` — Package config, entry point
- `/home/the_bomb/orkes/harga/data/*.db` — Databases

**Read-write** (experts modify during work):
- `/home/the_bomb/orkes/harga/harga_cli.py` — CLI entry point
- `/home/the_bomb/orkes/harga/tools/` — Helper modules
- `/home/the_bomb/orkes/harga/tests/` — Test suite
- `context/STATE.md` — Working memory
- `context/<handle>/learnings.md` — Personal learnings
- `context/<handle>/findings.md` — Work findings

**Auto-generated** (experts read but don't manually edit):
- `context/runs/<timestamp>/` — Timestamped run artifacts

---

## Verification Checklist

After each expert completes their task, run:

```bash
cd /home/the_bomb/orkes_ds2 && bash SETUP_VERIFY.sh
```

Key verifications by expert:

**Builder**:
- `python -c "import py_compile; py_compile.compile('/home/the_bomb/orkes/harga/harga_cli.py', doraise=True)"`
- `/home/the_bomb/orkes/.venv/bin/python /home/the_bomb/orkes/harga/harga_cli.py --help`
- Smoke test: `harga-cli entities list`, `harga-cli bids list`

**Tester**:
- `cd /home/the_bomb/orkes/harga && /home/the_bomb/orkes/.venv/bin/python -m pytest tests/test_harga_cli.py -v`
- Coverage >= 80%: `pytest --cov=tools/harga_cli --cov-report=term-missing`

**Reviewer**:
- Grep for SQL injection: `grep -n "f\".*{" /home/the_bomb/orkes/harga/harga_cli.py` (should be empty)
- Check index usage: Read HARGA_CLI_REFERENCE.md § Database Schemas
- No Flask imports: `grep -n "from flask\|import flask" /home/the_bomb/orkes/harga/harga_cli.py` (should be empty)

---

## Quick Links

- **Architecture**: `CLAUDE.md`
- **Mission**: `PROMPT.md`
- **Reference**: `context/HARGA_CLI_REFERENCE.md`
- **Patterns**: `context/shared_learnings.md`
- **Entry point**: `/home/the_bomb/orkes/harga/harga_cli.py`
- **Databases**: `/home/the_bomb/orkes/harga/data/`
- **Venv**: `/home/the_bomb/orkes/.venv/`

---

## Escalation

If stuck:
1. Write to `context/STATE.md` ## Blocker section with:
   - **Issue**: what failed
   - **Root cause**: diagnosis (or "unknown")
   - **Tried**: what you attempted
   - **Unblocked by**: what would help (info, permission, decision, etc.)

2. Send to operator: `python arbos.py send "blocker: <issue>"`

3. Await operator decision in `context/INBOX.md`

---

## Notes

- All experts have full context from `CLAUDE.md`, `PROMPT.md`, and `HARGA_CLI_REFERENCE.md`
- Workdir is `/home/the_bomb/orkes_ds2`, but **target codebase is `/home/the_bomb/orkes/harga/`** — always use absolute paths
- No new pip dependencies — argparse is stdlib, use reusable modules for DB/price/tender logic
- Transactions: SQLite's default autocommit; use explicit `BEGIN/COMMIT` if needed
- Secrets: Never log DB paths with credentials, .env values, or API tokens
