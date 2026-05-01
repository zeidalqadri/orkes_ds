# Elliot Reconnaissance Report — 2026-05-01

## Phase 1: Initialization Complete

### Systems Surveyed

| System | Path | Status |
|--------|------|--------|
| SmartGEP v2 Scraper | `/home/the_bomb/orkes/yellowpages/scrapers/smartgep_engine_v2/` | Engine intact, auth broken |
| Orkes DS Pipeline | `/home/the_bomb/orkes_ds/` | Triager functional, BoQ extractor idle |
| Alumni Platform | `/home/the_bomb/tronzz/` | All 7 services UP (backend, celery_worker, celery_beat, searxng, postgres, redis, meilisearch) |
| Expert Fleet | `context/experts.json` | 17 experts registered, 0 activated |

---

## Phase 1.1 — SmartGEP Attack Surface Map

### Ingress Points

| # | Entry Point | URL | Auth Required | Attack Vectors |
|---|-------------|-----|---------------|----------------|
| 1 | BizNet SSO Gateway | `businessnetwork.gep.com` | SAML/OIDC | Session replay, cookie injection, SSO redirect hijack |
| 2 | GEP IDP Login | `idplogin.gep.com` | Username/Password | Credential stuffing (locked), selectors brittle |
| 3 | Smart STS Redirect | `smart-sts.gep.com` | OIDC token exchange | **Current blocker** — daemon stuck in this redirect loop |
| 4 | SmartGEP SPA | `smart.gep.com` | netsessionid (heap) | Token extraction via page.evaluate(), SPA route bypass |
| 5 | Azure /data/ Tier | `smart.gep.com/data/*` | netsessionid + RVT | Direct HTTP with daemon tokens, response interception |
| 6 | Listings API | `businessnetwork.gep.com/supplynetwork/api/SupplyNetworkHome/GetMyTasksDocumentsV2` | Session cookies | Cookie replay from daemon, XHR-intercept capture |
| 7 | Price Sheet API | `smart.gep.com/data/psevent/{id}` | netsessionid + RVT | SPA-only — requires Playwright navigation for child sheets |

### SSO Redirect Chain (Observed)

```
browser → businessnetwork.gep.com
  → 302 → smart-sts.gep.com/Authenticate?ReturnUrl=...  ← DAEMON STUCK HERE
  → OIDC challenge
  → idplogin.gep.com (username/password form)
  → 302 → businessnetwork.gep.com/BusinessNetwork/Landing/v2#/bn-landing
```

**CRITICAL**: The daemon is stuck on `smart-sts.gep.com/Authenticate` — it got redirected but never resolved the OIDC challenge. The login form is at `idplogin.gep.com`, one redirect deeper. The daemon's `_ensure_login` selector `input[id="userId"]` targets the idplogin page, but the page is still on smart-sts.

### Rate Limiting & Anti-Automation

| Countermeasure | Trigger | Bypass |
|---------------|---------|--------|
| CAPTCHA | Repeated failed login | Visible browser (headless=false), session reuse |
| 429 Rate Limit | >N requests/min to /data/ | Multi-account rotation, exponential backoff |
| Headless Detection | Automated browser flags | `--disable-blink-features=AutomationControlled`, playwright-stealth |
| Token Expiry | ~8-10 min idle | Cookie Monster refresh loop (currently broken) |
| Smart STS IP reputation | Rapid SSO auth attempts | Cookie caching, session reuse |
| SPA Route Guards | Direct HTTP to /data/ without SPA init | Playwright SPA navigation → token extraction → HTTP replay |

---

## Phase 1.3 — Alumni Platform Attack Surface

| # | Entry Point | Status | Notes |
|---|-------------|--------|-------|
| 1 | Backend API (FastAPI) | UP | tronzz-backend-1, running 5 days |
| 2 | SearXNG | UP (healthy) | tronzz-searxng-1, 2 days |
| 3 | Celery Worker | UP | tronzz-celery_worker-1, 5 days |
| 4 | Celery Beat | UP | tronzz-celery_beat-1, 5 days |
| 5 | Postgres (alumni) | UP (healthy) | tronzz-postgres likely in the stack |
| 6 | Caddy Reverse Proxy | UP | tronzz-caddy, 32 hours |
| 7 | Meilisearch | UP | search index service |
| 8 | LinkedIn Harvesting | IDLE | No active harvester, no SERP crawl running |

No immediate vulnerabilities. All services healthy. The pipeline is idle, not broken.

---

## Phase 1.4 — Existing Countermeasures Catalog

| Countermeasure | Type | File | Status |
|---------------|------|------|--------|
| Cookie Monster Daemon | Persistence | `/home/the_bomb/orkes_ds/permauth.py` | **BROKEN** (see Phase 1.5) |
| Cookie File Cache | Persistence | `scrapers/data/smartgep_cookies_consurv.json` (21425 bytes) | Fresh (May 1 13:32) but from dead session |
| Stale Cookie Backup | Fallback | `scrapers/data/smartgep_cookies_consurv.json.stale` (15204 bytes) | From Apr 29 |
| Multi-Account Rotation | Anti-rate-limit | 5 accounts (3 enabled: consurv, dyna-om-petronas, dyna-segmen; 2 disabled: ctventures, dyna-sche) | Only consurv + dyna-om-petronas have cookie files |
| playwright-stealth | Anti-detection | `smartgep_scraper.py:47-49` | Available, conditionally loaded |
| Headless Chrome Flags | Anti-detection | `permauth.py:134`, `extract_boq.py:54-58` | `--disable-blink-features=AutomationControlled`, `--no-sandbox` |
| Token Extraction (JS eval) | Token harvest | `permauth.py:555-582` | `rfx.resources.constants.netsessionid` — only works on SPA pages |
| BoQ Checkpointing | Resume | `batch_boq_extractor.py:80-88`, `extract_boq.py CHECKPOINT_FILE` | Prevents re-extraction of completed events |
| Event ID Map | Routing | `data/pricesheet_extract/event_id_map.json` | 6 RFX events with doc_urls |

### Multi-Account Status

| Account ID | Enabled | Cookies File | daemon_session_configured |
|------------|---------|-------------|--------------------------|
| consurv | Yes | Yes (21425 bytes) | Yes (permauth.py default) |
| dyna-om-petronas | Yes | Yes (exact size unknown) | No (v2 permauth only) |
| dyna-segmen | Yes | **MISSING** | No |
| ctventures | No | No | No |
| dyna-sche | No | No | No |

---

## Phase 1.5 — What's Broken

### [!] CRITICAL — Cookie Monster Daemon Session Dead

```
daemon pid: 2049380
uptime: ~4 hours
http://localhost:9876/health → {"alive":true, "tokens_valid":false, "spa_available":false}
http://localhost:9876/tokens  → {"netsessionid":"", "requestverificationtoken":"", "oloc":"", "cookies":[...40 cookies...]}
```

**Root Cause**: The daemon navigates to `businessnetwork.gep.com`, gets redirected to `smart-sts.gep.com/Authenticate`, and the interactive login flow can't find the username field because:
1. `_ensure_login()` is never called during `_init_browser()` when the SSO redirect is detected — the code at line 210 checks for `smart-sts` but only logs and calls `_ensure_login()`, which navigates AGAIN to biznet (restarting the redirect loop).
2. The username selector `input[id="userId"]` exists on `idplogin.gep.com`, but the page is at `smart-sts.gep.com/Authenticate` — a Microsoft STS intermediate page that requires JavaScript to complete the OIDC challenge, not a form fill.

**Impact**: Every scraper that calls the daemon gets zero tokens. The entire BoQ pipeline, extract_boq.py, batch_boq_extractor.py, finale.py — all dead.

### [!] HIGH — Missing Cookie File for dyna-segmen

dyna-segmen is `enabled: true` but has **no cookie file** in `scrapers/data/`. The v2 multi-account permauth relies on pre-existing cookies to bootstrap sessions. Without a cookie file, this account can't be used for rotation.

### MEDIUM — 96.4% of Manifest is P2P Orders (Not Scrapable for BoQ)

640 events in manifest: 6 RFX (0.9%), 636 P2P Orders (99.1%)
- P2P orders have no Materials/Price Sheet tab — BoQ extraction not applicable
- Only 6 RFX events exist total — very narrow target surface
- BoQ coverage: 3 HAS_BOQ (online extraction), 2 BOQ_IN_DOCS (xlsx fallback), 1 NO_BOQ_ANYWHERE

### MEDIUM — No Active Enrichment Pipeline

The alumni platform is running but no enrichment/harvesting is active. All 17 experts at 0 steps.

### LOW — bot.json Expert Sources Desync

Already fixed — changed from `["global","local"]` to `["local"]` in prior action.

---

## Phase 1.6 — Available Fleet for Coordination

| Priority | Expert | Current Utility |
|----------|--------|----------------|
| P1 | builder | Docker restarts, service management, log inspection |
| P1 | debugger | Pipeline error diagnosis |
| P1 | harvester | LinkedIn SERP crawl (idle) |
| P2 | guardian | DB backup verification |
| P2 | ops | Infrastructure health (all healthy currently) |
| P2 | reporter | Progress reports |
| P2 | scheduler | Pipeline orchestration |
| P2 | **elliot** | **This recon report. Fix daemon auth, scraper bypass.** |
| P3 | architect, codex, qa, tdd, designer | Not needed for current fix |

---

## Phase 2 — Fix Plot

| # | Priority | Target | Component | Flaw | Impact | Fix | Dependencies | Effort |
|---|----------|--------|-----------|------|--------|-----|-------------|--------|
| **1** | **[!] CRITICAL** | SmartGEP | Cookie Monster Daemon (`permauth.py`) | Daemon stuck on `smart-sts.gep.com/Authenticate` — OIDC redirect never resolves. `_ensure_login()` can't find username selector because it targets `idplogin.gep.com` but page is at `smart-sts`. | Entire scraper pipeline dead. Zero tokens served. No BoQ extraction possible. All 6 RFX events unreachable. | **[a]** Fix `_init_browser()` to properly detect the SSO state and call `_ensure_login()` early. **[b]** In `_ensure_login()`, wait for `idplogin.gep.com` to load before targeting selectors — add a `wait_for_url("**idplogin**")` before attempting form fill. **[c]** Add OIDC wait: smart-sts does JS-based redirect — need `wait_for_timeout` + URL polling to catch the transition. | None (self-contained fix) | MEDIUM |
| **2** | **[!] HIGH** | SmartGEP | `dyna-segmen` Account Bootstrap | No cookie file exists. Account is `enabled: true` but can't be used for rotation. | Only 2 accounts usable (consurv + dyna-om-petronas). 33% rotation capacity lost. Rate limit exposure higher. | Run a fresh Playwright login for dyna-segmen to generate `smartgep_cookies_dyna-segmen.json`. If 2FA blocks it, disable the account in `smartgep_accounts.json`. | builder (to run playwright login) | LOW |
| **3** | MEDIUM | Orkes DS | `permauth.py` Token Extraction | `_extract_tokens()` runs `rfx.resources.constants.netsessionid` which only exists on SPA pages. If daemon stays on BizNet (can't reach smart.gep.com), netsessionid is always empty. | Direct API calls to `/data/` tier fail without netsessionid. Only BizNet listings API works with cookies-only auth. | Add fallback: if netsessionid extraction fails, the daemon should still serve cookies-only mode. Update `/health` to report `spa_available: false` (already done). Update scrapers that only need cookies (listing fetch) to use daemon even without netsessionid. | None | LOW |
| **4** | MEDIUM | SmartGEP | Headless Detection Bypass | Daemon runs `headless=true`. SmartGEP may have updated detection since daemon was built. `playwright-stealth` is imported but may not be applied to the daemon's context. | Session detection, CAPTCHA triggers, account flagging. | Add `stealth_async` call to daemon's `_init_browser()` after context creation. Test with headless=true vs headless=false and compare login success rate. | None | LOW |
| **5** | MEDIUM | Orkes DS | BoQ Coverage Gaps | Only 3/6 RFX events have BoQ extracted online. 2 have doc-based BoQ (xlsx). 1 has NO_BOQ_ANYWHERE. | Missing BoQ data for 3 events. RFP-000000178027 has zero BoQ coverage. | Run full BoQ extraction after daemon fix. For NO_BOQ_ANYWHERE event, manually verify Materials tab existence. If tab is absent, check CREMA documents for embedded BoQ tables. | builder, debugger | LOW |
| **6** | LOW | SmartGEP | dyna-om-petronas Cookie Staleness | Unknown when last refreshed. Cookie file exists but may be expired. | Backup account may not work if cookies expired. | Verify cookie file age > refresh. If >1 day old, run fresh login. | None | LOW |
| **7** | LOW | Alumni Platform | Idle Pipeline | All services running but no active enrichment/harvesting. harvesters, enrichers at 0 steps. | Data pipeline stagnant. No new alumni profiles being discovered or enriched. | Activate harvester (P1) and enricher (P1) experts. But do this AFTER SmartGEP scraper is fixed — don't compete for resources. | scheduler, harvester, enricher | MEDIUM |

---

## Immediate Action

**Fix #1 first** — the Cookie Monster daemon is the single point of failure. Everything downstream depends on it. The fix is a ~50-line patch to `permauth.py`:

1. In `_init_browser()`: after detecting SSO redirect (line 210), call `_ensure_login()` BEFORE navigating to BizNet landing (line 220) — the current order navigates to landing first, which re-triggers the redirect loop
2. In `_ensure_login()`: add `await self.page.wait_for_url("**idplogin**", timeout=30000)` before targeting username selectors
3. Add a `wait_for_url("**businessnetwork**")` after login submission to confirm redirect completed

### Fix #1 Detailed Patch Plan (permauth.py)

**File**: `/home/the_bomb/orkes_ds/permauth.py`

**Change at ~line 192-216** (`_init_browser` — SSO detection):
```python
# CURRENT (broken): detects smart-sts but then navigates to biznet landing
# which restarts the redirect loop

# FIX: if SSO detected, do login FIRST, then navigate to landing
if not nav_ok:
    await self._ensure_login()
elif any(h in current_url for h in ["smart-sts", "idplogin", "login", "authenticate"]):
    await self._ensure_login()
# THEN navigate to biznet landing (only if login succeeded)
```

**Change at ~line 338-361** (`_ensure_login` — login flow):
```python
# ADD before username selector:
await self.page.wait_for_url("**idplogin**", timeout=30000)
# If still on smart-sts (not redirected to idplogin), wait longer
if "smart-sts" in self.page.url.lower():
    await self.page.wait_for_timeout(15000)  # OIDC JS redirect
```

**Change at ~line 392-409** (post-login wait):
```python
# ADD explicit wait for redirect completion:
await self.page.wait_for_url("**businessnetwork**", timeout=60000)
```

---

## Dependencies for Fixes

```
Fix #1 (Daemon Auth) ← NO dependencies, fix first
    ↓
Fix #2 (dyna-segmen Bootstrap) ← can run in parallel with #3-#5
    ↓
Fix #3-#5 (Token Fallback, Stealth, BoQ Coverage) ← depend on #1
    ↓
Fix #7 (Alumni Pipeline) ← depends on resource availability, no code dep
```

Fix #1 must succeed before anything else. If the daemon can't authenticate, the entire scraper pipeline has zero value.
