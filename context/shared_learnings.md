# Shared Learnings

Fleet-wide knowledge base for the orkes_ds2 (Harga CLI) bot. All experts read this before starting any task.
Append new entries under the relevant section. Do not duplicate — check first.

---

## Harga Ecosystem & Databases

Source: cli-builder, cli-tester, cli-conductor

**Databases**:
- `harga_v8.db` — bids table, assignments, entities, audit_log (primary operational DB)
- `tenders.db` — tender feed intake, deduplicated tender records
- Query: always use parameterized queries (? placeholders) to prevent SQL injection

**Key tables** (harga_v8.db):
- `bids` — id, tender_id, entity_id, status, deadline, amount, created_at
- `entities` — id, name, category, notification_channel (Telegram chat_id for alerts)
- `audit_log` — user_id, action, timestamp, details (all Albert admin actions logged here)

**CLI design**:
- Entry point: `tools/harga_cli/__main__.py` with argparse
- Default output: JSON (machine-readable, stable schema)
- Add `--text` flag for human-readable formatted output
- Exit codes: 0 success, 1 DB error, 2 user error (invalid args)
- Commands must be idempotent (safe to run multiple times)

**Performance**: Database queries should use indexes. Add `--limit` and `--offset` for large result sets. Avoid full table scans.

## CLI Implementation Patterns

**Parameterized Queries**
- Always use `?` placeholders for filters/values
- Build WHERE clause dynamically, append params to list
- Never use f-strings or string interpolation for SQL values
- Example: `query += " AND entity = ?"; params.append(entity_slug)`

**Count Queries for Pagination**
- Execute separate COUNT(*) query to get total (needed for pagination response)
- Same WHERE filters as data query, but no LIMIT/OFFSET
- Pattern: query data → get rows, run count → get total, return both

**Output Formatting**
- Default: JSON with `{"rows": [...], "total": N, "limit": L, "offset": O}`
- Optional: `--text` flag for human-readable table (simple print, no tabulate dep)
- JSON keys are stable snake_case (tender_id, not tenderId)
- Null fields included in JSON (don't omit them)

**Exit Codes**
- 0 = success
- 1 = database error (file not found, schema issue, locked DB)
- 2 = user error (invalid arguments, bad value format)

**Row Factory**
- `conn.row_factory = sqlite3.Row` makes fetchall() return dict-like objects
- Convert to dict with `dict(row)` for JSON serialization
- If not set, fetchall() returns tuples and dict access fails

**Error Handling**
- FileNotFoundError — missing DB file (check path is absolute, file exists)
- sqlite3.OperationalError — schema issue, locked DB, or malformed query
- Always close() connection in finally block, even on error

## Recurring Mistakes (promoted from expert mistakes.md)

When the same root cause appears in 2+ expert mistakes.md files, it belongs here.
Format: Source experts | Dates | Root cause | Prevention rule.

**M1 Relative Paths** | builder, reviewer | 2026-07-28
- Using relative paths like "data/harga_v8.db" or "~/" in code
- Prevention: Always use absolute paths `/home/the_bomb/orkes/harga/data/harga_v8.db`

**M2 Missing row_factory** | builder | 2026-07-28
- Forgetting `conn.row_factory = sqlite3.Row` before queries
- Prevention: Set at connection time; test dict access with fetchone()[key] syntax

**M3 SQL Injection via f-strings** | reviewer | 2026-07-28
- Using f"WHERE entity = '{entity}'" in queries
- Prevention: Grep for patterns like f".*{" in SQL strings; always use ? placeholders
