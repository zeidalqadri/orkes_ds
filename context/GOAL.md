# Active Goal — Audit the outcome-attribution path in the learning loop

Read-only. Do not change code this goal; produce evidence.

`RUNBOOK.md` documents a past corruption: timeouts were scored as losses, wrongly marking
~56K provider votes as wrong and clamping `provider_weights` to the 0.3 floor.

Determine whether that failure mode is **still reachable** in the current code.

## Do

1. Read `/home/the_bomb/konsos/market-whisper/outcome_tracker.py` and trace every path
   that writes to `signal_outcomes` and `llm_provider_votes`.
2. Identify how a provider timeout / exchange error / expired signal is distinguished
   from a genuine wrong call — or show that it is not.
3. Check current data: are `provider_weights` still at or near the 0.3 floor, and what is
   the most recent row in `signals` and `signal_outcomes`? (The prior audit in
   `context/konsos_crosscutting_notes.md` found signals stale since ~2026-04-28; the
   service has restarted since, so confirm rather than assume.)

## Success criteria

A report stating:
- **Reachable / not reachable**, with the specific file and line that decides it.
- The evidence: the query you ran and the numbers it returned.
- If still reachable: the smallest change that would fix it, and what regression test
  would prove the fix. Do not implement it yet.

## Constraints

- Read-only. No code changes, no restarts, no writes to `konsos.db`.
- If you need to query `konsos.db`, use a read-only connection.
- `sqlite3` CLI is not installed on this host — use Python's `sqlite3` module.
