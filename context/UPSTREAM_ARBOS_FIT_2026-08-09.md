# Upstream Arbos Fit — 2026-08-09

## Decision

Do **not** replace `arbos-orkes_ds2` in place. Treat upstream
`unarbos/arbos` `v0.1.47` as a separately evaluated migration candidate.

## Why

- This host runs a customized Python Arbos core from `~/.arbos` under PM2,
  with the `GOAL.md` / `STATE.md` / `INBOX.md` loop contract and Claude/Codex
  CLI routing.
- Upstream is a Go `1.26.4` application with its own event-sourced SQLite
  sessions, configuration directory, web/TUI control plane, and native model
  providers. It is not compatible with the existing loop state or process
  model; Go is not installed on this host.
- The useful upstream improvement is its provider-catalog fallback when a
  stored session model is no longer offered. That addresses the earlier
  invalid-model failure class, but it should be adapted to the current Python
  router rather than used as a reason to replace the fleet.
- An additional persistent web/browser surface is a poor immediate fit for
  this capacity-constrained PM2 host. Existing always-on OCR and embedding
  services already consume multiple GiB.

## Safe Next Step

Only run a pilot when there is a concrete need for its web/session model:

1. Install the required Go toolchain outside the production path.
2. Build the pinned upstream commit in an isolated directory and database.
3. Use a new Telegram bot token; do not run two pollers on a production bot.
4. Verify provider authentication, model fallback, tool approvals, RSS, and
   restart behavior against the current loop.
5. Keep `arbos-orkes_ds2` online throughout the pilot and migrate only after
   explicit acceptance criteria pass.
