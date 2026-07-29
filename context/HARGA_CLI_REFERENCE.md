# Harga CLI Reference

Architecture reference for building `harga-cli` — a command-line interface for the Harga pricing intelligence platform.

## Codebase Location

- **Harga root**: `/home/the_bomb/orkes/harga/`
- **CLI target**: `/home/the_bomb/orkes/harga/harga_cli.py` (new file)
- **Shared packages** (pip-installed, editable):
  - `orkes-core` (0.2.0) — DB utils, LLM client, logging, alerts → `/home/the_bomb/orkes/packages/orkes_core/`
  - `orkes-pricing` (0.2.0) — price memory, FX rates, web search → `/home/the_bomb/orkes/packages/orkes_pricing/`
  - `orkes-tender` — tender DB, parsing, pipeline, alerts → `/home/the_bomb/orkes/packages/orkes_tender/`
- **Harga venv**: `/home/the_bomb/orkes/.venv/` (shared orkes venv)

## Reusable Modules (No Flask Dependency)

### `modules/bid_crud.py` — BidManager
```python
from modules.bid_crud import BidManager, UserContext, BidError, VALID_STATUSES

mgr = BidManager(get_conn=lambda: sqlite3.connect(DB_PATH))
ctx = UserContext(username="cli", entities={"consurv-technic"}, is_admin=True)

mgr.create(ctx, {"title": "...", "entity_slug": "dyna-om"})
mgr.get(ctx, bid_id)
mgr.list(ctx, entity_slug="dyna-om", status="draft")
mgr.update(ctx, bid_id, {"status": "priced"})
mgr.delete(ctx, bid_id)
```
Statuses: draft, priced, in_progress, submitted, won, lost, withdrawn, nobid, deleted

### `modules/scheduler.py` — Task Engine
```python
from modules.scheduler import Scheduler, EscalationTask, ReminderTask, NullNotifier

sched = Scheduler(get_conn=..., notifier=NullNotifier())
sched.register(EscalationTask(escalation_hours=2))
result = sched.run_once()  # {"escalation": 3, "reminder": 1}
```

### `orkes_pricing.price_memory` — Price History
```python
from orkes_pricing import price_memory
# Has FTS5 full-text search, Jaccard similarity matching
# DB at /home/the_bomb/orkes/harga/data/price_memory.db
```

### `orkes_tender.tender_db` — Tender Storage
```python
from orkes_tender import tender_db
# Tender CRUD, search, lifecycle management
```

## Database Schemas

### harga_v8.db (main app DB)
```
entities         — slug PK, name, label, notification_channel, team_leads, branding
v8_bids          — id PK, title, reference, status, entity_slug, items (JSON), levers (JSON),
                   confirmed_prices (JSON), source_tender_id, tender_context,
                   workflow_phase, assigned_to, outcome, outcome_history (JSON)
v8_assignments   — id PK, bid_id, assignee, task_type, status, deadline
v8_submissions   — id PK, bid_id, entity_slug, submitted_by, method, portal_ref
v8_chat_sessions — id PK, bid_id, title, entity_slug, workflow_state, messages (JSON)
v8_audit_log     — id PK, ts, user_id, action, resource_type, resource_id, entity_slug
v8_tender_assignments — tender_id PK, user_id, entity_slug
```

### price_memory.db
```
price_memory     — id PK, description, description_norm, tokens_json, unit_price,
                   total_price, quantity, unit, category, confidence, price_source,
                   strategy, tender_id, entity_slug, is_active, note
price_memory_fts — FTS5 index on description + description_norm
```

### supplier_index.db
```
suppliers        — id PK, slug UNIQUE, name, about, products_json, industries_json,
                   location, country, website, quality_score, product_count, price_count
suppliers_fts    — FTS5 index on name, about, products_text, industries_text, location
supplier_embeddings — slug PK, embedding BLOB, embed_text
```

## CLI Subcommand Surface

### Tier 1 — Read operations (safe, high-value)
```
harga tenders list [--entity SLUG] [--status STATUS] [--limit N]
harga tenders search QUERY
harga tenders show TENDER_ID

harga bids list [--entity SLUG] [--status STATUS]
harga bids show BID_ID
harga bids stats [--entity SLUG]

harga prices search QUERY [--category CAT]
harga prices stats

harga entities list
harga entities show SLUG

harga audit [--entity SLUG] [--since DATE] [--limit N]
```

### Tier 2 — Write operations (state-changing)
```
harga bids create --title TITLE --entity SLUG [--reference REF]
harga bids update BID_ID --status STATUS [--outcome won|lost]
harga bids import-tender TENDER_ID --entity SLUG

harga prices add --description DESC --unit-price PRICE --tender-id TID

harga assign BID_ID --to USER --task pricing|docs|review|submit [--deadline DATE]
```

### Tier 3 — Admin/ops
```
harga status                    # PM2 process health, DB sizes, queue depth
harga db sizes                  # All DB file sizes
harga scheduler run-once        # Execute scheduler tasks
harga sync                      # Trigger tender sync
```

## PM2 Processes
| Process | Port | Role |
|---------|------|------|
| harga | 3637 | Flask app (gunicorn) |
| harga-v8-scheduler | — | Assignment scheduler loop |
| harga-admin | — | Telegram bot (Albert) |

## Entities (Seed)
consurv-technic, dyna-om, dyna-segmen, dyna-sche

## Design Principles for the CLI
1. **Reuse modules/** — BidManager and Scheduler are already framework-free. Import directly.
2. **argparse, not click** — zero new dependencies. The orkes venv has enough.
3. **SQLite direct** for reads — the DBs are local files; no need to go through the HTTP API.
4. **JSON output by default** — pipe-friendly. Add `--table` flag for human-readable.
5. **Admin context** — CLI runs as admin (`UserContext(username="cli", is_admin=True)`).
6. **sys.path setup** — The CLI lives in `/home/the_bomb/orkes/harga/`. Import paths work naturally from there.
