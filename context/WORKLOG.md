# Active Work
Project: /home/the_bomb/orkes_ds2 — the_bomb remediation runbook (2026-08-03)
Task: Phases 0-2 done; Phase 3 STAGED (window ≥ 08-05 19:00 local, operator present)
Status: in progress
Updated: 2026-08-03T11:36 UTC (19:36 MYT)

## Checkpoint 11:36 UTC — step-4 no-regression re-verification (read-only)
- ALL CLEAR. / 83%, PSI mem avg60 1.56/1.50, PSI io 6.32/6.20, swap 10Gi, containers 42, load 2.32, GPU ocr 9379 MiB.
- pm2 restart counts IDENTICAL to baseline — zero service disturbance (sec-harga-vx 31, v9 28, v9-sched 37, ocr 53, embed 28).
- Token census masked: f174 ×129 + e6dc ×108 (legit, dump.pm2+backups+tmp copies) + cf_deploy.py 3e3e ×1. Leaked 2568 = ZERO everywhere. Active-tree sweep clean, /tmp clean, proc cmdline clear.
- Redaction intact (3 deployments + prompt.py:371/419 wiring). ~/.secrets 700. 7 .old dirs present.
- Operator-pending unchanged: rotation (2568 + 3e3e), journald vacuum (4.0G), apt clean, snapd rev, .old rm 08-05, pm2-logrotate. Phase 3 staged ≥08-05.

## Checkpoint 11:24 UTC — residual leak hunt (this step)
- dump.pm2 rewrite 19:23:15 MYT traced to operator's `pm2 delete harga-work-tunnel` + `pm2 save` (harga.work white-screen fix), NOT CF rotation. Tunnels now systemd user services, no CF_TUNNEL_TOKEN in environ.
- Scrubbed 2 post-18:25 residual copies of leaked token (tail 2568): ~/.pm2/logs/harga-work-tunnel-error.log (66.9KB, ×2 hits) + /tmp/opencode/pm2-now.json (×2). Both inode-preserving sed→tmp→mv. 0 cfut_ remain. /tmp full scan clean.
- NEW second leaked token: /tmp/cf_deploy.py (mtime 08-01 18:04) hardcodes cfut_aKQoe...3e3e. chmod 600, value kept (operator mid CF Pages work). Flagged for rotation.
- Token census: dump.pm2 + 48 backups contain ONLY legit f174/e6dc. No regressions (PSI mem 0.16 avg60, / 83%, containers 42, pm2 counts match baseline, redact.py intact).
- Operator actively fixing harga.work CF Pages (option 1: wrangler redeploy). No interference.

## Next
HOLD — all remaining items operator-gated (rotate BOTH tokens, journald vacuum+cap, apt clean, snapd rev, 48h .old rm). Phase 3 staged until 08-05 window.

## Completed (archived)
### 2026-08-03 remediation runbook
- Phase 0 (18:25 MYT): 38 files scrubbed, proc cmdline clear, pm2 logs flushed, secret stores 600/700, ~/.secrets 700, redact.py deployed orkes + orkes_sec + wired into prompt.py, fake-token verified.
- Phase 1 (18:45 UTC): baseline captured /mnt/data/runbook-2026-08-03/baseline/. Containers 42, services 32, restart policies all auto. PSI mem verdict ACTIVE PRESSURE.
- Phase 2 (19:10 UTC): freed ~14G, / 85%→83%, PSI mem 8.75→0.36. npm/uv/cargo caches, loose files, 7 cache relocations with .old 48h retention, HF cache 24G pre-staged. No restarts caused.
- Phase 3 STAGED (19:35 UTC): restore-commands.md at /mnt/data/runbook-2026-08-03/. Pre-flight verified. No execution.

## Earlier: Harga UI/UX — All 11 remaining issues fixed and verified

### Changes Applied (bidder.js + bidder.css)
1. **Disambiguation button** — "Sources" button per line item row (pre-existing)
2. **_wsDirty tracking** — Dirty flag on lever changes, disambiguation price select, price input. Cleared on save. Confirm dialog on workspace close. `beforeunload` browser warning.
3. **Stale empty state** — Search input always visible (pre-existing)
4. **Mark-status return flow** — `markStatus()` calls `closeWorkspace()` for proper dashboard return
5. **Tender picker loading state** — "Searching SmartGEP..." shown during fetch
6. **Bid search/filter** — Search input in dashboard (pre-existing)
7. **Read-only line items** — Prices as text when won/lost (pre-existing)
8. **Research tab badges** — Badge counts populated dynamically on Web Research and Memory tabs
9. **Inline styles → CSS classes** — All inline styles replaced with token-based classes
10. **aria-current** — Correct on research tabs (pre-existing)
11. **JSON export** — Blob download with proper filename

### Verification
- Flask: HTTP 200
- E2E: 23/23 passed
- Hex violations: 0

### Next
Awaiting operator direction.
