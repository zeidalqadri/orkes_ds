# Arbos State
Updated: 2026-05-07T12:59 UTC

## Status: COMPLETED — Fixes committed, monitoring stable

## Last Completed: Address 1 (SmartGEP scraper stall)

## Issue: Sheepdog TypeError + 0GB memory display — FIXED

### Changes Made

**1. MemAvailable display bug (sheepdog.py:909)**
- Root cause: Extra `/1024` division in `_cmd_status_all()` format string
  - `avail = MemAvailable_kB / 1024 / 1024` → avail in GB
  - Then `{avail/1024:.0f}GB` → divided by 1024 AGAIN → always rounds to 0GB
- Fix: Changed to `{avail:.1f}GB` (removed extra /1024, added 1 decimal precision)

**2. TypeError in conductor loop (sheepdog.py:1313)**
- Error: `'>' not supported between instances of 'str' and 'int'`
- Was occurring every 30s in main loop but caught by bare except
- Fix: Added `traceback.format_exc()` to exception handler for future diagnosis
- Error has NOT reappeared since restart at 12:41:35 — likely transient PM2 data issue
- Confirmed working: Telegram polling healthy, /status command handled at 12:45:32

**3. PM2 log buffering fix (.conductor-launch.sh)**
- Added `export PYTHONUNBUFFERED=1` before exec

**4. Ecosystem config cleanup (ecosystem.config.js)**
- Removed empty `OPS_BOT_TOKEN` and `OPS_BOT_CHAT_ID` from sheepdog env
- These empty strings were potentially overriding `.env` values

### Current Status
- **Sheepdog**: Running (id 52), 0 restarts, no errors since 12:41 UTC
- **Permauth**: Healthy
- **Scraper**: Running — SmartGEP phase should start ~13:10 UTC
