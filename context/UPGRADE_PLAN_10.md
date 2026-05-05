# Patch to 10: 6→10/10 Upgrade Plan

**Date:** 2026-04-28
**Current Score:** 6/10 — functional but fragile
**Target Score:** 10/10 — hardened, testable, observable, self-healing

---

## Phase 1: Test Foundation (Week 1)

### 1.1 Core Loop Integration Test

Write one integration test covering the full agent lifecycle:
- Read GOAL.md → load skills → execute → clear GOAL.md → update STATE.md
- Mock file system + command execution
- Verify state transitions (IDLE → BUSY → IDLE)
- **Files:** `tests/test_core_loop.py`

### 1.2 STATE.md Integrity Test

- Parse STATE.md, verify all required fields exist (Updated, Status, Summary)
- Detect garbled content (internal monologue, raw tool output in wrong fields)
- Assert clean handoff between agent runs
- **Files:** `tests/test_state_integrity.py`

### 1.3 Arbos Engine Tests

- Test INBOX.md read/write cycle
- Test GOAL.md clear-after-complete semantics
- Test .bot.lock acquisition/release
- Test restart signaling (.restart, .restart_continue)
- **Files:** `tests/test_arbos_core.py`

**Verification:** `pytest tests/` passes, coverage ≥80% on `~/.opencode-bot/core/`

---

## Phase 2: CI & Safety (Week 2)

### 2.1 GitHub Actions Pipeline

- **Trigger:** Push to main, PR to main
- **Jobs:**
  1. `lint` — ruff check (0 errors)
  2. `typecheck` — pyright if configured
  3. `test` — pytest with coverage report
  4. `state-integrity` — validate STATE.md, GOAL.md, INBOX.md are well-formed
- **Files:** `.github/workflows/ci.yml`

### 2.2 Pre-Push Hook (Optional)

- Local git hook running `ruff check . && pytest tests/`
- Prevents broken code from reaching remote

### 2.3 Backup/Restore Automation

- Pre-execution snapshot: `cp context/*.md context/backups/<timestamp>/`
- Post-execution snapshot on failure
- Restore command: `python arbos.py restore <timestamp>`
- Retention: 7 days of hourly snapshots
- **Files:** `scripts/backup_state.py`, `scripts/restore_state.py`

**Verification:** CI passes on push, backup creates valid restore point, restore succeeds

---

## Phase 3: Observability (Week 3)

### 3.1 Structured Logging

- Replace ad-hoc print/logging with structured JSON logs
- Fields: `timestamp`, `level`, `step`, `goal_id`, `duration_ms`, `status`
- Log file: `context/runs/<timestamp>/step-<N>.json`
- **Files:** `~/.opencode-bot/core/logger.py`

### 3.2 Telegram Alerting

- Failed steps → immediate Telegram notification
- Error summarization (don't dump stack traces, summarize)
- Configurable: `LOG_LEVEL=DEBUG|INFO|WARN|ERROR` in `.env`
- **Files:** `~/.opencode-bot/core/alerter.py`

### 3.3 Health Endpoint / Heartbeat

- Simple HTTP health endpoint on `localhost:<PORT>/health`
- Returns: `{"status":"ok","last_step":"<timestamp>","goal":"<current>","uptime":"<seconds>"}`
- Or lightweight alternative: heartbeat file `context/.heartbeat` updated every step
- pm2 monitoring via `pm2 monitor` or custom metrics
- **Files:** `~/.opencode-bot/core/health.py`

**Verification:** `curl localhost:PORT/health` returns 200, Telegram receives error alerts

---

## Phase 4: Resilience (Week 4)

### 4.1 Blast-Radius Isolation

- Wrap each skill execution in a subprocess with timeout
- Skill crash → log error, continue loop (don't crash agent)
- Per-skill resource limits (CPU, memory, runtime)
- **Files:** `~/.opencode-bot/core/skill_runner.py`

### 4.2 STATE.md Cleanup Filter

- Post-execution filter strips internal monologue from STATE.md
- Validates format before writing
- Rejects garbled content and rewrites cleanly
- **Files:** `~/.opencode-bot/core/state_writer.py`

### 4.3 Graceful Degradation

- If any subsystem fails (health, alerts, backup), agent continues
- Degraded status reported in STATE.md
- Auto-retry flaky operations (3 attempts with exponential backoff)

**Verification:** Kill a skill process mid-execution → agent logs error and continues next goal

---

## Success Criteria

| Metric | Now (6/10) | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|--------|-----------|---------|---------|---------|---------|
| Test coverage | 0% | ≥80% | ≥80% | ≥85% | ≥90% |
| CI passing | N/A | N/A | ✓ | ✓ | ✓ |
| STATE.md integrity | Garbled | Monitored | Clean | Clean | Clean |
| Backup/restore | None | None | ✓ | ✓ | ✓ |
| Error alerting | Silent | Silent | Silent | Telegram | Telegram |
| Blast radius | Full crash | Full crash | Full crash | Full crash | Isolated |
| Health check | None | None | None | ✓ | ✓ |

---

## Execution Order

```
Week 1: 1.1 → 1.2 → 1.3 → coverage verification
Week 2: 2.1 → 2.3 → backup verification
Week 3: 3.1 → 3.2 → 3.3 → alert test
Week 4: 4.1 → 4.2 → 4.3 → full resilience test
```

---

*Starting with Phase 1: Test Foundation. First step: write the core loop integration test.*
