# Active Work
Project: /home/the_bomb/orkes_ds
Task: Fix unresponsive bot — missing handlers + DeepSeek V4 Pro model change
Status: complete
Updated: 2026-05-01

## Root Causes (revised)
**Primary**: `register_handlers()` in `~/.opencode-bot/core/bot_handlers.py` referenced 25 handler functions, but 17 were missing from the module (including `handle_message` — the catch-all text handler). Every text message hit a `NameError`, silently swallowed by telebot's exception handler. The bot never responded.

**Contributing**: `OPENCODE_SMALL_MODEL` was set to `deepseek/deepseek-v4-pro` (same as main model), making classifier/routing calls slow. Changed to `deepseek/deepseek-v4-flash`.

## Fixes Applied
1. Added `_set_expert` and `_remove_expert` to `~/.opencode-bot/core/context.py`
2. Added `_kill_child_procs` and `_codex_photo_audit` helpers to bot_handlers.py
3. Implemented all 17 missing handlers in bot_handlers.py (adapted from ~/.arbos/core/bot_handlers.py):
   handle_message, handle_start, handle_help, handle_status, handle_stop,
   handle_goal, handle_experts, handle_expert_cmd, handle_expert_callback,
   handle_group, handle_kodak, handle_clear, handle_restart, handle_update,
   handle_peer_status, handle_peer_wake, handle_peer_kill
4. Fixed `OPENCODE_SMALL_MODEL` in `.env` from `deepseek/deepseek-v4-pro` → `deepseek/deepseek-v4-flash`
5. Both arbos-orkes_ds and arbos-orkes restarted via PM2
6. Handler integrity test catches missing handlers at source

## Test Results
- 797/797 pass (0 failures)
- All 15 pre-existing failures fixed:
  - Added `_clear_audit_pending`, `_save_audit_pending` (missing audit helpers)
  - Fixed `max_retries = 1` → `state.MAX_RETRIES` in runner.py
  - Fixed kodak/photo tests: added `monkeypatch` + `tmp_path` fixtures
  - Fixed chat-wake flakiness: reset `handling_message` Event, `_last_handled_message_ts/text` in conftest
  - Fixed hanging codex audit tests: changed to mock `run_agent_streaming`
- Raised context budget: `CONTEXT_BUDGET_SOFT=3M`, `HARD=3.9M` for DeepSeek V4 1M window
- New test: `tests/test_handler_integrity.py` — 3/3 passing, catches missing handlers

## Completed (from prior worklog)
- [x] handling_message flag fix in handle_message
- [x] _acknowledge_request() immediate feedback
- [x] Chat-wake 5-min cooldown
- [x] conftest.py reset _last_chat_wake_seed
