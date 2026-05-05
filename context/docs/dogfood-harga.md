# CREMA/harga — Dogfood Report

**Date**: 2026-05-04
**Scope**: Full UX audit of `/tools/harga` — deployment, SmartGEP picker, chatbot, bid workspace, price research, entity management
**Method**: Read-through of all source files, error log analysis, deployment config review

---

## 1. Deployment & Infrastructure

### Current State
- Flask app served via gunicorn (4 workers × 2 threads) on `0.0.0.0:3636`
- Managed by pm2 (`yellowpages` process), 434 lifetime restarts
- No reverse proxy (Caddy/nginx) found for yellowpages — other projects have Caddyfiles but not this one
- No TLS termination visible at the app level
- No auth middleware on bidder blueprint

### Issues Found

| Severity | Issue |
|----------|-------|
| **HIGH** | **434 restarts** — error log is 794 entries of mostly IMAP auth failures (zeidalqadri@consurv.com.my, farahin@dyna.com.my) plus scheduler duplicate-merge warnings. The rapid restart pattern (~1/min in the log) suggests gunicorn workers are being recycled, likely from 300s timeout being hit during long LLM/research calls. |
| **HIGH** | **No auth on `/api/harga/*`** — Anyone who discovers the URL can create bids, view pricing strategies, and access tender data. The main app has session auth but the bidder blueprint doesn't use `require_auth`. |
| **MEDIUM** | **No reverse proxy** — Direct gunicorn exposure means no request buffering, no rate limiting, no caching layer. Static files are served by Flask (no CDN/nginx offload). |
| **LOW** | **preload_app=True** with gunicorn can cause issues with database connections and background threads being shared across workers. |

### Proposed Improvements
1. **Add auth middleware to bidder blueprint** (`@require_auth` decorator from user_routes)
2. **Add reverse proxy** (nginx/Caddy in front of gunicorn) for TLS termination, static file serving, request buffering
3. **Fix IMAP credentials** or disable pollers for accounts that keep failing
4. **Increase gunicorn timeout** or add streaming response for long LLM calls
5. **Move static file serving** to the reverse proxy or use `send_from_directory` with proper cache headers

---

## 2. SmartGEP Tender Picker

### Current State
- Fetches ALL SmartGEP-sourced tenders from `tender_db.list_tenders()`, then fetches full detail for EACH tender individually via `tender_db.get_tender()`
- Client-side substring match filtering (`q in reference/title/issuer`)
- Results limited to 20 displayed items
- On pick, fills `bidRef` and `bidClient` fields

### Issues Found

| Severity | Issue |
|----------|-------|
| **HIGH** | **N+1 query problem** — `list_smartgep_tenders()` iterates every tender entry and calls `tender_db.get_tender()` per item to check metadata. With hundreds of tenders this is very slow. |
| **MEDIUM** | **No pagination** — returns ALL SmartGEP tenders in one response, filtered client-side. The backend still fetches everything. |
| **MEDIUM** | **Search is too basic** — simple `q in string` substring match, no fuzzy search, no entity/buyer filter. |
| **LOW** | **Tender picker list is disconnected** — after selecting a tender, the list just clears. If you mistype the search, you need to open the modal again. |
| **LOW** | **No visual indication** of which tenders are already in a bid (to avoid duplicates). |

### Proposed Improvements
1. **Move filtering to the database layer** — add a query parameter to `tender_db.list_tenders()` pre-filtering by portal
2. **Add server-side search** with SQL `LIKE` or FTS on reference/title/issuer
3. **Add pagination** (load 20 at a time, scroll or "load more")
4. **Cache tender metadata** — avoid `get_tender()` per-item by storing portal/source in the list query
5. **Show entity/buyer icon badge** next to each tender in the picker results

---

## 3. Multi-LLM Price Chatbot

### Current State
- Queries DeepSeek and Mistral in parallel; Gemini if `GEMINI_API_KEY` env var is set
- DuckDuckGo web search provides grounding context
- Returns consolidated estimate (average of valid results) + individual provider breakdowns
- Web sources shown as clickable links with snippets
- Traceability: references, provider labels, confidence badges

### Issues Found

| Severity | Issue |
|----------|-------|
| **MEDIUM** | **No conversation memory** — each query is standalone. You can't ask follow-ups like "what about in USD?" or "compare with last week's price". |
| **MEDIUM** | **Blocking architecture** — the endpoint waits for ALL providers + web search to complete before returning. If Mistral is slow, the user waits. No streaming. |
| **MEDIUM** | **JSON parsing is fragile** — LLM output is parsed with `json.loads()` with strict expectations. If the LLM returns markdown fences or extra text, it's marked as an error. |
| **LOW** | **Web search is fixed to "Malaysia price"** — appends this to all queries which may not be appropriate for specialized items. |
| **LOW** | **No error recovery** — if one provider fails entirely, the consolidated estimate may be skewed (only from working providers). |
| **LOW** | **No prompt customization** — the system prompt is hardcoded, users can't set context (e.g., "I'm a sub-contractor in Sarawak"). |

### Proposed Improvements
1. **Add conversation memory** — maintain a chat history in the bid_workspace context (per-bid chat thread)
2. **Stream responses** — return provider results as they arrive (SSE or WebSocket) instead of blocking for all
3. **Add JSON repair** — handle markdown fences, trailing commas, unquoted strings with a repair step before parsing
4. **Make web search query configurable** — let users specify location/context
5. **Show intermediate progress** — "DeepSeek done, waiting on Mistral & Gemini..."
6. **Add Gemini circuit breaker** — if the API key isn't set, don't show "Gemini" in the UI

---

## 4. Bid Workspace

### Current State
- Dashboard with KPI row + active bids table
- Workspace with line items table, strategy levers, cost buildup
- Status lifecycle: draft → priced → submitted → won/lost
- XLSX export with formatted "jadual_harga" spreadsheet
- Win probability estimation based on margin × strategy

### Issues Found

| Severity | Issue |
|----------|-------|
| **HIGH** | **No auto-save** — line item price changes require clicking individual cells. If the user navigates away, edits are lost. |
| **MEDIUM** | **No confirmation on delete** — clicking the ✕ button instantly deletes a bid with no "Are you sure?" dialog |
| **MEDIUM** | **Line item input UX** — the bid price input is a bare number field. No validation feedback (e.g., highlighting if price is above/below market range). |
| **MEDIUM** | **No bulk operations** — no select-all, no bulk price update (e.g., "apply 10% increase to all items"), no reordering |
| **LOW** | **Margin calculation not visible per-row** in the workspace without triggering cost buildup |
| **LOW** | **Summary bar doesn't update in real-time** as you edit prices |
| **LOW** | **No "last edited" timestamp** shown on bids in the dashboard |
| **LOW** | **Strategy selector doesn't show margin impact preview** before applying |

### Proposed Improvements
1. **Add auto-save** with debounce (1s after last keystroke) for line item edits
2. **Add confirmation dialog** for bid deletion (and undo toast for 5s)
3. **Add inline validation** — show green/red indicator if bid price is within market range
4. **Add bulk operations** — checkbox column, "Edit Selected" action bar, bulk markup adjustment
5. **Add drag-to-reorder** for line items
6. **Add real-time summary updates** via a reactive update function on input change
7. **Add "last modified" column** to the dashboard

---

## 5. Price Research Panel

### Current State
- Slide-in panel with 4 tabs: Price Sheet, Web Research, Memory, Chatbot
- Research triggered asynchronously in a background thread
- Price memory lookup (previously saved prices)
- Disambiguation modal when multiple candidates found

### Issues Found

| Severity | Issue |
|----------|-------|
| **MEDIUM** | **No push notification** when research completes — user must keep the panel open and wait for polling |
| **MEDIUM** | **Research runs in memory** — if the gunicorn worker restarts, the research thread is lost |
| **LOW** | **Memory tab shows "No memory matches yet"** even when there's historical price data in the bidder DB |
| **LOW** | **Polling interval is hardcoded** — no feedback on progress until the first poll completes |
| **LOW** | **Price Sheet tab doesn't show uploads** for the current bid — you need to know to open the research panel |

### Proposed Improvements
1. **Persist research results** to the database so they survive restarts
2. **Add server-sent events (SSE)** for real-time research completion notifications
3. **Improve memory lookup** — join across all bids' line items, not just the current bid
4. **Add research history** — show past research results with timestamps
5. **Auto-open research panel** when a pricesheet is uploaded

---

## 6. Entity Management

### Current State
- CRUD for entities (bidding companies) with default strategy config
- Entities stored in bidder.db
- Used as defaults when creating new bids

### Issues Found

| Severity | Issue |
|----------|-------|
| **LOW** | **Entity form doesn't validate** registration number format |
| **LOW** | **No entity search** — if you have many entities, the list modal shows all at once |
| **LOW** | **Entity not linked** to user/account — in a multi-user setup, entities should be per-account |

### Proposed Improvements
1. Add entity search/filter
2. Add registration number format validation
3. Link entities to user accounts (when auth is added)

---

## 7. UX Polish

### Current State
- Single `@media (max-width: 768px)` breakpoint for responsive
- CSS variables from crema.css (consistent design tokens)
- Toast notifications via `crema.toast()`
- Empty states with icons and descriptions

### Issues Found

| Severity | Issue |
|----------|-------|
| **MEDIUM** | **Mobile experience is basic** — only 1 breakpoint, toolbar wraps awkwardly, table scrolls off-screen |
| **MEDIUM** | **No keyboard shortcuts** — common actions (save, export, close panel) require mouse clicks |
| **LOW** | **Loading states are plain text** — "Loading..." and "Loading workspace..." with no skeleton/spinner |
| **LOW** | **Error states are inconsistent** — some use `crema.toast()`, others set `innerHTML` |
| **LOW** | **No dark mode** — relies on crema.css variables but the bidder-specific CSS doesn't test against dark theme |
| **LOW** | **Slide panels have no swipe-to-close** on mobile |
| **LOW** | **Table header doesn't stick** when scrolling through many line items |
| **LOW** | **No export format choice** — XLSX only, no CSV or PDF option |

### Proposed Improvements
1. **Add sticky table headers** for line items table
2. **Add skeleton loading states** instead of "Loading..." text
3. **Add keyboard shortcuts** — `Ctrl+S` to save, `Escape` to close panels, `Ctrl+F` to search items
4. **Add more responsive breakpoints** (480px, 1024px) for better tablet/mobile layout
5. **Add dark mode support** with CSS custom properties
6. **Add CSV export** in addition to XLSX
7. **Add swipe-to-close** gesture on mobile slide panels
8. **Standardize error handling** — all errors should go through `crema.toast()`

---

## Summary: Priority Matrix

| Priority | Area | Fix | Effort |
|----------|------|-----|--------|
| P0 | Auth | Add auth middleware to bidder blueprint | 1h |
| P0 | Deployment | Fix IMAP credentials or disable failing pollers | 30m |
| P0 | Deployment | Investigate 434 restarts — gunicorn timeout issue | 1h |
| P1 | Tender Picker | N+1 query — add portal filter to list_tenders() | 2h |
| P1 | Workspace | Add confirmation dialog on bid delete | 30m |
| P1 | Workspace | Add auto-save with debounce for line items | 1h |
| P1 | Chatbot | Add JSON repair for LLM output parsing | 1h |
| P2 | Deployment | Add nginx/Caddy reverse proxy | 2h |
| P2 | Chatbot | Add conversation memory per bid session | 3h |
| P2 | Workspace | Add bulk operations (checkboxes, bulk edit) | 3h |
| P2 | Research | Persist research results to DB | 2h |
| P3 | UX | Keyboard shortcuts | 2h |
| P3 | UX | Skeleton loading states | 1h |
| P3 | UX | Sticky table headers | 30m |
| P3 | UX | Dark mode | 2h |
| P3 | Export | CSV export | 1h |

---

## Immediate Quick Wins (can be done in <1h each)

1. Add `@require_auth` decorator to bidder routes
2. Add delete confirmation dialog
3. Add sticky table headers (CSS: `position: sticky; top: 0`)
4. Add CSV export (reuse existing `_generate_xlsx` logic, write CSV variant)
5. Fix JSON parsing with regex repair before `json.loads()`
6. Reduce gunicorn timeout log noise (filter IMAP errors)
