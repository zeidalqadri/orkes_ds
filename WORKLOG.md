## Active Work
Project: /home/the_bomb/orkes_ds (yellowpages)
Task: SmartGEP scraper — kill stuck browser + seed event_map
Status: completed
Updated: 2026-05-06T07:55 UTC

### Done
- Killed stuck Playwright Chromium (PID 2201916, 500MB resident) that was stuck from the HTTP refresh → browser restart loop
- Removed arbos-smartgep and permauth PM2 processes to stop auto-restart loop
- Fresh BizNet cookies (24 cookies, saved at 07:46) found; HTTP bootstrap SUCCEEDED (acquired 1 smart.gep.com cookie via requests.Session)
- Seeded event_id_map.json from a fresh HTTP listing fetch (638 documents → 642 event_map entries, up from 6)
- Saved fresh API state to all _v2_output_consurv and _engine_output_consurv directories
- Verified: HTTP bootstrap + listing fetch works with fresh cookies + seeded event_map
- Flask 200 at localhost:3636/, ~500MB memory freed

### Root Cause
The scraper was stuck in a loop: HTTP bootstrap needed docUrl candidates from event_map (only 6 stale entries) → bootstrap failed → fallback browser restart → browser consumed 500MB → cookies saved without smart.gep.com domain → next cycle same failure. With 642 entries providing diverse docUrl candidates, the HTTP path now succeeds on first try without Playwright.

### Next for SmartGEP
- v3: Full HTTP-only scraper (smartgep_http.py integration, no Playwright dependency)
- v4: Stateless permauth via bootstrap_smart_session() only

## Previous
# Active Work
Project: /home/the_bomb/orkes_ds (yellowpages)
Task: design system — dark mode
Status: completed — awaiting operator
Updated: 2026-05-06T08:05 UTC

### Done
- Dark mode `@media (prefers-color-scheme: dark)` block added to crema.css
  - Overrides all color tokens (bg, surface, text 1-6, borders, shadows, semantic colors, category colors)
  - Replaced hardcoded `#fff` with `var(--text-on-accent)` in nav-btn.active, toast, user-mgmt-badge
  - Mobile tab bar gets dark blur background override
- Verified: crema.css now has OS-level dark mode auto-detection
- harga-v2.css uses only var() tokens from crema.css — benefits automatically
- Scraper Phase 2 (HTTP-First) deferred to v3 per operator
- harga.roowang.com live (HTTP 200), /tools/harga removed from yellowpages
- Status reported to operator — awaiting next direction

## Previous
# Active Work
Project: /home/the_bomb/orkes_ds
Task: (idle)
Status: idle — awaiting operator
Updated: 2026-05-06T06:50 UTC

### Done
- Scraper client investigation complete (operator request at 06:33)
- Root cause: Playwright Chromium OOM (800MB+ resident, 19 processes)
- deepthink_scraper_replacement.md written with Phase 1-3 migration plan
- HTTP migration Phase 1 deployed: permauth browser close-after-init (45MB stable)
- Issue found: event_id_map.json missing — HTTP cookie refresh has no docUrl candidates
- SmartGEP scraper stuck on PETRONAS client select loop
- Status reported to operator via Telegram

## Completed
- 2026-05-06: CREMA hex violation cleanup — users.css, gallery.css, nova.css, workspace.css
- 2026-05-06: HTTP migration Phase 1 verified — permauth browser-free operation confirmed
- 2026-05-06: Removed all harga deployments (roowang.com + zeidgeist.com)
- 2026-05-06: harga dogfood — 3 critical bugs, css/ux issues found
- 2026-05-06: Fixed all 10 harga UX issues — Canvas/ARIA/CSS/double-hiding/drag-drop
- 2026-05-06: Verification — Flask 200 | Hex 0 | E2E 117/117 pass
- 2026-05-06T04:10: Follow-up fixes: toggleCanvas global button sync, focusChatbot() added, .canvas-global-btn.active CSS
- 2026-05-06T06:50: Memory investigation + scraper deepthink — OOM root cause found (Playwright Chromium), SmartGEP HTTP v2 transport ready, reported to operator
