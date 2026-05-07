# Active Work
Project: /home/the_bomb/orkes_ds2
Task: Address Issue 1 — SmartGEP scraper stalled
Status: completed
Updated: 2026-05-07T12:15 UTC

## What was done
- Investigated SmartGEP scraper stall (last ran May 4, 3d stale)
- Found root cause: permauth daemon stuck on `<app-maintainance-message>` overlay on idplogin.gep.com — blocked Playwright clicks
- Applied fix: JS overlay removal + `force=True` on login button clicks in `permauth.py`
- Restarted permauth daemon → authenticated successfully (nsid, 26 cookies, smart.gep.com cookies)
- Current scraper run (started 09:54) includes SmartGEP after ePerolehan finishes (~13:10 UTC)
- Found secondary issue: sheepdog conductor loop error `'>' not supported between instances of 'str' and 'int'`

## Progress
- [x] Verified Harga split from Yellowpages (done by ds2 agent)
  - harga standalone on 3637, yellowpages on 3636
  - Cloudflare tunnel routes harga.roowang.com → 3637
  - yellowpages.zeidgeist.com → 3636
- [x] Memory limits tuned: yellowpages 2G, harga 1G (was 4G each)
- [x] Both services healthy (HTTP 200, 0 restarts)
- [x] Verified all dogfood fixes intact:
  - Chat input maxlength=2000
  - AbortController + Cancel button (no hardcoded timeout)
  - Loading indicators on all API calls
  - Font: DM Sans + JetBrains Mono (not Space Grotesk)
  - Single _dogfood_harga-v2.py (v2 target)
- [x] Confirmed 21GB available memory — settings are sustainable

## Key findings
- The Harga split was already fully implemented by the ds2 agent
- Memory limits already tuned to 2G/1G (from original 4G)
- Cloudflare tunnel config updated: harga.roowang.com → localhost:3637
- All 5 dogfood issues from earlier audit already resolved
- No remaining pending items for this task

## Domain correction
- ada.roowang.com (not ada.ruang.com) — Cloudflare Worker for UTP/Tronoh Mines frontend

## Consurvatory_bot data check
- Verified: bot IS streaming legit data
- 3,008 tenders in main DB (65MB at tenders/tenders.db)
- Sources: eperolehan (188), government (1380), petronas (16), smartgep (1378), unknown (46)
- ePerolehan scraper running (1h ago), SmartGEP stalled (~1d)
- Pipeline deals thin/stale (1 entry, last updated Mar 18)
- "No tenders database" was transient path resolution issue — resolved

## 2026-05-07 — FIX: sheepdog TypeError + permauth overlay on smart.gep.com

### Fix 1: Sheepdog conductor loop TypeError
- File: `orkes/sheepdog/sheepdog.py` line 1302
- Error: `'>' not supported between instances of 'str' and 'int'` when comparing memory trend
- Fix: Wrapped comparison in try/except TypeError → `h.clear()` to reset corrupted history
- Status: Restarted (PID 47), online 0 restarts

### Fix 2: Permauth SmartGEP SSO handoff
- The `<app-maintainance-message>` overlay ALSO appears on `smart.gep.com` workspace page
- Previous fix only dismissed it on `idplogin.gep.com` — overlay blocked Strategy C's Sourcing tab click
- Fix: Extracted `_dismiss_overlay()` helper, called after each `page.goto()` in Strategy C
- Result: Permauth SSO now succeeds — `nsid=nn5ks43x4dty`, cookies=26
- Browser-based SmartGEP API calls (Layer 1) now functional

### Remaining: HTTP bootstrap for smart.gep.com cookies still fails
- SmartGEP SSO requires full browser JS context — HTTP-only bootstrap can't get cookies
- Only affects Layer 2 fallback, not Layer 1 (Playwright)

## 2026-05-07 — Memory + Consurvatory_bot verification
- Investigated "0GB memory" alert — confirmed FALSE ALARM
  - Sheepdog correctly reads MemAvailable (21GB) from /proc/meminfo
  - PM2 shows 0MB per process due to cgroup v2 limitation (cosmetic only)
  - Swap at 2% — minimal pressure
- Verified @Consurvatory_bot reads `tenders/tenders.db` correctly (3008 records)
- All 9 PM2 services online, 0 restarts, HTTP 200 responses
- Yellowpages stable at 2h uptime, 0 restarts
- Known issues flagged: SmartGEP Dyna scraper stale (22d), pipeline thin (50d stale)
