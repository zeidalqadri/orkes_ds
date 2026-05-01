# Active Work
Project: /home/the_bomb/orkes_ds
Task: Deepfix: unresponsive/delayed feedback from orkes_ds agent
Status: in-progress
Updated: 2026-05-01

## Plan
Operator reported feedback being non-existent, not useful, or very delayed.
Root causes identified:
1. handling_message leak when expert routing is used (flag never cleared)
2. No useful immediate acknowledgment — just "(processing)" then silence for minutes
3. Chat-wake auto-seeds goals too aggressively, causing idle spam cycle
4. Chat-wake has no debounce — can re-seed within seconds of goal being cleared

## Progress
- [x] Fix 1: Move handling_message.set() after expert routing in handle_message; add explicit set() before _route_to_expert call
- [x] Fix 2: Add _acknowledge_request() helper + bot.send_message for immediate feedback in handle_message
- [x] Fix 3: Add 5-min cooldown (_CHAT_WAKE_SEED_COOLDOWN) in check_and_wake()
- [x] Fix 4: Update conftest.py to reset _last_chat_wake_seed
- [ ] Run tests
- [ ] Restart arbos-orkes_ds

## Files Modified
- ~/.opencode-bot/core/bot_handlers.py — handle_message + _acknowledge_request
- ~/.opencode-bot/core/loops.py — chat-wake debounce
- tests/conftest.py — reset _last_chat_wake_seed
