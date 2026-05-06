# DeepThink: SmartGEP Scraper Replacement

## Current State

The SmartGEP scraper uses Playwright (headless Chromium) for two things:
1. **Auth** — Login to SmartGEP portal, maintain SSO session (permauth daemon)
2. **Data fetching** — Navigate SPA pages, extract psevent data, fetch price sheets

## Memory Cost of Playwright

- **permauth daemon** (uptime 42h): 1 Chromium instance → 8-10 child processes
- **Scraper runs**: 1 additional Chromium instance per scrape cycle
- **Total**: 19 Chromium processes consuming ~800MB+ resident memory
- **Swap pressure**: 7.7GB/8GB used — Playwright Chromium is a significant contributor

## Existing Alternative: HTTP-Only Transport

`smartgep_http.py` (smartgep_engine_v2/) already provides:

| Capability | Playwright | HTTP-Only |
|---|---|---|
| Auth/Login | `permauth.py` (browser) | `bootstrap_smart_session()` (requests) |
| Listing fetch | Page navigation | `fetch_listing_page_http()` POST |
| Event detail | SPA interaction | `fetch_psevent_http()` GET/POST |
| Attachments | Click-to-download | `fetch_attachments_http()` GET |
| Price sheets | UI scrape | `PricesheetRowParser` via HTTP |
| Cookie management | Browser context | `build_http_session()` + session refresh |

**Key insight**: `bootstrap_smart_session()` performs the SAML/OIDC redirect chain via `requests.Session.get()` with `allow_redirects=True` — no JavaScript execution needed. The server sets `smart.gep.com` cookies on the session automatically.

**Only one function requires Playwright**: `extract_smart_cookies_from_browser()` — which can be replaced by `bootstrap_smart_session()` + `_has_smart_session_cookies()`.

## Hybrid Approach (Already Prototyped in scrapling_boq.py)

```
permauth daemon (initial auth only, then kill browser)
       │ GET /tokens
       ▼
scrapling_boq.py (HTTP-only data extraction)
       │
       ▼
bootstrap_smart_session() (cookie refresh, no browser)
```

## Recommended Migration Plan

### Phase 1: Permauth → Cookie Farm (low risk)
- Keep permauth daemon for initial login
- After successful login, immediately close browser context
- Refresh cookies via `bootstrap_smart_session()` every 10 min
- Only restart browser if refresh fails 3x consecutive
- **Memory impact**: Zero Chromium processes 99% of the time

### Phase 2: HTTP-First Scraper (medium risk)
- Refactor `smartgep_scraper.py` to try HTTP path first (`smartgep_http.py`)
- Fall back to Playwright only if HTTP fails
- Remove hard Playwright dependency from the codebase
- **Memory impact**: Eliminates per-scrape Chromium startup

### Phase 3: Fully Stateless (higher risk)
- Replace permauth entirely with `bootstrap_smart_session()`
- Store cookies in a file, refresh before each scrape cycle
- No persistent daemon needed
- **Memory impact**: -80MB permanent, -800MB peak

## Recommendation

**Proceed with Phase 1 immediately** — it's low risk, high impact:
- Frees ~800MB of resident memory
- Eliminates 19 Chromium processes
- Reduces pm2 restart count (Playwright asyncio crashes caused 58 restarts)
- No functional change to scraper output

Phase 2 can be done in parallel by adapting existing `scrapling_boq.py` patterns.
