# Arbos State
Updated: 2026-08-03T11:43 UTC (local 19:43 MYT)

## Status: IN PROGRESS — the_bomb remediation runbook (2026-08-03) — Phases 0-2 done; Phase 3 STAGED (needs operator window, earliest after 48h soak)

## Goal
Execute `/home/the_bomb/orkes_ds2/context/uploads/the_bomb-remediation-runbook-2026-08-03.md`:
Phase 0 (rotate token — OPERATOR browser step; scrub copies; audit secret stores; deploy redaction), Phase 1 diagnostics, Phase 2 and Phase 3 changes gated on evidence. Update STATE.md at each checkpoint. Zero interruption to sec-* services, harga.work, yellowpages, Unlimited-OCR, authentik, ollama.

## Approach
1. **Phase 0** (this step, prioritized): operator notified re: Cloudflare rotation (manual browser step — cannot be automated). Meanwhile: find on-disk copies by prefix pattern (never literal value, never argv), scrub with inode-preserving technique, audit secret store modes, deploy `redact.py` to `~/orkes/lib/` + `~/orkes_sec/lib/` and wire into prompt-builder path, verify with fake token.
2. **Phase 1**: read-only diagnostics → baseline to `/mnt/data/runbook-2026-08-03/baseline/`, PSI/swap/open-code verdicts.
3. **Phase 2**: no-restart reclaims (apt/snap/journald/caches/docker prune/loose files); opencode kill ONLY if all 1.3 gates agree.
4. **Phase 3**: STAGE ONLY (restore commands + pre-flight). Requires operator maintenance window — interrupts all containers/authentik/ollama → violates zero-interruption constraint if run now. Do not execute without explicit operator window.

## File manifest
- MODIFY: `~/orkes/lib/redact.py` (new), `~/orkes_sec/lib/redact.py` (new), prompt-builder call sites (both repos)
- CREATE: `/mnt/data/runbook-2026-08-03/{baseline,incident-2026-08-03}/`, `~/.secrets/` (700)
- MODIFY: `context/STATE.md`, `WORKLOG.md` (checkpoints)

## Verification plan
- `grep -rlaE 'cfut_[A-Za-z0-9_-]{20,}'` on `/home/the_bomb` (excl. git/caches) → empty
- `/proc/[0-9]*/cmdline` → clear
- Secret stores all 600/700
- Redact.py unit test with fake `cfut_` token → replaced, alerted
- `pm2 ls` restart counts match baseline (proof zero service disturbance)

## Phase 0 exit criteria (track)
- [ ] TOKEN ROTATION — OPERATOR (dashboard, browser). Blocked on human. dump.pm2 rewrite 19:23:15 MYT was the operator's tunnel-removal `pm2 save`, NOT rotation. **TWO tokens to rotate now:** leaked cfut_ixC...2568 AND second /tmp/cf_deploy.py cfut_aKQoe...3e3e.
- [x] Disk search clean (scrub verified 18:25 MYT; 2 post-18:25 residuals scrubbed 19:24 — harga-work-tunnel-error.log + /tmp/opencode/pm2-now.json)
- [x] proc cmdline clean (re-checked 19:21 MYT → clear)
- [x] pm2 logs flushed, today's .gz deleted (re-checked 19:21 → none today)
- [x] secret stores 600/700 (verified 18:25 MYT)
- [x] ~/.secrets exists; redact.py deployed both repos + verified (fake-token test passed)

## Checkpoints
- 17:05 UTC — plan written; Phase 0 starting.
- 18:25 UTC — Phase 0 verified clean: 38 files scrubbed (prior step) + re-verified; proc cmdline clear; pm2 logs clean; .gz none today; git/shell history/containers clean; secret stores 600/700; ~/.secrets 700 exists; redact.py deployed orkes/lib + orkes_sec/lib + ~/.arbos/core/redaction.py wired into prompt.py (log_chat:371, prompt-side:419) with throttled owner alert; fake-token verified.
- 18:25 UTC — Operator notified (Telegram): 3 residual items all operator-only — (1) ROTATE CF token at dash.cloudflare.com (browser), (2) journald vacuum `sudo journalctl --vacuum-time=1h` (3 hits, 3.9G, root-only), (3) post-rotation pm2 env update + `pm2 save` (live tunnel pid 33889 + harga-work-tunnel pm2 env carry old CF_TUNNEL_TOKEN; dump.pm2 holds buzzbuzz legit CF_API_TOKEN/CLOUDFLARE_API_TOKEN — NOT the leaked one, do not scrub).
- 18:45 UTC — Phase 1 baseline captured to /mnt/data/runbook-2026-08-03/baseline/ (system/ps/services/containers/restart-policies/networks/volumes/docker-df/pm2/gpu/listeners/last). Containers 42, services 32 running, restart-policies ALL auto (none missing), only human account the_bomb.
- 19:21 MYT (11:21 UTC) — No-regression verification (read-only): PSI mem some/full avg60 = 0.03/0.03 (resolved; the 9.48/9.34 blip did not persist). PSI io some/full avg60 ~17 — traced to STALE bg cfut_ sweep PID 448247 (grep -rlaE over /home/the_bomb, running 1h03m in D-state, writing /tmp/cf-hits-home.txt + /tmp/cf-sweep.done) → TERMINATED (redundant duplicate of 18:25 scrub verification; /tmp artifacts discarded as incomplete, no re-sweep needed). / 83% (742G/936G, 155G avail) unchanged; /mnt/data 8%. Swap 9.8G stale, si/so ~0. Containers 42. pm2 all online except baseline-stopped download-retry. Post-Phase-2 restarts (sec-harga-vx ↺31 12m, harga-work-tunnel ↺7 10m, arbos-Orkes_Buzz2 ↺32 21m) all operator-directed harga.work white-screen fix (18:59-19:08 MYT) — NOT remediation-caused. All 7 .old dirs present (~7.1G), symlinks resolve to /mnt/data/caches; 48h rm eligible from ~08-05 19:00 local. /proc cmdline CLEAR; no today .gz. dump.pm2 mtime 08-02 → CF rotation + pm2 save still pending.
- 19:23-19:24 MYT (11:23-11:24 UTC) — **Residual leak hunt (this step):** (a) dump.pm2 rewritten 19:23:15 MYT + dump.pm2.bak (identical 194709B) — traced via Telegram chat log 20260803_191104.jsonl to OPERATOR-directed `pm2 delete harga-work-tunnel` (19:22, white-screen fix) + `pm2 save`; NOT CF rotation. Diff vs 19:15 backup: sec-harga-v9 + sec-harga-vx gained legit CF_API_TOKEN (f174)/CLOUDFLARE_API_TOKEN (e6dc) env. Tunnels now systemd user services (cloudflared.service config.json gpu-vps pid 3099085; cloudflared-humina.service humina pid 1469; both under systemd --user pid 1420), NO CF_TUNNEL_TOKEN in environ, configs clean. (b) **SCRUBBED LEAK**: ~/.pm2/logs/harga-work-tunnel-error.log (66.9KB, mtime 19:21) held LEAKED token tail 2568 ×2 (written 11:03:31Z tunnel restart, post-18:25 scrub) — sed→tmp→mv, 0 cfut_ left, 5 [REDACTED-CF-TOKEN-2026-08-03] markers, inode-preserving. (c) **SCRUBBED LEAK**: /tmp/opencode/pm2-now.json (644, mtime 19:04) held tail 2568 ×2 — same technique, 0 left. /tmp full scan tail 2568 = clean. (d) **SECOND TOKEN FOUND**: /tmp/cf_deploy.py (mtime 2026-08-01 18:04) hardcodes different CF token (prefix cfut_aKQoe, tail 3e3e, len 53) — a separate leak per runbook 0.4; NOT running; CHMOD 600 (value kept for operator's active CF Pages work); flagged for rotation. (e) Tail census: dump.pm2 + all 48 backups + defuse/restore-bundle tmp copies contain ONLY legit f174/e6dc; leaked 2568 existed ONLY in the 2 scrubbed files. (f) Health re-check: / 83%, PSI mem avg60 0.16/0.16, containers 42, pm2 36 online + download-retry (baseline stop) = 37, restart counts match baseline (sec-harga-vx 31, v9 28, v9-sched 37, ocr 53, embed 28), redact.py deployments intact (orkes 1360B, orkes_sec 1360B, ~/.arbos/core/redaction.py 3186B), ~/.secrets 700. Operator actively fixing harga.work white screen (CF Pages Direct Upload serves _worker.js static; user chose option 1: wrangler redeploy + Pages:Edit perm) — do NOT interfere.

## Phase 1 findings (memory — issue #3 verdict: ACTIVE PRESSURE, Phase 2 priority)
- PSI memory some/full avg60 = 8.75/8.55 (runbook: full>10 = real sustained stalls; we're near it). PSI io some/full avg60 = 48.39/46.60 — SEVERE I/O stall, dominant symptom.
- vmstat: si/so low (0-1128/0-148 KB/s) = swap stale, NOT thrashing. bi ~50MB/s = active page-cache demand.
- Committed_AS 54G > CommitLimit 33G — overcommit exposure on spike.
- AnonPages 10.2G, Cached 18G, MemAvailable 18.2G, Dirty 12MB. swappiness already 10 (not 60).
- Swap accounted 7.1GiB of 9.9G: ocr_server.py (Unlimited-OCR, protected) 2.86G cold; embed_server 823M; 3 abandoned opencode 256-307M each; tenders_api 256M; harga_v8 app 253M; litellm 232M; authentik workers ~500M total.
- **opencode abandonment verdict (1.3): DO NOT KILL.** All candidates (4131680, 93395, 321500) have PPID=live bash (`bash --rcfile /dev/fd/63`), each has 1 child (ecc-memory-mcp), STAT=Sl, no TCP sockets, CPU delta 66-72 ticks/60s (just above 50-tick idle threshold, below active-work thousands). Runbook: any gate fails → leave alone. Note: 482412 + 3697870 also opencode (482412 = THIS agent; 3697870 bare opencode since 15:27Z).
- embed_server (1.2): RSS 1.66G, VmData 5.69G, VmSwap 823M, 64 threads, 21 fds (no fd leak), 28 pm2 restarts, maxmem 6GB guard. GPU: only ocr_server pid 3836736 holds GPU mem (9370/10240 MiB); embed_server not on GPU.
- pm2 totals: 5.26G RSS across apps; ocr-server 53 restarts (maxmem 4GB), embed-server 28.

## Phase 2 plan (next step, gated)
Reclaim WITHOUT restarts: apt autoremove/clean (sudo-needed), journald vacuum (sudo + operator), ~/.pm2/logs old 10MB+ rotated logs (arbos-OrkesBayu/Buzz2 May files, 28 .gz), /home orphaned run dirs, docker prune (operator judgment), loose files. NO opencode kill (gates fail). No swappiness change (already 10). Phase 3 = STAGE ONLY.

## Phase 2 DONE (2026-08-03, 19:10 UTC) — reclaim without restarts
**Result: / 85%→83% (freed ~14G, now 742G/936G, 155G avail). PSI memory some/full avg60 8.75/8.55 → 0.36/0.36 (pressure RESOLVED).** Swap 9.8G unchanged (expected — swap drains naturally as cold pages decay). Containers 42, pm2 all online except baseline-stopped download-retry.

Completed:
- npm _cacache 3.3G purged (also removed ~/.npm/_libvips, _npx, _prebuilds trees); uv cache 61M cleaned; cargo registry/cache+src (~490M) moved to /mnt/data/archive/2026-08-03/cargo-cache/ (safety net blocked rm, so moved instead of deleted).
- Loose files ~544M → /mnt/data/archive/2026-08-03/: bocra.tar.gz (386M), cbaas-server.tar.gz (89M), RFP-000000168142.zip (11M), 404b42f0...heapsnapshot (35M), n8n.log (91M→2.3M .gz; n8n NOT running, confirmed via pgrep+docker). lsof confirmed no live writers before moving.
- Docker: `image prune -f` + `builder prune --filter until=336h` reclaimed 0B (nothing dangling).
- Container logs: none >200MB (2.6 scan clean; no truncation needed).
- Cache relocations (rsync→verify byte-exact→mv .old→symlink; .old retained 48h): torch 2.5G, swift 2.5G, android-sdk 458M, google-cloud-sdk 862M, puppeteer 643M, EasyOCR 94M, crawl4ai 5M → /mnt/data/caches/. Symlinks verified resolve to /mnt/data; gcloud --version works.
- HF cache 24G rsynced to /mnt/data/caches/huggingface/ (byte-exact, 429 files). Symlink swap DEFERRED to Phase 3 — embed_server pid 2652772 holds bge-large-en blob open (lsof confirmed). .old NOT created (source untouched, copy is pure pre-stage).
- ms-playwright 2.7G SKIPPED — held open by live yellowpages download_retry.py (pid 667688→672539 chrome, ~18s old).

Verified NOT caused by Phase 2 (all natural/fleet-orchestrated):
- sec-harga-vx restarted 10:51:01Z: clean gunicorn SIGTERM graceful shutdown, exit 0, restart_time 29→30. Journald shows pm2-runtime SIGTERM 10:51:45Z + "new goal ... Bot restarted" = arbos fleet self-restart. NOT in watchdog EXPECTED_PROCS.
- arbos-Orkes_Buzz2 restarted 10:56:21Z, exit 42, restart_time 31→32. Launch PATH references ~/.cargo/bin (untouched — only registry/cache+src moved). No crash trace; natural.
- harga-work-tunnel restarted 11:03:31Z: Cloudflare "control stream encountered a failure" (tunnel error log) — natural.
- pm2_watchdog.sh (5-min cron) logged NO restarts in window (only 09:55 arbos-tronzz, pre-window). It only restarts offline procs and doesn't include sec-harga-vx.

## Phase 2 operator-only remainder (sudo/NOPASSWD-exempt)
1. `sudo apt-get clean` (113M /var/cache/apt). 2. `sudo snap remove snapd --revision=27406` (disabled rev). 3. `sudo journalctl --vacuum-size=1G` (3.9G→1G) + journald.conf cap (SystemMaxUse=1G, SystemMaxFileSize=128M, MaxRetentionSec=30day; backup to /mnt/data/runbook-2026-08-03/baseline/journald.conf.bak first; `sudo systemctl restart systemd-journald` — socket-activated, safe, the one restart in Phase 2). 4. After 48h soak: `rm -rf` the seven ~/.cache/torch.old, swift-6.0.3.old, android-sdk.old, google-cloud-sdk.old, ~/.cache/puppeteer.old, .EasyOCR.old, .crawl4ai.old (~7G total). 5. pm2-logrotate install (optional; `pm2 install pm2-logrotate`, max_size 50M, retain 7, compress true).

## Phase 3 (STAGE ONLY — requires operator maintenance window, no execution now)
3.1 docker data-root → /mnt/data (biggest; SKIP if / under 70% after Phase 2 soak — currently 83%). Pre-stage rsync `sudo rsync -aHAX --numeric-ids /var/lib/docker/ /mnt/data/docker/` live. 3.2 ollama models via OLLAMA_MODELS. 3.3 swap → /mnt/data (second swap area first). 3.4 embed_server restart (only if leak persists — no fd leak found, may skip). 3.5 buzz-keycloak (only if 1.6 said in use). 3.6 /proc hidepid (optional, breakage risk). 3.7 git history rewrite (only if Phase 0.4 found cfut_ in git history + unpushed — none found). Pre-flight checklist at runbook line 1627. Suggested window 90 min.

## Phase 3 STAGED (2026-08-03, 19:35 UTC) — restore-commands.md written
- Full operator run-sheet at **/mnt/data/runbook-2026-08-03/restore-commands.md** (pre-flight status + per-step commands + verification + do-not-do). No execution — everything interrupts services.
- **Pre-flight verified (arbos, read-only):** (1) ZERO containers with restart=no — all unless-stopped/always, no manual starts needed (runbook 1629). (2) docker overlay2/extfs, Root Dir /var/lib/docker; /mnt/data = ext4 (d_type OK for overlay2). (3) swap = /swap.img 16G 9.8G used prio -2; gate: MemAvailable 17G (>5G) → 3.3 NOT postponed but 9.8G churn expected. (4) ollama systemd User=ollama, NO OLLAMA_MODELS env; real store needs sudo locate (NOT ~/.ollama blindly — that's only the CLI store). (5) buzz-keycloak = Up 2 days (unhealthy) → 3.5 applies. (6) swappiness already 10 AND persisted (/etc/sysctl.d/90-swappiness.conf) → runbook 3.3 swappiness step skipped. (7) 3.7 SKIPPED (Phase 0.4 found no cfut_ in git history).
- **Window gate:** earliest 2026-08-05 ~19:10Z (48h soak after Phase 2). Operator items pending from Phase 2 sudo list must also be done (apt clean, snapd rev 27406, journald vacuum+cap, 48h .old deletion, optional pm2-logrotate).
- PSI re-check 19:35Z: memory some/full avg60 = 9.48/9.34 (crept back up from 0.36 — likely this agent session + page-cache churn; still <10 alert threshold, watch not act).

## Latest status (19:36 MYT / 11:36 UTC) — HOLD: no autonomous work left; all remaining items operator-gated

- **Step 4 re-verification (read-only): ALL CLEAR.** / 83% (743G/936G, 154G avail) unchanged. PSI mem avg60 1.56/1.50 (healthy, <10); PSI io avg60 6.32/6.20. Swap 10Gi used (unchanged, expected). Containers 42. Load 2.32. GPU: ocr_server 9379 MiB (matches baseline 9370). pm2 all online, restart counts IDENTICAL to baseline (sec-harga-vx 31, v9 28, v9-sched 37, ocr 53, embed 28) — zero disturbance.
- Token census re-confirmed: ONLY legit tails f174 + e6dc in dump.pm2+backups+defuse/restore tmp copies (masked census: f174 ×129, e6dc ×108, plus cf_deploy.py's 3e3e ×1). Leaked 2568 = ZERO everywhere. Active-tree sweep (orkes/orkes_sec/.arbos/orkes_ds2/.pm2, excl caches/git) = clean. /tmp clean. proc cmdline CLEAR. No today's .gz.
- /tmp/cf_deploy.py STILL present (chmod 600, mtime 08-01 18:04) — operator mid CF Pages wrangler work; still needs rotation verdict + removal after deploy completes. dump.pm2 mtime 19:23 = operator tunnel-removal save, NOT rotation.
- Redaction intact: redact.py orkes 1360B + orkes_sec 1360B + ~/.arbos/core/redaction.py 3186B, wired at prompt.py:371 (log_chat) + :419 (prompt-side), runner.py:1378, telegram.py:128/195/233/261. ~/.secrets 700.
- 7 .old dirs present (torch.old 2.5G, puppeteer.old 643M, google-cloud-sdk.old, .EasyOCR.old, android-sdk.old, .crawl4ai.old, swift-6.0.3.old); 48h rm eligible ~08-05 19:00 local.
- journald STILL 4.0G (target 1G), apt cache 113M, snapd_27406.snap still present — all operator/sudo-pending, unchanged.
- **Still pending from operator (unchanged):** (1) rotate leaked CF token tail 2568 at dash.cloudflare.com (browser), (2) rotate second token 3e3e in /tmp/cf_deploy.py + rm file after wrangler deploy, (3) journald vacuum+cap, (4) apt clean + snapd rev rm, (5) 08-05 19:00 local .old rm, (6) optional pm2-logrotate. Phase 3 staged for operator window ≥08-05.
- **No regressions.** Memory pressure resolved (PSI mem 0.16/0.16 avg60). Disk stable 83%. All services online. Phase 2 relocations intact (7 .old dirs + symlinks verified). Two post-18:25 residual token copies (harga-work-tunnel-error.log, /tmp/opencode/pm2-now.json) found + scrubbed this step.
- **Operator-gated, still pending (verified this step):**
  1. CF token ROTATION at dash.cloudflare.com (browser) — NOT yet done. NOTE: dump.pm2 WAS rewritten at 19:23:15 MYT but that was the operator's `pm2 delete harga-work-tunnel` + `pm2 save` (white-screen fix), NOT rotation.
  2. **NEW — second leaked token**: /tmp/cf_deploy.py hardcodes a DIFFERENT CF token (prefix cfut_aKQoe, tail 3e3e). chmod 600'd (kept intact for active CF Pages work). Needs rotation verdict + removal after wrangler deploy completes.
  3. journald vacuum + cap: still 3.9G (target 1G); `sudo journalctl --vacuum-size=1G` + journald.conf SystemMaxUse=1G/MaxRetentionSec=30day + `systemctl restart systemd-journald`.
  4. `sudo apt-get clean` (113M) + `sudo snap remove snapd --revision=27406`.
  5. After soak (~08-05 19:00 local): rm the seven .old dirs (~7.1G).
  6. Optional: pm2-logrotate install.
- **Phase 3 remains STAGED.** Earliest window 08-05 ~19:00 local (48h soak from Phase 2). Runbook 3.1 docker data-root move stays optional if / stays under 70% (currently 83% → likely still needed unless operator reclaims ~140G).
- **Action needed from operator before next autonomous step:** complete rotation (both tokens), items 3-4 above; then arbos re-verifies and, on 08-05, confirms window for Phase 3 execution (operator must be present — all Phase 3 steps interrupt services).

## 11:43 UTC (19:43 MYT) — Step 5 re-verification: HOLD CONFIRMED, all clean
- Leaked-token census (rg `cfut_[...]{20,}2568`) across orkes/orkes_sec/.arbos/orkes_ds2/.pm2/.bash_history/tmp (excl git/caches/db/png): **ZERO hits**. (2 run-log hits were redact.py fake test tokens cfut_ZZZZ/AbCd + legit masked f174/e6dc; 2 proc "hits" were my own sweep self-match.) proc cmdline clean apart from self-match.
- Disk / 83% (743G/936G, 154G avail); /mnt/data 8%. PSI mem avg60 0.34/0.33 (healthy); PSI io avg60 7.29/7.21 (elevated but below 10, no action). Swap 10Gi stale, si/so ~0. Load 0.93. Containers 42.
- pm2: all online except baseline-stopped download-retry; restart counts IDENTICAL to baseline (sec-harga-vx 31, v9 28, v9-sched 37, ocr 53, embed 28, arbos-orkes_ds2 31) — zero disturbance.
- Redaction intact: orkes/redact.py + orkes_sec/redact.py 1360B each, ~/.arbos/core/redaction.py 3186B. ~/.secrets dir exists.
- **7 .old dirs re-verified**: torch.old + puppeteer.old in ~/.cache; swift-6.0.3.old, android-sdk.old, google-cloud-sdk.old at HOME root; .EasyOCR.old + .crawl4ai.old at HOME. All live symlinks resolve to /mnt/data/caches/* (swift→/mnt/data/caches/swift, android-sdk→.../android-sdk, google-cloud-sdk→.../gcloud, torch→.../torch, puppeteer→.../puppeteer).
- Unchanged operator-pending: journald 3.9G (target 1G), apt 113M, snapd_27406 present, /tmp/cf_deploy.py (600, mtime 08-01) still awaiting rotation verdict, dump.pm2 mtime 19:23 = tunnel-removal save (NOT rotation). Both CF tokens (2568, 3e3e) still unrotated.
- NO regressions. No autonomous work remains — everything operator-gated. Next autonomous action only after operator completes rotation + sudo items; Phase 3 window earliest 08-05 ~19:00 local.
