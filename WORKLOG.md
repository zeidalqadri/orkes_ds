# Active Work
Project: /home/the_bomb/orkes_ds2
Task: Yellowpages crash fix + harga.v2 verification
Status: completed
Updated: 2026-05-07T08:55 UTC

## Progress
- [x] Investigate "loop not looping?" question — loop IS running (arbos-orkes_ds2 online, 0 restarts, 32m uptime)
- [x] Yellowpages crash investigation — 11+ restarts, root cause: `interpreter: "none"` in pm2 config (fork mode defaults to Node.js, can't run Python gunicorn script)
- [x] Fixed: Changed interpreter to `/home/the_bomb/orkes/.venv/bin/python3` in ecosystem.config.js
- [x] Cleared stale `__pycache__/` with mixed Python 3.12/3.13 bytecode
- [x] Yellowpages now stable: 53s uptime, 0 restarts, HTTP 200
- [x] Also bumped max_memory_restart from 500MB to 1G to prevent OOM restarts (process had 290MB baseline growing ~16MB/min)
- [x] Verified all 5 harga.v2 fixes intact (max length, timer, loading, font, dogfood scripts)
- [x] harga.v2: Increased processing timeout from 120s to 300s to match gunicorn worker timeout
- [x] Rewrote _dogfood_harga-v2.py: 11 phases, updated selectors, targets localhost
- [x] Sent Telegram summary to operator

## Key findings
- The `interpreter: "none"` with pm2 fork mode is problematic for Python scripts. pm2's ProcessContainerFork.js uses Node.js `require()` to load the script regardless of interpreter setting.
- The `__pycache__/` had both `.cpython-312.pyc` and `.cpython-313.pyc` files from different Python versions, contributing to intermittent import failures.
- The ModuleNotFoundError for harga_sessions was a symptom, not the root cause — the real issue was Node.js trying to parse the Python gunicorn script.
- PM2 also had global max_memory_restart: 500MB which would kill the yellowpages master when it grew past 500MB (it starts at 290MB baseline due to preload_app=True)
