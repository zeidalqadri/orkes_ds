# CLAUDE.md

## Architecture

Orkes Ds2: builds harga-cli for the Harga pricing intelligence platform.

- **Harga root**: `/home/the_bomb/orkes/harga/`
- **CLI entry**: `/home/the_bomb/orkes/harga/harga_cli.py` (single file, argparse)
- **Venv**: `/home/the_bomb/orkes/.venv/`
- **Reference**: `context/HARGA_CLI_REFERENCE.md` (DB schemas, module APIs, subcommand surface)

Reusable modules (no Flask dependency):
- `modules/bid_crud.py` — BidManager class (CRUD, status transitions, audit log)
- `modules/scheduler.py` — Scheduler, EscalationTask, ReminderTask
- `orkes_pricing.price_memory` — price history with FTS5 search
- `orkes_tender.tender_db` — tender storage and search
- `orkes_core.db_utils` — get_connection() helper

Databases (all in `/home/the_bomb/orkes/harga/data/`):
- `harga_v8.db` — bids, entities, assignments, submissions, audit log
- `price_memory.db` — price history (FTS5 indexed)
- `supplier_index.db` — supplier catalog (FTS5 + embeddings)

## Verification

| Deliverable | Command | Pass |
|---|---|---|
| Python syntax | `python -c "import py_compile; py_compile.compile('/home/the_bomb/orkes/harga/harga_cli.py', doraise=True)"` | No exception |
| CLI boot | `/home/the_bomb/orkes/.venv/bin/python /home/the_bomb/orkes/harga/harga_cli.py --help` | Shows subcommands |
| Smoke test | `/home/the_bomb/orkes/.venv/bin/python /home/the_bomb/orkes/harga/harga_cli.py entities list` | JSON output |
| Tests pass | `cd /home/the_bomb/orkes/harga && /home/the_bomb/orkes/.venv/bin/python -m pytest tests/test_harga_cli.py -x` | 0 failed |

## Named Mistakes

- **M1 Stale Edit**: Edit tool fails silently on stale context. Re-read after every edit.
- **M2 SQL injection**: Always use parameterized queries (`?` placeholders, not f-strings).
- **M3 Wrong cwd**: Your cwd is ~/orkes_ds2, but the target is ~/orkes/harga/. Always use absolute paths.

## Guardrails

- Always use absolute paths — cwd is ~/orkes_ds2, target is ~/orkes/harga/.
- Tool results >50K chars silently truncate. Re-run with narrower scope.
- Ambiguous request: ask. >5 files: phase it. DB migration: backup first.
- No new pip dependencies — argparse is stdlib.
- JSON output default, --table for humans. No tabulate dependency.
