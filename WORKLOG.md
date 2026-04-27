# Active Work
Project: /home/the_bomb/orkes_ds
Task: Fix idle polling interval in agent loop
Status: complete
Updated: 2026-04-27T05:22 UTC

## Root Cause
`_auto_resume_on_boot()` in engine.py line 278 had condition:
```python
if state_is_idle and not state_text:
```
When STATE.md contained "IDLE — completed" (which _write_completion_state always writes),
`state_is_idle` was True but `state_text` was also truthy, so the guard failed.
Result: every restart seeded "Bot restarted. Act immediately..." goal, causing LLM spin loop.

## Fix Applied
Changed condition to:
```python
if state_is_idle:
```
Now skips auto-resume whenever STATE.md shows IDLE, regardless of text content.

## Changes
- engine.py line 278: Removed `and not state_text` guard
- IDLE_POLL_INTERVAL=120s was already wired (state.py, engine.py, loops.py)
