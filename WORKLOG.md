# Active Work
Project: /home/the_bomb/orkes_ds
Task: SmartGEP v2 BoQ Extraction
Status: blocked (BizNet maintenance)
Updated: 2026-05-02T05:36:00+00:00

## Plan
1. Fix permauth daemon auth (BizNet→SmartGEP SSO handoff)
2. Extract BoQ from 3 SUSPECT_BOQ tenders (RFP-178432, 178387, 178027)
3. QMD fix (parallel, no deps)

## Progress
- [x] QMD fix — export-sessions + update + embed (5905 files, 6186 indexed)
- [x] Fixed permauth.py bugs:
  - `self._context` → `self.context` (3 lines: 492, 495, 521) — was crashing daemon
  - Guard `_navigate_to_smartgep_event()` link scanning to BizNet pages only — was finding false "Forgot Username?" link with "smart-auth" in ReturnUrl
- [x] Daemon login working — SSO completes, 8 BizNet cookies (smart-sts-bpc, CultureCode, etc.)
- [ ] Extract netsessionid from smart.gep.com SPA — BLOCKED by BizNet maintenance
- [ ] Run main scraper for 3 SUSPECT_BOQ tenders

## Current State (2026-05-02)
- **BizNet**: AngularJS SPA loads but renders maintenance overlay ("UNDER MAINTENANCE — scheduled maintenance, site currently not accessible")
- **Daemon**: Alive on 127.0.0.1:9876, account consurv, 8 cookies, refreshes every 10 min
- **netSessionId**: EMPTY — can't reach smart.gep.com SPA without BizNet SPA rendering SMART/RFX links
- **3 SUSPECT_BOQ tenders**: JSON files exist with 0 price_sheet_rows, need live SSO for extraction

## Daemon Fixes Applied
- `/home/the_bomb/orkes_ds/permauth.py`:
  - `_is_on_biznet()` accepts cookies-only state (cookie_count >= 8)
  - `_ensure_login()` return value uses `_is_on_biznet()`
  - Post-login recovery to BizNet when cookies valid but redirect timed out
  - `_navigate_to_smartgep_event()`: Ctrl+click BizNet SMART links (mirrors main scraper approach)
  - `_is_biznet_under_maintenance()` added
  - Bug fixes: `self._context` → `self.context`, guard link scanning to BizNet only

## Next Steps (when BizNet recovers)
1. Daemon will auto-detect SPA available and extract netsessionid
2. Run BoQ extraction for 3 SUSPECT_BOQ tenders via daemon's /boq-extract endpoint
3. Verify child sheet fetch with valid netsessionid

## Completed
- [x] Bot handler fix — 17 missing handlers, model change to deepseek-v4-flash
- [x] All 797 tests passing
- [x] Telegram bot fix (2026-05-02) — arbos-orkes_ds was not running; started under PM2, cleaned stale .bot.lock, removed useless arbos-testproj
- [x] Bot relapse prevention (2026-05-02) — 3 layers:
  - Layer 1: PM2 systemd startup already configured (verified)
  - Layer 2: Cron watchdog every 5min on scripts/check-bot.sh — auto-restarts + Telegram alert on failure
  - Layer 3: HEALTH_PORT=8766 enabled, health endpoint live at :8766/health
