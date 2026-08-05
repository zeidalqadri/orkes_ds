# the_bomb — remediation runbook

**Host:** `thebomb.tailb31897.ts.net` (Tailscale 100.108.103.5, LAN 192.168.0.251)
**Platform:** Ubuntu 24.04.4 LTS, kernel 6.8.0-136, 16 cores, 30Gi RAM, NVIDIA GPU
**Recon snapshot:** 2026-08-03 12:29 UTC
**Runbook written:** 2026-08-03
**Executed by:** Zeid (operator), by hand. The author of this runbook has no shell on the host.

---

## How to read this runbook

Every command block is followed by four lines:

- **Does** — what the command actually changes or reads.
- **Healthy** — what the output looks like when things are fine.
- **If wrong** — what to do when it isn't.
- **Rollback** — how to undo. Read-only steps say "none needed".

Conventions used throughout:

- Commands are written to be pasted one block at a time. Do not paste a whole phase at once.
- Anything that stops, restarts, or recreates a process is confined to **Phase 3**. Phases 0–2 are safe to run with everything live.
- `$LEAKED_TOKEN` refers to the Cloudflare token that was pasted into Telegram at 10:31 UTC. Its literal value appears nowhere in this document and must not be typed into a shell that records history.
- Where a search could print the secret to your terminal, the command is written to print **file names and counts only**. Keep it that way — your scrollback and your terminal multiplexer's buffer are additional copies.

---

## Executive summary

The host is not in danger of falling over in the next few hours. It is in danger of two slower things: an attacker using a live Cloudflare credential, and root filling up. Everything else on the list is either a symptom of those two or is cosmetic.

The single most important reframe before you touch anything: **9.8G of swap in use is not the same as being out of memory.** `free -h` reports 18Gi *available* out of 30Gi. Low `free` with 18Gi of `buff/cache` is what a healthy Linux box under sustained I/O looks like. Swap fills during spikes and then stays full, because the kernel has no reason to pay the cost of reading pages back in until something wants them. Phase 1 tells you how to distinguish "9.8G of parked pages from a spike two days ago" from "the box is thrashing right now". Those two situations have opposite correct responses, and only one of them justifies any action at all.

Similarly: load average 7.85 on 16 cores is 49% utilisation. That is not a problem and is not addressed in this runbook.

### Risk ranking

| # | Issue | Severity | Time horizon | Why it ranks here |
|---|---|---|---|---|
| 1 | Leaked Cloudflare API token (`cfut_` prefix) | **High** | Minutes to hours | The only item with an active, adversarial counterparty. The token has been live since 10:31 UTC. It is in a Telegram conversation, in `ps aux` output where any local account can read it, in pm2 logs, and in Arbos context files. Every hour it stays valid is exposure. Rotation costs you nothing and ends the exposure immediately. |
| 2 | Root filesystem at 87% (126G free of 936G) | **High** | Days to weeks | Not urgent today, but the failure mode is severe and simultaneous: at 100% you lose Postgres writes across every stack, dockerd's ability to write container state, journald, and every pm2 service's logging in one moment. `/mnt/data` has 852G free and 5% used, so this is a placement problem, not a capacity problem. Fix by relocation, not deletion. |
| 3 | Memory pressure / 9.8G swap in use | **Medium** | Ongoing | Degraded but stable. Real risk is an OOM kill landing on a `claude -p` agent mid-step, which corrupts an in-flight `STATE.md` transition — `orkes_sec` is mid "harga vX" phase work, so a torn step is expensive. Three abandoned `opencode` processes holding ~1.9G RSS are free money. Anything past that needs measurement first. |
| 4 | Container sprawl (45 containers, ~12 stacks idle 3–4 months) | **Low–Medium** | Weeks | No direct failure mode. It is the upstream cause of a meaningful share of #2 and #3. Treat as capacity hygiene, gated on evidence, and stop rather than remove. |
| 5 | `buzz-keycloak` unhealthy for 2 days | **Low** | None, possibly | Authentik is already running as the SSO layer and is fully healthy. Establish whether Keycloak serves anything before spending effort. Most likely outcome is that the Keycloak 26 health endpoint moved to the management port and the healthcheck was never updated — a false alarm on a stack you may not need at all. |

### What good looks like when this is done

- Cloudflare token rotated, no on-disk copies, redaction filter in the Telegram→prompt path, and adjacent secret stores audited and mode 600.
- Root filesystem under 70% (needs roughly 160G moved or freed).
- Swap in use trending down without a single forced reclaim, because the anonymous working set shrank.
- A written classification of all 45 containers into active / dormant-but-needed / dead, with restore commands for anything stopped.
- Zero interruption to: sec-proxy 3641, sec-sched-api 3642, sec-failsafe 3643, sec-products-api 3644, sec-tenders-api 3646, harga.work via tunnel to 3647, yellowpages 3636 via tunnel, Unlimited-OCR 10100, authentik, ollama.

---

## Phase 0 — rotate the leaked Cloudflare token

**Run this first. Before diagnostics, before anything.** Everything else in this runbook can wait a day; this cannot. Order matters: rotate at Cloudflare *before* you go hunting on disk, because rotation makes every copy you're about to find worthless, which converts a live incident into a cleanup job.

### 0.1 Rotate at Cloudflare (browser, not shell)

Do this in the Cloudflare dashboard, by hand:

1. `dash.cloudflare.com` → **My Profile** → **API Tokens**.
2. Find the token used for the Pages deploy on 2026-08-03. Note its **permissions and scope before you kill it** — screenshot it. Scope determines blast radius. A `Pages:Edit` token scoped to one account is a very different incident from an account-wide `Zone:Edit` or Workers token.
3. **Roll** the token (generates a new value, same scope) if you still need it for the Pages deploy pipeline. **Delete** it if the deploy was one-off.
4. Copy the new value straight into a file (see 0.3), never into a chat window.

The `cfut_` prefix indicates a Cloudflare **user** API token — account- or user-scoped, distinct from an Origin CA key or a `cloudflared` tunnel credential. Confirm the scope in the dashboard rather than assuming; if it turns out to be broader than Pages, widen the audit in 0.2 accordingly.

- **Does:** Invalidates the leaked credential at the source.
- **Healthy:** Token disappears from the list, or shows a new "last used" of never after rolling.
- **If wrong:** If you cannot find the token in the list, it may belong to a different Cloudflare account or be an Account-owned token (**Manage Account** → **API Tokens**) rather than a user token. Check both. If you still can't find it, escalate to deleting all tokens you don't currently recognise — you can recreate them.
- **Rollback:** None. Do not un-rotate. If a pipeline breaks, issue it a fresh, narrower token.

### 0.2 Check what the token did while it was live

The window of exposure is 2026-08-03 10:31 UTC to whenever you completed 0.1.

In the dashboard: **Manage Account** → **Audit Log**, filter from 2026-08-03 10:00 UTC. Then check by hand:

- Pages projects — any deployment you didn't trigger.
- DNS records on every zone the token could reach — any added, changed, or proxied-status flipped.
- Tunnels — any new tunnel created (`cloudflared` tunnels are the fastest way to turn a leaked CF token into inbound access).
- Workers / R2 / Access policies, if the scope reached them.

- **Does:** Establishes whether the leak was merely exposure or actual compromise.
- **Healthy:** Every audit-log entry between 10:31 and rotation maps to something you did.
- **If wrong:** Any unrecognised entry escalates this from cleanup to incident response — assume the account is compromised, rotate every credential in the account, and check whether any DNS/tunnel change could have exposed the host itself. Note that `harga.work` and `yellowpages.zeidgeist.com` both reach this box through Cloudflare tunnels, so a hostile DNS or tunnel change is a path *to* `the_bomb`.
- **Rollback:** None needed (read-only).

### 0.3 Set up a shell that doesn't record what you type

Everything from here on happens in one dedicated shell. Open it and immediately:

```bash
export HISTFILE=/dev/null
set +o history
umask 077
```

- **Does:** Stops this shell writing to `~/.bash_history` and makes any file you create in it owner-only.
- **Healthy:** No output. Confirm with `echo $HISTFILE` → `/dev/null`.
- **If wrong:** If you're in zsh, use `unset HISTFILE` and `setopt no_share_history` too — zsh's `SHARE_HISTORY` will pull from and push to the shared file even mid-session.
- **Rollback:** Close the shell.

You almost certainly do not need the token's literal value for the cleanup — the prefix regex in 0.4 finds it without you ever typing it. But if you do need it (for example, to confirm a match is *this* token and not a different `cfut_` token), read it into a variable without it appearing on the command line or in history:

```bash
read -rs LEAKED_TOKEN && echo "captured ${#LEAKED_TOKEN} chars"
```

Then paste the value and press Enter. Nothing echoes.

- **Does:** Puts the value in a shell variable only. It does not appear in `ps`, in history, or on screen.
- **Healthy:** Prints a plausible character count (Cloudflare user tokens are ~40+ chars).
- **If wrong:** A count of 0 means the paste didn't land. Retry. A count that includes a trailing newline artifact is fine; `read` strips it.
- **Rollback:** `unset LEAKED_TOKEN`, or close the shell.

Never do `grep "$LEAKED_TOKEN" ...` — the shell expands the variable before `exec`, so the secret lands in the new process's `argv` and becomes visible in `ps aux` to every account on the box. That is exactly the failure you are cleaning up. If you must search by literal value, write it to a tmpfs file and use `grep -f`:

```bash
umask 077
printf '%s\n' "$LEAKED_TOKEN" > /dev/shm/.tok
grep -rlaFf /dev/shm/.tok /home/the_bomb 2>/dev/null
shred -u /dev/shm/.tok
```

`/dev/shm` is tmpfs (16G, currently 1.1M used) so the file never touches a disk. `shred -u` on tmpfs is theatre but costs nothing; the real guarantee is that tmpfs pages die with the file.

### 0.4 Find every on-disk copy

Search by **prefix pattern**, not by value. This finds the leaked token and any other Cloudflare user token sitting around, and it never requires the secret to be in a command line.

Set the pattern once:

```bash
CFPAT='cfut_[A-Za-z0-9_-]{20,}'
```

**Home directory sweep** (skipping the directories that will otherwise dominate the runtime — `node_modules`, venvs, conda, caches, SDKs):

```bash
sudo grep -rlaE "$CFPAT" /home/the_bomb \
  --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=venv \
  --exclude-dir=miniconda3 --exclude-dir=.cache --exclude-dir=.rustup \
  --exclude-dir=.cargo --exclude-dir=.nvm --exclude-dir=android-sdk \
  --exclude-dir=google-cloud-sdk --exclude-dir=swift-6.0.3 \
  --exclude-dir=.git \
  2>/dev/null | tee /tmp/cf-hits-home.txt
wc -l < /tmp/cf-hits-home.txt
```

- **Does:** Lists files containing something shaped like a Cloudflare user token. `-l` means file names only — the secret is never printed.
- **Healthy:** A short list you can explain. Expect hits under `~/orkes/context/chat/`, `~/orkes/context/runs/<timestamp>/`, `~/orkes_sec/context/`, and possibly `STATE.md` or its history.
- **If wrong:** A hit in an unexpected place — a project `.env`, a committed config, a deploy script — is a second, separate leak. Add it to the list and treat it the same way. A hit inside an excluded directory is plausible; do a targeted second pass on `~/.cache` and `~/.nvm` only if the first sweep looks incomplete.
- **Rollback:** None needed (read-only).

**Run the excluded-directory pass separately** so it doesn't stall the main sweep:

```bash
sudo timeout 900 grep -rlaE "$CFPAT" \
  /home/the_bomb/.cache /home/the_bomb/.npm /home/the_bomb/.config \
  /home/the_bomb/.local/share 2>/dev/null | tee /tmp/cf-hits-cache.txt
```

- **Does:** Same search across the caches and config trees.
- **Healthy:** Usually empty. A hit in `.config` or `.local/share` means an application persisted the token.
- **If wrong:** If `timeout` fires at 15 minutes, narrow to one directory at a time. `.cache` has 52 subdirectories and some of them (HuggingFace, playwright) are enormous binary trees — exclude those specifically rather than raising the timeout.
- **Rollback:** None needed (read-only).

**pm2 logs and dump:**

```bash
sudo grep -caE "$CFPAT" \
  /home/the_bomb/.pm2/logs/*.log \
  /home/the_bomb/.pm2/pm2.log \
  /home/the_bomb/.pm2/dump.pm2 2>/dev/null | grep -v ':0$'
```

- **Does:** Per-file **count** of matches, filtering out files with zero. Counts, not content.
- **Healthy:** Hits in the out/error logs of whichever pm2 app was handling the Telegram message — most likely `sec-harga-bot`, `sec-agent`, or `sec-proxy`.
- **If wrong:** A hit in `dump.pm2` is worse than a log hit: `dump.pm2` is the resurrection state file, so the token would be re-injected as an environment variable on the next `pm2 resurrect`. Handle it in 0.5 with priority.
- **Rollback:** None needed (read-only).

**Rotated and compressed pm2 logs**, if `pm2-logrotate` is installed:

```bash
ls -la /home/the_bomb/.pm2/logs/ | head -50
sudo zgrep -cE "$CFPAT" /home/the_bomb/.pm2/logs/*.gz 2>/dev/null | grep -v ':0$'
```

- **Does:** Checks archived log rotations.
- **Healthy:** Either no `.gz` files (no rotation configured — which is its own problem, see Phase 2) or no matches.
- **If wrong:** Any `.gz` hit gets deleted outright in 0.5. Rotated logs have no operational value here.
- **Rollback:** None needed (read-only).

**Live process memory-adjacent surfaces** — the argv and environ of every running process:

```bash
sudo grep -laE "$CFPAT" /proc/[0-9]*/cmdline /proc/[0-9]*/environ 2>/dev/null
```

- **Does:** Identifies which running processes carry the token in their command line (world-readable) or environment (root/owner-readable).
- **Healthy:** One or more `/proc/<pid>/cmdline` hits corresponding to the `claude -p` process whose assembled prompt contains the message. Map pid to command with `ps -o pid,lstart,cmd -p <pid>`.
- **If wrong:** A hit in `/proc/<pid>/environ` for a long-lived service means the token was exported into a service environment and will survive process restarts via pm2's saved env. Cross-check `dump.pm2`.
- **Rollback:** None needed (read-only).

**You cannot scrub the memory of a running process.** This is why rotation came first. Do not kill the `claude -p` process to clear it — see the "do not do this" section. It will exit at the end of its current step and take the string with it. Confirm afterwards:

```bash
sudo grep -laE "$CFPAT" /proc/[0-9]*/cmdline 2>/dev/null || echo "clear"
```

**Shell history:**

```bash
grep -cE 'cfut_' \
  /home/the_bomb/.bash_history \
  /home/the_bomb/.zsh_history \
  /home/the_bomb/.local/share/fish/fish_history 2>/dev/null
sudo find /home/the_bomb -maxdepth 3 -name '.*history*' -o -maxdepth 3 -name '*_history' 2>/dev/null
```

- **Does:** Checks the obvious history files, then finds any others (some tools keep their own — `.node_repl_history`, `.python_history`, `.psql_history`, `.mysql_history`).
- **Healthy:** Zero counts. The token came in via Telegram, not via your keyboard, so history is a low-probability location.
- **If wrong:** If you did paste it into a shell at any point, also check `.psql_history` and any tmux/screen scrollback capture files.
- **Rollback:** None needed (read-only).

**journald:**

```bash
sudo journalctl --since '2026-08-03 10:00' --no-pager -o cat \
  | grep -caE "$CFPAT"
```

- **Does:** Counts occurrences in the journal since before the leak. Counts only, so nothing is printed to your terminal.
- **Healthy:** `0`. pm2 apps log to their own files, not the journal, so a zero here is expected.
- **If wrong:** A non-zero count means a systemd unit logged it — most likely `konsos`, `konsos-bot`, `paraty-api`, or `paraty-ingest` if any of them touch the Telegram channel. journald cannot be selectively edited; the fix is vacuuming (0.5).
- **Rollback:** None needed (read-only).

**Container logs:**

```bash
for c in $(docker ps -aq); do
  n=$(docker inspect -f '{{.Name}}' "$c")
  p=$(docker inspect -f '{{.LogPath}}' "$c")
  [ -n "$p" ] && sudo grep -qaE "$CFPAT" "$p" 2>/dev/null && echo "HIT $n -> $p"
done
echo "container log scan done"
```

- **Does:** Greps each container's json-file log for the pattern, printing container name and log path on a hit.
- **Healthy:** No `HIT` lines, just `container log scan done`. The agent fleet runs under pm2 on the host, not in containers, so containers are unlikely.
- **If wrong:** A hit means a containerised service saw the token. Note the container, and truncate its log in 0.5.
- **Rollback:** None needed (read-only).

**Git history** — the Arbos context directories may be committed. `git grep` on file contents misses history, so use the pickaxe:

```bash
for d in ~/orkes ~/orkes_sec ~/OrkesBayu ~/tronzz; do
  [ -d "$d/.git" ] || continue
  echo "== $d"
  git -C "$d" log --all --oneline -S 'cfut_' | head -20
done
```

- **Does:** Finds commits, on any branch, that added or removed a string containing `cfut_`.
- **Healthy:** No commits listed. Context directories are usually gitignored.
- **If wrong:** Any commit listed means the token is in git objects and will survive file-level redaction. If the repo has **not** been pushed, `git filter-repo` can rewrite it — but not while agents are committing to it. Note it and schedule for the window (Phase 3.7). If it **has** been pushed to a remote, rotation is your only real mitigation, which you have already done.
- **Rollback:** None needed (read-only).

### 0.5 Scrub the on-disk copies

Two techniques, and choosing the wrong one loses data.

**Technique A — for files nothing is actively writing to.** Standard in-place edit is fine:

```bash
sudo sed -i -E "s/cfut_[A-Za-z0-9_-]{20,}/[REDACTED-CF-TOKEN-2026-08-03]/g" <file>
```

**Technique B — for files a running process holds open for append** (agent context JSONL, pm2 logs, anything under `context/runs/`). `sed -i` writes a temp file and renames it over the original, which gives the file a **new inode**. Any process holding the old file descriptor keeps writing to the now-unlinked old inode, and those writes vanish silently. Use a truncate-and-rewrite that preserves the inode instead:

```bash
scrub() {
  f="$1"
  tmp=$(mktemp) || return 1
  sed -E "s/cfut_[A-Za-z0-9_-]{20,}/[REDACTED-CF-TOKEN-2026-08-03]/g" "$f" > "$tmp" \
    && cat "$tmp" > "$f" \
    && rm -f "$tmp" \
    && echo "scrubbed $f"
}
```

`cat "$tmp" > "$f"` truncates and rewrites the same inode. Processes with the file open in `O_APPEND` (which is how both pm2 and Python logging open log files) continue appending correctly.

Check which files have live writers before choosing:

```bash
while read -r f; do
  if sudo lsof -- "$f" >/dev/null 2>&1; then echo "OPEN  $f"; else echo "idle  $f"; fi
done < /tmp/cf-hits-home.txt
```

- **Does:** Splits the hit list into files with and without open file descriptors.
- **Healthy:** Most context files are `idle` — the agent writes and closes. Active run directories and any live log will show `OPEN`.
- **If wrong:** If `lsof` isn't installed, `sudo fuser "$f"` works as a substitute. If in doubt, use Technique B for everything — it is safe for idle files too.
- **Rollback:** Before scrubbing anything, snapshot the file list and line numbers so you can prove what was touched:
  ```bash
  sudo grep -naE "$CFPAT" -c $(cat /tmp/cf-hits-home.txt) > /mnt/data/incident-2026-08-03/hitmap.txt
  ```
  Do **not** back up the files verbatim — that just creates another copy of the secret. The redaction marker plus the line map is enough to reconstruct what happened.

Create the incident directory first, root-owned and locked down:

```bash
sudo mkdir -p /mnt/data/incident-2026-08-03
sudo chmod 700 /mnt/data/incident-2026-08-03
```

**pm2 logs** — do not `truncate` or `rm` these by hand; pm2 holds the descriptors. Use pm2's own flush, which truncates in place:

```bash
pm2 flush sec-harga-bot
pm2 flush sec-agent
pm2 flush sec-proxy
```

- **Does:** Empties the named app's out and error logs without disturbing the process.
- **Healthy:** `[PM2] Flushing <app>` then the file is 0 bytes. Verify: `ls -la ~/.pm2/logs/ | grep <app>`.
- **If wrong:** If `pm2 flush` reports the app isn't found, list them with `pm2 ls` and match exact names. Flushing all apps at once (`pm2 flush`) is also safe but destroys logs you may want for the Phase 1 diagnostics — flush selectively.
- **Rollback:** None. Flushed logs are gone. This is acceptable: you already recorded the hit map.

**Rotated `.gz` logs** — delete, don't edit:

```bash
sudo find /home/the_bomb/.pm2/logs -name '*.gz' -newermt '2026-08-03 00:00' -print
# review the list, then:
sudo find /home/the_bomb/.pm2/logs -name '*.gz' -newermt '2026-08-03 00:00' -delete
```

- **Does:** Lists then deletes today's rotated logs.
- **Healthy:** The list matches what you'd expect. Rotated logs from before 2026-08-03 00:00 cannot contain a 10:31 leak, so they're untouched.
- **If wrong:** If the list is huge, `pm2-logrotate` is rotating aggressively and you should check its retention setting in Phase 2.
- **Rollback:** None. Accept the loss.

**journald**, if 0.4 found hits:

```bash
sudo journalctl --disk-usage
sudo journalctl --vacuum-time=1d
sudo journalctl --disk-usage
```

- **Does:** Reports journal size, drops everything older than 1 day, reports again. journald cannot selectively delete an entry, so time-based vacuuming is the only lever.
- **Healthy:** Size drops. Re-run the 0.4 journald grep; count should now be 0 or reflect only entries from the last day.
- **If wrong:** The leak was at 10:31 today, so `--vacuum-time=1d` will **not** remove it. If you must remove it, you need `--vacuum-time=1h` run after 11:31, which costs you all of today's journal. Weigh that against the fact that the token is already rotated and journald is root-readable only. Usually: leave it.
- **Rollback:** None. Vacuumed journal entries are gone.

**Container logs**, for any `HIT` from 0.4:

```bash
sudo truncate -s 0 "$(docker inspect -f '{{.LogPath}}' <container>)"
```

- **Does:** Zeroes the json-file log while the container runs. dockerd writes with append, so it keeps working.
- **Healthy:** `docker logs <container>` returns nothing, and the container carries on. New lines appear within a minute for a chatty container.
- **If wrong:** `docker logs` erroring on a malformed line right after truncation is a known cosmetic effect of a partially-written line; it clears on the next log rotation or container restart. It does not affect the container.
- **Rollback:** None.

**Telegram** — delete the message on both sides (your client and the bot's). Then check whether the bot persists messages:

```bash
grep -rlnE 'cfut_' ~/orkes_sec/data ~/orkes/data 2>/dev/null
sudo grep -rlaE "$CFPAT" /var/lib/docker/volumes 2>/dev/null | head
```

- **Does:** Looks for the message stored in a bot-side database or volume.
- **Healthy:** Nothing found.
- **If wrong:** If a bot database holds chat history, that is a durable copy and needs a targeted `UPDATE ... SET text = replace(...)` against that table. Identify the table before writing to it.
- **Rollback:** Dump the affected table before editing it (to `/mnt/data/incident-2026-08-03/`, mode 600).

Note that deleting a Telegram message removes it from clients; Telegram's servers and any third-party client that already synced it are outside your control. This is one more reason rotation was step one.

### 0.6 Audit the adjacent secret stores while you're here

The Cloudflare token is not the only credential on this box, and if one leaked through the chat path, the others are worth a permissions check.

```bash
ls -la ~/.env ~/.claude.json ~/.npmrc 2>/dev/null
ls -la ~/.cloudflared/ ~/.aws/ ~/.docker/ 2>/dev/null
```

- **Does:** Shows ownership and mode on each secret store.
- **Healthy:** Everything `-rw-------` (600) or `drwx------` (700), owned by `the_bomb`.
- **If wrong:** Anything group- or world-readable is a live exposure on a box where the `docker` and `lxd` groups exist and 6 sessions are logged in. Fix immediately:
  ```bash
  chmod 600 ~/.env ~/.claude.json ~/.npmrc 2>/dev/null
  chmod 700 ~/.cloudflared ~/.aws ~/.docker 2>/dev/null
  chmod 600 ~/.cloudflared/*.json ~/.aws/credentials ~/.docker/config.json 2>/dev/null
  ```
- **Rollback:** Tightening permissions on your own dotfiles has no meaningful rollback need. If a service breaks, it was running as a different user and that is itself a finding.

Then look at what's inside each, without printing values:

```bash
# What kinds of secret live in ~/.env — key names only, values stripped
sed -E 's/=.*/=<redacted>/' ~/.env 2>/dev/null

# MCP servers and any inline credentials in the Claude config (57KB)
python3 -c "import json,sys; d=json.load(open('$HOME/.claude.json')); print(json.dumps(list(d.keys()), indent=1))"

# Docker registry auths present (base64, trivially reversible — treat as plaintext)
python3 -c "import json;print(list(json.load(open('$HOME/.docker/config.json')).get('auths',{}).keys()))" 2>/dev/null

# npm auth tokens present?
grep -c '_authToken' ~/.npmrc 2>/dev/null

# Which tunnels have credentials on this box
ls -la ~/.cloudflared/*.json 2>/dev/null
```

- **Does:** Enumerates what credentials exist without displaying them.
- **Healthy:** You recognise every key name, every registry, and every tunnel credential file.
- **If wrong:** `~/.claude.json` in particular tends to accumulate MCP server definitions with API keys inline in `env` blocks — if you find any, move them to `~/.secrets/` (see 0.7) and reference them by env var. A `~/.cloudflared/*.json` for a tunnel you no longer run should be deleted; those are long-lived credentials that grant inbound reach to this host. Note that `harga.work` (→3647) and `yellowpages.zeidgeist.com` (→3636) are live tunnels — leave those alone.
- **Rollback:** None needed (read-only inspection).

### 0.7 Prevent recurrence

Two changes. Both matter; the second is the one that would have prevented today.

**Change 1 — a secret ingestion path that isn't chat.**

```bash
mkdir -p ~/.secrets && chmod 700 ~/.secrets
# one secret per file, filename is the env var name
printf '%s' '<new token value>' > ~/.secrets/CF_PAGES_TOKEN
chmod 600 ~/.secrets/CF_PAGES_TOKEN
```

The agent tooling should load these into the **environment of the subprocess that needs them**, never into the prompt. When you want the agent to use a credential, you tell it the *name*: "deploy using CF_PAGES_TOKEN". The value never enters the conversation, never enters the prompt, never enters `ps`.

Environment is strictly better than argv here: `/proc/<pid>/environ` is readable only by the owner and root, while `/proc/<pid>/cmdline` is world-readable. That difference is the entire mechanism of today's leak. Any wrapper that currently does `subprocess.run(["wrangler", "deploy", "--api-token", tok])` should become `subprocess.run(["wrangler","deploy"], env={**os.environ, "CLOUDFLARE_API_TOKEN": tok})`.

- **Does:** Gives you a place to put secrets that is not a chat message.
- **Healthy:** `ls -la ~/.secrets` shows 700 on the directory, 600 on every file.
- **If wrong:** If the agent can't read them, check it runs as `the_bomb` (`pm2 jlist | python3 -c "import json,sys;[print(a['name'], a['pm2_env'].get('uid')) for a in json.load(sys.stdin)]"`).
- **Rollback:** `rm -rf ~/.secrets` and revert to the old path. Don't.

**Change 2 — redact at the point where Telegram chat is concatenated into the agent prompt.**

Find the concatenation site:

```bash
grep -rn "context/chat" ~/orkes ~/orkes_sec --include='*.py' --include='*.js' --include='*.ts' \
  --exclude-dir=node_modules --exclude-dir=.venv | head -30
```

- **Does:** Locates the code that assembles chat history into the prompt.
- **Healthy:** A small number of files — a prompt builder and a chat reader.
- **If wrong:** If the search is noisy, look for where `claude -p` is invoked and trace backwards from the argument construction.
- **Rollback:** None needed (read-only).

Then insert a redaction pass. Drop this in as a module and call it on every chat message before it enters the prompt, and on every agent output before it goes back to Telegram — leaks travel in both directions:

```python
# ~/orkes/lib/redact.py  (mirror to ~/orkes_sec/lib/redact.py)
import re

_PATTERNS = [
    (re.compile(r'cfut_[A-Za-z0-9_-]{20,}'),                          'CF_USER_TOKEN'),
    (re.compile(r'\bv1\.0-[A-Za-z0-9]{20,}-[A-Za-z0-9]{20,}'),        'CF_ORIGIN_CA_KEY'),
    (re.compile(r'sk-ant-[A-Za-z0-9_\-]{20,}'),                       'ANTHROPIC_KEY'),
    (re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}'),                     'GITHUB_TOKEN'),
    (re.compile(r'\bglpat-[A-Za-z0-9_\-]{20,}'),                      'GITLAB_PAT'),
    (re.compile(r'\bxox[abprs]-[A-Za-z0-9-]{10,}'),                   'SLACK_TOKEN'),
    (re.compile(r'\bAKIA[0-9A-Z]{16}\b'),                             'AWS_ACCESS_KEY_ID'),
    (re.compile(r'\b[0-9]{8,10}:AA[A-Za-z0-9_\-]{30,}'),              'TELEGRAM_BOT_TOKEN'),
    (re.compile(r'\bey[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}'), 'JWT'),
    (re.compile(r'-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----'), 'PRIVATE_KEY'),
    (re.compile(r'(?i)\b(?:api[_-]?key|secret|password|passwd|token)\s*[:=]\s*["\']?([A-Za-z0-9_\-]{24,})'), 'GENERIC_SECRET'),
]

def redact(text: str) -> tuple[str, list[str]]:
    """Returns (redacted_text, list_of_kinds_found). Never logs the value."""
    found = []
    for pat, kind in _PATTERNS:
        text, n = pat.subn(f'[REDACTED:{kind}]', text)
        if n:
            found.extend([kind] * n)
    return text, found
```

Wire it so that a hit also **alerts** you on Telegram — "I redacted what looks like a CF_USER_TOKEN from your message; send it as a file in ~/.secrets instead" — so you find out immediately rather than two hours later.

- **Does:** Stops secrets shaped like known credential formats from reaching the prompt, `ps`, or the context files.
- **Healthy:** Paste a fake `cfut_` + 30 random characters into Telegram and confirm the agent's context file shows `[REDACTED:CF_USER_TOKEN]` and that the string never appears in `ps aux`.
- **If wrong:** The `GENERIC_SECRET` pattern will produce false positives on long identifiers (tender IDs like `GEP-RFP-000000188015` are safe — they contain hyphens but are under 24 chars of the required class; check anyway). If it over-redacts and breaks agent work, drop that last pattern and keep the specific ones — the specific patterns carry almost all the value.
- **Rollback:** Remove the `redact()` call from the prompt builder. Keep the module.

**Change 3 (cheap, do it too) — a repo-level secret scanner:**

```bash
# scan on demand; wire into a pre-commit hook per repo afterwards
docker run --rm -v ~/orkes_sec:/repo:ro zricethezav/gitleaks:latest detect --source=/repo --no-git -v | tail -30
```

- **Does:** Scans a working tree for credential patterns beyond your own list.
- **Healthy:** `no leaks found`.
- **If wrong:** Triage each finding; add `.gitleaksignore` entries only for confirmed false positives.
- **Rollback:** None; read-only scan.

### Phase 0 exit criteria

- [ ] Token rolled or deleted at Cloudflare, scope recorded.
- [ ] Audit log reviewed 10:31 UTC → rotation; no unexplained activity.
- [ ] `sudo grep -rlaE "$CFPAT" /home/the_bomb ...` returns nothing.
- [ ] `sudo grep -laE "$CFPAT" /proc/[0-9]*/cmdline` returns nothing (may require waiting for the current agent step to finish).
- [ ] pm2 logs flushed; today's `.gz` rotations deleted.
- [ ] `~/.env`, `~/.claude.json`, `~/.npmrc`, `~/.cloudflared`, `~/.aws`, `~/.docker` all 600/700.
- [ ] `~/.secrets/` exists; redaction module deployed to both `~/orkes` and `~/orkes_sec` and verified with a fake token.

---

## Phase 1 — read-only diagnostics

Nothing here changes state. All of it is safe to run right now, under load, with everything live. The point of this phase is that **three of the four remaining issues have a plausible "do nothing" answer**, and you cannot tell which without measuring.

### 1.0 Capture a baseline first

Before any change in Phase 2 or 3, snapshot what "now" looks like so you can prove what you altered and restore it.

```bash
BASE=/mnt/data/runbook-2026-08-03/baseline
mkdir -p "$BASE"
{
  date -u
  echo '--- uname'; uname -a
  echo '--- uptime'; uptime
  echo '--- free'; free -h
  echo '--- df'; df -hT
  echo '--- swap'; swapon --show
  echo '--- mounts'; findmnt -no TARGET,SOURCE,FSTYPE,OPTIONS
  echo '--- sysctl vm'; sysctl -a 2>/dev/null | grep -E '^vm\.(swappiness|vfs_cache_pressure|overcommit|min_free_kbytes|dirty_)'
} > "$BASE/system.txt"

ps auxwww --sort=-rss | head -60          > "$BASE/ps-by-rss.txt"
systemctl list-units --type=service --state=running --no-pager > "$BASE/services.txt"
docker ps -a --format '{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' > "$BASE/containers.txt"
docker inspect -f '{{.Name}} restart={{.HostConfig.RestartPolicy.Name}} max={{.HostConfig.RestartPolicy.MaximumRetryCount}}' $(docker ps -aq) > "$BASE/restart-policies.txt"
docker network ls                          > "$BASE/networks.txt"
docker volume ls                           > "$BASE/volumes.txt"
docker system df -v                        > "$BASE/docker-df.txt"
pm2 jlist                                  > "$BASE/pm2.json"
pm2 ls --no-color                          > "$BASE/pm2.txt"
crontab -l                                 > "$BASE/crontab.txt" 2>&1
sudo ss -tlnp                              > "$BASE/listeners.txt"
nvidia-smi                                 > "$BASE/gpu.txt" 2>&1
who -u                                     > "$BASE/who.txt"
last -n 30                                 > "$BASE/last.txt"
ls -la "$BASE"
```

- **Does:** Writes a full picture of current state to `/mnt/data` (which has 852G free, so this costs nothing on root).
- **Healthy:** Every file non-empty. `containers.txt` has 45 lines. `services.txt` shows 28 running services.
- **If wrong:** `pm2 jlist` failing means the pm2 daemon isn't reachable as your user — check you're `the_bomb` and not root; pm2 is per-user. `nvidia-smi` failing while `nvidia-persistenced` runs is worth a separate look, but doesn't block this runbook.
- **Rollback:** None needed (read-only, writes only to a new directory).

**The most important file here is `restart-policies.txt`.** Read it now:

```bash
grep -v 'restart=always\|restart=unless-stopped' "$BASE/restart-policies.txt"
```

- **Does:** Lists containers that will **not** come back on their own if dockerd restarts.
- **Healthy:** Empty, or a short list you have a `docker compose up -d` for.
- **If wrong:** Every container listed here needs a documented start command written down *before* Phase 3.1 (the docker data-root move), because that step restarts the daemon and anything with `restart=no` stays down. Find its compose file: `docker inspect -f '{{index .Config.Labels "com.docker.compose.project.config_files"}}' <name>`.
- **Rollback:** None needed (read-only).

Also confirm who's logged in — it bears directly on the Phase 0 `ps` exposure assessment:

```bash
who -u; echo '---'; awk -F: '$3>=1000 && $3<65534 {print $1, $3, $6}' /etc/passwd
```

- **Does:** Shows the 6 active sessions and every non-system local account.
- **Healthy:** All 6 sessions are yours (same user, from Tailscale or LAN addresses you recognise), and `the_bomb` uid 1000 is the only human account.
- **If wrong:** Any account you don't recognise, or any session from an unfamiliar address, escalates Phase 0 to a full compromise investigation. Also check `sudo grep -c . /home/the_bomb/.ssh/authorized_keys` and read the keys.
- **Rollback:** None needed (read-only).

### 1.1 Memory: is there actually pressure?

This is the diagnostic that decides whether issue #3 needs any action at all.

**Pressure stall information — the single best signal:**

```bash
cat /proc/pressure/memory
cat /proc/pressure/io
```

- **Does:** Reports the percentage of time tasks were stalled waiting on memory (`some` = at least one task stalled; `full` = all tasks stalled) over 10s, 60s, and 300s windows.
- **Healthy:** `full avg60` below ~1.0 and `some avg60` below ~5.0. That means the box is not meaningfully waiting on memory, and the 9.8G of swap is parked pages from an earlier spike — **which requires no action**.
- **If wrong:** `full avg60` above 10 means real, sustained memory stalls and Phase 2's reclaim work becomes a priority rather than an option. `some avg300` high with `full` near zero means one or two processes are stalling while the rest of the box is fine — find which with the per-process swap listing below.
- **Rollback:** None needed (read-only).

**Is swap actively moving, or is it just occupied?**

```bash
vmstat 5 6
```

- **Does:** Six samples, 5 seconds apart. Watch the `si` (swap in) and `so` (swap out) columns, in KB/s.
- **Healthy:** `si` and `so` both at or near `0` across all six samples. That is the definitive answer that 9.8G of swap is *stale*, not *thrashing*. The pages went out during a spike and nothing has asked for them since. Leaving them there is correct behaviour.
- **If wrong:** Sustained `si`/`so` in the thousands means live thrashing — the box is paying disk latency for every memory access to those regions. That changes Phase 2 from optional to required, and makes the abandoned `opencode` reclaim urgent. Also check `r` (runnable) and `b` (blocked): a high `b` with high `si` confirms processes blocked on swap I/O.
- **Rollback:** None needed (read-only).

**Cumulative swap activity since boot** — cross-check for the above:

```bash
grep -E 'pswpin|pswpout|pgmajfault|pgscan_|pgsteal_' /proc/vmstat
```

- **Does:** Lifetime counters. Run it, wait 10 minutes, run it again, and diff.
- **Healthy:** `pswpin` barely moves between the two readings. `pgmajfault` growing slowly is normal (it counts every file-backed page fault from disk too).
- **If wrong:** `pswpin` climbing by tens of thousands over 10 minutes confirms active swap-in traffic even if `vmstat`'s instantaneous samples looked calm.
- **Rollback:** None needed (read-only).

**What is actually swapped, per process:**

```bash
cat > /tmp/swaptop.sh <<'EOF'
#!/bin/sh
for f in /proc/[0-9]*/smaps_rollup; do
  pid=${f#/proc/}; pid=${pid%/smaps_rollup}
  sw=$(awk '/^Swap:/ {print $2; exit}' "$f" 2>/dev/null)
  [ -n "$sw" ] || continue
  [ "$sw" -gt 51200 ] || continue
  cmd=$(tr '\000' ' ' < /proc/$pid/cmdline 2>/dev/null | cut -c1-110)
  printf '%9s kB  pid=%-9s %s\n' "$sw" "$pid" "$cmd"
done | sort -rn
EOF
chmod +x /tmp/swaptop.sh
sudo /tmp/swaptop.sh | head -30
sudo /tmp/swaptop.sh | awk '{s+=$1} END {printf "total accounted: %.1f GiB\n", s/1048576}'
```

- **Does:** Lists every process with more than 50MB swapped out, largest first, with its command line. Then totals it.
- **Healthy:** The total lands near 9.8 GiB and is dominated by processes you'd expect to have cold pages — long-idle `opencode` instances, old container processes, the four-month-old stacks. Cold pages belonging to idle processes are *exactly what swap is for*.
- **If wrong:** If the bulk of swap belongs to something on the critical path (`embed_server.py`, `sec-proxy`, a Postgres backend serving live traffic), that process is paying disk latency for its working set and is the reclaim target. If the total is well under 9.8 GiB, the remainder belongs to tmpfs/shmem pages that were swapped — check `grep -E 'Shmem|SwapCached' /proc/meminfo`.
- **Rollback:** None needed (read-only).

Optionally, `smem` gives the same view with proportional set size, which is more honest for processes sharing memory:

```bash
sudo apt-get install -y smem && sudo smem -rs swap -c "pid user command swap uss pss rss" | head -25
```

- **Does:** Installs `smem` (a small Python script, ~200KB) and sorts processes by swap.
- **Healthy:** Same story as the script above, plus USS/PSS columns that tell you how much would actually be freed by killing each process.
- **If wrong:** If you'd rather not install anything, skip it — `/tmp/swaptop.sh` covers the essential question. Note the `apt-get install` is the first mutation in this runbook; it is trivially reversible with `apt-get remove smem`.
- **Rollback:** `sudo apt-get remove -y smem`.

**Anonymous memory vs page cache:**

```bash
grep -E '^(MemTotal|MemFree|MemAvailable|Buffers|Cached|SwapCached|Active\(anon\)|Inactive\(anon\)|AnonPages|Mapped|Shmem|SReclaimable|SUnreclaim|Committed_AS|CommitLimit|Dirty|Writeback)' /proc/meminfo
```

- **Does:** Breaks 30Gi down into what's actually holding it.
- **Healthy:** `AnonPages` around 11–13 GiB (matching the 12Gi `used` from `free -h`), `Cached` around 18 GiB, `MemAvailable` ~18 GiB. `Committed_AS` below `CommitLimit`. `Dirty` in the low hundreds of MB.
- **If wrong:** `Committed_AS` far above `CommitLimit` means processes have promised themselves more memory than exists and an allocation failure is possible under a spike. `Shmem` in the multiple-GB range points at `/dev/shm` or tmpfs usage — but `/dev/shm` shows only 1.1M used, so a large `Shmem` would mean container tmpfs mounts. `SUnreclaim` above 2GB suggests a kernel-side leak (check `sudo slabtop -o -s c | head -15`).
- **Rollback:** None needed (read-only).

**Swappiness and related tunables:**

```bash
sysctl vm.swappiness vm.vfs_cache_pressure vm.min_free_kbytes vm.overcommit_memory vm.overcommit_ratio
```

- **Does:** Reads the current tuning.
- **Healthy:** Ubuntu defaults — `swappiness=60`, `vfs_cache_pressure=100`, `overcommit_memory=0`.
- **If wrong:** `swappiness=60` on a box with heavy page cache demand (45 containers plus several Postgres instances plus model loading) does bias the kernel toward swapping anonymous pages. Lowering it to 10 is defensible — but **only after** Phase 2 has reduced the anonymous working set. Lowering swappiness while free RAM is 647Mi tells the kernel to evict page cache instead of swapping, which will make every Postgres and every container read slower. Order matters: free memory first, then tune.
- **Rollback:** Record the current values now; they go in `$BASE/system.txt`.

**Where does swap actually live?** This matters for Phase 3 more than most people expect:

```bash
swapon --show
ls -la /swap.img /swapfile 2>/dev/null
sudo filefrag /swap.img 2>/dev/null | tail -1
```

- **Does:** Shows the swap device or file, its size, and how much is used.
- **Healthy:** One entry, 15Gi, 9.8G used.
- **If wrong (and this is the likely case):** If swap is a **file on `/`** (`/swap.img` is Ubuntu's default), then 15G of your 772G of root usage is the swap file. Moving it to the NVMe at `/mnt/data` frees 15G on root and puts swap on faster storage. That's Phase 3.3. If swap is an LVM logical volume, moving it is more involved and probably not worth it.
- **Rollback:** None needed (read-only).

### 1.2 Is `embed_server.py` leaking?

pid 2652772, 1.78G RSS, 255% CPU, 1946 CPU-minutes. Started Aug 02, so roughly 1.4–1.6 days of wall time. 1946 CPU-minutes over ~2100 wall-minutes is close to one full core sustained — that is a busy service, not necessarily a broken one. Distinguish "working hard" from "leaking" by watching RSS over time under known load.

```bash
EPID=2652772
grep -E '^(VmRSS|VmSwap|VmData|Threads)' /proc/$EPID/status
ls /proc/$EPID/fd | wc -l
ls /proc/$EPID/task | wc -l
awk '{print "utime+stime ticks:", $14+$15}' /proc/$EPID/stat
```

- **Does:** Baseline snapshot: resident size, swapped size, heap size, thread count, open file descriptor count, cumulative CPU.
- **Healthy:** `Threads` matching your worker configuration (a handful to low tens). FD count stable in the low hundreds.
- **If wrong:** FD count in the thousands and climbing is a descriptor leak, which usually accompanies a memory leak — check what they are: `sudo ls -l /proc/$EPID/fd | awk '{print $NF}' | sort | uniq -c | sort -rn | head`. Thread count in the hundreds means a thread leak.
- **Rollback:** None needed (read-only).

Then sample for an hour:

```bash
EPID=2652772
for i in $(seq 1 12); do
  printf '%s  RSS=%s  SWAP=%s  DATA=%s  THR=%s  FD=%s\n' \
    "$(date -u +%H:%M:%S)" \
    "$(awk '/VmRSS/{print $2}' /proc/$EPID/status)" \
    "$(awk '/VmSwap/{print $2}' /proc/$EPID/status)" \
    "$(awk '/VmData/{print $2}' /proc/$EPID/status)" \
    "$(ls /proc/$EPID/task | wc -l)" \
    "$(ls /proc/$EPID/fd 2>/dev/null | wc -l)"
  sleep 300
done | tee /mnt/data/runbook-2026-08-03/embed-rss-trend.txt
```

- **Does:** Twelve samples over an hour, logged to `/mnt/data`.
- **Healthy:** RSS oscillating within a band — rising while batches are processed, falling between them. A ceiling that it returns to is a healthy allocator, not a leak.
- **If wrong:** Monotonic growth with no plateau across all 12 samples is a leak. `VmData` growing while `VmRSS` stays flat means it's allocating and the pages are going straight to swap. Either way, the fix is a restart (Phase 3.4) plus a `max_memory_restart` guard in pm2, and separately a look at the code — the usual culprit in an embedding server is accumulating results or model outputs in a module-level list, or a torch tensor cache that never releases.
- **Rollback:** None needed (read-only). Kill the loop with Ctrl-C at any time.

Also check the GPU side, since `ollama` and this embed server may be competing:

```bash
nvidia-smi --query-compute-apps=pid,used_memory --format=csv
nvidia-smi --query-gpu=memory.total,memory.used,utilization.gpu --format=csv
```

- **Does:** Shows which processes hold GPU memory and how much.
- **Healthy:** `ollama` and possibly `embed_server.py` / `ocr_server.py` holding GPU memory, total used comfortably under total available.
- **If wrong:** GPU memory near-full will cause CUDA allocations to fall back to host RAM in some frameworks, which would explain host memory pressure that looks unexplained. If `embed_server.py` holds GPU memory that keeps growing, the leak is on the GPU side and the host RSS is a symptom.
- **Rollback:** None needed (read-only).

### 1.3 Are the three `opencode` processes abandoned?

Candidates: **4131680** (started Aug 01, 703M RSS, 51 CPU-min), **93395** (Jul 31, 599M, 94 CPU-min), **321500** (Jul 31, 586M, 72 CPU-min). Together ~1.9G RSS plus whatever they've swapped. Do not kill anything until all five checks below agree.

```bash
for p in 4131680 93395 321500; do
  echo "=== pid $p"
  ps -o pid,ppid,pgid,sid,tty,stat,lstart,etime,times,%cpu,%mem,rss,wchan:22,cmd -p "$p" --no-headers 2>/dev/null || { echo "gone"; continue; }
  echo "  children: $(pgrep -P "$p" | tr '\n' ' ')"
  echo "  sockets:  $(sudo ls -l /proc/$p/fd 2>/dev/null | grep -c socket)"
  echo "  cwd:      $(sudo readlink /proc/$p/cwd 2>/dev/null)"
done
```

- **Does:** For each pid: parent, session, controlling terminal, state, start time, cumulative CPU, wait channel, child processes, open socket count, and working directory.
- **Healthy (i.e. safe to kill):** `TTY` is `?` (no controlling terminal, so nobody is looking at it), `PPID` is `1` (reparented to init — its launching shell is gone), `STAT` is `Sl` or `S` (sleeping, not running), no children, and CPU accumulation has stopped (see the delta check below).
- **If wrong:** A real TTY like `pts/3` means it's attached to a live session — check `who -u` to see whose. A PPID pointing at a live tmux or screen server means it's in a detached session you may return to: confirm with `tmux list-sessions` and `tmux list-panes -a -F '#{session_name} #{pane_pid} #{pane_current_command}'`. Non-zero children means it's supervising something. Any of these and you leave it alone.
- **Rollback:** None needed (read-only).

**CPU delta over 60 seconds** — the strongest evidence of abandonment:

```bash
for p in 4131680 93395 321500; do
  a=$(awk '{print $14+$15}' /proc/$p/stat 2>/dev/null)
  echo "$p before=$a"
done
sleep 60
for p in 4131680 93395 321500; do
  b=$(awk '{print $14+$15}' /proc/$p/stat 2>/dev/null)
  echo "$p after=$b"
done
```

- **Does:** Reads cumulative user+system CPU ticks before and after a 60-second gap.
- **Healthy (safe to kill):** `after` equals `before` exactly. Zero ticks in 60 seconds means the process did literally nothing.
- **If wrong:** Any increase means it's doing work. Even a small increase — an idle event loop still consumes a few ticks per minute, so a delta under ~50 ticks (0.5s) is consistent with an idle-but-alive process, while a delta in the thousands is active work. If it's merely idle-alive with no TTY and no children, it's still a reclaim candidate, but check network activity next.
- **Rollback:** None needed (read-only).

**Network activity** — an `opencode` session with a live connection to a language model API or an editor is not abandoned:

```bash
for p in 4131680 93395 321500; do
  echo "=== $p"
  sudo ss -tanp 2>/dev/null | grep "pid=$p," || echo "  no tcp sockets"
done
```

- **Does:** Lists TCP sockets owned by each pid.
- **Healthy (safe to kill):** No sockets, or only sockets in `CLOSE-WAIT` / `FIN-WAIT` (dead connections nobody cleaned up).
- **If wrong:** An `ESTAB` connection to an external address means it may be mid-request. Wait and re-check.
- **Rollback:** None needed (read-only).

**Is it holding a lock or a file another process needs:**

```bash
for p in 4131680 93395 321500; do
  echo "=== $p  cwd=$(sudo readlink /proc/$p/cwd)"
  sudo ls -l /proc/$p/fd 2>/dev/null | grep -vE 'socket|pipe|anon_inode|/dev/null' | awk '{print $NF}' | sort -u | head -10
done
```

- **Does:** Shows which real files each process has open, and where it was working.
- **Healthy:** Files under a project directory you're no longer working in. If the `cwd` is a project you finished days ago, that's your confirmation.
- **If wrong:** An open `.git/index.lock` or a `.db` file being held means killing the process could leave a stale lock. Note the path so you can clean it up afterwards.
- **Rollback:** None needed (read-only).

Record the verdict for each pid before proceeding to Phase 2.3.

### 1.4 pm2 and cgroup memory limits

If a leak eventually kills something, you want it to be a bounded, automatic restart rather than an OOM kill at a random moment.

```bash
pm2 jlist | python3 -c "
import json,sys
for a in json.load(sys.stdin):
    e = a.get('pm2_env', {})
    m = a.get('monit', {})
    print(f\"{a['name']:24} status={e.get('status','?'):8} rss={m.get('memory',0)/1048576:8.1f}M cpu={m.get('cpu',0):5.1f}% restarts={e.get('restart_time',0):4} max_mem={e.get('max_memory_restart') or '-'}\")
"
```

- **Does:** Tabulates every pm2 app with its memory, CPU, restart count, and whether a memory ceiling is configured.
- **Healthy:** Every long-running app has a `max_memory_restart`. Restart counts low and stable.
- **If wrong:** `max_mem=-` on everything is the common case and is what lets a leak run to OOM. Setting one is a Phase 2 change with a caveat: `max_memory_restart` restarts the app *when it crosses the threshold*, which for a `claude -p` agent loop means possibly mid-step. Set it generously (e.g. 2G for `sec-agent`) so it only fires on a genuine runaway, and check whether the agent loop has step-boundary checkpointing before relying on it. A restart count climbing steadily is an app that's already crash-looping — investigate that app's logs first.
- **Rollback:** None needed (read-only).

```bash
systemctl show pm2-the_bomb -p MemoryCurrent -p MemoryMax -p MemoryHigh -p TasksCurrent -p TasksMax
systemd-cgtop -1 -m --depth=2 2>/dev/null | head -25
```

- **Does:** Shows the pm2 service's cgroup memory accounting and limits, then a one-shot snapshot of memory by cgroup across the box.
- **Healthy:** `MemoryMax=infinity` (no limit — fine for a trusted workload), and `systemd-cgtop` showing a sane split between `system.slice` (the 28 services plus docker), `user.slice`, and the docker cgroups.
- **If wrong:** If `MemoryMax` is set and `MemoryCurrent` is near it, pm2's children are being reclaimed hard by the kernel and that alone explains the swap. `systemd-cgtop` showing one docker cgroup dominating identifies which container stack to look at first.
- **Rollback:** None needed (read-only).

Per-container memory, which `systemd-cgtop` won't name usefully:

```bash
docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}\t{{.NetIO}}\t{{.BlockIO}}' \
  | sort -k2 -h -r | head -25
```

- **Does:** One-shot resource snapshot of all 45 containers, sorted by memory.
- **Healthy:** The Postgres containers and meilisearch at the top (databases use memory deliberately), everything else modest.
- **If wrong:** A container from a stack you haven't touched in 4 months sitting near the top is a straightforward reclaim candidate. Note that `docker stats` counts page cache in `MemUsage`, so a Postgres showing 2G may be mostly cache the kernel will hand back on demand — don't over-react to it. `NetIO` and `BlockIO` here are **cumulative since container start**, which makes them a useful activity signal in 1.6.
- **Rollback:** None needed (read-only).

### 1.5 Disk: where did 772G go?

Measure before deleting. The rule for this host is **relocate, don't delete** — `/mnt/data` has 852G free at 5% used, so almost nothing genuinely needs to be destroyed.

**Top-level, without crossing into `/mnt/data`:**

```bash
sudo du -x -h -d1 / 2>/dev/null | sort -h | tail -20
```

- **Does:** Size of each top-level directory on the root filesystem only (`-x` stops it descending into other mounts).
- **Healthy:** `/var` and `/home` dominating, everything else small.
- **If wrong:** If the numbers sum to far less than 772G, you have space consumed by **deleted-but-still-open files** — see the `lsof +L1` check below. That is a classic and it will make every other measurement look wrong.
- **Rollback:** None needed (read-only).

**Deleted files still held open** — check this early, it explains otherwise-impossible arithmetic:

```bash
sudo lsof -nP +L1 2>/dev/null | awk 'NR==1 || $7+0 > 104857600' | head -20
```

- **Does:** Lists open files with zero directory links (deleted but still consuming blocks), filtered to those over 100MB.
- **Healthy:** Empty, or one or two small ones.
- **If wrong:** A multi-GB deleted-but-open file means a process is holding space you think you freed. The space returns only when that process closes the descriptor or exits. If it's a log file someone `rm`'d instead of truncating, the fix is to restart that process (which means the window) — or, if you can identify the fd, truncate through `/proc`: `sudo truncate -s 0 /proc/<pid>/fd/<n>`. That last one is safe and immediate and needs no restart.
- **Rollback:** None needed (read-only, unless you truncate).

**The big four consumers, measured individually:**

```bash
echo '--- docker'
docker system df
sudo du -sh /var/lib/docker 2>/dev/null
echo '--- journald'
journalctl --disk-usage
echo '--- postgres (host, not containers)'
sudo du -sh /var/lib/postgresql 2>/dev/null
echo '--- home'
sudo du -sh /home/the_bomb 2>/dev/null
echo '--- apt/snap'
sudo du -sh /var/cache/apt /var/lib/snapd 2>/dev/null
```

- **Does:** Sizes each of the usual suspects.
- **Healthy:** A distribution you can explain. On a box running 45 containers built from 15+ projects, `/var/lib/docker` in the 100–300G range is entirely normal.
- **If wrong:** `/var/lib/snapd` over 10G means old snap revisions are accumulating (`snap list --all | awk '/disabled/{print $1, $3}'` then `sudo snap remove <name> --revision=<rev>` — safe, no restart). `/var/cache/apt` over 2G is fixed by `sudo apt-get clean` — safe, no restart, nothing depends on it.
- **Rollback:** None needed (read-only).

**Docker, broken down:**

```bash
docker system df -v | head -80
echo '--- images not used by any container'
docker images --filter dangling=true --format '{{.Repository}}:{{.Tag}} {{.Size}}' | head -20
echo '--- build cache'
docker builder du 2>/dev/null | tail -5
echo '--- container log sizes'
for c in $(docker ps -aq); do
  p=$(docker inspect -f '{{.LogPath}}' "$c")
  [ -f "$p" ] && printf '%10s  %s\n' "$(sudo du -h "$p" | cut -f1)" "$(docker inspect -f '{{.Name}}' "$c")"
done | sort -h -r | head -15
```

- **Does:** Splits docker's footprint into images, containers, local volumes, build cache; identifies dangling images; then sizes each container's json log.
- **Healthy:** `RECLAIMABLE` on the images line is the number that matters. Container logs each under ~100MB.
- **If wrong:** A container log over 1GB means no log rotation is configured on the daemon — very likely here, since `daemon.json` probably doesn't set `log-opts`. Fixing it properly requires a daemon restart (Phase 3.1, bundled with the data-root move); truncating is the no-restart stopgap (Phase 2.6). Build cache in the tens of GB is safe to prune with an age filter (Phase 2.5).
- **Rollback:** None needed (read-only).

**Home directory, ranked:**

```bash
sudo du -h -d1 /home/the_bomb 2>/dev/null | sort -h | tail -30
```

- **Does:** Ranks all 178 entries in `$HOME` by size.
- **Healthy:** `.cache`, `miniconda3`, `.ollama`, `android-sdk`, `google-cloud-sdk`, and the project directories at the top.
- **If wrong:** Anything unexpected in the top 10 gets investigated before it gets moved.
- **Rollback:** None needed (read-only).

**Model weights and caches specifically** — these are the big, movable, redownloadable-but-slow items:

```bash
for d in ~/.ollama ~/.cache/huggingface ~/.cache/torch ~/.EasyOCR ~/.crawl4ai \
         ~/.cache/uv ~/.cache/pip ~/.npm ~/.cache/ms-playwright ~/.cache/puppeteer \
         ~/.cargo ~/.rustup ~/.nvm ~/miniconda3 ~/android-sdk ~/google-cloud-sdk \
         ~/swift-6.0.3 ~/pg_data; do
  [ -e "$d" ] && printf '%8s  %s\n' "$(sudo du -sh "$d" 2>/dev/null | cut -f1)" "$d"
done | sort -h -r
```

- **Does:** Sizes every known cache and toolchain directory in one pass.
- **Healthy:** You'll typically find `~/.ollama` (models — often 20–80G), `~/.cache/huggingface` (10–60G), `~/miniconda3` (5–15G), `~/android-sdk` (10–30G) as the leaders.
- **If wrong:** `~/pg_data` being large is important — that's a Postgres data directory in `$HOME` on the root filesystem. Establish which instance owns it (`sudo lsof +D ~/pg_data | head`) before touching it. If it belongs to a container via bind mount, moving it is a Phase 3 operation for that stack.
- **Rollback:** None needed (read-only).

**venvs and node_modules** — many small directories that add up:

```bash
sudo find /home/the_bomb -maxdepth 4 -type d \( -name node_modules -o -name .venv -o -name venv \) -prune -print0 2>/dev/null \
  | xargs -0 -r sudo du -sh 2>/dev/null | sort -h -r | head -25
sudo find /home/the_bomb -maxdepth 4 -type d \( -name node_modules -o -name .venv -o -name venv \) -prune -print 2>/dev/null | wc -l
```

- **Does:** Sizes the 25 largest, then counts how many there are.
- **Healthy:** Individually 200MB–2G; the count tells you the aggregate story.
- **If wrong:** If the count is in the dozens and the aggregate is 50G+, the highest-value action is deleting `node_modules` in projects you're not actively building (they regenerate from lockfiles) — but **not** the venvs backing running services (`~/orkes/.venv`, `~/orkes_sec/.venv`, `~/Unlimited-OCR/.venv` are all in use right now by live processes; deleting them kills those services immediately).
- **Rollback:** `npm ci` regenerates any deleted `node_modules` from `package-lock.json`. Verify the lockfile exists before deleting.

**The loose files in `$HOME`:**

```bash
ls -lah ~/ | awk '$5 ~ /[0-9]+M|[0-9]+G/ {print $5, $9}' | sort -h -r
sudo lsof -- ~/n8n.log ~/bocra.tar.gz ~/cbaas-server.tar.gz 2>/dev/null
```

- **Does:** Lists loose files over ~1MB, then checks whether anything holds the big ones open.
- **Healthy:** `bocra.tar.gz` 404M, `n8n.log` 91M, `cbaas-server.tar.gz` 92M, the 36M heapsnapshot, `RFP-000000168142.zip` 11M — about 634M total, and `lsof` returns nothing (no live writers).
- **If wrong:** If `lsof` shows n8n still writing to `n8n.log`, don't move it — truncate it instead (Phase 2.4) or you'll break the writer's path assumption.
- **Rollback:** None needed (read-only).

**Growth rate** — this tells you how much time you have. Run it now and again in 24 hours:

```bash
date -u; df -h / | tail -1
```

- **Does:** One data point in a two-point measurement.
- **Healthy:** Less than ~1G/day of growth. At that rate, 126G free is four months of runway and none of this is urgent.
- **If wrong:** 5G/day or more means under a month of runway and Phase 3.1 (the docker data-root move) should be scheduled this week rather than "sometime". Find the source by re-running the docker and journald sizing 24 hours apart and diffing.
- **Rollback:** None needed (read-only).

### 1.6 `buzz-keycloak`: diagnose before you invest

Two questions, in this order: **is it broken**, and **does anyone care**. The second question is the important one, because authentik is already running as the SSO layer and is fully healthy.

**Is anything actually talking to it?**

```bash
docker port buzz-keycloak
docker inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{$v.IPAddress}}{{"\n"}}{{end}}' buzz-keycloak
sudo ss -tnp state established | grep -E ':(8080|8443|9000)\b' | head -20
```

- **Does:** Shows published ports, container IPs, and any established TCP connections on Keycloak's usual ports.
- **Healthy for "in use":** Established connections from application containers.
- **Healthy for "not in use":** No published ports at all, or published ports with zero established connections. Note the recon shows the management port 9000 is *exposed but not published* — meaning it's reachable inside the buzz network but not from the host, which is itself a strong hint about the healthcheck failure below.
- **If wrong:** Absence of connections at one instant isn't proof. Do the Postgres transaction-delta check next.
- **Rollback:** None needed (read-only).

**Transaction delta on its database** — the honest "is anything using this" test. Run twice, ten minutes apart:

```bash
docker exec buzz-postgres psql -U postgres -Atc \
  "select now(), datname, xact_commit, xact_rollback, numbackends
   from pg_stat_database where datname not in ('template0','template1','postgres')"
```

- **Does:** Reads committed transaction counters and current backend count per database.
- **Healthy for "in use":** `xact_commit` climbing by a meaningful amount between the two readings, and `numbackends` > 0 for the Keycloak database.
- **Healthy for "dead":** `xact_commit` identical or up by a handful (autovacuum and Keycloak's own internal housekeeping produce a small trickle even with zero users), `numbackends` reflecting only Keycloak's idle pool.
- **If wrong:** If `psql -U postgres` fails, find the right user: `docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' buzz-postgres | grep -i postgres_user`. If the container's Postgres is on 5437 published, you can also reach it from the host.
- **Rollback:** None needed (read-only).

**Who references it in config:**

```bash
grep -rliE 'keycloak|realms/|/auth/realms' ~/ \
  --include='*.env' --include='*.yml' --include='*.yaml' --include='*.json' \
  --include='*.toml' --include='*.conf' --include='Caddyfile' \
  --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=.git \
  --exclude-dir=.cache --exclude-dir=miniconda3 2>/dev/null | head -25
```

- **Does:** Finds config files that point at Keycloak.
- **Healthy for "dead":** Only files inside the `buzz` project itself.
- **If wrong:** A reference from any other stack — especially a Caddyfile or an app `.env` — means something depends on it and you need to fix rather than retire it. Check `bungaraya-caddy`, `cbaas`'s caddy on 3030, and the authentik caddy specifically.
- **Rollback:** None needed (read-only).

**Now diagnose the health failure itself:**

```bash
docker inspect --format '{{json .Config.Healthcheck}}' buzz-keycloak | python3 -m json.tool
docker inspect --format '{{json .State.Health}}' buzz-keycloak | python3 -m json.tool | head -40
```

- **Does:** Prints the healthcheck definition, then the last few probe results with their exit codes and output.
- **Healthy:** A healthcheck whose command actually exists in the image and whose target port is right.
- **If wrong — and this is the most likely finding:** Keycloak moved `/health`, `/health/ready`, `/health/live` and `/metrics` off the main HTTP port onto a **separate management interface on port 9000** in Keycloak 25, and 26 keeps that. A healthcheck still probing `http://localhost:8080/health/ready` will 404 forever while the server is perfectly fine. The recon note that "management port 9000 is exposed but not published" is consistent with an image that expects 9000 to be probed and a healthcheck that isn't doing it. Second most likely: the Keycloak container images are UBI-micro based and ship **no `curl` and no `wget`**, so a healthcheck of the form `CMD curl -f ...` fails with exit 127 ("executable not found") regardless of server health. The `.State.Health.Log[].Output` field tells you which of these it is instantly.
- **Rollback:** None needed (read-only).

**Confirm the server is actually fine**, from inside the buzz network so you don't need the port published:

```bash
NET=$(docker inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}' buzz-keycloak)
docker run --rm --network "$NET" curlimages/curl:latest \
  -sS -o /dev/null -w 'ready=%{http_code}\n' http://buzz-keycloak:9000/health/ready
docker run --rm --network "$NET" curlimages/curl:latest \
  -sS -o /dev/null -w 'live=%{http_code}\n' http://buzz-keycloak:9000/health/live
```

- **Does:** Runs a throwaway curl container on the same docker network and probes the management endpoints. Touches nothing on the host and does not modify the Keycloak container.
- **Healthy:** `ready=200` and `live=200`. That means Keycloak is fine and the healthcheck definition is simply wrong — the fix is a compose edit and container recreate (Phase 3.5), or nothing at all if you're retiring the stack.
- **If wrong:** `000` (connection refused) on 9000 means the management interface is disabled — Keycloak needs `--health-enabled=true` (and in a container, `KC_HEALTH_ENABLED=true`). A `503` on `ready` with `200` on `live` means the server is up but its database is unreachable — check `buzz-postgres` on 5437 next. Anything else, read `docker logs --since 48h --tail 300 buzz-keycloak` and look for the first error after startup.
- **Rollback:** None. The curl container is `--rm` and exits immediately.

```bash
docker logs --since 72h --tail 300 buzz-keycloak 2>&1 | grep -iE 'error|fatal|exception|refused|timeout' | tail -40
```

- **Does:** Pulls the errors from the last three days.
- **Healthy:** Nothing after the startup banner, which supports "healthcheck is wrong, server is fine".
- **If wrong:** Repeated `Connection refused` to Postgres means the DB link is broken; check whether `buzz-postgres` (postgres:17 on 5437) is on the same network and accepting connections. `OutOfMemoryError` means the JVM heap is undersized — but note it's been "Up 2 days" without restarting, so it isn't crash-looping.
- **Rollback:** None needed (read-only).

**Decision:** if `xact_commit` is flat, nothing outside `buzz` references it, and there are no established connections, Keycloak is dead weight. Stop the whole `buzz` stack in Phase 2.7 rather than fixing a healthcheck on something nobody uses. If it *is* in use, fix the healthcheck in Phase 3.5.

### 1.7 Container triage: classify all 45

The goal is a written classification, not an immediate action. Build the evidence table first, decide second.

**Collect the signals:**

```bash
OUT=/mnt/data/runbook-2026-08-03/container-triage.tsv
printf 'name\timage\tcreated\tstarted\tlast_log\tnetIO\tblockIO\tmem\n' > "$OUT"
for c in $(docker ps -aq); do
  n=$(docker inspect -f '{{.Name}}' "$c" | tr -d '/')
  img=$(docker inspect -f '{{.Config.Image}}' "$c")
  cre=$(docker inspect -f '{{.Created}}' "$c" | cut -c1-10)
  sta=$(docker inspect -f '{{.State.StartedAt}}' "$c" | cut -c1-19)
  lastlog=$(docker logs --tail 1 -t "$c" 2>&1 | head -1 | cut -c1-19)
  stats=$(docker stats --no-stream --format '{{.NetIO}}\t{{.BlockIO}}\t{{.MemUsage}}' "$c" 2>/dev/null)
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$n" "$img" "$cre" "$sta" "$lastlog" "$stats" >> "$OUT"
done
column -t -s $'\t' "$OUT" | less -S
```

- **Does:** Builds one row per container with image, creation date, start time, the timestamp of its most recent log line, and cumulative network/block I/O and memory since start.
- **Healthy:** Active stacks show a `last_log` within the last few hours and non-trivial `NetIO`. Dormant stacks show a `last_log` from days ago and `NetIO` in the low kB.
- **If wrong:** A blank `last_log` means the container logs nothing (common for Redis and some Postgres configs) — for those, fall back to the connection-count check below. All containers were started ~2d16h ago at the host reboot, so `started` carries no information; `created` (the image/container age) and `last_log` are the signals that matter.
- **Rollback:** None needed (read-only).

**Cumulative network I/O is the sharpest single signal.** All 45 containers have been up the same 2 days 16 hours, so `NetIO` is directly comparable across them:

```bash
docker stats --no-stream --format '{{.NetIO}}\t{{.Name}}' | sort -h | head -25
```

- **Does:** Ranks containers by total bytes moved since the shared start time.
- **Healthy:** Live stacks in the MB–GB range. Genuinely idle containers in the low kB — that's just docker network housekeeping and a healthcheck or two.
- **If wrong:** A container with near-zero I/O that you *believe* is in use means either it's reached over a volume/socket rather than the network, or your belief is wrong. Check with the DB connection count.
- **Rollback:** None needed (read-only).

**Database connection counts** for the many Postgres containers — the definitive activity signal for a data stack:

```bash
for pg in bayu-main-db obtener-postgres bocra-postgres beslut-postgres cbaas-postgres \
          tender-automation-postgres ops-postgres sec-postgres; do
  docker ps --format '{{.Names}}' | grep -qx "$pg" || { printf '%-28s not running\n' "$pg"; continue; }
  n=$(docker exec "$pg" psql -U postgres -Atc \
      "select count(*) from pg_stat_activity where backend_type='client backend' and pid<>pg_backend_pid()" 2>/dev/null)
  x=$(docker exec "$pg" psql -U postgres -Atc \
      "select sum(xact_commit) from pg_stat_database" 2>/dev/null)
  printf '%-28s clients=%-5s commits=%s\n' "$pg" "${n:-?}" "${x:-?}"
done
```

- **Does:** For each Postgres container, counts live client backends and total commits since stats reset.
- **Healthy for "active":** `clients` ≥ 1 and `commits` climbing between two runs ten minutes apart.
- **Healthy for "dormant":** `clients=0`. A database with no client connections for a 10-minute sample, on a stack whose image is 3–4 months old, is dormant.
- **If wrong:** `clients=?` means the psql user is wrong for that container — get it from `docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' <name> | grep -i POSTGRES_USER`. Note `sec-postgres` and `ops-postgres` should show clients; if they don't, something in the Arbos fleet is broken and that's a more urgent finding than any of this.
- **Rollback:** None needed (read-only).

**Established connections on published ports** — for the app containers:

```bash
for p in 8383 8400 3030 8787 7233 18080 7843 8084 9001 9002; do
  c=$(sudo ss -Htn state established "( sport = :$p or dport = :$p )" 2>/dev/null | wc -l)
  printf 'port %-6s established=%s\n' "$p" "$c"
done
```

- **Does:** Counts live TCP connections on the published ports of the older stacks (people-search 8383, beslut 8400, cbaas caddy 3030, bungaraya caddy 8787, temporal 7233, ops-app 18080, waha 7843, adminer 8084, minio 9001/9002).
- **Healthy:** Zero on the stacks you expect to be dormant.
- **If wrong:** Any non-zero count on a stack you were about to stop means it has a live consumer — often a Cloudflare tunnel or a cron job. Identify it before stopping: `sudo ss -tnp state established "( sport = :$p )"`.
- **Rollback:** None needed (read-only).

**Classification rubric.** Write the verdict for each stack into a file you keep:

| Class | Criteria (all must hold) | Action |
|---|---|---|
| **Active** | Log lines within 24h, OR ≥1 DB client backend, OR established connections on a published port, OR named in a running tunnel/Caddy config | Leave running. No action. |
| **Dormant but needed** | No activity signal, but you can name a reason you'll want it back (a client project, a demo, data you query occasionally) | `docker compose stop` in Phase 2.7. Volumes untouched. Restore command recorded. |
| **Dead** | No activity signal, no named reason, and you're confident it's finished | Still only `stop` in Phase 2.7. Revisit removal after 30 days of it being stopped with nothing breaking. |

Candidate list based on the recon, to be confirmed by the measurements above — the 3–4 month-old stacks: `bayu-main-db`, `people-search`, `beslut-backend` + `beslut-postgres`, `obtener-postgres`, `bocra-redis` + `bocra-postgres`, `cbaas` (caddy + server + postgres + redis), `bungaraya-caddy`, `tender-automation-temporal` + `tender-automation-postgres`, and the `ops` stack.

Do **not** put these in the candidate list regardless of what the numbers say: anything in `authentik` (SSO for everything else), `orkes_sec` (`sec-redis`, `sec-postgres` — the harga backend depends on them), `tronzz` (the agent fleet uses it), or `waha` (WhatsApp API, likely wired into an active flow).

### Phase 1 exit criteria

- [ ] Baseline captured to `/mnt/data/runbook-2026-08-03/baseline/`.
- [ ] `restart-policies.txt` reviewed; any `restart=no` container has a written start command.
- [ ] PSI + `vmstat si/so` recorded → verdict on whether memory pressure is real or stale.
- [ ] Per-process swap listing captured; the 9.8G is attributed.
- [ ] `embed_server.py` RSS trend sampled for ≥1 hour → leak / no leak verdict.
- [ ] Each of the three `opencode` pids has a written abandoned / not-abandoned verdict.
- [ ] Disk consumers ranked; a target list totalling ≥160G of relocatable data identified.
- [ ] Keycloak: in-use / not-in-use verdict, and healthcheck-vs-server verdict.
- [ ] All 45 containers classified active / dormant-but-needed / dead.

---

## Phase 2 — reclaim without restarting anything

Everything in this phase can run with all services live. Nothing here stops, restarts, or recreates a running process that serves traffic. The one class of process this phase does terminate is the abandoned `opencode` instances, which serve nothing by definition of the Phase 1.3 checks.

Work top to bottom. Re-measure after each group.

### 2.1 A note on what "reclaiming swap" actually means

You will be tempted to try to empty swap. Don't aim at that. Swap being full is a **consequence**, not a cause. The kernel put 9.8G of cold anonymous pages on disk because it had better uses for that RAM, and it will read them back the moment something touches them. Forcing them back in doesn't create memory; it consumes memory.

The correct target is **reducing the anonymous working set**, i.e. `AnonPages` in `/proc/meminfo`. When that drops, the kernel stops needing swap, `MemAvailable` rises, and swap usage decays naturally as processes exit and restart. Swap-used going down is the scoreboard, not the lever.

There is exactly one legitimate reason to force swap empty on this box, and it is the Phase 3.3 swap relocation. That is handled there, safely, with a second swap area.

### 2.2 Cheap, zero-risk disk wins first

These are safe, immediate, and need no coordination. Do them all.

```bash
sudo apt-get clean
sudo du -sh /var/cache/apt
```

- **Does:** Deletes downloaded `.deb` packages from the apt cache. They are re-downloadable and nothing reads them after installation.
- **Healthy:** `/var/cache/apt` drops to a few MB.
- **If wrong:** Cannot really go wrong. If it reports nothing freed, the cache was already clean.
- **Rollback:** None needed; apt re-downloads on demand.

```bash
snap list --all | awk '/disabled/{print $1, $3}'
snap list --all | awk '/disabled/{print $1, $3}' | while read -r name rev; do
  sudo snap remove "$name" --revision="$rev"
done
sudo du -sh /var/lib/snapd
```

- **Does:** Lists then removes superseded snap revisions. Snap keeps old revisions for rollback; on a server with 3 snaps that's typically 2–8G.
- **Healthy:** Each removal prints `<name> (revision <rev>) removed`. `/var/lib/snapd` shrinks.
- **If wrong:** If a removal errors with "snap is in use", skip that one. Removing a *disabled* revision cannot affect the running revision.
- **Rollback:** `sudo snap revert <name>` no longer has an old revision to revert to. That is the only cost, and it is acceptable.

```bash
journalctl --disk-usage
sudo journalctl --vacuum-size=1G
journalctl --disk-usage
```

- **Does:** Trims the journal to 1GB, oldest first.
- **Healthy:** Reports how much it deleted, then the new size at or under 1G.
- **If wrong:** If the journal was already under 1G, nothing happens and you've learned journald isn't a consumer here.
- **Rollback:** None. Deleted journal entries are gone. Do the Phase 0 journald grep first if you haven't.

Then cap it permanently so it can't grow back:

```bash
sudo cp /etc/systemd/journald.conf /mnt/data/runbook-2026-08-03/baseline/journald.conf.bak
sudo sed -i 's/^#\?SystemMaxUse=.*/SystemMaxUse=1G/;s/^#\?SystemMaxFileSize=.*/SystemMaxFileSize=128M/;s/^#\?MaxRetentionSec=.*/MaxRetentionSec=30day/' /etc/systemd/journald.conf
grep -E '^(SystemMaxUse|SystemMaxFileSize|MaxRetentionSec)' /etc/systemd/journald.conf
sudo systemctl restart systemd-journald
journalctl -n 5 --no-pager
```

- **Does:** Sets a hard 1GB ceiling and 30-day retention, then restarts journald to apply.
- **Healthy:** The three settings echo back correctly, journald restarts in well under a second, and `journalctl -n 5` returns recent entries.
- **If wrong:** If `sed` didn't match (because the keys are absent rather than commented), append them instead: `printf 'SystemMaxUse=1G\nSystemMaxFileSize=128M\nMaxRetentionSec=30day\n' | sudo tee -a /etc/systemd/journald.conf`.
- **Restart note:** `systemd-journald` restart is the one restart in this phase. It is socket-activated — clients write to `/run/systemd/journal/socket`, which persists across the restart, so log lines are buffered rather than lost. It takes well under a second and does not touch any service that logs. It is safe here; it is called out for honesty, not because it carries risk.
- **Rollback:** `sudo cp /mnt/data/runbook-2026-08-03/baseline/journald.conf.bak /etc/systemd/journald.conf && sudo systemctl restart systemd-journald`.

```bash
pip cache dir 2>/dev/null && pip cache info 2>/dev/null
pip cache purge 2>/dev/null
npm cache verify 2>/dev/null | tail -3
du -sh ~/.npm/_cacache 2>/dev/null
npm cache clean --force 2>/dev/null
du -sh ~/.cache/uv 2>/dev/null && uv cache clean 2>/dev/null
~/miniconda3/bin/conda clean -a -y 2>/dev/null | tail -5
rm -rf ~/.cargo/registry/cache ~/.cargo/registry/src 2>/dev/null
du -sh ~/.cache/pip ~/.npm ~/.cache/uv ~/.cargo 2>/dev/null
```

- **Does:** Empties the pip, npm, uv, conda, and cargo download caches. All five are pure caches of re-downloadable artifacts.
- **Healthy:** Sizes drop. Often 5–20G combined on a box with this many projects.
- **If wrong:** `pip cache purge` failing means pip is old or the venv-specific pip is being picked up — it's per-user, so run it from a shell without a venv active. Deleting `~/.cargo/registry/src` only slows the next `cargo build`; it never breaks a built binary. Do **not** delete `~/.cargo/bin` or `~/.rustup/toolchains` — those are installed tools, not caches.
- **Rollback:** None needed; every one of these repopulates on next use.

```bash
docker image prune -f
docker builder prune -f --filter until=336h
docker system df
```

- **Does:** `image prune` (no `-a`) removes **only dangling images** — layers with no tag, orphaned by rebuilds. `builder prune --filter until=336h` removes build cache older than 14 days. Neither touches a tagged image, a running container, or any volume.
- **Healthy:** Reports reclaimed space, often 10–60G on a box that has built this many projects. `docker system df` afterwards shows images `RECLAIMABLE` much lower.
- **If wrong:** If it reclaims almost nothing, images aren't the consumer and you should look at volumes and container logs instead.
- **Rollback:** None. Dangling images have no tag and cannot be referenced. Build cache regenerates.
- **Do not** add `-a` to `image prune` or use `docker system prune -a`. See the "do not do this" section — on this box that is a destructive command.

### 2.3 Reclaim the abandoned `opencode` processes

**Gate:** only proceed for pids where all four Phase 1.3 checks agreed — no controlling TTY, PPID 1 (or a dead parent), zero CPU ticks over 60 seconds, no children, no established sockets.

Re-confirm immediately before acting, because the world may have changed since you measured:

```bash
for p in 4131680 93395 321500; do
  ps -o pid,tty,stat,etime,times,rss,cmd -p "$p" --no-headers 2>/dev/null || echo "$p already gone"
done
```

- **Does:** Final confirmation the pids still exist and still look abandoned.
- **Healthy:** `?` in the TTY column, `S` or `Sl` state.
- **If wrong:** A pid that's gone needs no action. A pid that now has a TTY means you reconnected to it — skip it.
- **Rollback:** None needed (read-only).

Terminate gracefully, one at a time, checking between each:

```bash
P=4131680
kill -TERM "$P"
sleep 10
ps -p "$P" >/dev/null 2>&1 && echo "still alive" || echo "exited cleanly"
free -h
```

- **Does:** Sends SIGTERM, giving the process a chance to flush and exit cleanly. Then checks.
- **Healthy:** `exited cleanly`, and `free -h` shows `used` dropping by roughly the process's RSS.
- **If wrong:** `still alive` after 10 seconds means it's ignoring SIGTERM or is stuck in uninterruptible sleep. Check `ps -o stat= -p $P`: state `D` means it's blocked in the kernel on I/O and `kill -9` will not help either — wait. Any other state, wait another 20 seconds, then `kill -KILL "$P"`.
- **Rollback:** None. A killed `opencode` session is gone. Its on-disk project files are untouched — `opencode` writes to the filesystem as it goes, so you lose the session context, not the work.

Repeat for `93395` and `321500`, pausing between each to watch the effect:

```bash
free -h; cat /proc/pressure/memory
```

- **Does:** Shows the cumulative effect on memory and pressure.
- **Healthy:** After all three, `used` down by ~1.9G and `available` up correspondingly. Swap-used will **not** drop immediately — the freed pages were resident, and the swapped pages belonging to those processes are released asynchronously. Give it a few minutes and re-check `swapon --show`.
- **If wrong:** If `used` barely moves, the three processes shared most of their memory (all three are the same binary, so shared libraries and the Node runtime are counted once). That's why the `smem` USS column from Phase 1.1 was worth capturing — USS is the honest "freed by killing this" number.
- **Rollback:** None.

If any of the three had an open lock file (from the Phase 1.3 fd listing), clean it up now:

```bash
# only for locks you identified in 1.3 and confirmed belonged to a killed pid
ls -la <path>/.git/index.lock 2>/dev/null && rm -f <path>/.git/index.lock
```

- **Does:** Removes a stale lock left behind by the killed process.
- **Healthy:** `git status` in that repo works again.
- **If wrong:** Only remove a lock file whose owning pid you just killed. Removing a lock held by a live process corrupts whatever it protects.
- **Rollback:** None needed; git recreates locks as required.

### 2.4 Move the loose files out of `$HOME`

About 634MB. Small in absolute terms, but they're the easiest thing to get out of the way and moving them establishes the archive directory you'll use for everything else.

```bash
ARCH=/mnt/data/archive/2026-08-03
mkdir -p "$ARCH"
sudo lsof -- ~/bocra.tar.gz ~/cbaas-server.tar.gz ~/n8n.log ~/*.heapsnapshot ~/RFP-000000168142.zip 2>/dev/null
```

- **Does:** Creates the archive directory and checks whether anything holds these files open.
- **Healthy:** `lsof` prints nothing — no live writers.
- **If wrong:** If n8n (or anything) has `n8n.log` open, do not move it. Truncate instead: `sudo truncate -s 0 ~/n8n.log`, which preserves the inode and the writer keeps working. If a tarball is open, something is reading it — wait.
- **Rollback:** None needed (read-only check).

Copy with verification, then remove the source. `mv` across filesystems is a copy-then-unlink with no integrity check; `rsync -c` verifies checksums before removing:

```bash
rsync -avh --checksum --remove-source-files \
  ~/bocra.tar.gz ~/cbaas-server.tar.gz ~/RFP-000000168142.zip ~/*.heapsnapshot \
  "$ARCH"/ 2>&1 | tail -10
ls -lah "$ARCH"
df -h /
```

- **Does:** Copies each file to `/mnt/data`, verifies by checksum, and only then deletes the original.
- **Healthy:** rsync's summary shows the files transferred, `ls` shows them at the destination with matching sizes, `/` frees ~550MB.
- **If wrong:** `--remove-source-files` leaves the source in place if verification fails, so a source file still existing means the copy didn't verify — re-run. If rsync reports a permission error, prefix with `sudo` and `chown the_bomb:the_bomb` the destination afterwards.
- **Rollback:** `rsync -avh "$ARCH"/<file> ~/` moves it back. Nothing has been deleted, only relocated.

For `n8n.log` (91MB), decide by whether n8n still runs:

```bash
pgrep -af n8n || docker ps --format '{{.Names}}' | grep -i n8n || echo "no n8n running"
```

- **Does:** Checks for an n8n process or container.
- **Healthy:** `no n8n running` — in which case the log is dead history and can be compressed to the archive: `gzip -c ~/n8n.log > "$ARCH/n8n.log.gz" && rm ~/n8n.log`.
- **If wrong:** If n8n *is* running and writing to that path, use `sudo truncate -s 0 ~/n8n.log` after archiving a compressed copy. Never `rm` a log a process has open — the space isn't freed until the process exits (this is exactly the `lsof +L1` scenario from Phase 1.5).
- **Rollback:** `gunzip -c "$ARCH/n8n.log.gz" > ~/n8n.log`.

### 2.5 Relocate the model weights and big caches

This is where the meaningful root-filesystem space is, and none of it requires stopping a service **as long as you check for open files first**. The pattern throughout is: verify nothing has the directory open → rsync to `/mnt/data` → verify → replace with a symlink.

Symlinks work here because every one of these consumers resolves paths at open time, not at start time. The exception is `ollama`, which caches its model directory path in the running daemon — that one goes in Phase 3.2.

**HuggingFace cache** (often the largest single item):

```bash
D=~/.cache/huggingface
sudo lsof +D "$D" 2>/dev/null | head
du -sh "$D"
```

- **Does:** Checks for open files anywhere under the directory, then sizes it.
- **Healthy:** `lsof` prints nothing. If it does, note which process — likely `embed_server.py` or `ocr_server.py` holding a model file open.
- **If wrong:** If a live process has a model file open, the safe move is: copy now (rsync is read-only on the source), then do the swap-and-symlink in the Phase 3 window when you restart that process anyway. Copying while live is always safe.
- **Rollback:** None needed (read-only).

```bash
mkdir -p /mnt/data/caches
rsync -aH --info=progress2 ~/.cache/huggingface/ /mnt/data/caches/huggingface/
du -sh ~/.cache/huggingface /mnt/data/caches/huggingface
```

- **Does:** Copies the cache to `/mnt/data`, preserving hard links (`-H` matters — HuggingFace's blob store uses them heavily and without `-H` the copy can be far larger than the original).
- **Healthy:** The two `du` outputs match within a few percent.
- **If wrong:** A destination much larger than the source means `-H` didn't take effect; delete and retry. A destination smaller means the copy was interrupted; rsync is resumable, just re-run it.
- **Rollback:** `rm -rf /mnt/data/caches/huggingface`. The source is untouched at this point.

```bash
mv ~/.cache/huggingface ~/.cache/huggingface.old
ln -s /mnt/data/caches/huggingface ~/.cache/huggingface
ls -la ~/.cache/ | grep huggingface
python3 -c "import os;print(os.path.realpath(os.path.expanduser('~/.cache/huggingface')))"
```

- **Does:** Renames the original aside (does not delete it), then puts a symlink in its place.
- **Healthy:** The symlink resolves to `/mnt/data/caches/huggingface`.
- **If wrong:** If anything errors, `rm ~/.cache/huggingface && mv ~/.cache/huggingface.old ~/.cache/huggingface` restores instantly.
- **Rollback:** Exactly that. Keep `.old` for 48 hours before deleting.

Then verify a consumer still works before deleting the old copy. Trigger one embedding request through whatever normally calls `embed_server.py`, and confirm:

```bash
sudo lsof -p $(pgrep -f embed_server.py | head -1) 2>/dev/null | grep -c huggingface
```

- **Does:** Confirms the running process is now reading through the symlink into `/mnt/data`.
- **Healthy:** A non-zero count, and the paths shown resolve under `/mnt/data`.
- **If wrong:** If the process still has files open from the old inode, that's expected — already-open descriptors follow the old path. It will pick up the new location on its next open. Don't delete `.old` until you've confirmed a fresh open lands in the new place.
- **Rollback:** Restore as above.

After 48 hours of everything working:

```bash
rm -rf ~/.cache/huggingface.old
df -h /
```

Apply the same four-step pattern (check open → rsync → symlink → verify → delete after 48h) to:

| Directory | Notes |
|---|---|
| `~/.EasyOCR` | Model weights for the OCR stack. Check `ocr_server.py` (pid 3836736) isn't mid-job first. |
| `~/.crawl4ai` | Browser profiles and caches; usually safe. |
| `~/.cache/ms-playwright` | Browser binaries, often 2–5G. Nothing holds them open unless a browser is running. |
| `~/.cache/puppeteer` | Same. |
| `~/.cache/torch` | Downloaded checkpoints; re-downloadable but slow. |
| `~/android-sdk` | Almost certainly not in use on a server. Move the whole thing. |
| `~/swift-6.0.3` | Same. |
| `~/google-cloud-sdk` | Move and add a symlink; `gcloud` resolves through it fine. |
| `~/miniconda3` | **Care.** Conda hardcodes absolute paths in its shebangs and `conda-meta`. A symlink usually works but a moved conda that breaks is annoying to repair. Only move it if you've confirmed no running process uses a conda env: `sudo lsof +D ~/miniconda3 \| head`. If any of the live Python services resolve to conda, leave it alone — the venvs under `~/orkes` and `~/orkes_sec` are separate and unaffected either way. |

- **Healthy overall:** Each move frees its measured size on `/` and nothing changes behaviour.
- **If wrong on any one of them:** Restore from `.old` and move on to the next. None of these are load-bearing individually.

**`node_modules` in inactive projects:**

```bash
sudo find /home/the_bomb -maxdepth 4 -type d -name node_modules -prune -print 2>/dev/null | while read -r d; do
  proj=$(dirname "$d")
  lock=$( [ -f "$proj/package-lock.json" ] || [ -f "$proj/yarn.lock" ] || [ -f "$proj/pnpm-lock.yaml" ] && echo yes || echo NO-LOCK )
  age=$(find "$proj" -maxdepth 1 -name 'package.json' -printf '%TY-%Tm-%Td\n' 2>/dev/null)
  printf '%8s  lock=%-7s mtime=%s  %s\n' "$(du -sh "$d" 2>/dev/null | cut -f1)" "$lock" "$age" "$d"
done | sort -h -r | head -25
```

- **Does:** For each `node_modules`, reports its size, whether a lockfile exists to regenerate it, and when the project's `package.json` was last modified.
- **Healthy:** Most have `lock=yes` and an old mtime — those are safe to delete and regenerate with `npm ci` when needed.
- **If wrong:** `lock=NO-LOCK` means deleting is irreversible without resolving versions again. Skip those. Also skip anything under `~/tronzz`, `~/orkes`, `~/orkes_sec`, `~/OrkesBayu` regardless — those are live.
- **Rollback:** `cd <project> && npm ci`.

### 2.6 Container log truncation (no-restart stopgap)

If Phase 1.5 found container logs in the hundreds of MB or GB, truncate them now. The permanent fix (a daemon-wide `log-opts` rotation policy) needs a daemon restart and lives in Phase 3.1.

```bash
for c in $(docker ps -aq); do
  p=$(docker inspect -f '{{.LogPath}}' "$c")
  n=$(docker inspect -f '{{.Name}}' "$c" | tr -d '/')
  s=$(sudo stat -c %s "$p" 2>/dev/null || echo 0)
  if [ "$s" -gt 209715200 ]; then
    printf 'truncating %-32s %s\n' "$n" "$(numfmt --to=iec "$s")"
    sudo truncate -s 0 "$p"
  fi
done
df -h /
```

- **Does:** Zeroes any container log over 200MB, in place, while the container runs.
- **Healthy:** A list of what was truncated and a measurable drop in `/` usage. Containers keep running; `docker logs <name>` starts filling again within minutes for anything chatty.
- **If wrong:** `docker logs` complaining about a malformed JSON line immediately after truncation is a cosmetic artifact of cutting mid-line. It clears itself. It does not affect the container or the daemon.
- **Rollback:** None. Truncated logs are gone. Run the Phase 0 container-log grep first if you haven't.

### 2.7 Stop the dormant container stacks

**Gate:** only stacks you classified as dormant-but-needed or dead in Phase 1.7, with the evidence recorded.

This is reversible and causes no downtime — by construction, these stacks serve nothing. It sits in Phase 2 rather than Phase 3 for that reason, but it carries the most *judgement* risk of anything in this phase, so go one stack at a time with a soak period between.

**Write the restore command first.** For each stack, before stopping it:

```bash
C=cbaas-server   # example: one container from the stack
docker inspect -f 'project={{index .Config.Labels "com.docker.compose.project"}}
dir={{index .Config.Labels "com.docker.compose.project.working_dir"}}
files={{index .Config.Labels "com.docker.compose.project.config_files"}}
service={{index .Config.Labels "com.docker.compose.service"}}
restart={{.HostConfig.RestartPolicy.Name}}
image={{.Config.Image}}
imageid={{.Image}}' "$C"
docker inspect -f '{{range .Mounts}}{{.Type}} {{.Name}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}' "$C"
```

- **Does:** Extracts the compose project name, its working directory, its compose file paths, the service name, the restart policy, the exact image and image ID, and every volume mount.
- **Healthy:** A compose project and a working directory you can `cd` into. Volume mounts listed with named volumes (not anonymous).
- **If wrong:** Empty compose labels mean the container was created with `docker run`, not compose — in that case capture the full run command with `docker inspect` output or a tool like `runlike`, and write it into your restore document by hand. Do not stop a container you can't reconstruct.
- **Rollback:** None needed (read-only).

Record all of it:

```bash
REST=/mnt/data/runbook-2026-08-03/restore-commands.md
{
  echo "## $C"
  echo '```'
  docker inspect -f 'cd {{index .Config.Labels "com.docker.compose.project.working_dir"}} && docker compose -f {{index .Config.Labels "com.docker.compose.project.config_files"}} up -d' "$C"
  echo '```'
  echo 'Volumes (DO NOT DELETE):'
  docker inspect -f '{{range .Mounts}}- {{.Type}} {{.Name}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}' "$C"
  echo
} >> "$REST"
cat "$REST"
```

Then stop the whole stack, not individual containers — stopping a backend while its Postgres runs leaves a half-stack that looks broken:

```bash
PROJ=cbaas
cd "$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project.working_dir"}}' cbaas-server)" || exit 1
docker compose stop
docker compose ps
```

- **Does:** Stops every container in the compose project. `stop` sends SIGTERM, waits, then SIGKILL. Containers remain defined; images remain; **volumes are untouched**.
- **Healthy:** `docker compose ps` shows every service `exited (0)`. `docker volume ls` count is unchanged. `free -h` and `df -h /` both improve.
- **If wrong:** A container exiting non-zero means it didn't shut down cleanly — for a Postgres, check `docker compose logs --tail 50 <svc>` for a clean shutdown message before moving on, because an unclean Postgres stop means recovery on next start (which is fine, just slower).
- **Rollback:** `docker compose start` from the same directory brings the stack back with all data intact, usually in seconds. This is the whole reason for `stop` rather than `down`.

Use `stop`, never `down`. `docker compose down` removes containers and networks, and `down -v` removes volumes. `stop` is a pause you can undo with one command.

**Soak.** After stopping each stack, wait at least 24 hours (72 for anything you're less sure about) before stopping the next. Watch for:

```bash
# anything failing to reach a now-stopped service
sudo journalctl --since '1 hour ago' -p warning --no-pager | tail -30
pm2 logs --lines 50 --nostream 2>/dev/null | grep -iE 'refused|timeout|unreachable|econnrefused' | tail -20
docker ps --format '{{.Names}}\t{{.Status}}' | grep -iE 'restarting|unhealthy'
```

- **Does:** Looks for connection failures that appeared after the stop.
- **Healthy:** Nothing new.
- **If wrong:** Any `ECONNREFUSED` naming a port belonging to a stack you just stopped is your answer — `docker compose start` it back and reclassify it as active.
- **Rollback:** `docker compose start`.

Suggested order — least likely to be missed first: `obtener-postgres` → `bocra-*` → `bungaraya-caddy` → `beslut-*` → `people-search` → `tender-automation-*` → `cbaas-*` → `bayu-main-db` → `ops-*`. Put `ops` last; a three-month-old stack with a worker, an app, pgvector, minio and redis looks more like infrastructure than a finished project, and pgvector in particular suggests something the agent fleet might reach for.

If Phase 1.6 concluded Keycloak is unused, the `buzz` stack (adminer, minio, keycloak, postgres, redis, prometheus) joins this list — but check minio first, since object storage tends to have consumers you forget about:

```bash
sudo ss -Htn state established '( sport = :9001 or sport = :9002 )' | wc -l
grep -rliE 'localhost:900[12]|minio' ~/orkes ~/orkes_sec ~/tronzz --include='*.py' --include='*.env' --include='*.yml' --exclude-dir=node_modules --exclude-dir=.venv 2>/dev/null | head
```

### 2.8 Add memory guards to pm2 (no restart required to set)

Setting `max_memory_restart` in the ecosystem file does not take effect until the app restarts, so this is a change you *make* now and that *applies* at the next natural restart. That's deliberate — it means you get the guard without forcing a restart today.

```bash
grep -rn 'max_memory_restart' ~/orkes/ecosystem*.js ~/orkes_sec/ecosystem*.js ~/*/ecosystem*.config.js 2>/dev/null
```

- **Does:** Finds the ecosystem files and checks whether guards already exist.
- **Healthy:** You locate the file(s) defining `sec-proxy`, `sec-sched-api`, `sec-failsafe`, `sec-products-api`, `sec-tenders-api`, `sec-enrich`, `sec-scheduler`, `sec-guardian`, `sec-price-pipeline`, `sec-agent`, `sec-harga-bot`, and the yellowpages gunicorn.
- **If wrong:** If there's no ecosystem file and apps were started with `pm2 start` directly, the config lives only in `~/.pm2/dump.pm2`. Generate a real ecosystem file before changing anything: `pm2 ecosystem` scaffolds one, or reconstruct from `pm2 jlist`.
- **Rollback:** None needed (read-only).

Add generous ceilings — high enough that they only fire on a genuine runaway, because for a `claude -p` agent loop a restart may land mid-step:

```javascript
// in each app's block
max_memory_restart: '2G',   // agents and API services
// max_memory_restart: '4G' // embed_server, if it is managed by pm2
```

- **Does:** Tells pm2 to restart an app that exceeds the ceiling.
- **Healthy:** After the next natural restart, `pm2 jlist` shows `max_memory_restart` populated.
- **If wrong:** Setting this too low turns a slow leak into a restart loop, and for the agent fleet a restart mid-step can leave `STATE.md` and `context/runs/<timestamp>/` in a torn state. If you're unsure whether the agent loop checkpoints at step boundaries, set the ceiling high (4G) and treat it as a last-resort backstop rather than a management tool.
- **Rollback:** Remove the line; it applies at the following restart.

Also add log rotation, which pm2 does not do by default and which is a live contributor to root usage:

```bash
pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 50M
pm2 set pm2-logrotate:retain 7
pm2 set pm2-logrotate:compress true
pm2 set pm2-logrotate:rotateInterval '0 0 * * *'
pm2 conf pm2-logrotate
```

- **Does:** Installs and configures pm2's log rotation module: rotate at 50MB or daily, keep 7 compressed generations.
- **Healthy:** `pm2 conf pm2-logrotate` echoes the settings. This installs a pm2 *module*, which runs as its own process — it does **not** restart your apps.
- **If wrong:** `pm2 install` needs network access to npm. If it fails, the manual fallback is a logrotate config in `/etc/logrotate.d/pm2` using `copytruncate` (which preserves inodes, matching how pm2 holds the files open).
- **Rollback:** `pm2 uninstall pm2-logrotate`.

### 2.9 Re-measure

```bash
df -h / /mnt/data
free -h
swapon --show
cat /proc/pressure/memory
docker ps -q | wc -l
pm2 ls --no-color
```

- **Does:** The scoreboard.
- **Healthy:** `/` meaningfully below 87% — how far depends on what Phase 1.5 found, but the docker prune plus caches plus model relocation should realistically land you in the 70s. `free -h` showing more `available`. Container count down by however many you stopped. **Every pm2 app still `online` with the same restart count as in the baseline** — that is the proof that nothing in this phase disturbed a live service.
- **If wrong:** A pm2 app showing an increased restart count means something in this phase touched it. Compare against `$BASE/pm2.txt` and read that app's log around the time of the change.
- **Rollback:** Per-step, as documented above.

If `/` is still above 75% after all of Phase 2, the remaining space is in `/var/lib/docker` and only Phase 3.1 will move it.

---

## Phase 3 — requires a maintenance window

**Everything below interrupts a running service.** Nothing here should be attempted opportunistically. Book a window, tell whoever depends on `harga.work` and `yellowpages.zeidgeist.com`, and work the list in order.

### Before the window: the pre-flight checklist

- [ ] Phase 2 complete and soaked for at least 48 hours. In particular, if `/` is already under 70% after Phase 2, **step 3.1 becomes optional** — reconsider whether you want it at all.
- [ ] `restart-policies.txt` from Phase 1.0 reviewed, and a written start command exists for every container with `restart=no`.
- [ ] The Arbos fleet is **at a step boundary**, not mid-step. `orkes_sec` is mid "harga vX" — Phase 1 committed, so pause between phases, not inside one. Check `~/orkes_sec/STATE.md` and the newest `context/runs/<timestamp>/` before you start.
- [ ] A `docker compose` file (or written run command) is on hand for every stack you intend to bring back.
- [ ] You are on the Tailscale address (100.108.103.5), not a session that routes through anything you're about to restart.
- [ ] `tmux` or `screen` — every command below should survive your SSH session dropping.

**Suggested window:** 90 minutes booked, roughly 35 minutes of actual work. The order below is deliberate: the swap relocation goes after the docker move because the docker restart will churn memory, and you want swap stable before you touch it.

### Ordering and duration at a glance

| Step | Change | Interrupts | Working estimate | Notes |
|---|---|---|---|---|
| 3.1 | Move docker data-root to `/mnt/data` + add log rotation | **All 45 containers** | 6–15 min in-window (plus hours of pre-staged rsync beforehand, which is live and free) | The big one. Biggest space win. Skip if `/` is already under 70%. |
| 3.2 | Move ollama models via `OLLAMA_MODELS` | `ollama` only | 1–2 min | Pre-stage the rsync live. Models reload lazily on first request. |
| 3.3 | Move swap to `/mnt/data` NVMe | Nothing, but heavy I/O | 5–20 min | Frees ~15G on `/` if swap is `/swap.img`. Safe because a second swap area exists throughout. |
| 3.4 | Restart `embed_server.py` | Embedding consumers | 1–3 min | Only if Phase 1.2 confirmed a leak. Pause the indexer first. |
| 3.5 | Fix or retire `buzz-keycloak` | Keycloak realm consumers | 2 min | Only if Phase 1.6 said it's in use. |
| 3.6 | Optional: `/proc` `hidepid` hardening | Potentially several services | 5 min + verification | Reduces the `ps aux` exposure that made the token leak worse. Has real breakage risk — read it fully. |
| 3.7 | Optional: git history rewrite for leaked context | Agent commits to that repo | 10–30 min | Only if Phase 0.4 found `cfut_` in git history **and** the repo is unpushed. |

Run 3.1 → 3.2 → 3.3 → 3.4 → 3.5. Treat 3.6 and 3.7 as separate windows.

### 3.1 Move the docker data-root to `/mnt/data`

This is the largest single reclaim available and the only one that requires stopping everything containerised.

**Why a restart is unavoidable:** dockerd holds the entire graph driver state, container filesystems, and volume mounts open under `/var/lib/docker`. Changing where that lives means the daemon must not be running while the data moves, and every running container's filesystem is served from that tree — they cannot survive it being moved out from under them. There is no live-migration path.

**Pre-check the destination filesystem** — overlay2 has requirements:

```bash
docker info 2>/dev/null | grep -E 'Storage Driver|Backing Filesystem|Docker Root Dir'
findmnt -no FSTYPE,OPTIONS /mnt/data
sudo tune2fs -l /dev/nvme0n1p1 2>/dev/null | grep -iE 'filesystem features|default mount options'
df -h /mnt/data
```

- **Does:** Confirms the storage driver, the current root dir, and that `/mnt/data` can host overlay2.
- **Healthy:** `Storage Driver: overlay2`, and `/mnt/data` on ext4 or xfs with `d_type` support (ext4 has it; for xfs check `ftype=1` in `xfs_info /mnt/data`). At least 300G free — you have 852G.
- **If wrong:** overlay2 on a filesystem without `d_type` will silently misbehave. If `/mnt/data` is xfs with `ftype=0`, do not proceed — that filesystem needs recreating. If the storage driver is `vfs` or `devicemapper`, this is a much bigger job than described here; stop and reassess.
- **Rollback:** None needed (read-only).

**Pre-stage the copy while everything runs.** This takes hours and costs nothing — do it the day before:

```bash
sudo mkdir -p /mnt/data/docker
sudo rsync -aHAX --info=progress2 --numeric-ids /var/lib/docker/ /mnt/data/docker/
```

- **Does:** Copies the entire docker tree, preserving hard links (`-H`, essential for overlay2), ACLs, extended attributes, and numeric ownership. Runs live — the copy will be inconsistent, which is fine because you re-run it in the window to catch the delta.
- **Healthy:** Completes. `sudo du -sh /var/lib/docker /mnt/data/docker` roughly match.
- **If wrong:** Errors on `/var/lib/docker/overlay2/*/merged` are expected and harmless — those are live mount points, not real directories, and the window's second pass will handle them correctly once the daemon is stopped. If rsync fails with "no space", re-check `/mnt/data`.
- **Rollback:** `sudo rm -rf /mnt/data/docker`. Nothing on `/var/lib/docker` has been touched.

**Now the window starts.**

```bash
date -u
docker ps --format '{{.Names}}' | sort > /mnt/data/runbook-2026-08-03/pre-window-containers.txt
wc -l < /mnt/data/runbook-2026-08-03/pre-window-containers.txt
```

- **Does:** Records exactly which containers were running, so you can diff afterwards.
- **Healthy:** The count matches what you expect (45 minus anything stopped in Phase 2.7).
- **If wrong:** N/A.
- **Rollback:** None needed.

```bash
sudo systemctl stop docker.socket docker containerd
sudo systemctl is-active docker containerd
docker ps 2>&1 | head -2
```

- **Does:** Stops the docker socket (so nothing re-triggers the daemon), the daemon, and containerd. Every container stops.
- **Healthy:** Both report `inactive`, and `docker ps` errors with "Cannot connect to the Docker daemon".
- **If wrong:** If docker refuses to stop, something is holding it — check `sudo systemctl status docker` and `journalctl -u docker -n 50`. Do not proceed while it's running.
- **Rollback:** `sudo systemctl start containerd docker` restores immediately; nothing has changed yet.

```bash
mount | grep -c '/var/lib/docker'
sudo rsync -aHAX --numeric-ids --delete --info=progress2 /var/lib/docker/ /mnt/data/docker/
sudo du -sh /var/lib/docker /mnt/data/docker
```

- **Does:** Confirms no leftover overlay mounts, then syncs the delta with `--delete` so the destination is an exact mirror.
- **Healthy:** The mount count is 0 (or only the parent). The delta sync finishes in 1–5 minutes since you pre-staged. The two `du` figures match closely.
- **If wrong:** A non-zero mount count means containerd left mounts behind. `sudo umount /var/lib/docker/overlay2/*/merged 2>/dev/null` clears them; if any refuse, a stale process holds them — find it with `sudo fuser -m /var/lib/docker`. Do not rsync while overlay mounts are live.
- **Rollback:** Start docker again. `/var/lib/docker` is still intact and authoritative.

Now choose one of two mechanisms. **They are equivalent in effect and in downtime; they differ in what breaks them later.**

**Option A — `data-root` in `daemon.json`** (explicit, visible in `docker info`):

```bash
sudo cp /etc/docker/daemon.json /mnt/data/runbook-2026-08-03/baseline/daemon.json.bak 2>/dev/null || echo '{}' | sudo tee /etc/docker/daemon.json
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "data-root": "/mnt/data/docker",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  }
}
EOF
sudo python3 -c "import json;json.load(open('/etc/docker/daemon.json'));print('json ok')"
```

**Option B — bind mount** (leaves `daemon.json` alone; survives anything that rewrites docker config):

```bash
sudo mv /var/lib/docker /var/lib/docker.old
sudo mkdir -p /var/lib/docker
echo '/mnt/data/docker  /var/lib/docker  none  bind  0 0' | sudo tee -a /etc/fstab
sudo mount /var/lib/docker
findmnt /var/lib/docker
```

Option A is easier to reason about and easier to reverse — `docker info` tells you plainly where the data lives. Option B keeps `/var/lib/docker` as the canonical path, which matters if you have tooling, backup scripts, or a monitoring check that hardcodes it. Pick A unless you know you have such tooling. If you pick B, you still want the `log-opts` from A, so apply the `daemon.json` log settings either way — **that log rotation is the fix for the container-log growth you were truncating by hand in Phase 2.6, and it is worth the window on its own.**

- **Does (either):** Points docker at `/mnt/data` and caps container logs at 50MB × 3 files each.
- **Healthy:** The JSON validates (Option A) or `findmnt` shows the bind mount (Option B).
- **If wrong:** A malformed `daemon.json` prevents dockerd from starting at all, which is why the `python3 -c` validation step is there. Fix the JSON before starting the daemon.
- **Rollback:** Option A — restore `daemon.json.bak`. Option B — `sudo umount /var/lib/docker && sudo rmdir /var/lib/docker && sudo mv /var/lib/docker.old /var/lib/docker` and remove the fstab line.

Start it back:

```bash
sudo systemctl start containerd docker
sleep 20
docker info 2>/dev/null | grep -E 'Docker Root Dir|Storage Driver|Containers|Images'
docker ps --format '{{.Names}}' | sort > /mnt/data/runbook-2026-08-03/post-window-containers.txt
diff /mnt/data/runbook-2026-08-03/pre-window-containers.txt /mnt/data/runbook-2026-08-03/post-window-containers.txt && echo "ALL CONTAINERS BACK"
```

- **Does:** Starts the daemon, waits for containers with restart policies to come up, then diffs the container list against the pre-window snapshot.
- **Healthy:** `Docker Root Dir: /mnt/data/docker` (Option A) or `/var/lib/docker` resolving through the bind mount (Option B). `ALL CONTAINERS BACK` with an empty diff.
- **If wrong:** Lines prefixed `<` in the diff are containers that did not return — those are your `restart=no` containers, and you start them from the commands you recorded in the pre-flight checklist. If the daemon itself won't start, `sudo journalctl -u docker -n 100 --no-pager` will name the reason; the two common ones are malformed `daemon.json` and a permissions/ownership mismatch on the copied tree (which `--numeric-ids` prevents, but check with `sudo ls -la /mnt/data/docker`).
- **Rollback:** Stop docker, revert the config change (A or B), start docker. `/var/lib/docker` (or `.old`) still holds the original data, untouched, so this rollback is complete and fast. **Keep the original for at least a week before deleting.**

Verify the stacks that matter, individually:

```bash
docker ps --filter 'health=unhealthy' --format '{{.Names}}\t{{.Status}}'
docker ps --format '{{.Names}}\t{{.Status}}' | grep -i restarting
curl -sS -o /dev/null -w 'authentik=%{http_code}\n' http://127.0.0.1:9100/ 2>&1
curl -sS -o /dev/null -w 'ocr=%{http_code}\n'       http://127.0.0.1:10100/ 2>&1
curl -sS -o /dev/null -w 'harga=%{http_code}\n'     http://127.0.0.1:3647/ 2>&1
curl -sS -o /dev/null -w 'ypages=%{http_code}\n'    http://127.0.0.1:3636/ 2>&1
pm2 ls --no-color
```

- **Does:** Checks for unhealthy or crash-looping containers, then probes the load-bearing endpoints, then confirms the pm2 fleet.
- **Healthy:** No restarting containers. Each curl returns a 2xx/3xx/401 (401 from authentik is a healthy answer — it means the SSO layer is up and asking you to authenticate). All pm2 apps `online`. Note pm2 runs on the host and is unaffected by the docker restart — but the services it runs may depend on `sec-postgres` and `sec-redis`, so confirm they reconnected.
- **If wrong:** A pm2 app that started erroring after the docker restart lost a database connection and didn't reconnect — `pm2 restart <app>` at a step boundary. Check `sec-tenders-api` and `sec-products-api` first, they're closest to the containerised databases.
- **Rollback:** As above.

Finally, once you're satisfied (**wait a week**):

```bash
df -h /
sudo rm -rf /var/lib/docker.old   # Option B
# or, Option A:
sudo rm -rf /var/lib/docker
df -h /
```

- **Does:** Deletes the original tree, realising the space.
- **Healthy:** `/` drops by the full size of the docker tree. This is the moment the 87% figure actually moves.
- **If wrong:** If you delete this and then need to roll back, you're re-pulling images. Hence the week.
- **Rollback:** None after this point.

### 3.2 Move the ollama models

```bash
systemctl cat ollama | grep -E 'Environment|ExecStart|User|Group'
sudo du -sh /usr/share/ollama/.ollama /home/the_bomb/.ollama 2>/dev/null
ollama list
```

- **Does:** Shows how the ollama unit is configured, where its models live (system installs use `/usr/share/ollama/.ollama`; user installs use `~/.ollama`), and what models exist.
- **Healthy:** You can see which path holds the weights and how big it is. On a box also running an embedding server and an OCR VLM, expect 20–80G.
- **If wrong:** If both paths have content, the service and your CLI are looking at different stores — resolve that first or you'll move the wrong one.
- **Rollback:** None needed (read-only).

Pre-stage live (costs nothing, no interruption):

```bash
sudo mkdir -p /mnt/data/ollama/models
sudo rsync -aH --info=progress2 /usr/share/ollama/.ollama/models/ /mnt/data/ollama/models/
sudo du -sh /usr/share/ollama/.ollama/models /mnt/data/ollama/models
```

**Why a restart is unavoidable:** the ollama daemon resolves `OLLAMA_MODELS` at startup and keeps model files open across requests. A bind mount or symlink swap under a live daemon can leave an in-flight request reading a file that no longer resolves. The restart is short — models load lazily, so ollama comes back immediately and the first request per model pays a reload.

**In-window (1–2 minutes):**

```bash
sudo systemctl stop ollama
sudo rsync -aH --delete /usr/share/ollama/.ollama/models/ /mnt/data/ollama/models/
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/override.conf >/dev/null <<'EOF'
[Service]
Environment="OLLAMA_MODELS=/mnt/data/ollama/models"
EOF
sudo chown -R ollama:ollama /mnt/data/ollama 2>/dev/null || sudo chown -R the_bomb:the_bomb /mnt/data/ollama
sudo systemctl daemon-reload
sudo systemctl start ollama
sleep 5
systemctl show ollama -p Environment
ollama list
```

- **Does:** Stops ollama, syncs the delta, adds a systemd drop-in setting the model path, fixes ownership, restarts.
- **Healthy:** `systemctl show` includes `OLLAMA_MODELS=/mnt/data/ollama/models`, and `ollama list` shows the same models as before the move.
- **If wrong:** An empty `ollama list` means it can't read the new path — almost always ownership. Check which user the unit runs as (`systemctl cat ollama | grep User`) and chown to match. `ollama` refusing to start: `journalctl -u ollama -n 50`.
- **Rollback:** `sudo rm /etc/systemd/system/ollama.service.d/override.conf && sudo systemctl daemon-reload && sudo systemctl restart ollama`. The original models are still at `/usr/share/ollama/.ollama/models` until you delete them.

Test an actual inference before deleting the original:

```bash
ollama run <a-model-you-have> "reply with the single word ok" --verbose 2>&1 | tail -5
```

- **Healthy:** A response, and timing that looks like a first-load (slower) followed by normal speed on a second run.
- **If wrong:** Restore via the rollback above.
- **Then, after a day:** `sudo rm -rf /usr/share/ollama/.ollama/models && df -h /`.

### 3.3 Move swap to the NVMe

Only if Phase 1.1 found swap is a **file on `/`**. This frees ~15G on root and moves swap to faster storage.

**Why this needs a window:** `swapoff` on the old area forces 9.8G of pages to fault back into RAM before they can be released. That is minutes of sustained I/O and a transient memory spike, during which everything on the box is slower. It does not stop any service, but it degrades all of them, which is why it belongs here rather than Phase 2.

**The safety mechanism is ordering: add the new swap area before removing the old one.** With a second area active, the kernel can page back out immediately as it faults pages in, so the operation completes without needing 9.8G of free RAM. Doing it in the other order is the `swapoff -a` failure described in the "do not do this" section.

```bash
swapon --show
free -h
```

- **Does:** Confirms starting state.
- **Healthy:** Current swap usage ideally lower than 9.8G after Phase 2's reclaim. If Phase 2 went well, this may be down to 5–7G, which shortens this step considerably.
- **If wrong:** If swap usage is still at or above 9.8G *and* `MemAvailable` is under 5G, postpone — do more Phase 2 reclaim first.
- **Rollback:** None needed (read-only).

```bash
sudo fallocate -l 16G /mnt/data/swapfile || sudo dd if=/dev/zero of=/mnt/data/swapfile bs=1M count=16384 status=progress
sudo chmod 600 /mnt/data/swapfile
sudo mkswap /mnt/data/swapfile
sudo swapon --priority 10 /mnt/data/swapfile
swapon --show
```

- **Does:** Creates a 16G swap file on the NVMe, formats it, and activates it at a **higher priority** than the existing swap (higher number = preferred). New pages now go to the NVMe.
- **Healthy:** `swapon --show` lists two areas: the new one at priority 10, the old one at its default (usually -2). Total swap now 31G.
- **If wrong:** `fallocate` failing on some filesystems (or producing a sparse file the kernel rejects) is why the `dd` fallback is there. `swapon` refusing with "insecure permissions" means you skipped the `chmod 600`.
- **Rollback:** `sudo swapoff /mnt/data/swapfile && sudo rm /mnt/data/swapfile`.

```bash
date -u
sudo swapoff /swap.img
date -u
swapon --show
free -h
```

- **Does:** Deactivates the old swap file. The kernel reads every used page back and either keeps it in RAM or writes it to the new NVMe area.
- **Healthy:** Completes. Duration is roughly (used swap) ÷ (disk throughput), so 9.8G at ~200MB/s is around a minute of pure I/O, realistically 5–20 minutes with contention. Afterwards `swapon --show` lists only the NVMe file, and `free -h` shows total swap 16G with some amount used.
- **If wrong:** If `swapoff` hangs for more than 30 minutes, it is making progress but slowly — check with `watch -n5 'swapon --show; free -h'` and confirm the old area's used figure is falling. **Do not interrupt it**; `swapoff` is not safely cancellable mid-operation. If the box becomes unresponsive and the OOM killer fires, you'll see it in `dmesg -T | tail -50` — this is the scenario the second swap area is meant to prevent, and if it happens anyway, your anonymous working set is larger than you measured.
- **Rollback:** `sudo swapon /swap.img` re-activates the old area at any point before you delete it.

```bash
sudo rm /swap.img
df -h /
sudo cp /etc/fstab /mnt/data/runbook-2026-08-03/baseline/fstab.bak
sudo sed -i '/swap\.img/d' /etc/fstab
echo '/mnt/data/swapfile  none  swap  sw,pri=10  0 0' | sudo tee -a /etc/fstab
sudo swapon --verify-all 2>/dev/null || sudo findmnt --verify --verbose 2>&1 | tail -5
```

- **Does:** Deletes the old swap file (freeing ~15G on `/`), removes its fstab entry, and adds the new one so swap survives reboot.
- **Healthy:** `df -h /` drops by 15G. fstab contains exactly one swap line, pointing at `/mnt/data/swapfile`.
- **If wrong:** **An incorrect fstab prevents the machine booting.** Verify before you ever reboot: `sudo findmnt --verify` should report no errors, and `grep swap /etc/fstab` should show one clean line. If in doubt, add `nofail` to the options. Also confirm `/mnt/data` itself is mounted early enough — check its own fstab entry has no `noauto`.
- **Rollback:** Restore `fstab.bak`. The old `/swap.img` is gone, but you can recreate it with the same `fallocate`/`mkswap` sequence.

Now that memory is stable, consider the swappiness change you deferred in Phase 1.1:

```bash
sysctl vm.swappiness
sudo sysctl -w vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-thebomb.conf
sudo sysctl --system | grep swappiness
```

- **Does:** Biases the kernel away from swapping anonymous pages, and persists it.
- **Healthy:** Reports 10. Over the following days, swap usage should stay flat rather than creeping up.
- **If wrong:** If page cache hit rates fall and container/Postgres latency rises after this, 10 is too aggressive for a box with this much I/O. 20–30 is a reasonable middle. Watch `/proc/pressure/io` for a week.
- **Rollback:** `sudo rm /etc/sysctl.d/99-thebomb.conf && sudo sysctl -w vm.swappiness=60`.

### 3.4 Restart `embed_server.py` (only if a leak was confirmed)

Skip this unless Phase 1.2 showed monotonic RSS growth with no plateau across all 12 samples.

**Why a restart is unavoidable:** there is no way to make a Python process release leaked memory. `gc.collect()` won't return memory the allocator has already claimed from the OS in most leak shapes, and `malloc_trim` only helps a specific fragmentation case. Restart is the fix; the code change is the cure.

**Sequence matters** — pause consumers first, or in-flight requests error:

```bash
pm2 ls --no-color | grep -iE 'indexer|embed|enrich|rag'
pgrep -af tender_doc_indexer
```

- **Does:** Identifies what calls the embed server. `tender_doc_indexer.py` (pid 2676387) is actively working `GEP-RFP-000000188015`; `sec-enrich` and `~/orkes/rag/server.py` are likely callers too.
- **Healthy:** A short list you can pause.
- **If wrong:** If you can't tell what calls it, watch its established connections for a minute: `sudo ss -tnp state established | grep "pid=2652772"` shows the peers.
- **Rollback:** None needed (read-only).

```bash
pm2 stop sec-enrich          # adjust to the actual consumer names
# let the current indexer job finish rather than killing it:
watch -n 10 'pgrep -af tender_doc_indexer || echo "indexer finished"'
```

- **Does:** Stops the enrichment consumer, then waits for the in-flight indexing job to complete on its own.
- **Healthy:** `indexer finished`. Depending on the tender's document count this may take a while — that's why it's in a window.
- **If wrong:** If the indexer runs indefinitely, check whether it's stuck (zero CPU delta over 60s, same technique as Phase 1.3). A stuck indexer is a separate bug; kill it and note it.
- **Rollback:** `pm2 start sec-enrich`.

```bash
pm2 describe embed_server 2>/dev/null || pgrep -af embed_server.py
# if under pm2:
pm2 restart embed_server --update-env
# if not under pm2, it is a bare process — restart it the way it was started:
kill -TERM 2652772
sleep 15
pgrep -af embed_server.py || echo "stopped; start it via its normal launcher"
```

- **Does:** Restarts the embedding server.
- **Healthy:** New pid, RSS back to its baseline (a few hundred MB before models load), and a test embedding request succeeding.
- **If wrong:** If it isn't managed by pm2, you need to know how it was started — check `sudo readlink /proc/2652772/cwd` and the full argv from `tr '\000' ' ' < /proc/2652772/cmdline`. Reconstruct from that. **Put it under pm2 while you're here**, with `max_memory_restart: '4G'`, so the next leak self-heals.
- **Rollback:** Restart it again. There is no state to lose in an embedding server; if it has a persistent index, that lives in a database or on disk, not in the process.

```bash
pm2 start sec-enrich
sleep 30
pm2 ls --no-color
```

- **Does:** Resumes the consumers.
- **Healthy:** `online`, no error spike in `pm2 logs sec-enrich --lines 30 --nostream`.
- **If wrong:** Connection-refused errors mean the embed server isn't listening yet — wait for model load and check its port with `sudo ss -tlnp | grep -i python`.

### 3.5 Fix or retire `buzz-keycloak`

Only if Phase 1.6 concluded it is in use. If it isn't, stop the `buzz` stack in Phase 2.7 and delete this step.

**Why a restart is unavoidable:** a container's healthcheck is baked into its configuration at creation. Changing it requires recreating the container. That is a ~60-second interruption to whatever the Keycloak realm serves.

```bash
cd "$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project.working_dir"}}' buzz-keycloak)" || exit 1
cp docker-compose.yml /mnt/data/runbook-2026-08-03/baseline/buzz-docker-compose.yml.bak
```

Edit the keycloak service to probe the management port, and to use a probe that works in an image without `curl`:

```yaml
  keycloak:
    # ... existing config ...
    environment:
      KC_HEALTH_ENABLED: "true"
      KC_METRICS_ENABLED: "true"
    healthcheck:
      # Keycloak images ship no curl/wget. Bash's /dev/tcp plus a raw HTTP
      # request is the portable way to probe the management port from inside.
      test: ["CMD-SHELL", "exec 3<>/dev/tcp/127.0.0.1/9000; echo -e 'GET /health/ready HTTP/1.1\\r\\nHost: localhost\\r\\nConnection: close\\r\\n\\r\\n' >&3; grep -q '200 OK' <&3"]
      interval: 30s
      timeout: 5s
      retries: 5
      start_period: 90s
```

- **Does:** Enables the management health endpoints and probes port 9000 (where Keycloak 25+ serves `/health/ready`) using only bash builtins.
- **Healthy:** After recreation, `docker ps` shows `Up (healthy)` within `start_period + interval`.
- **If wrong:** If `/dev/tcp` isn't available (some Keycloak base images are further stripped), the alternative is an external healthcheck — drop the container-level healthcheck entirely and monitor from Prometheus (which is already running in this stack on 9092) by scraping `http://buzz-keycloak:9000/metrics`. That is arguably the better answer anyway. A `start_period` under 90s will mark a cold Keycloak unhealthy while it's still legitimately starting.
- **Rollback:** Restore the compose file backup and `docker compose up -d keycloak`.

```bash
docker compose up -d keycloak
sleep 90
docker ps --format '{{.Names}}\t{{.Status}}' | grep keycloak
docker inspect --format '{{json .State.Health}}' buzz-keycloak | python3 -m json.tool | head -20
```

- **Does:** Recreates only the keycloak container, waits out the start period, then reports health.
- **Healthy:** `Up (healthy)` and a `State.Health.Log` entry with `ExitCode: 0`.
- **If wrong:** Read the `Output` field of the most recent failing log entry — it tells you exactly what the probe command printed. Exit code 127 means the command isn't in the image; a connection error means the management interface isn't listening, which means `KC_HEALTH_ENABLED` didn't take.
- **Rollback:** As above.

### 3.6 Optional: reduce `ps aux` exposure with `hidepid`

The reason the token leak was as bad as it was is that `/proc/<pid>/cmdline` is world-readable by default, so the assembled agent prompt was visible to every account on the box. Mounting `/proc` with `hidepid` closes that.

**Read this whole step before running any of it.** `hidepid=2` breaks software that expects to enumerate other users' processes. On a box running docker, lxd, snapd, polkit and systemd-logind, that risk is real.

```bash
findmnt -no OPTIONS /proc
getent group proc || sudo groupadd -r proc
```

- **Does:** Shows current `/proc` mount options and creates a group that will be exempted from the restriction.
- **Healthy:** Current options show no `hidepid` (the default). Group `proc` exists.
- **If wrong:** N/A.
- **Rollback:** None needed.

```bash
sudo mount -o remount,hidepid=invisible,gid=$(getent group proc | cut -d: -f3) /proc
findmnt -no OPTIONS /proc
ps aux | wc -l
sudo ps aux | wc -l
```

- **Does:** Remounts `/proc` so that non-root users see only their own processes, exempting members of the `proc` group. Takes effect immediately, no reboot.
- **Healthy:** As `the_bomb` (uid 1000, who owns nearly everything here) you still see your own processes — which, on this box, is most of them. The difference shows up for any *other* account.
- **If wrong:** Watch for breakage over the next 15 minutes: `systemctl --failed`, `docker ps`, `pm2 ls`, `snap list`. If polkit or logind misbehave (symptoms: `systemctl` hanging, session management errors, sudo becoming slow), revert immediately.
- **Rollback:** `sudo mount -o remount,hidepid=off /proc` — instant, no reboot. **Do not add this to `/etc/fstab` until it has survived a week of normal use**, because a bad `/proc` line in fstab can leave you unable to boot cleanly.

Honest assessment: on a single-user box where `the_bomb` owns every interesting process, `hidepid` buys less than it appears to — it protects against *other* accounts, and there aren't any. The redaction filter from Phase 0.7 is the change that actually prevents recurrence. Treat `hidepid` as defence in depth, and skip it entirely if the breakage risk isn't worth it to you.

### 3.7 Optional: rewrite git history containing the token

Only if Phase 0.4's `git log -S 'cfut_'` found commits, **and** the repository has never been pushed to a remote. If it has been pushed, rewriting local history achieves nothing — rotation was your mitigation, and you already did it.

**Why a window:** the Arbos agents commit to `~/orkes_sec` continuously. Rewriting history under a live committer produces conflicts and lost work.

```bash
cd ~/orkes_sec
git remote -v
git log --all --oneline -S 'cfut_' | wc -l
git status --short | head
```

- **Does:** Confirms whether there's a remote, counts affected commits, and checks the tree is clean.
- **Healthy:** No remotes (or only ones you control and can force-push), a small number of commits, and a clean working tree.
- **If wrong:** A dirty working tree means an agent is mid-work — stop and come back at a step boundary. Any remote you don't control means stop; the exposure is already external.
- **Rollback:** None needed (read-only).

```bash
pm2 stop sec-agent sec-guardian     # anything that commits to this repo
git bundle create /mnt/data/runbook-2026-08-03/orkes_sec-prerewrite.bundle --all
pip install --user git-filter-repo
python3 -m git_filter_repo --replace-text <(echo 'regex:cfut_[A-Za-z0-9_-]{20,}==>[REDACTED-CF-TOKEN]') --force
git log --all --oneline -S 'cfut_' | wc -l
```

- **Does:** Pauses the committers, takes a complete backup bundle, then rewrites every commit replacing the pattern.
- **Healthy:** The final count is `0`. `git log --oneline | head` still shows your recent work with the same messages (commit SHAs will all have changed — that is expected and is the point).
- **If wrong:** `git-filter-repo` refuses to run on a repo with uncommitted changes or without `--force` on a non-fresh clone. If anything goes wrong, `git clone /mnt/data/runbook-2026-08-03/orkes_sec-prerewrite.bundle` restores the pre-rewrite state completely.
- **Rollback:** Restore from the bundle.

```bash
git reflog expire --expire=now --all && git gc --prune=now --aggressive
git log --all --oneline -S 'cfut_' | wc -l
pm2 start sec-agent sec-guardian
pm2 ls --no-color
```

- **Does:** Drops the old objects that the rewrite orphaned, then resumes the agents.
- **Healthy:** `0`, and the agents come back `online`.
- **If wrong:** If an agent errors on startup because commit SHAs it recorded in `STATE.md` no longer exist, edit `STATE.md` to reference the new SHAs or drop the references. This is the main cost of a history rewrite on a repo an agent tracks, and it's a good reason to skip this step entirely if the repo is unpushed and local-only — the token is already dead.
- **Rollback:** Bundle restore, then `pm2 start`.

### Post-window verification

```bash
df -h / /mnt/data
free -h
swapon --show
cat /proc/pressure/memory
uptime
docker ps --format '{{.Names}}\t{{.Status}}' | grep -icE 'up' 
docker ps --filter 'health=unhealthy' --format '{{.Names}}'
docker ps --format '{{.Names}}' | sort | diff - /mnt/data/runbook-2026-08-03/pre-window-containers.txt
pm2 ls --no-color
systemctl --failed
sudo journalctl -p err --since '2 hours ago' --no-pager | tail -30
curl -sS -o /dev/null -w 'harga=%{http_code}\n'  http://127.0.0.1:3647/
curl -sS -o /dev/null -w 'ypages=%{http_code}\n' http://127.0.0.1:3636/
curl -sS -o /dev/null -w 'ocr=%{http_code}\n'    http://127.0.0.1:10100/
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv
```

- **Does:** Full state check against the Phase 1.0 baseline.
- **Healthy:** `/` under 70%. Container list matches the pre-window snapshot. No failed systemd units. No unhealthy containers other than any you deliberately left. All three tunnelled endpoints answering. GPU visible and in use.
- **If wrong:** Work the diffs one at a time against `$BASE/`. Every file in the baseline directory exists precisely for this comparison.

Also confirm from **outside** the box, since the Cloudflare tunnels are the real user-facing path:

- Load `harga.work` in a browser.
- Load `yellowpages.zeidgeist.com`.
- Send a message to the Telegram operator channel and confirm the agent responds.

A green `curl` on localhost with a broken tunnel means `cloudflared` needs a restart — check `systemctl status cloudflared` or `pm2 ls` depending on how it's run.

---

## Do not do this

Each of these is a command you will be tempted to run, or will find recommended in a generic tutorial. Each is wrong on this specific host.

### `docker system prune -a`

**What it looks like:** the obvious way to reclaim docker space.

**What it does here:** `-a` removes every image not used by a **running** container. You are about to stop roughly a dozen dormant stacks in Phase 2.7. The moment those containers are stopped, their images become "unused" — and this command deletes them. Several of those stacks are 3–4 months old: `bocra`, `obtener`, `cbaas`, `bungaraya`, `beslut`, `people-search`. If any of their images were built locally and never pushed to a registry — which is the normal case for private project images — **they cannot be recovered.** Your `docker compose start` restore path evaporates and you're rebuilding from a Dockerfile that may no longer build with today's upstream base images.

Adding `--volumes` is worse: it destroys the data volumes behind every stopped Postgres, Redis, and MinIO in that set.

**Do instead:** `docker image prune -f` (dangling only) and `docker builder prune --filter until=336h`, both in Phase 2.2. They reclaim most of the same space and cannot delete a tagged image.

### `swapoff -a && swapon -a`

**What it looks like:** the standard "reset swap" incantation.

**What it does here:** `swapoff` must read every used page back into RAM before it can release the area. You have 9.8G used and 647Mi free. The kernel will reclaim page cache to make room — that's the 18Gi of `buff/cache` that is currently making 45 containers and several Postgres instances fast — and when that isn't enough, it invokes the OOM killer.

The OOM killer picks the highest `oom_score`, which on this box is whichever process has the largest resident anonymous footprint: `embed_server.py` at 1.78G, or a `claude -p` agent loop. Killing an agent mid-step in `orkes_sec` while it's working the harga vX plan is precisely the outcome the whole "no downtime" constraint exists to prevent. And the box will be near-unresponsive for the several minutes it takes.

**Do instead:** don't target swap at all in Phase 2 — reduce the anonymous working set and let swap drain naturally. If you genuinely need the swap area moved, Phase 3.3 does it safely by activating a second area *first*, so the kernel always has somewhere to put pages.

### `rm -rf ~/.cache`

**What it looks like:** a cache is by definition disposable.

**What it does here:** `~/.cache` has 52 subdirectories and is not homogeneous. It holds HuggingFace model weights (potentially tens of GB, hours to re-download), `torch` checkpoints, Playwright browser binaries, and possibly ollama blobs. It may also hold the `uv` and `pypoetry` stores that some venvs on this box reference by hard link — deleting those can break an installed environment, not just slow a rebuild. And `embed_server.py` and `ocr_server.py` are running right now with model files open under there; ripping the tree out from under a live process gives you a half-working service that fails on its next model load rather than immediately, which is worse than a clean crash.

**Do instead:** Phase 2.5 — measure each subdirectory, check for open files, rsync to `/mnt/data`, symlink, verify, and only then delete the original after 48 hours.

### `echo 3 > /proc/sys/vm/drop_caches`

**What it looks like:** frees memory instantly. `free -h` will show a dramatic improvement.

**What it does here:** discards 18Gi of page cache that is actively serving 45 containers, eight-plus Postgres instances, and the model files of three inference services. Every one of them then re-reads from disk. You get a latency spike across the whole box lasting minutes to tens of minutes while the cache refills, in exchange for a number in `free -h` that means nothing — cache is already "available" memory, which is why `MemAvailable` reads 18Gi.

It also does not free a single byte of swap, which was the thing you were trying to fix.

**Do instead:** nothing. Page cache is not a leak.

### `kill -9` on a pm2 `claude -p` agent process

**What it looks like:** the fast way to reclaim memory from an agent that's grown large.

**What it does here:** SIGKILL cannot be caught, so the process dies between writes. The Arbos loops write `STATE.md` and `context/runs/<timestamp>/` as they progress; killing mid-write leaves a truncated state file. pm2 then restarts the app, which reads that torn state and either re-runs a partially-applied step or resumes from a position that doesn't match reality. `orkes_sec` is mid-implementation of the 7-phase harga vX plan with Phase 1 just committed — a re-run of a partially-applied phase against a database is expensive to unpick.

**Do instead:** `pm2 stop <app>` at a step boundary (SIGTERM with pm2's kill timeout, which lets the loop finish). Check `STATE.md` and the newest `context/runs/` directory to confirm you're between steps. If you need the memory urgently, the abandoned `opencode` processes in Phase 2.3 give you ~1.9G with no such risk.

### `pm2 kill`, `pm2 update`, or `pm2 restart all`

**What it looks like:** a clean way to refresh the pm2 fleet.

**What it does here:** takes down every named service simultaneously — `sec-proxy` 3641, `sec-sched-api` 3642, `sec-failsafe` 3643, `sec-products-api` 3644, `sec-tenders-api` 3646, `sec-enrich` 3650, the schedulers and the agents, plus the yellowpages gunicorn on 3636. Both Cloudflare tunnels start returning 502 immediately: `harga.work` (→3647) and `yellowpages.zeidgeist.com` (→3636). `pm2 kill` additionally stops the pm2 daemon itself, and if `dump.pm2` is stale, `pm2 resurrect` brings back a *different* set of apps than you had.

**Do instead:** restart individual apps by name, one at a time, verifying each. If you must refresh the pm2 daemon, do it in a window and `pm2 save` first.

### `docker compose down` on a dormant stack

**What it looks like:** the counterpart to `up`.

**What it does here:** removes containers and networks. With `-v` it removes volumes, and that is the one irreversible action in this entire runbook — the Postgres data behind `bocra`, `obtener`, `beslut`, `bayu-main-db`, `cbaas` and `tender-automation` lives in those volumes. Even without `-v`, you lose the container definitions, which means restoring requires the compose file to still be present and still resolve the same images.

**Do instead:** `docker compose stop`. It's reversible with `docker compose start`, takes seconds, and touches nothing.

### `apt autoremove --purge` without reading the list

**What it looks like:** routine cleanup.

**What it does here:** this box has an NVIDIA GPU with `nvidia-persistenced` and `ollama` depending on the driver stack, which is DKMS-built against kernel 6.8.0-136. `autoremove` occasionally proposes removing kernel headers or a driver metapackage that DKMS needs, and on a headless box you find out at the next reboot when the GPU doesn't come up.

**Do instead:** run it, **read the list of packages it proposes**, and only confirm if nothing containing `nvidia`, `dkms`, `linux-headers` for the running kernel, or `linux-image` for the running kernel appears. `uname -r` tells you which kernel must be preserved.

### Deleting anything under `/var/lib/docker` by hand

**What it looks like:** you found a huge directory under `overlay2` and it belongs to a container you don't recognise.

**What it does here:** the overlay2 tree is an index-plus-content store. dockerd's metadata database records which layer directories belong to which image and container. Removing a directory by hand desynchronises them, and the symptoms are confusing and delayed — containers that won't start, images that report as present but fail to run, a daemon that errors on operations unrelated to what you deleted.

**Do instead:** `docker image prune`, `docker builder prune`, and for the big win, the Phase 3.1 relocation. Let the daemon manage its own store.

### Running the Phase 0 search with the token on the command line

Restating it because it's the specific trap this incident sets: `grep -r "$LEAKED_TOKEN" ~` puts the expanded value in the new process's `argv`, which is world-readable via `/proc/<pid>/cmdline` for the life of the grep. On a large home directory that grep runs for minutes. You would be re-committing the exact leak you're cleaning up, in the act of cleaning it up.

**Do instead:** search by prefix pattern (`cfut_[A-Za-z0-9_-]{20,}`), or put the value in a tmpfs file and use `grep -f`. Both are in Phase 0.4.

---

## Appendix A — space ledger

Fill in the measured column as you work Phase 1.5, then track what you actually recover. Target: get `/` from 87% (772G used) to under 70% (under 655G used), which means finding **at least 117G**, and 160G to have margin.

| Source | Where measured | Estimated | Measured | Recovered | Phase |
|---|---|---|---|---|---|
| Docker images (dangling) + build cache | `docker system df`, `docker builder du` | 10–60G | | | 2.2 |
| Container json logs | per-container `LogPath` | 1–20G | | | 2.6 (truncate), 3.1 (rotation) |
| apt cache | `du -sh /var/cache/apt` | 0.5–2G | | | 2.2 |
| Old snap revisions | `snap list --all` | 2–8G | | | 2.2 |
| journald | `journalctl --disk-usage` | 1–4G | | | 2.2 |
| pip / npm / uv / conda / cargo caches | `du -sh` each | 5–20G | | | 2.2 |
| Loose `$HOME` files (tarballs, n8n.log, heapsnapshot) | `ls -lah ~` | 0.63G | 0.63G | | 2.4 |
| HuggingFace cache | `du -sh ~/.cache/huggingface` | 10–60G | | | 2.5 (relocate) |
| Other model caches (EasyOCR, torch, crawl4ai) | `du -sh` each | 2–15G | | | 2.5 (relocate) |
| Playwright / puppeteer browsers | `du -sh ~/.cache/ms-playwright` | 2–6G | | | 2.5 (relocate) |
| android-sdk, swift, gcloud sdk | `du -sh` each | 15–50G | | | 2.5 (relocate) |
| `node_modules` in inactive projects | find + du | 5–40G | | | 2.5 (delete, lockfile-backed) |
| Dormant container stacks (writable layers) | `docker ps -s` | 1–10G | | | 2.7 |
| **Docker data-root relocation** | `du -sh /var/lib/docker` | **50–300G** | | | **3.1** |
| Swap file on `/` | `swapon --show` | 15G | | | 3.3 |
| Ollama models | `du -sh` model dir | 20–80G | | | 3.2 |

The two rows in bold-adjacent territory — docker data-root and ollama models — are where this is won or lost. Everything above them is worth doing and none of it individually gets you to 70%.

## Appendix B — verification checklist

Run this at the end of each phase and compare against `$BASE/`.

```bash
BASE=/mnt/data/runbook-2026-08-03/baseline
echo "=== disk";      df -h / /mnt/data | tail -3
echo "=== memory";    free -h
echo "=== swap";      swapon --show
echo "=== pressure";  cat /proc/pressure/memory
echo "=== load";      uptime
echo "=== failed";    systemctl --failed --no-pager
echo "=== pm2";       pm2 ls --no-color
echo "=== unhealthy"; docker ps --filter 'health=unhealthy' --format '{{.Names}}\t{{.Status}}'
echo "=== restarting"; docker ps --format '{{.Names}}\t{{.Status}}' | grep -i restarting || echo none
echo "=== container count"; docker ps -q | wc -l
echo "=== endpoints"
for p in 3641 3642 3643 3644 3646 3647 3636 10100 9100; do
  printf '  :%-6s %s\n' "$p" "$(curl -sS -o /dev/null -m 5 -w '%{http_code}' http://127.0.0.1:$p/ 2>&1)"
done
echo "=== restart counts vs baseline"
diff <(pm2 ls --no-color | awk '{print $2, $12}') <(awk '{print $2, $12}' "$BASE/pm2.txt") || echo "  (differences above)"
```

The line that matters most is the pm2 restart-count diff. If it's empty, nothing you did disturbed a live service — which is the entire point of the phasing.

## Appendix C — quick reference: what runs where

| Port | Service | Managed by | Exposure |
|---|---|---|---|
| 3636 | Yellowpages CRM (Flask/gunicorn) | pm2 | Cloudflare tunnel → yellowpages.zeidgeist.com |
| 3641 | sec-proxy | pm2 | internal |
| 3642 | sec-sched-api | pm2 | internal |
| 3643 | sec-failsafe | pm2 | internal |
| 3644 | sec-products-api | pm2 | internal |
| 3646 | sec-tenders-api | pm2 | internal |
| 3647 | harga.work backend | pm2 | Cloudflare tunnel → harga.work |
| 3650 | sec-enrich | pm2 | internal |
| 10100 | Unlimited-OCR VLM | host process | internal |
| 9100 | authentik server | docker | SSO for other stacks |
| 3030 | cbaas caddy | docker | 4-month-old stack |
| 5433–5438 | assorted Postgres | docker | one per stack |
| 6380, 16379, 16380 | assorted Redis | docker | one per stack |
| 7233 | tender-automation temporal | docker | 4-month-old stack |
| 7843 | waha (WhatsApp API) | docker | 4 days old — likely active |
| 8084 | adminer (buzz) | docker | admin UI |
| 8383 | people-search | docker | 3-month-old stack |
| 8400 | beslut-backend | docker | 3-month-old stack |
| 8787 | bungaraya caddy | docker | 4-month-old stack |
| 9001/9002 | minio (buzz) | docker | object storage — check consumers |
| 9092 | prometheus (buzz) | docker | could monitor keycloak instead of a healthcheck |
| 18080 | ops-app | docker | 3-month-old stack |
| — | ollama | systemd | GPU inference |
| — | nvidia-persistenced | systemd | GPU |
| — | tailscaled | systemd | 100.108.103.5 — your access path, do not disturb |

Services never to interrupt outside a declared window: everything on 3636–3650, 10100, 9100, plus `tailscaled` (it is how you reach the box) and `sshd`.

---

*Runbook ends. Work Phase 0 today. Phases 1 and 2 can be spread across a week. Book the window for Phase 3 once Phase 2 has soaked for 48 hours.*

