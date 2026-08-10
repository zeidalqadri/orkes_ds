# Arbos State
Updated: 2026-08-10T02:40 UTC

## Status: COMPLETE — konsos implementation gaps identified (read-only PLAN→analysis). Goal delivered.

## Phase: PLAN (read-only analysis, no code changes to any repo)

## Goal (operator, step 4)
"to identify the gaps in the implementation of konsos"

## Scope note
konsos = /home/the_bomb/konsos/ (live host). Two co-existing implementations:
- LIVE/DEPLOYED: market-whisper (konsos.service, :8080) + trading-bot (konsos-bot.service, :8001). systemd, User=the_bomb.
- RESEARCH (NOT deployed here): research/market-whisper (+meta_gate.py), research/trading_system, research/konsos/bot — target /root/konsos/ (different root-owned box). Contains a more advanced self-driven bot (SignalComputer, 3 strategy bots, hold_policy).

## Key evidence (measured 2026-08-10 ~02:30 UTC)
- /home/the_bomb/konsos/ is NOT a git repo (no rollback/history).
- market-whisper :8080 → HTTP 000, 0 bytes, 5s timeout (process p956 alive, child p1243 ZOMBIE). reload-mode freeze.
- trading-bot :8001 /health → 200 in 0.11s ("healthy", bot_running=1).
- market-whisper konsos.db (271.7MB): 42,896 signals; MAX created_at = 2026-04-28T01:06; bulk 42,629 in 2026-02, only 21 in Apr. 45 ERROR-direction rows stored.
- outcomes: 18,531 resolved (timeout=18,484 sl_hit=36 tp1=9 tp2=2 tp3=0); MAX resolved_at=2026-05-28. perf_snapshots MAX=2026-08-03 (scheduler alive till then).
- provider_weights: openai=1.0/total_votes=0/acc=None; anthropic acc=0.0/638v; gemini 0.010/1725v; deepseek 0.0/1744v; mistral 0.0/1744v; perplexity 0.0/878v.
- votes: 68 is_correct=1, 56,269 =0, 174,237 NULL; success=0 (LLM failures) = 104,745 of 230,574 (45.4%); OpenAI 429 quota errors present.
- trading-bot trades.db: trades=0, orders=0, daily_performance=0; bot_state (id=1, is_running=1, mode=paper, last_trade_at=None, updated_at=2026-02-09T07:48). trades table has NO sl/tp/tp1 column.
- .env: EXCHANGE_ID=kraken, LLM_PROVIDERS=6 (incl mistral,perplexity — no key fields in config.py LLMConfig), DEBUG=true, PORT=8080.

## Findings (grouped)
### A. Deploy/reliability (hard outages)
1. DEBUG=true + uvicorn reload in PRODUCTION → reloader worker died, zombie child, parent holds :8080 FD, serves 0 bytes; Restart=always can't recover (process "alive"). Root cause of frozen :8080.
2. No self-driven signal generation in market-whisper: background_jobs only does outcome/weight/snapshot. Signal rows require an external POST /signal caller. Stall correlates with a caller going away (~Apr 28), not a code freeze on the generate path.
3. journald has zero entries for both units → logging gap despite 1.2G journal disk.

### B. Learning/outcome correctness corruption
4. 94% of outcomes = "timeout". _determine_correct_direction treats any timeout as a LOSS and asserts the correct direction = OPPOSITE of signal → systematically marks near-every directional vote wrong. Result: 56,269 votes =0, only 68 =1; all provider accuracies collapse → all weights clamp to weight_min=0.3 (openai anomaly: weight=1.0, 0 votes, acc=None).
5. mark_votes_correctness sets is_correct=CASE direction=correct_direction; FLAT votes (LLM undecided) never match LONG/SHORT → always =0, deflating accuracy.

### C. LLM ensemble reliability/security
6. Hardcoded CF gateway token + account id committed in source (llm_ensemble.py:19-22). Secret leak.
7. 12s timeout (LLM_TIMEOUT=12) across 6 providers; 45.4% of all votes failed (OpenAI 429 quota). High ensemble failure rate with no backoff/retry/circuit-breaker on provider level.

### D. trading-bot execution/persistence bugs
8. Paper-exit loop can never fire TP/SL in paper mode: trades table has no sl/tp columns, create_trade stores none (they live only on orders). check_paper_exits reads trade.get("sl"/"tp_price") → always None. Paper trades never closed; no timeout fallback.
9. R-multiple math inconsistent: position_tracker._handle_closed_position divides realized_pnl by price-distance (no *qty) → wrong; paper path divides by (sl_distance*qty). Incompatible R values.
10. _handle_closed_position has `break` after first pnl record — attributes wrong close, skips TP/SL reason.
11. close_position paper branch returns early WITHOUT close_trade → closing never persists a paper close.
12. /control/start|stop silently flip DB is_running even with no bot attached; DB flag vs reality diverge.

### E. Drift / dead code
13. monitoring/metrics.py never imported (dead). PositionSizer.validate_size + CircuitBreaker.check_daily_drawdown + ByBitClient.cancel_order/get_order_history + database.update_order_status/get_trade_by_id never called (dead; drawdown limit never enforced).
14. research tree (proposed self-driven v2 with meta_gate + SignalComputer) never deployed; live host runs older request-driven v1. meta_gate missing from live market-whisper.

## Assumptions vs observations
- OBSERVED: stall time, DB row counts, zero trades, frozen :8080, corrupted weights, 45% vote failure.
- ASSUMED: external caller stopped (driver of signal stall); reload reloader-worker died ~Aug 5 restart w/ DEBUG=true.

## File Manifest
- MODIFY: STATE.md, context/shared_learnings.md
- CREATE: none (analysis only)
- DELETE: none

## Verification
- Not applicable this step (analysis). All findings are read-only db/ps/curl/grep evidence above.

## Last
Delivered "konsos implementation gaps" report to operator. No code changed on konsos or harga. harga-cli baseline (33/33) untouched. Goal cleared.
Next-step candidates for operator: (1) fix :8080 freeze (DEBUG=false, disable reload, kill zombie), (2) purge stale signals/outcomes, (3) add paper-mode SL/TP persistence + timeout close, (4) fix timeout-as-loss accuracy corruption, (5) remove committed secrets, (6) wire metrics, (7) decide v1-vs-v2 (research) deployment path.
