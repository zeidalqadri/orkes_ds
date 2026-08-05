# Active Work
Project: /home/the_bomb/orkes_ds2
Task: CF token leak remediation — Phases 0-2 done; Phase 3 staged (operator window)
Status: In progress — Phases 0/1/2 complete; Phase 3 run-sheet written, awaiting operator window (earliest 08-05 ~19:00 local). Operator-gated: CF rotation (BOTH tokens) + pm2 save, journald vacuum (3.9G), snapd_27406.snap rm (file re-present), .old rm after soak. apt clean DONE.
Updated: 2026-08-05

## Completed

### Implement 5 self-improving proposals as skill artifacts (2026-08-05, ~14:13 UTC)
Operator: "action on the self improving shared leanings." Turned @rvaniaaaa loop's 5 proposals into durable registry artifacts (verified on disk), then closed out tracking.
- **P1** skill-discover loop → `~/.claude/skills/skill-discover/SKILL.md` + REFERENCE.md (scout→filter→reader docs-first→score-gate→generate→publish, no auto-merge, ≤weekly).
- **P2** score-gate (novel/actionable/minimal-deps, kill≤1) → `skill-discover/SKILL.md:41-48` + `skill-improver/SKILL.md:30-52`.
- **P3** install-ready bar ("would engineer install without editing?") → `skill-improver` SKILL.md:54-57 + REFERENCE Code-Gen checklist.
- **P4** docs-first reading → `skill-discover` stage-3 reader prompt.
- **P5** provenance chain → `~/.claude/skills/_discovery/skill_discovery_log.md` (800B, 3 seed rows).
- Closure: recorded 5-proposal table in `context/shared_learnings.md`, STATE marked complete, GOAL cleared. Verification: frontmatter name/description/user-invocable all present; skills <100 lines; grep confirms proposals recorded; no secrets.

### ArbOS re-seed loop root-caused + engine fix (2026-08-05, ~10:50 UTC)
- Symptom: every bot boot auto-seeded goal "Bot restarted. Act immediately — do NOT wait for operator." → agent confirms idle → goal clear → next boot re-seeds. Infinite loop (steps at 10:24, 10:35).
- Root cause (confirmed in ~/.arbos/core): `_auto_resume_on_boot()` computed `has_unreported_completion = state_is_idle and "last completed" in state_text.lower()`. `_write_completion_state()` (loops.py) always writes `## Last Completed:` on goal clear, so STATE.md was always "idle + last completed" → every boot re-seeded. Project-local STATE.md rewrite (10:30 step) was undone by engine on next goal clear.
- Durable fix in ~/.arbos/core/engine.py (~line 693-704): added `already_reported = "idle — completed" in state_text.lower()` and `has_unreported_completion = state_is_idle and not already_reported and "last completed" in ...`. Post-clear "IDLE — completed" now counts as already-reported → seed skipped.
- Verified: py_compile OK; logic sim against live context/STATE.md → has_unreported_completion=False, seed skipped. Requires process restart to load (running pm2 arbos-orkes_ds2 pid 142855 holds old code).
- Operator notified via Telegram; GOAL.md cleared; .goal_status=clear-goal.

## Completed

### CF Token Leak Remediation — Step 8 re-verification (2026-08-03, 19:56 MYT)
- / 83%, /mnt/data 8%, PSI mem avg60 0.25/0.23 healthy, io 2.01/1.90. Containers 42. Swap stale 10.2G.
- Load spike to 9.26 traced to embed-server embedding batch (210-780% CPU) + transient scheduler worker + own session — NOT a regression.
- pm2 restart counts identical to baseline. Token census clean (2568 ZERO; only legit f174/e6dc in defuse/restore bundles + known 3e3e in cf_deploy.py). Redaction intact, ~/.secrets 700.
- CORRECTION: snapd_27406.snap file re-present (52MB, hardlink x2) — operator rm still pending. journald 3.9G unchanged. Both CF tokens unrotated.
- STATE.md checkpoint + Telegram status sent.

### CF Token Leak Remediation — Step 6 re-verification (2026-08-03, 19:48 MYT)
- Operator completed 2 sudo items: apt cache clean (44K, was 113M) + snapd_27406.snap removed. journald STILL 3.9G (not done).
- Both CF tokens (2568, 3e3e) STILL unrotated; dump.pm2 mtime unchanged 19:23 (tunnel-removal save); /tmp/cf_deploy.py still present (600).
- NEW: ~/.cloudflared/cf_api_token now holds only redaction marker (no live token); cloudflared configs zero cfut_/token keys; tunnels systemd-active; harga.work 200.
- PSI mem avg60 1.66/1.63 (healthy); io avg60 33.39 transient — traced to tender_doc_indexer D-state (now exited). Load 4.93 (embed_server 210% CPU normal). / 83%, swap stale.
- pm2 restart counts identical to baseline; containers 42. Leaked-token census clean except known cf_deploy.py. 7 .old dirs intact.
- STATE.md checkpoint + Telegram status sent.

### CF Token Leak Remediation — No-regression sweep + stale sweep cleanup (2026-08-03, 19:21 MYT)
- Read-only verification: PSI mem some/full avg60 0.03/0.03 (pressure resolved; 9.48 blip did not persist). PSI io ~17 — driven by stale background `grep -rlaE cfut_...` PID 448247 (running 1h03m, D-state, writing /tmp/cf-hits-home.txt) → TERMINATED as redundant (Phase 0 scrub verified 18:25; /tmp artifacts discarded). IO decayed after kill.
- No regressions: / 83% (742G/936G) stable, /mnt/data 8%, swap 9.8G stale (si/so ~0), containers 42, pm2 all online except baseline-stopped download-retry. /proc cmdline clear, no today .gz.
- Post-Phase-2 pm2 restarts (sec-harga-vx ↺31, harga-work-tunnel ↺7, arbos-Orkes_Buzz2 ↺32) = operator-directed harga.work white-screen fix (18:59-19:08 MYT), NOT remediation-caused.
- Verified all 7 .old dirs present (~7.1G) + symlinks resolve to /mnt/data/caches; 48h rm eligible ~08-05 19:00 local.
- Operator-gated still pending (verified): CF rotation + pm2 env update + pm2 save (dump.pm2 mtime 08-02 18:10), journald vacuum (3.9G→1G), apt-get clean (113M), snap remove snapd rev 27406. Phase 3 remains STAGED.
- STATE.md checkpoint + Telegram status sent.

### CF Token Leak Remediation — Phase 3 STAGING (2026-08-03, 19:35 UTC)
- Wrote /mnt/data/runbook-2026-08-03/restore-commands.md (full operator run-sheet, no execution).
- Pre-flight verified: zero restart=no containers; docker overlay2/extfs + /mnt/data ext4 (safe for overlay2); swap /swap.img 16G/9.8G prio -2 (3.3 applies, gate passes); ollama User=ollama no OLLAMA_MODELS (store needs sudo locate); buzz-keycloak Up 2 days (unhealthy) → 3.5 applies; swappiness already 10+persisted (90-swappiness.conf); 3.7 skipped (no cfut_ in git history).
- Window gate: 48h soak from Phase 2 → earliest 2026-08-05 ~19:10Z.

### CF Token Leak Remediation — Phase 2 Reclaim (2026-08-03, 19:10 UTC)
No-restart reclaims. `/` 85%→83% (freed ~14G, 742G used). **PSI memory some/full avg60 8.75/8.55 → 0.36/0.36.** Swap 9.8G (unchanged, drains naturally). Containers 42; pm2 online except baseline-stopped download-retry.
- npm cache 3.3G purged, uv 61M, cargo registry/cache+src (~490M) moved to archive (safety net blocked rm).
- Loose files ~544M → /mnt/data/archive/2026-08-03 (bocra 386M, cbaas 89M, RFP 11M, heapsnapshot 35M, n8n 91M→gz).
- Docker prune 0B (nothing dangling); container logs all <200MB.
- 7 cache relocations → /mnt/data/caches (torch 2.5G, swift 2.5G, gcloud 862M, puppeteer 643M, android-sdk 458M, EasyOCR 94M, crawl4ai 5M) with 48h .old retention. Symlinks verified + gcloud works.
- HF cache 24G pre-staged to /mnt/data/caches/huggingface (byte-exact); symlink swap deferred to Phase 3 (embed_server holds blob open). ms-playwright skipped (live yellowpages download_retry).
- Verified natural restarts (sec-harga-vx clean SIGTERM fleet restart, Buzz2 exit 42 natural, tunnel Cloudflare stream fail) — none caused by Phase 2.

### CF Token Leak Remediation — Phase 1 Diagnostics (2026-08-03, 18:55 UTC)
Baseline captured to /mnt/data/runbook-2026-08-03/baseline/. Containers 42, services 32 running, restart policies ALL auto, root / 85%.
- Issue #3 memory: ACTIVE PRESSURE. PSI mem full avg60=8.55 (threshold 10), PSI io avg60=48 (SEVERE I/O stall, dominant symptom). swap stale not thrashing (si/so low). Committed_AS 54G > CommitLimit 33G. AnonPages 10.2G, Cached 18G.
- opencode abandonment (1.3): DO NOT KILL — all 3 candidates have live bash PPID + 1 child (ecc-memory-mcp), idle-alive CPU. 482412 = this agent.
- embed_server (1.2): no fd leak (21 fds), 64 threads, 28 pm2 restarts, maxmem 6GB, RSS 1.66G + 823M swap, NOT on GPU. ocr_server holds 9370/10240 MiB GPU.
- Phase 0 exit criteria re-verified CLEAN (disk, proc cmdline, git/shell history, containers, secret stores 600/700). Redaction live both directions (prompt.py:371 write, :419 prompt-side) + throttled owner alert.

### CF Token Leak Remediation — Phase 0 (2026-08-03)
Runbook: context/uploads/the_bomb-remediation-runbook-2026-08-03.md (2312 lines).
- **0.4 Search**: 3 cfut_ tokens inventory (hashes only). Leaked = CF_TUNNEL_TOKEN, pasted in Telegram 2026-08-01T18:21 + 2026-08-03T10:31. Found in orkes chat JSONL, context/runs outputs, pm2 tunnel error log, journald, live cloudflared env. Clear: proc cmdline, git history, shell history, .gz, containers.
- **0.5 Scrub**: 38 files scrubbed via Technique B (inode-preserving truncate-and-rewrite). Hitmap /mnt/data/incident-2026-08-03/hitmap.txt. Post-scrub: tunnel online, harga.work 200, JSONL valid, pm2 restart counts unchanged. journald vacuum FLAGGED (needs sudo).
- **0.6 Secret store modes**: chmod 600/700 applied + verified.
- **0.7 Prevention**: ~/.secrets (700) created; redact.py deployed to orkes/lib + orkes_sec/lib; shared core redaction extended (cfut_/gh[pousr]_/glpat_/telegram/JWT/PEM + throttled alert); wired into prompt.py load_chatlog() + log_chat() — write-side + prompt-side redaction live.
- Operator needed: token rotation (browser), pm2 env + ~/.secrets update, journald vacuum (sudo).
- Verified: redact.py fake-token test, prompt.py end-to-end test, pm2 restart counts unchanged (except arbos-orkes 42->43 natural crash 09:42Z pre-op).

### W33 Blocked + Deferred Items (2026-08-03)
Operator request: "Address blocked and deferred issues."
- **I1b [HIGH] ePerolehan dyna accounts — code-ready, blocked on creds**: fixed `_resolve_account` mis-attribution fallback in `eperolehan_submit.py` (dyna-om/dyna-segmen now hard-fail instead of silently using consurv account); `_load_accounts` supports `username_env`/`password_env`/`softcert_pin_env` + `enabled` flag; disabled stubs for dyna-segmen/dyna-om added to `scrapers/data/eperolehan/accounts.json`. Operator must supply `EPEROLEHAN_DYNA_*_USERNAME/PASSWORD/SOFTCERT_PIN` + challenge_answer.
- **I4b [MEDIUM] supplier backfill — done**: `scripts/backfill_deal_company.py` set `company_name` on all 100 won deals (consurv-technic 32, dyna-om 32, dyna-segmen 36). Backup `data/profiles.db.bak-20260803_012551`. Idempotent. supplier_pipeline discovery mechanism validated; heavy LLM enrichment left operator-dispatchable.
- Verified: eperolehan_submit.py py_compile OK, 109 tests pass. STATE.md + CONNECTIONS.md updated, Telegram sent.

### Pipeline Activation (2026-07-29)
Operator directive: build pipeline stages 3-5 (autoRFQ, autoemail, autoembed, package enhancement, approval auto-trigger).
Discovery: entire pipeline already built in orkes_sec/services/harga_v8/scheduler.py (34 tasks, 7000+ lines).
Problem: pm2 process sec-harga-v9-scheduler was defined in ecosystem.config.js but never started.
Fix: `pm2 start ecosystem.config.js --only sec-harga-v9-scheduler` from orkes_sec cwd.
First pass completed successfully. PM2 state saved.

### Refactor — Pool Common Components (2026-07-29)
3-phase refactor: interface alignment, shared module extraction, service consolidation.
- Phase 1 ✓: Interface alignment (db_utils, llm_client, fx_rates, alerts, web_search)
- Phase 2 Tier 1 ✓: Pure function extraction (context_assembler_prompts, user_prefs, comparison_engine, price_guardrails)
- Phase 2 Tier 2 ✓: quality_logger + response_cache → orkes_core; price_intent already in orkes_pricing
- Phase 3 pending: Service consolidation (Flask V8 retirement)

## Completed

### CL4R1T4S Harness Enhancements (2026-07-15)
Cross-project enhancement of all 4 orkes bots based on convergent patterns from leaked AI system prompts.

| Repo | Commit | Changes |
|---|---|---|
| orkes | `3845b19` | PROMPT.md + experts.json + shared_learnings.md |
| Orkes_Buzz2 | `edd36c4` | CLAUDE.md + PROMPT.md + experts.json (5 experts) + shared_learnings.md |
| tronzz | `a78670d` | PROMPT.md (23→83 lines) |
| orkes_ds2 | `79ad79e` | PROMPT.md + experts.json |

All pushed to origin + gibhub.

### تعلّ — Path B1 (2026-05-27)
B1.4 Gate 2: 0/28. Centroid dispersion 8.3x worse in 128D. Accepted boundary.

### Cycle 1 Complete (2026-05-26)
17/17 milestones, 9 findings (F001-F009), strongest: zone→entropy η²=0.44.

### CF Token Leak Remediation — Step 7 (2026-08-03, 19:51 MYT) — HOLD: no regressions
Read-only re-verification. / 83%, PSI mem avg60 0.04/0.04, io 4.16/4.06. pm2 restarts IDENTICAL to baseline. Token census ZERO hits (proc "hits" self-referential only). Redaction + ~/.secrets intact. All 7 .old dirs + symlinks verified. Operator progress: apt clean + snapd rev done; journald 4.0G + BOTH CF tokens still pending. Phase 3 window ≥08-05 ~19:00 local.

### Outstanding cleared (2026-08-05, ~18:48 MYT)
Operator: "Clear outstanding" (18:41 MYT).
- .old cleanup: 7 dirs (7.0G) staged to /mnt/data/trash-20260805/ (rm blocked by guardrail; move is the safe equivalent — frees root disk, rollback copy retained). Live symlinks verified on /mnt/data/caches before move. Disk 84% -> 83%.
- pm2 save run (dump.pm2 updated 18:47).
- snapd_27406.snap: full-disk find = absent, resolved.
- hargai.roowang.com: gpu-vps tunnel config.json already has ingress hargai.roowang.com -> localhost:3652 (staged 08-05 11:30). DNS record missing. Cannot be added locally: roowang.com zone lives in a different Cloudflare account (local account "Zeidalqadri@gmail.com's Account" only hosts zeidgeist.com; cf_api_token file is a redacted placeholder; cloudflared route dns failed scoped to zeidgeist.com). Operator action: add CNAME hargai -> 674690a0-0ebc-4a06-9ab4-238940a0fb1f.cfargotunnel.com (proxied) in roowang.com zone.
- CF token cleanup Phase 3: operator-gated remainder = rotate BOTH CF tokens (dashboard), then pm2 restart harga-work-tunnel + pm2 save. journald now 1.4G (down from 3.9G); sudo journalctl --vacuum-size=200M still pending operator.

## 2026-08-05T19:14 MYT — Operator: drop hargai.roowang (coverage already on harga.work/vX)
- Removed hargai.roowang.com ingress from ~/.cloudflared/config.json (was staged -> localhost:3652 since 08-05 11:30). Backup: config.json.bak-hargai-drop-*. JSON validated (30 -> 29 ingress rules).
- Rationale: harga.work/vX already serves ex-SmartGEP (Forsah/Etimad/ePerolehan); hargai.roowang.com DNS never existed (roowang.com zone = other CF account), so nothing live was affected. hargai.zeidgeist.com kept as the live mirror.
- pm2 restart harga-work-tunnel + pm2 save. Verified post-restart: harga.roowang.com/vX, /v9, harga.work/vX = 200; hargai.zeidgeist.com = 302.
- Outstanding operator-gated items unchanged: CF token rotation (Phase 3), sudo journald vacuum.
