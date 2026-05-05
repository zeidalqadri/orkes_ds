# CREMA/harga — Product Design & Component Map

## Direction
A dense, tool-focused pricing cockpit for tender bidders. Think Bloomberg terminal for bid pricing — all data visible, zero clicks to see your margin on any line item. Monochrome with semantic color only for margin warnings and status.

**Three things this is NOT:**
1. Not a CRM dashboard with KPI widgets and sparklines
2. Not a project management board with cards and swimlanes
3. Not a spreadsheet replacement with gridlines everywhere

---

## 1. Core Concept

Spin the existing CREMA pricing module (`pricing_engine.py` + `workspace-pricing.js`) into a standalone product at `/tools/bid` on the yellowpages domain.

**The moat:** Price Memory SQLite DB. Every bid you price makes the next one faster and more accurate. The tool compounds in value.

**Users:** Bidders/suppliers responding to tenders (SmartGEP, ePerolehan, direct RFx). Single user or small team (2-5 people) per entity.

**Pricing model:** Free for basic use (3 active bids). Subscription for unlimited bids + price memory + competitor intel.

---

## 2. Feature-to-Component Mapping

### Primary Flow: Price a Tender

| # | Feature | Existing Component | Build Status | Notes |
|---|---------|-------------------|-------------|-------|
| 1 | Dashboard of all bids | Pricing workspace list + drafts API | **Borrow** | `pricing_workspace.py` `list_drafts()`, workspace-pricing.js already renders draft list |
| 2 | "+ New Bid" → upload pricesheet | Workspace pricing tab + ingest pipeline | **Borrow** | Pricesheet parsing exists in `price_researcher.py`, workspace upload pattern exists |
| 3 | Parse pricesheet → line items | `generate_pricing_data()` + price_researcher | **Borrow** | XLSX parsing, LLM extraction, regex extraction all exist |
| 4 | Price research (web + memory) | `price_researcher.py` + `price_memory.py` | **Borrow** | Background web scraping, memory similarity lookup exist |
| 5 | Line items with recommended price | Workspace-pricing.js line item table | **Borrow** | `_renderPricingWorkspace()` renders full table with price candidates |
| 6 | Price disambiguation modal | workspace-pricing.js `openDisambig()` | **Borrow** | Full disambiguation UI: price line, candidate cards, manual input |
| 7 | Strategy levers (markup/overhead/contingency) | `apply_cost_buildup()` + levers-grid CSS | **Borrow** | 3-column lever grid, 4 strategy presets exist |
| 8 | Margin/win probability display | pricing-summary bar + apply_cost_buildup | **Borrow** | Status bar with margin%, total bid price exists |
| 9 | Save draft / produce artifacts | `save_draft()` / `produce_pricing()` | **Borrow** | Draft CRUD + artifact generation (Jadual Harga, etc.) exist |
| 10 | Price memory ingestion on completion | `save_workspace()` ingests to price_memory | **Borrow** | Auto-ingestion on workspace save already implemented |

### Secondary Flow: Quick Price Check

| # | Feature | Existing Component | Build Status | Notes |
|---|---------|-------------------|-------------|-------|
| 1 | Paste line item → get price range | `price_memory.lookup()` + web_search | **Borrow** | similarity search + web extraction exist |
| 2 | Confidence score display | Confidence tier system in price_memory | **Borrow** | high/medium/low tiers exist |

### Screens / UI Components

| Component | Existing | Build Status | Notes |
|-----------|----------|-------------|-------|
| Dashboard: Active Bids table | `.crema-table` + draft list | **Borrow** | Need to wire up as standalone view |
| Dashboard: KPI summary cards | `.kpi-card` / `.kpi-row` in workspace.css | **Borrow** | Pipeline value, win rate, avg margin |
| Dashboard: Price memory health | — | **Build** | New component — memory coverage %, aging stats |
| Bid Pricing Workspace toolbar | `.pricing-toolbar` in workspace.css | **Borrow** | Entity picker, strategy selector, save/export buttons |
| Bid Pricing Workspace summary bar | `.pricing-status-bar` in workspace.css | **Borrow** | Items priced, base cost, markup, bid price, margin |
| Bid Pricing Workspace line items table | `.pricing-table` + workspace-pricing.js | **Borrow** | Inline editing, source badges, sub toggles |
| Price Disambiguation Modal | `.disambig-*` classes in workspace.css | **Borrow** | Price line, candidate cards, manual input |
| Strategy Panel (slide-in) | `.levers-grid` + strategy presets | **Borrow** | Per-category override support exists |
| Price Research Panel |  | **Build** | New panel — 3 tabs: price sheet, web research, memory matches |

---

## 3. Existing Modules (Inventory)

### Backend — Complete and Reusable

| File | Size | Purpose | Reuse |
|------|------|---------|-------|
| `pricing_engine.py` | ~400 lines | LLM-powered line item analysis & allocation | Direct |
| `pricing_workspace.py` | ~500 lines | CRUD, cost buildup, draft management, memory ingestion | Direct |
| `pricing_artifacts.py` | ~300 lines | Jadual Harga, assumptions doc generation | Direct |
| `price_memory.py` | ~200 lines | Similarity-based price lookup, confidence scoring | Direct |
| `price_researcher.py` | ~300 lines | XLSX parsing, web extraction, LLM estimation | Direct |
| `tender_pricing_routes.py` | ~200 lines | Pricing REST API (analyze, configure, produce, etc.) | Direct |
| `tender_pricing_service.py` | ~300 lines | Background scraping, pricing orchestration | Direct |

### Frontend — Complete and Reusable

| File | Size | Purpose | Reuse |
|------|------|---------|-------|
| `workspace-pricing.js` | ~800 lines | Full pricing workspace UI | Direct |
| `workspace.css` (pricing section) | ~400 lines | All pricing-specific CSS | Direct |

### Design System Tokens (from crema.css / nova.css)

- Color scale: `--text-1` through `--text-6`, `--success`/`--warning`/`--error`
- Spacing: 8px grid (`--space-1` through `--space-8`)
- Type scale: `--font-2xs` through `--font-5xl`
- Semantic backgrounds: `--success-bg`, `--error-bg`, `--warning-bg`, `--info-bg`
- Modal system: `--modal-sm/md/lg`, `.dialog-confirm`, focus trap
- Toast: fixed bottom-center, slide-up, undo/duration control
- Skeleton loading: shimmer animation classes
- Table: `.crema-table` with monospace numbers, hover rows
- Navigation: `.topbar`, `.mobile-tab-bar`, `.breadcrumb`

---

## 4. Build-vs-Borrow Summary

### Borrow (already exists, minimal adaptation needed)
- Full pricing backend API
- Full pricing workspace UI
- Price memory + research modules
- Design token system
- All data models (pricing_workspace.json, price_memory.db)
- Entity management, auth, user management

### Build (new, specific to standalone tool)
1. **Standalone page skeleton** — new route, new HTML page, wire up existing CSS/JS
2. **Dashboard view** — compose existing components (draft list + KPI cards) into a focused landing page
3. **Price memory health component** — new KPI-style card showing coverage stats
4. **Price Research Panel** — new slide-in panel with 3 tabs (price sheet / web research / memory matches)
5. **Navigation** — bid list + current bid context breadcrumb
6. **Quick Price Check** — new simple page or modal: paste description → get price range

### Estimated Build Effort
- Phase 1 (standalone shell + dashboard): **1-2 days**
- Phase 2 (full pricing workspace integration): **1-2 days** (mostly wiring)
- Phase 3 (export + memory + win tracking): **2-3 days**

Total: **~5-7 days** to full production, reusing ~80% of existing code.

---

## 5. User Flows

### Primary Flow: Price a Tender (Implementation)

1. Open `/tools/bid` → see dashboard of all bids via `list_drafts()` API
2. Click "+ New Bid" → enter tender reference + upload pricesheet Excel
3. Tool parses pricesheet via `price_researcher.py` → extracts line items → runs price research (web + memory) via `run_price_research_bg()`
4. Tool presents via `_renderPricingWorkspace()`: each line item with recommended price, confidence tier, source
5. User adjusts in pricing table: select supplier, override prices, apply strategy levers via `apply_cost_buildup()`
6. Tool shows: total bid price, margin breakdown, win probability via summary bar
7. User saves draft or produces artifacts via `produce_pricing()` (Jadual Harga, assumptions doc)
8. Submit. Workspace saves → auto-ingests prices into memory via `save_workspace()`

### Secondary Flow: Quick Price Check

1. Open `/tools/bid/quick` → paste a single line item description
2. Tool returns: estimated price range from `price_memory.lookup()` + web research, confidence score
3. Useful for preliminary go/no-go decisions before full bid preparation.

---

## 6. Screens

### 6.1 Dashboard (`/tools/bid`)

Two sections above the fold — no scrolling required on 13" laptop:

**Left (60%): Active Bids table** (reuse `.crema-table` + draft list)
| Bid Ref | Client | Items | Priced | Your Price | Est Value | Margin | Status |
|---------|--------|-------|--------|-----------|-----------|--------|--------|
| RFP-2026-0517 | PETRONAS Carigali | 24 | 18/24 | RM 1,240,500 | RM 1.8M | 22.4% | draft |
| GTC-00941 | Shell MDS | 8 | 8/8 | RM 347,200 | RM 400K | 15.0% | ready |

**Right (40%): Quick glance KPIs** (reuse `.kpi-card`)
- Active bids: 4 (RM 3.2M pipeline)
- Win rate: 68% (17/25)
- Avg margin: 19.7%
- Memory coverage: 73% (items with price memory hits)

Bottom: Price memory health — "Learned from 42 bids, 847 line items" (**new component**)

### 6.2 Bid Pricing Workspace (`/tools/bid/<id>`)

Full-width, three vertical bands:

**Band 1 — Toolbar (60px)** (reuse `.pricing-toolbar`)
[Back] [Bid Ref] [Strategy selector] [Entity picker] [Save Draft ▾] [Export ▾] ── [RM 1,240,500 total]

**Band 2 — Summary bar (auto-height)** (reuse `.pricing-status-bar`)
Items: 24 | Priced: 18 | Unpriced: 6 | Base cost: RM 980K | Markup: 18.5% | Overhead: 8% | Contingency: 3% | **Bid price: RM 1,240,500** | Margin: 22.4% | Win prob: 74%

**Band 3 — Line items table** (reuse `.pricing-table` + workspace-pricing.js)
| # | Description | Qty | Unit | Base Price (RM) | Source | Markup | Your Price | Margin | Sub |
|---|------------|-----|------|----------------|--------|--------|-----------|--------|-----|
| 1 | Flange 8" 300# RF | 12 | pcs | 850.00 | Memory | 18% | 1003.00 | 22% | — |
| 2 | Gate Valve 4" | 4 | pcs | 2,400.00 | Web | 15% | 2,760.00 | 18% | — |
| 3 | Pipe 6" SCH 40 | 50 | m | — | — | — | — | — | ✓ |

Column behavior: Click any price cell to edit. Click Source badge to see disambiguation modal. Click Sub checkbox to mark for subcontractor.

**Color semantics:**
- Green margin: >20%
- Yellow margin: 10-20%
- Red margin: <10%

### 6.3 Price Disambiguation Modal (reuse `.disambig-*`)

Overlay triggered by clicking a Source badge or price cell.

Left: Current item details. Right: Price candidates.
| Source | Price | Confidence | Action |
|--------|-------|-----------|--------|
| Price Memory (Flange 8" RF, Apr 2026) | RM 850 | High | Use |
| Web search (avg of 3 sources) | RM 920 | Medium | Use |
| LLM estimate | RM 780 | Low | Use |
| Supplier quote (ABC Sdn Bhd) | RM 890 | High | Use |

Keyboard: ↑↓ to navigate, Enter to select. Escape to close.

### 6.4 Strategy Panel (reuse `.levers-grid`)

Slide-in from right. Three preset strategies + custom:

**Competitive (default):** Markup 15%, Overhead 8%, Contingency 3%
**Aggressive:** Markup 8%, Overhead 5%, Contingency 2%
**Premium:** Markup 25%, Overhead 10%, Contingency 5%

Per-category overrides: e.g., "Electrical items: Markup 12% instead of 15%"

**Win probability estimator:** Based on historical bid prices vs award prices from memory.

### 6.5 Price Research Panel (**new build**)

Slide-in from left. Three tabs:

1. **Price sheet:** Uploaded Excel, auto-parsed line items with match status
2. **Web research:** Per-item web search results, auto-extracted prices
3. **Memory matches:** Similar items from past bids with price and confidence

---

## 7. Implementation Plan

### Phase 1 — Standalone routes (week 1)

**Backend:**
- New Flask blueprint `/tools/bid` in `yellowpages/tools/bidder_routes.py`
- Thin wrapper over existing `pricing_engine.py` and `pricing_workspace.py`
- Standalone price memory DB at `data/bidder_memory.db` (or shared)
- 5 routes: list bids, get bid, save bid, create bid, delete bid

**Frontend:**
- Single page at `static/tools/bid.html` + `static/tools/bidder.js` + `static/tools/bidder.css`
- Dashboard view: active bids table + KPI summary
- New bid modal: tender ref + pricesheet upload
- All using crema.css tokens, no new dependencies

**Files to create:**
```
yellowpages/
  tools/
    bidder_routes.py          # Flask blueprint (~150 lines)
  static/tools/
    bidder.html               # Main page (~200 lines HTML)
    bidder.js                 # Frontend logic (~800 lines)
    bidder.css                # Page styles (~200 lines)
```

### Phase 2 — Pricing workspace (week 2)

- Extend `bidder.html` with full pricing workspace view (reuse workspace-pricing.js patterns)
- Line items table with inline editing
- Strategy selector and lever controls
- Save/load drafts per bid
- Price research integration (Excel upload + web search trigger)
- Disambiguation modal (adapted from workspace-pricing.js)

### Phase 3 — Export & memory (week 3)

- Artifact production: Jadual Harga PDF/XLSX, assumptions doc
- Price memory ingestion on bid completion
- Win probability tracking (user marks bid as won/lost)
- Dashboard metrics (pipeline value, win rate, avg margin, memory coverage)

---

## 8. Data Model

```
bidder_bids:
  id (uuid PK)
  ref (text, e.g. "RFP-2026-0517")
  client (text)
  entity_id (text, FK to bidder_entities)
  strategy (text: "competitive"/"aggressive"/"premium"/"custom")
  markup_pct (real)
  overhead_pct (real)
  contingency_pct (real)
  total_base_cost (real)
  total_bid_price (real)
  status (text: "draft"/"priced"/"submitted"/"won"/"lost")
  created_at (timestamp)
  updated_at (timestamp)

bidder_line_items:
  id (uuid PK)
  bid_id (uuid FK)
  idx (int)
  description (text)
  quantity (real)
  unit (text)
  base_price (real, nullable)
  source (text: "memory"/"web"/"llm"/"quote"/"manual")
  markup_pct (real, nullable — overrides global)
  your_price (real, nullable)
  is_subcontract (bool)
  confidence (text: "high"/"medium"/"low")
  category (text, nullable)
  created_at (timestamp)

bidder_entities:
  id (uuid PK)
  name (text)
  reg_no (text, e.g. SSM)
  default_strategy (text)
  default_markup (real)
  default_overhead (real)
  default_contingency (real)
  created_at (timestamp)
```

---

## 9. Price Memory Schema (existing, for reference)

```
price_memory:
  id (integer PK)
  description (text)
  unit_price (real)
  currency (text default "MYR")
  confidence (text)
  source (text)
  category (text)
  tender_id (text, nullable)
  tender_ref (text, nullable)
  client (text, nullable)
  created_at (timestamp)
```

Schema stays as-is. The bidder tool writes to this on bid completion and reads from it for price suggestions.

---

## 10. Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Price memory DB grows stale | Low accuracy over time | Auto-decay weights after 12 months. Prioritize recent matches. |
| User uploads wrong pricesheet | Bad line items | Show preview before accepting. Allow manual line item add/edit. |
| Web price research is slow | User waits | Run async, show progress per item. Cache results per tender ref. |
| Export format doesn't match buyer requirements | Rejected submission | Let user configure export templates per buyer. Start with PETRONAS format. |

---

## 11. Success Metrics

- A bidder can price a 20-item tender in under 10 minutes (vs 2-3 hours in Excel)
- Price memory hit rate > 70% after 10 bids
- Win rate improves by at least 5% after 20 bids (user tracks win/loss)
- Zero hardcoded hex violations (CREMA audit compliance from day one)
- 60 FPS on mid-range mobile in landscape orientation
