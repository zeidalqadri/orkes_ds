# Active Work
Project: /home/the_bomb/orkes_ds2
Task: Harga v5 fix — bigger landing rectangle + auto-factsheet on import
Status: done
Updated: 2026-05-08T07:45 UTC

## Investigation: SmartGEP Browser Restart Cycle

**Root cause**: `_refresh_cookies_http()` called `bootstrap_smart_session()` which tried to get `smart.gep.com` cookies via HTTP GET requests. These cookies are set by the Angular SPA's JavaScript, not by HTTP response headers. So the HTTP approach always returned False, and after 3 consecutive failures the browser was restarted — expensive at ~800MB per restart.

**Cycle**:
- HTTP refresh every 10 min → always fails → after 3 failures (30 min) → browser restart → SSO → browser close
- Repeat. 38 restarts on May 7 alone.

**Proper fix** (permauth.py):
1. **`_refresh_cookies_http()` rewritten**: Removed `bootstrap_smart_session()` call entirely. Replaced with lightweight nsid validation: `GET /data/psevent/{event_id}` with `netsessionid` header + stored cookies. If 200 + valid JSON, nsid is good → scrapers can continue working.
2. **Init phase cleaned up**: Removed redundant `bootstrap_smart_session()` call after browser login (nsid is already fresh from SPA extraction).
3. **Import cleanup**: Removed top-level `from smartgep_http import bootstrap_smart_session` (only used in refresh which no longer calls it).
4. **REFRESH_INTERVAL** 600→3600s (less frequent).
5. **Alert downgraded**: warning→info for browser restarts.

**Verification**: permauth restarted, SSO handoff OK, nsid=drv5zwgb5qku, tokens_valid=true, cookies=26, auth_mode=spa. Browser closed, serving from memory.

## Investigation Results

### Items 1 & 2 — Verified ✅
1. **Bid Import on Landing Page**: The "↓ Import Tender from CREMA" button is visible on the welcome screen (harga-v3.html line 116-120), below example queries, above the chat area. Also duplicated in the bid panel (line 181).
2. **Logo → New Chat**: Clicking `◆ harga` in the header (line 45) triggers `newChat()` which starts a fresh session without losing the last one.

### Tender Count Deep Dive
**Question**: "Do we really only have 265 tenders with line items available?"
**Answer**:
- 3,008 tenders total in `harga/tenders/tenders.db` (65MB)
- 782 have line items (26%)
- But the CREMA import preview filters out closed/cancelled → ~265 available for import
- The 265 figure was correct, just with the closed filter applied

**By source** (from live `harga/tenders/tenders.db`, 2026-05-08):
- government: 1,380 total, 588 with line items (42.6%)
- smartgep: 1,378 total, 71 with line items (5.2%) ← the drag
- eperolehan: 188 total, 93 with line items (49.5%)
- unknown: 46 total, 23 with line items (50%)
- petronas: 16 total, 7 with line items (43.8%)

**Status breakdown** (of the 3008 total):
- closed: 1,558 (51.8%)
- new: 826 (27.5%)
- matched: 384 (12.8%)
- insufficient_data: 139 (4.6%)
- analyzed: 56 (1.9%)
- draft: 45 (1.5%)

**Root cause**: SmartGEP tenders are mostly PDF-based without extracted BOQ data. Only 4% have structured line items vs 40-49% for government/ePerolehan.

### Housekeeping
- Removed empty 0-byte `data/tenders.db` and `harga/data/tenders.db` (stale artifacts)
- Fixed `scripts/backup.py` and `scripts/restore.py` — tender DB path was `data/tenders.db` (empty), corrected to `tenders/tenders.db` (3008 records)
- `data/tenders.db` symlink removed; actual tender DB lives at `harga/tenders/tenders.db` (65MB, WAL mode)
- All harga code committed (latest: b37b78f)
- PM2: All processes online, harga HTTP 200

## Progress
- [x] Verify bid import control on landing page — visible ✅
- [x] Verify logo navigates to new chat — working ✅
- [x] Investigate 265 tender count — explained above
- [x] Remove empty tenders.db artifact
- [x] Update STATE.md, WORKLOG.md

## Completed
- Bid import + logo nav verification (2026-05-08)
- Tender count investigation (2026-05-08)
- Housekeeping (2026-05-08)
- Landing page redesign (2026-05-08): Stats bar, 8 categories, market ticker, mini dashboard — all confirmed live
- CREMA import error fix (2026-05-08): Fixed api() swallowing errors — now surfaces HTTP errors + server error messages properly to the user
- Light mode implementation (2026-05-08): CSS custom properties for dark/light, all inline styles migrated, theme toggle button + JS, localStorage persistence, prefers-color-scheme respect. Covering chat area, landing, overlays, and all UI chrome.
- Phase 2 — Desktop context rail (2026-05-08): Full implementation — HTML `#appLayout` wrapper restructured for flex row/column, 220px left rail at 900px+ with Import Tender, Recent Queries, Tender Database pulse. Desktop content centred at 580px max-width, category grid 4-column on desktop, input area centred. `landing-content`, `landing-categories`, `input-wrap` CSS classes. Rail populated via `loadWelcomeRecent()` from `/landing` API. `newChat()` clears stale rail data. All overlays (sessions, bid panel, canvas, etc.) unaffected outside layout wrapper.
