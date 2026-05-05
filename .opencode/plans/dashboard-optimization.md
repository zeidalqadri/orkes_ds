# v2 Dashboard Optimization Plan

## Phase 1 — System Pulse Strip (monitoring)
Add live health indicators to the Centcom bar. All data already exists in `/api/ops/status`.

**Changes:**
- `static/v2.html`: Add 5 new `.centcom-item` elements (enrichment last run, stale profiles, pipeline active jobs, scheduler state, queue depth). Each polls every 15s.
- `page_routes.py`: Add `GET /api/v2/ops-status` — thin proxy that calls `ops_routes.ops_status()` and returns the JSON (avoids CORS/auth issues hitting internal endpoints directly from the browser).

**Effort:** Low (data exists, just render it). **Impact:** High (immediate situational awareness).

## Phase 2 — Control Panel (control)
Replace bare "▶ List" / "▶ Pricesheets" buttons with an action panel.

**Changes:**
- `static/v2.html`: Replace `.centcom-actions` div with collapsible action panel containing:
  - `[▶ List]` `[▶ Pricesheets]` triggers (keep existing, add account selector dropdown)
  - `[⊘ Scheduler ON/OFF]` toggle switch → `POST /api/v2/scheduler/toggle`
  - `[⚡ Enrich Now]` → `POST /api/v2/scheduler/run`
  - `[↻ Re-Auth]` → `POST /api/v2/daemon/reload`
  - `[⏹ Stop All]` → `POST /api/v2/scrapers/stop`
  - Account selector dropdown for SmartGEP (consurv/ctventures/dyna-om-petronas)
- `page_routes.py`: Add 4 POST endpoints that proxy to existing APIs:
  - `POST /api/v2/scheduler/toggle` → `PATCH /api/scheduler/config`
  - `POST /api/v2/scheduler/run` → `POST /api/scheduler/run`
  - `POST /api/v2/daemon/reload` → `POST http://127.0.0.1:9876/reload`
  - `POST /api/v2/scrapers/stop` → `POST /api/scrapers/stop`

**Effort:** Low (4 proxy endpoints + HTML expansion). **Impact:** High (operators can react without switching pages).

## Phase 3 — Batch Operations + Live Logs (execution)
Enable multi-select on tenders and real-time scraper log streaming.

**Changes:**
- `static/v2.html`:
  - Add checkboxes to tender rows in the tree
  - "Select all in group" button per group header
  - Batch action bar: `[Fetch Selected (N)]` `[Reparse Selected]` `[Clear Selection]`
  - Replace 5s log poll with SSE `EventSource` on `/api/scrapers/logs/smartgep/stream` for real-time log display
  - Batch fetch: iterate selected tenders, POST each in sequence, show batch progress
- `page_routes.py`:
  - Add `POST /api/v2/tenders/batch-fetch` — accepts `{tender_ids: [...]}` and returns job IDs
  - Add `GET /api/v2/scrapers/logs/stream` — SSE pass-through (or the existing endpoint works directly since it's already on port 3636)

**Effort:** Medium (checkbox logic + SSE + batch API). **Impact:** Medium (productivity multiplier for operators processing multiple tenders).

## Phase 4 — Pipeline + Alert Feed (deep monitoring)
Add pipeline visualization and a persistent alert feed.

**Changes:**
- `static/v2.html`:
  - New "Pipeline" tab in main panel:
    - Horizontal pipeline bar: `Scraped(642) → Parsed(180) → Analyzed(150) → Matched(120) → Actioned(90) → Gallery(50)`
    - Each stage shows count + delta from last poll (up/down arrow)
    - Highlight bottleneck stages (red border if count > threshold)
    - Enrichment batch: progress bar `[████████░░] 80% (240/300 profiles, ETA 4 min)`
  - New "Alerts" tab:
    - Timeline of recent alerts with severity badges
    - Auto-scroll, filter by severity level
- `page_routes.py`:
  - Add `GET /api/v2/pipeline` — proxy to `ops_routes.ops_pipeline()`
  - Add `GET /api/v2/alerts` — read from new ring-buffer file
  - Add `POST /api/v2/alerts` — write to ring buffer (for internal use)
- New `alerts.py`:
  - Ring buffer (last 200 alerts) persisted to `alerts_ring.json`
  - `emit(level, source, message)` — called by existing error handlers in scheduler, scraper, daemon health checks
  - Levels: CRITICAL (daemon dead, all scrapers failed), WARNING (portal error, enrichment degraded), INFO (scrape complete, enrichment done)

**Effort:** Medium-High (alerts infra + pipeline rendering). **Impact:** High (visibility into system operation + actionable alerting).

## Phase 5 — Per-Tender Execution Detail + Polish (execution depth)
Surface detailed progress for individual tender operations.

**Changes:**
- `static/v2.html`:
  - Inline fetch progress per tender: phase indicators (authenticating → downloading → parsing → extracting pricesheets → done) as small dots
  - BoQ extraction live count: "BoQ: 45 items found" updating as child sheets are fetched
  - Enrichment batch drill-down: click enrichment progress bar to see per-profile enrichment log
  - Scraper config inline (max pages, download docs) — small expandable section
- `page_routes.py`:
  - Add `GET /api/v2/tender/{id}/progress` — returns current fetch/parse/enrichment state for a single tender
  - Add `PATCH /api/v2/scrapers/config` — proxy to scraper config update

**Effort:** Medium. **Impact:** Medium (power-user features, operator debugging).

---

## File Inventory
| File | Phase | Action |
|------|-------|--------|
| `static/v2.html` | 1-5 | Expand — add HTML + JS for all features |
| `page_routes.py` | 1-5 | Add proxy endpoints to existing APIs |
| `alerts.py` | 4 | New — ring-buffer alert feed |
| `alerts_ring.json` | 4 | New — persistent alert storage |
| `scheduler.py` | 4 | Light touch — call alerts.emit() on errors |
| `scraper_routes.py` | (no changes) | Existing APIs sufficient |
| `ops_routes.py` | (no changes) | Existing APIs sufficient |

## Dependencies
- Phase 2 depends on Phase 1 (action panel items reference centcom layout)
- Phase 3 is independent of Phases 1-2
- Phase 4's alert feed depends on new `alerts.py` module
- Phase 5 depends on Phases 1-4 (builds on existing monitoring data)
- Phase 1, 3 can run in parallel if two developers
