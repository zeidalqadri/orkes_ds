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

## Verification Defect (synthesizer, recurring) | 2026-08-01
- **Root cause**: CONNECTIONS.md twice (W31, W32) claimed builder's learnings.md was "~30 corrupted noise entries, all Build X/Fix timeout" WITHOUT reading the file. Actual file (46 lines, ~20 substantive patterns) disproves it; the 2026-08-01 correction in-file is the second time (reviewer made the same claim 2026-03-30 re: "1604 actions").
- **Rule**: Never report on another agent's file/artifact without reading it first. Synthesis claims about knowledge quality are high-severity because they drive action items (purge/reseed) that would DESTROY good data. If the premise is false, the action item is invalid.

## Supplier Aggregate Accounting (webdav-intel)

**Finding (2026-07-31) | price_count accounting bug | root cause → prevention**

- `_upsert_supplier` (services/webdav_intel/pipeline.py) upserted supplier identity only and never maintained derived `price_count`/`product_count`/`price_min`/`price_max`. Every supplier read 0 despite ~12K offerings in `m_offerings`, breaking downstream `has_prices`/price-rank/sort.
- **Rule**: when a table carries derived aggregates (`count`, `min`, `max`) that other queries filter/rank on, recompute them from the single source of truth (`m_offerings`), never increment at insert. Incrementing is fragile — breaks on dedup, restart, deletion, and can't backfill existing rows.
- **Pattern used**: one aggregate `UPDATE ... SET product_count=(SELECT COUNT(*)...), price_count=(COUNT WHERE unit_price>0), price_min/max=(MIN/MAX positive)` keyed off the FK column; plus an idempotent whole-table `repair_` backfill + `--apply` script for pre-existing rows.
- **Verify** derived metrics by checking `COUNT(DISTINCT supplier_slug)` vs `SUM(price_count)` and that a known supplier's count matches its offering count.
- After patching a long-running pm2 service, **restart it** so the new code loads; run the backfill, then health-check. `sec-webdav-intel` port 3651 `/health`.

---

## Phase 4 Testing (2026-08-02)

Source: arbos-orkes_ds2

- **_fake_conn with dict-based rows_by_query**: Only matches exact SQL strings. Multi-query task.check() methods must use MagicMock with side_effect instead. ProductionReportTask, DashboardTask etc. query multiple tables — single dict can't handle it.
- **_material_total** (delivery_cost_task): Uses `unit_price` first, `bid_price` as fallback only when `unit_price` absent. `quantity=0` results in `0 or 1 = 1` (falsy zero). `_source="delivery_cost_review"` items are excluded from material total.
- **_parse_llm_response**: Code-block JSON extraction only triggers when backticks present. Without backticks, the raw text is passed straight to json.loads — any extraneous text causes failure. Trailing text after `}` is OK only if inside ``` fences (find/rfind strips it).
- **_get_llm_caller fallback**: try/except wraps the function DEFINITION not EXECUTION. Patching `sdk.llm_client.call_llm` with ImportError doesn't trigger fallback — it's already imported successfully. Need to block the import statement itself.
- **Scheduler task names**: PackagingTask="auto_package" not "package". ForsahPostSubmissionScanTask="forsah_post_submission_scan" not "forsah_post_submission". ProposalTemplateTask="proposal_templates" not "proposal_template". Verify names from source before asserting.
- **TenderAlertTask attributes**: Has THRESHOLDS (list of tuples) not ALERT_WINDOW_DAYS. No COOLDOWN_HOURS class attr (cooldown logic is check-local).
- **CertExpiryTask**: No WARNING_DAYS constant — thresholds are defined inline in check() via threshold list.
- **Module-level imports in check() methods**: patch the source module where the import happens, not the scheduler. E.g. `build_production_status` → patch `services.harga_v8.production`. `record_task_run/get_task_metrics` → patch `services.harga_v8.db`.
- **_salvage_llm_estimates(None)**: Raises AttributeError (.find() called on None). Not handled gracefully — expected behavior given the function assumes string input. Tests should handle this as known behavior.
- **calc_final_price with bool**: float(True) → 1.0, float(False) → 0.0. No ValueError/TypeError. Not a testable edge case for `raises` assertions.

---

## Verification Defect (arbos, recurring) | 2026-08-04

- **Root cause**: Bookmark triage `outbox/bookmarks/2084591994412675436.md` (2026-08-04) claimed OmniRoute was "already recorded in shared_learnings.md line 107-108" — **false**. `grep -inr omniroute context/shared_learnings.md` returns zero matches. The file is 111 lines and ends at "Phase 4 Testing". No OmniRoute entry exists anywhere in the file. This is the same pattern as the 2026-08-01 synthesizer defect above: claiming knowledge exists in another file without reading it.
- **Rule**: Before claiming an artifact contains a specific entry, read the artifact. grep is fast and definitive.
- **Correction**: OmniRoute eval completed 2026-08-04 (`outbox/omniroute-eval.md`). Verdict: HOLD.

---

## Self-Improving Agent Loop — 5 Proposals IMPLEMENTED (2026-08-05)

Source: @rvaniaaaa self-improving agent loop triage (`outbox/bookmarks/2084589218043462126.md`). Turned into durable skill-registry artifacts, not reports.

| # | Proposal | Where implemented | Status |
|---|---|---|---|
| P1 | Skill discovery loop (researcher→analyst→Explore→reviewer→write-a-skill→publish, no auto-merge) | `~/.claude/skills/skill-discover/SKILL.md` | ✓ |
| P2 | Score-gate before token investment (3-point kill gate) | `skill-discover/SKILL.md:41-48`, `skill-improver/SKILL.md:30-52` | ✓ |
| P3 | Install-ready reviewer standard ("would engineer install without editing?") | `skill-discover/SKILL.md:50-55`, `skill-improver/SKILL.md:54-57` + Code-Gen checklist | ✓ |
| P4 | Docs-first reading (README/DESIGN before source) | `skill-discover/SKILL.md` step 3 + REFERENCE stage-3 prompt | ✓ |
| P5 | Compound-effect / provenance chain tracking | `~/.claude/skills/_discovery/skill_discovery_log.md` | ✓ |

**Rule**: kill early, invest late. A candidate that fails the 3-point gate (novel / actionable / minimal-deps) dies before generation. Anything requiring edits to run is a draft, not a deliverable. Every operator-approved publish appends a provenance row.
