# Arbos State
Updated: 2026-05-25T07:20 UTC

## Status: IDLE — completed after 1 steps

## Last Completed: Analyze the following cross-domain data and produce CONNECTIONS.md with at least 3 non-obvious insights and actionable i

### Summary
Insight 3 now points to the actual root cause. The 69 crash dumps all tell the same story: PM2 sends SIGINT, gunicorn's default handler does SIGQUIT to workers (non-graceful kill), scraper subprocesses die mid-parse leaving stuck states, recovery runs on next boot, and if recovery takes too long PM2 sends another SIGINT. The fix is already documented in MEMORY.md — the SIGINT→SIGTERM redirect that
