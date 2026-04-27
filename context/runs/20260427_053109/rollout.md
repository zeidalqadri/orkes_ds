Now I need to check the actual run directory structure to confirm the glob bug.I've traced the issue. The auto-clear mechanism (`_step_result_appears_idle`) relies on a glob pattern and `st_mtime` sort that may be unreliable. The real problem is there's no gap between steps when a goal is active — each step runs back-to-back with no cooldown. Let me fix `loops.py` now.Now I have a complete understanding. The core bugs are:

1. `_latest_rollout_text()` sorts by unreliable `st_mtime` — should use directory name (timestamp-based)
2. No minimum delay between consecutive steps when goal is active
3. After auto-clearing goal for idle, no cooldown before re-checking for new work

Let me apply all fixes:Now add the `STEP_MIN_INTERVAL` constant and implement step cooldown in `agent_loop()`:Now add the step minimum interval logic and cooldown after goal terminations:Now add the `_sleep_cooldown` helper and apply the same fix to `_expert_loop`:Now apply the same fixes to `_expert_loop`:Now add `last_step_completed` update and cooldown after auto-clear in the expert loop:Syntax is clean. Now let me update the STATE.md and clear GOAL.md:Let me do a final verification read of the critical sections:Done. Fixed `~/.opencode-bot/core/loops.py` with three layers of protection:

1. **`_latest_rollout_text()`** — sorts by directory name (UTC timestamps) instead of `st_mtime`, which was unreliable on this filesystem. That's why auto-clear never fired.

2. **`_STEP_MIN_INTERVAL = 3s`** — minimum delay between consecutive steps even when a goal is active. Prevents the 7-26s spin cycle that burned through 9 steps.

3. **Cooldown after every goal termination path** — `_sleep_cooldown` pauses before re-entering the check loop after auto-clear, circuit breaker, step cap, and done-marker clears. Applied to both `agent_loop()` and `_expert_loop()`.

The bot will now poll infrequently (120s) when idle, and won't spin tight loops when there's "nothing to do."