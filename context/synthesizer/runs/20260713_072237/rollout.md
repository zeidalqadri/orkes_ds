Here's the status:

## Fleet Health (2026-07-13 07:30 MYT)

| Process | Status | Restarts | Memory | Uptime | Notes |
|---------|--------|----------|--------|--------|-------|
| harga | online | 228 | 15MB | 7.7h | Gunicorn worker auto-cycling (normal). v7 health = 200 |
| yellowpages | online | 14 | 341MB | 31h | Stable |
| rag-server | online | 1 | 375MB | 92h | Recovered from W27's 32-restart regression |
| embed-server | online | 1 | 157MB | 41.7h | Stable |
| ocr-server | online | 4 | 1.2GB | 67h | Stable |
| arbos-orkes | online | 59 | 183MB | 21h | Currently running W29 synthesizer step |
| arbos-orkes_ds2 | online | 5 | 39MB | 68h | Currently running W29 synthesizer step |
| token-carousel | online | 2 | 123MB | 92h | Stable |

## Jul 12 "Check" 401 Diagnosis

The 401 came from **arbos-orkes** (not ds2). The logs show:
- `proxy: chutes returned 401 (attempt 3/3): {"detail":"Unauthorized"}` — the DeepSeek/Mistral proxy backend rejected the request
- `streaming: API error ... mistral routing failed (401)` — routing layer auth failure

This was a **transient proxy/routing auth failure**, not a Claude API issue. The ds2 bot's oauth tokens have been healthy throughout (no auth errors in its logs).

## Current Activity

Both `arbos-orkes` and `arbos-orkes_ds2` are **actively running W29 weekly synthesis** right now (started ~07:22 MYT). The CONNECTIONS.md will be updated when they complete.

## Notable Changes Since W27

- **rag-server**: Recovered — down from 32 restarts to 1, memory stable at 375MB
- **harga**: 228 PM2 restarts looks alarming but the error logs show normal gunicorn `max_requests` worker cycling, not crash-looping. Currently serving fine (`/api/harga-v7/health` = 200)
- **Stale worktree warning**: Both bots hit `fatal: '/tmp/orkes-worktrees/synthesizer' is a missing but already registered worktree` — non-blocking (they fell back to main), but should be cleaned up with `git worktree prune`

Want me to clean up the stale worktree, or anything else?