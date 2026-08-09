# Shared Learnings

Fleet-wide knowledge base for the orkes_ds2 (Harga CLI) bot. All experts read this before starting any task.
Append new entries under the relevant section. Do not duplicate — check first.

**Source precedence**: operator directives → `PROMPT.md` →
`context/HARGA_CLI_REFERENCE.md` → live schema/source inspection → this file. When
sources disagree, do not implement from memory; record the conflict and verify the
live platform before making a change.

---

## Harga Ecosystem & Databases

Source: `context/HARGA_CLI_REFERENCE.md` (reconciled 2026-08-09)

**Databases**:
- `harga_v8.db` — primary operational database; use the `v8_*` tables below.
- `price_memory.db` — FTS-backed historical pricing records.
- `supplier_index.db` — supplier intelligence and embeddings.
- Query: always use parameterized queries (? placeholders) to prevent SQL injection

**Key tables** (harga_v8.db):
- `entities` — slug, name, label, notification_channel, team_leads, branding
- `v8_bids` — id, title, reference, status, entity_slug, items, levers,
  confirmed_prices, source_tender_id, tender_context, workflow_phase, assigned_to,
  outcome, outcome_history
- `v8_assignments` — id, bid_id, assignee, task_type, status, deadline
- `v8_submissions` — id, bid_id, entity_slug, submitted_by, method, portal_ref
- `v8_audit_log` — id, ts, user_id, action, resource_type, resource_id, entity_slug
- `v8_tender_assignments` — tender_id, user_id, entity_slug

**CLI design**:
- Working source belongs in this repository's `cli/` directory. The legacy target
  path `/home/the_bomb/orkes/harga/harga_cli.py` is a platform reference, not a
  second executable to maintain.
- Use `argparse`; add no CLI framework dependency.
- Preserve a stable machine-readable mode, but favour dense terminal tables for
  interactive use. The JSON-default versus terminal-default contract remains open;
  resolve it before creating a public CLI entry point.
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
- Use stable JSON fields for machine-readable output, including null fields.
- Use compact ANSI-aware tables for interactive output; no filler prose.
- Choose and document one public default plus an explicit format flag before release.
- JSON keys are stable snake_case (tender_id, not tenderId)

## Shared-learning Review (2026-08-09)

- **Adopt — evidence gate**: the supplied synthesizer warning duplicates the existing
  verification rule below. Cross-artifact claims must cite a file read in the current
  step; otherwise label them unverified and take no destructive action.
- **Adopt — completion gate**: after a deliverable or terminal block, write the
  result once, set the goal state, and stop. Do not loop on near-identical “what next”
  messages without new operator input.
- **Adopt — report quality**: use observed facts, exact paths, concrete status, and
  named next actions. Do not substitute generic quality language for evidence.
- **Defer — multi-agent audit pattern**: phased parallel review is reserved for a
  bounded, independently divisible audit with explicit operator approval. It is not
  a default workflow for Harga CLI changes.
- **Reject — malformed synthesizer excerpt**: the supplied `LETE`/retro text has no
  verifiable source or CLI action. Do not promote it into operating guidance.
- **Corrected**: the prior shared baseline named stale tables, an obsolete entry
  point, and `--text` output assumptions. Historical example tests are not a source
  of truth and also mention paused Forsah/eTimad workflows.

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

## Codex 0.146 + DeepSeek models refresh — fixed via static catalog | 2026-08-06

- **Symptom**: `codex exec` aborted every step: `failed to refresh available models: missing
  field 'models'` (rc=1, 5 retries ~55s), loop fell back to claude→proxy. Trigger: stale
  `~/.codex/models_cache.json` (fetched_at > TTL) → codex refetches `GET {base_url}/models`.
- **Root cause**: codex 0.146 expects `{"models":[{slug,display_name,...}]}` (its own cache
  schema); DeepSeek returns OpenAI shape `{"object":"list","data":[...]}` → decode fails.
  `wire_api="chat"` is REMOVED in 0.146 (responses-only).
- **Fix**: static catalog `~/.codex/models_catalog.json` (entries cloned from
  `models_cache.json`, slugs incl. bare `deepseek-v4-flash`/`deepseek-v4-pro` so metadata
  lookup resolves) + top-level `model_catalog_json = "~/.codex/models_catalog.json"` in
  `~/.codex/config.toml`. With a catalog, refresh failure is non-fatal AND metadata resolves.
- **Prevention**: if a provider's /models shape isn't OpenAI-standard for codex, ship a
  catalog instead of debugging the refresh; verify with `codex exec -m <id> "say OK"`.
- DeepSeek v4 supports the responses API (codex 0.146 default) — no shim needed for chat.

## Host Reconfiguration (2026-08-06)

Source: arbos-orkes_ds2 (reconfig-plan.md)

- **Memory is the binding constraint** on this single 30GB box running ~30 pm2 processes.
  Swap at 99%, OOM killer active, service restart counts climbing. Relieve RAM before
  optimizing anything else.
- **Biggest levers** (descending): ollama qwen3.5:9b (9.2GB) → embed-server (1.9GB) →
  ocr-server (1.6GB) → idle opencode sessions (~1.0GB). ~13GB reclaimable total.
- **ollama model mismatch**: .env says `qwen3:8b` but `qwen3.5:9b` is loaded. Pin to
  qwen3:8b for 0.5-2GB savings; test sec-enrich output quality before committing.
- **OCR is always-on, never used**: ocr-server loads a 3B VLM on GPU1 (6.4GB VRAM) but
  GPU utilization is 0%. Convert to on-demand lifecycle via pm2 start/stop in
  text_extract.py; pytesseract Tier 2 fallback covers cold-start gap.
- **embed-server CPU-only by choice**: `CUDA_VISIBLE_DEVICES=""` despite GPU1 having
  3.4GB free. Move to GPU1 (`CUDA_VISIBLE_DEVICES=1`) to free ~466% CPU.
- **glorycloud exists but unused**: configured in orkes_sec/.env (GLORYCLOUD_*),
  pingable at 44ms, SSH not configured. Before migration: investigate hardware specs,
  install services, benchmark latency.
- **Orkes_Buzz2 flapping at 129 restarts**: exit code 42, chutes API 401, max_restarts=999.
  Cap at 5 or switch provider to deepseek. Exit code 42 → .arbos-launch.sh exited with
  that code (not OOM 137); likely chutes billing exhaustion.
- **Mission drift**: PROMPT.md still says "build harga-cli" — built. Actual role is ops/
  triage for orkes_sec production. Update PROMPT.md to reflect ops identity.
- **System design pattern**: this is a capacity-planning problem. Treat the box as a
  fixed-capacity cluster: identify over-provisioned services, right-size or offload,
  leave headroom for spikes. Full plan: ~/orkes/reconfig-plan.md.

## 2026-08-06 — DeepSeek price-hike derisk
- All arbos fleet bots currently route direct-api deepseek-v4-flash via provider_state fallback; opencode sessions go through OpenCode Zen reseller (partially insulated).
- LLM.md O1/O2/O3 (batching/single-shot) still unimplemented — verified no batch in tender_matcher.py, 40K chunking in passes. Biggest lever before any price change.
- Ledger (llm_ledger.jsonl + price_ledger.jsonl) has cost data but zero aggregation/alert tooling — spend visibility is the cheapest first derisk.
- Provider flip is one env var (`PROVIDER=`) + persisted provider_state.json — keep reseller/local paths alive; derisk = options, not replacement.
- **Spend/balance alert shipped (2026-08-06)**: `scripts/llm_spend_alert.py` in
  orkes/yellowpages aggregates both ledgers -> per-project/model cost, checks
  DeepSeek balance via /user/balance; cron daily 06:30 + every 6h. First run caught
  REAL low balance ($3.72 vs $5 threshold) -> Telegram alert fired, cooldown works.
- **Buzz2 flip corrected in reconfig-plan §3.1**: chutes -> zen/openrouter (NOT
  deepseek) per derisk P0.1 — don't add new direct-DS consumers before the hike.

## 2026-08-09 — Upstream Arbos compatibility gate

- `unarbos/arbos` `v0.1.47` is a strategic successor, not a drop-in update for
  the customized Python/PM2 fleet: it is Go `1.26.4`, stores state per project
  in `.arbos/sessions.db`, and keeps user configuration under `~/.config/arbos`.
- It includes web/TUI, Telegram, scheduler/outbox, MCP, and native OpenAI/
  Anthropic/Google adapters, but no Claude CLI subprocess compatibility was
  found. Validate auth and cost parity before any migration from the current
  Claude/Codex CLI router.
- Never launch it against a live project's Telegram identity during evaluation:
  its own source documents one poller per bot token. Use a separate bot and
  isolated PM2 pilot; preserve the current Python process as rollback.
- This host is capacity constrained (40 online PM2 processes, 11 GiB swap used
  at assessment). Measure pilot RSS and restart behavior before adding a
  persistent web/browser surface.
## 2026-08-09 — `andrew-btt/arbos` compatibility

- `andrew-btt/arbos` at `30dedaaa` is a standalone Python Ralph loop for Claude/OpenRouter and Telegram, not a compatible upgrade path for the shared `~/.arbos/core` controller.
- Do not run it alongside an existing Arbos process using the same Telegram bot: concurrent long polling can conflict. Any trial requires isolated state, credentials, PM2 name, and bot identity.

## 2026-08-10 — harga-cli post-restart checkpoint

- harga-cli is end-to-end functional and stable: syntax clean, 33/33 pytest pass, all Tier 1–3 subcommand groups (ent/bids/prices/tenders/audit/assign/status) present with --json/--table. Treat it as baseline-healthy; small evidence-backed changes only, never a rewrite.
- `status` dashboard is the single observability surface a fresh agent should run first — it reports PM2 health, all four DB sizes, pipeline counts, recent audit, swap, and disk in one invocation.
- Restart loop root cause class here was Codex model-config (`deepseek-v4-flash` unsupported with ChatGPT account in the router), NOT an app defect. When a pm2 arbos step fails with model 400s, check the LLM router config before touching the codebase.
- Reference Tier-3 `db sizes`/`scheduler run-once`/`sync` are deliberately unexposed — `status` already covers DB sizes, and scheduler/sync are operational, out of the read-terminal persona's value band.
