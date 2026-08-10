# Andrew-BTT Arbos Fit — 2026-08-09

## Decision

Do **not** adopt `andrew-btt/arbos` for `arbos-orkes_ds2`, and do not use it
as the basis for a fleet upgrade.

## What It Is

- A compact Python Telegram/Ralph-loop implementation: 867 lines of
  `arbos.py`, plus shell launch/restart scripts and three small dependencies.
- It runs the Claude CLI only, explicitly directs it to OpenRouter, and
  defaults to `anthropic/claude-opus-4.6`.
- The repository has 68 commits through 2026-03-11. The visible history is
  authored as `unconst`, so it should be treated as an external fork/mirror,
  not as a separately maintained Arbos architecture.

## Why It Does Not Fit This Host

- `arbos-orkes_ds2` is a project shim over the shared `~/.arbos/core` runtime,
  not a standalone loop. The current core supplies provider routing,
  model-fallback handling, encrypted environment support, PM2/fleet controls,
  per-bot locking, restart continuation, shared memory, and run state.
- Replacing it would discard the live `GOAL.md` / `STATE.md` / `INBOX.md`
  operational contract and remove the existing Codex/DeepSeek routing that
  avoids the previously observed unavailable-Claude-model failure.
- The fork writes project-local Claude settings that force OpenRouter and
  broad CLI permissions. That conflicts with this fleet's current provider
  controls and would introduce a new model/key management path.
- Its restart behavior only handles `.restart`; it does not preserve the
  existing `.restart_continue` mechanism used to resume active work safely.
- Running it alongside production would require a separate Telegram token:
  two long-polling processes cannot safely share one bot identity.

## Useful Ideas To Reuse

- It has a simple streaming Telegram response path and a no-output subprocess
  timeout. Evaluate these as isolated improvements to the shared core only if
  an observed delivery or hung-subprocess problem warrants them.
- Its deliberately small surface is suitable as a disposable sandbox demo,
  not as the production controller for this host.

## Safe Path If A Trial Is Wanted

1. Clone it into an isolated directory with a new Telegram bot token and
   dedicated OpenRouter budget/key.
2. Run it under a distinct PM2 name; do not point it at production context or
   shared `~/.arbos/core` files.
3. Test goal lifecycle, restart recovery, streaming, failed-model behavior,
   and concurrent Telegram updates.
4. Keep the current fleet untouched. Promote only a narrowly extracted feature
   after it passes the same operational tests in the shared core.
