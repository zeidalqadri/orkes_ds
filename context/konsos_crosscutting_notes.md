# Konsos Cross-Cutting Observations (live host) — 2026-08-10
Read-only observations, no secrets.

## Deploy / runtime (systemd)
- konsos.service (market-whisper) + konsos-bot.service (trading-bot) both ENABLED + RUNNING since 2026-08-05, from /home/the_bomb/konsos/, User=the_bomb.
- research/ tree + trading-bot/deploy/* reference /root/konsos/ + User=root => targeting a DIFFERENT root-owned box (not this live host).

## market-whisper (konsos.service, pid 956) — CRITICAL
- Listens on :8080 (RUN config PORT numeric len4=8080) but **times out on /, /health with 0 bytes**. FastAPI layer is up-but-frozen: accepts TCP, never serves.
- konsos.db is 271MB but newest `signals` row = 2026-04-28 (~3.5 mo stale as of 2026-08-10). 42,896 signals / 230,574 llm_provider_votes / 18,531 signal_outcomes / 483 performance_snapshots — all stale since late April.
- => signal pipeline effectively dead since ~2026-04-28 despite process up.

## trading-bot (konsos-bot.service, pid 958) — CRITICAL
- Listens :8001; GET /health -> {"status":"healthy","bot_running":1,"mode":"paper","testnet":true}.
- trades.db empty: trades=0, orders=0, daily_performance=0; bot_state row updated_at=2026-02-09 (~6 mo stale). is_running=1, mode='paper', circuit_breaker_active=0.
- => no trade ever recorded; persistent state stale since Feb 9; reports healthy.

## Observability
- journalctl -u konsos.service / konsos-bot.service => "No entries" (both over last day). No stdout/stderr reaching journald despite 1.2G journal disk. Logging gap.

## Root cause of market-whisper freeze (updated)
- run.py calls uvicorn.run(reload=config.debug); DEBUG=TRUE in .env => reload mode in PRODUCTION (bad).
- Process tree pid 956 -> child 1244 [python] Z (DEFUNCT ZOMBIE). The reloader worker died, parent keeps :8080 FD, never respawns functional worker.
- => accepts TCP on :8080 but serves nothing (0 bytes). Restart=always won't help (process alive).
- Dashboard: konsos-dashboard Cloudflare Pages (konsos.zeidgeist.com) ~4 months stale (from wrangler list).
