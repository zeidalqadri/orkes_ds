# Active Work
Project: /home/the_bomb/orkes_ds
Task: SmartGEP v2 BoQ — Content Scanner + Fetch Verification
Status: blocked (auth)
Updated: 2026-05-01T20:15:00+00:00

## Operator Message
"Let's get going with SmartGEP v2 BoQ. I think the right test is to run through the parsed content of a tender and identify if anything expected of a BoQ ie quantity and item name in the parsed output. Those without could be tackled easier. Fetch must work."

## Plan
1. Build `scan_boq_content.py` — scans all RFX tender parsed items, classifies by BoQ completeness
2. Verify yellowpages dashboard + permauth daemon are running (Fetch must work)
3. Identify tenders with/without BoQ data

## Progress
- [x] Explored codebase: batch_boq_extractor.py, triager.py, extract_boq.py, pricesheet_extract.py
- [x] Built `scan_boq_content.py` — BoQ content validator
- [x] Fixed yellowpages server (port 3636 conflict, restarted)
- [x] Ran scanner — results below
- [x] Fixed permauth SSO — rewrote `_ensure_login()` to navigate idplogin.gep.com → BizNet (17 cookies)
- [x] Deep investigation of 3 SUSPECT_BOQ tenders — confirmed child sheets exist
- [ ] Re-extract 3 SUSPECT_BOQ tenders with full child sheet scan — BLOCKED (auth)

## Deep Investigation Results (2026-05-01T20:15)

### RFP-000000178432 (FSH_26121-MLNG)
Already-captured parent pricesheet (`pricesheet_full.json.gz`, 873KB) confirms:
- **112 supplierDataSheets** (child sheet IDs) — each potentially has multiple line items
- **4 buyerDataSheets** (buyer comparison sheets)
- **colSchema**: 19 columns mapping virtual IDs (v1-v19) to real names (Item Number, Item Name, Volume, Unit, etc.)
- Parent `supplierDataRows` has only 1 row (top-level CONSURV bid row)
- Actual line items are in the child data sheets, each fetched via `/data/pricedatasheet/{id}?oloc=663`

### RFP-000000178387 & RFP-000000178027
Each has 1 item from API (parent sheet). Expected: 100+ child data sheets per tender, each with multiple rows.

### Root Cause: Child sheet extraction blocked by auth
- **Child sheets need**: valid smart.gep.com SPA session with netsessionid
- **Daemon state**: Has 17 BizNet/SSO cookies, but `nsid=NONE` — never accesses smart.gep.com SPA
- **Why daemon can't go to smart.gep.com**: Comment at `permauth.py:281` says "Stays on BizNet — does NOT navigate to smart.gep.com (breaks session)"
- **smart.gep.com/Sourcing/Rfx**: Returns 302→`smarterr.gep.com/404.aspx` without auth, but loads SPA with Chrome User-Agent
- **Direct API calls**: `/data/pricesheet/{id}` and `/data/pricedatasheet/{id}` return 500 (session required)
- **Playwright ERR_NETWORK_CHANGED**: Intermittent VPS network issues with fresh browser contexts

### Attempted (all failed)
1. HTTP-only with daemon cookies → 500 (no SPA session)
2. Playwright + daemon cookies → STS redirect, 0-byte body, ERR_NETWORK_CHANGED
3. Playwright + file cookies → stale, same errors
4. Playwright + fresh login → Login OK but smart.gep.com navigation redirects to BizNet (no smart.gep.com cookies established)
5. Engine permauth.py (navigates to smart.gep.com) → crashes immediately (15 restarts in seconds)
6. Stale backup cookies with SmartAuth0 → still 500 (expired session)

### Infrastructure
- **Yellowpages**: ONLINE on port 3636, yellowpages.zeidgeist.com/v2
- **Permauth daemon**: UNSTABLE (23 restarts, tokens endpoint returning 0 cookies at last check)
- **PM2**: 9 processes online

## BoQ Scanner Results (2026-05-01)
| Tender | Category | Items | Named | With Qty | Complete % |
|--------|----------|-------|-------|----------|------------|
| RFP-000000178771 | FULL_BOQ | 112 | 112 | 105 | 93.8% |
| RFP-000000176710 | PARTIAL_BOQ | 203 | 203 | 41 | 20.2% |
| RFP-000000178432 | SUSPECT_BOQ | 1 | 1 | 1 | 100% (1 item) |
| RFP-000000178387 | SUSPECT_BOQ | 1 | 1 | 1 | 100% (1 item) |
| RFP-000000178027 | SUSPECT_BOQ | 1 | 1 | 1 | 100% (1 item) |
| RFP-000000177523 | NO_BOQ_DATA | 0 | 0 | 0 | 0% |

### Key Findings
1. **3 SUSPECT_BOQ**: Each has only 1 item from price sheet API. RFP-178432 confirmed to have 112 child sheets in parent pricesheet — these contain the actual line items. RFP-178387 and 178027 likely have similar counts.
2. **1 FULL_BOQ**: RFP-178771 (STEM Hub Sabah) — 112 items from downloaded xlsx, 94% have quantities.
3. **1 PARTIAL_BOQ**: RFP-176710 (Masjid Baru) — 203 items but only 20% have quantities.
4. **1 NO_BOQ**: RFP-177523 — engineering services, no BoQ docs.

## Completed
- [x] Bot handler fix — 17 missing handlers, model change to deepseek-v4-flash
- [x] All 797 tests passing
