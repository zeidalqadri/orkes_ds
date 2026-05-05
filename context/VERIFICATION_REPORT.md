# SmartGEP v2 Option C — Verification Test Report
Date: 2026-04-29 06:50 UTC
Status: **COMPLETE — definitive result**

## What Was Tested
HTTP-only price sheet row extraction (Option C) — using `requests.Session` with
GEP auth cookies to fetch `/data/psevent/` and `doGetPricesheet` endpoints,
bypassing Playwright entirely.

## Test Results

### ✅ Full Auth & Navigation (via Playwright)
- Login to idplogin.gep.com → businessnetwork.gep.com → smart.gep.com: **OK**
- RFX listing page loaded: **OK** (1,980+ tenders visible)
- Listing interceptor captures event map: **OK**

### ❌ HTTP-Only Path (Option C)
| Test | Result |
|------|--------|
| `bootstrap_smart_session()` | OK (SMART cookies acquired) |
| SPA page load (Sourcing/Rfx) | OK (200, 199KB HTML) |
| `/data/psevent/{id}` via HTTP | **FAIL** (IIS 500) |
| `doGetPricesheet` via HTTP (5 patterns) | **FAIL** (all 404) |
| `arrprodus.eastus.cloudapp.azure.com` via HTTPS | **FAIL** (connection refused / SSL error) |
| /data/ endpoints with XSRF-TOKEN header | **FAIL** (still 500) |
| Even with fresh cookies (seconds old) | **FAIL** (still 500) |

## Root Cause
The `/data/` API tier on `smart.gep.com` requires the **Angular SPA's full
browser context** — including JavaScript-set cookies, CSRF tokens, and HTTP
interceptor headers that `requests.Session` cannot replicate. The
`SmartAuth0` cookie alone is insufficient; the SPA bootstrap process sets
additional context that enables the `/data/` endpoints.

## Recommendation
- **Use the existing Playwright-based approach** (smartgep_v2.py) for price
  sheet row extraction. The `fetch_psevent_direct` and `fetch_pricesheet_rows`
  functions already work via `page.evaluate()`.
- HTTP-only shortcut is not viable for the `/data/` tier on this portal.
- To extract real price sheet rows with material specs, run:
  `python -m scrapers.smartgep_v2 pricesheets --event GEP-XXXXX --account consurv`
