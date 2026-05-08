# Active Work
Project: /home/the_bomb/orkes_ds2
Task: Retune Harga scope to be industry-agnostic, driven by SmartGEP BOQ data
Status: done
Updated: 2026-05-08T17:00 UTC

## Completed

### Harga scope retune — industry-agnostic, SmartGEP BOQ driven (2026-05-08)
**Directive**: "retune harga to not only be about specific area of industries or products. use the SmartGEP tender notices boq as reference."

**Change**: Rewrote `_base_persona()` in `context_assembler.py` (lines 156-183):
- Removed hardcoded industry list ("construction, retail, wholesale, F&B, services")
- Replaced with data-driven scope: "Your coverage is informed by available procurement and tender data — including SmartGEP line items, price history, and current market intelligence"
- Explicit declaration: "You are not limited to any specific industry or product category; your scope is defined by the data available to you in each session"
- Merged dual pricing guidance (construction/procurement vs retail/consumer) into single generic section referencing tender line items + price memory
- CRITICAL RULES and tone guidance preserved unchanged

**Not changed** (not scope-limiting):
- `_CATEGORY_KEYWORDS` in bidder_routes.py (item categorization, not prompt)
- `_INTENT_KEYWORDS` in price_intent.py (intent detection keywords)
- Output format examples (examples, not restrictions)
- LLM council role prompts (build on base_system, no additional scope)

**Restart**: harga pm2 restarted (pid changed), HTTP 200 verified

## Completed

### Deepthink 5-Phase System Test (2026-05-08)
**Directive**: "Hiw about this? Can we put this to test?"
**Result**: All 5 phases verified PASS.

**5 bugs fixed during test:**
1. Template crash (NoneType .get on template match response)
2. Help regex `^(?:help|bantuan|tolong|what|how|apa|...)` ate substantive queries
3. `_circuit_used_stale` UnboundLocalError on cache hit path
4. `session_id` null crash in JSON body parsing
5. Missing `cached`/`stale`/`cache_similarity` fields in API response

**Files changed:** bidder_routes.py, cache_templates.json, response_cache.py (null guard)

### Deferred deepthink phases (2026-05-08)
**Directive**: "Plan for the deferred phases" and "Proceed"

All 4 deferred phases of the deepthink LLM response caching system implemented and verified:

**Phase 2 — Embeddings-Based Semantic Matching**: all-MiniLM-L6-v2 via transformers (384-dim), cosine sim threshold 0.82, catches paraphrases, graceful fallback to exact-match, auto-DB-migration.

**Phase 3 — Circuit Breaker + Stale Cache**: opens after 3 consecutive failures, auto-recloses after 30s, serves stale cache with transparent age metadata. Integrated into llm_council.py + bidder_routes.py.

**Phase 4 — Pattern-Based First-Level Responses**: 6 template groups, 47 patterns (exact/prefix/regex), zero-DB/zero-LLM path for greetings/help/thanks/status/goodbye. Templates in cache_templates.json.

**Phase 5 — Cache Dashboard**: /admin/cache (HTML) + /admin/cache/json (JSON) endpoints with cache stats, circuit state, template info, action buttons (prune, reset).

**Key files changed:**
- harga/response_cache.py — Phase 1+2 integration (embedding column, semantic_search)
- harga/response_cache_embeddings.py — NEW: ONNX/torch embedding computation (384-dim, all-MiniLM-L6-v2)
- harga/circuit_breaker.py — NEW: circuit breaker state + stale fallback (3 failures → 30s cooldown)
- harga/data/cache_templates.json — NEW: 5 template groups, 47 patterns (greeting, help, goodbye, status_check, praise)
- harga/app.py — Phase 5 dashboard routes (/admin/cache HTML + JSON)
- harga/tools/bidder_routes.py — Phase 3+4 integration (circuit check, template check)
- context/deepthink_phases.md — updated planned status

## Completed

### Round 3 — View Sources sheet + keyboard shortcuts (2026-05-08)
**Directive**: "Retain hypersimplistic calm white space with black tinges and frames."

#### View Sources bottom sheet (rtbv5 bud #8)
- "View sources" button on price cards now opens bottom sheet with full research data
- `_lastWizard` stores wizard response client-side for instant access
- Sources shown: title, full snippet, URL, category badge, source count
- Replaces previous behavior of sending text command to LLM (unnecessary round-trip)

#### Keyboard shortcuts (rtbv5 bud #9)
- Cmd+K / Ctrl+K — new chat
- Cmd+I / Ctrl+I — import tender
- Cmd+Shift+C / Ctrl+Shift+C — open chats
- Cmd+/ / Ctrl+/ — show shortcuts reference sheet
- All shortcuts use `e.preventDefault()` to avoid browser conflicts
- Mac/Win detection via `navigator.platform` for correct key labels

#### already deployed from Round 2
- Backend state-passing verified (rfp_context in chat calls, CRITICAL instruction in ContextAssembler)
- Landing: greeting / headline / subtext / diverse chips / black frames
- Processing procurement verbs (7 cycling)
- Price cards with confidence colors + inline action buttons
- Sessions with message preview, date, entity slug

#### Verification
- harga.roowang.com HTTP 200
- All changes confirmed live (curl | grep shows _lastWizard, showSourcesSheet, showShortcuts, metaKey handler)

### Round 2 — Harga v5 refinements (2026-05-08)
**Operator directive**: "Proceed with remedial actions. Retain hypersimplistic calm white space with black tinges and frames."

#### Landing page — black frames applied
- Input border: changed from `1.5px solid rgba(0,0,0,0.2)` → `2px solid #000`
- Send badge: `1px solid rgba(0,0,0,0.08)` → `1.5px solid #000` with weight 700
- All suggestion chips: `1px solid rgba(0,0,0,0.15)` → `1px solid #000`
- Hover states on chips (subtle background tint) + hover shadow on input
- White background retained. No color additions.

#### Wizard cards — visual hierarchy
- Added "Research Sources" uppercase header (10px, letter-spacing 0.08em)
- Source titles: 12px → 13px, weight 500
- Added snippet previews (120 char max) below each source
- Category badge + source count in a flex row
- Card padding: 14px → 16px, border stronger (0.5px → 0.12 opacity)

#### Processing status — procurement verbs
- 7 verbs replacing 4 generic ones:
  - Sourcing market data / Packing price intelligence / Weighing supplier quotes / Analysing cost trends / Cross-referencing sources / Consolidating estimates / Validating price confidence

#### Backend state-blindness (case002) — verified working
- `rfp_context` IS forwarded through `harga_v2_chat()` proxy to `price_chat()`
- ContextAssembler `_format_bid_items()` includes CRITICAL instruction: never ask user to re-provide visible items
- Both DB-loaded (g.h2_bid_items) and rfp_context fallback paths operational

#### v5 landing finishing touches (this round)
- Added "Hi, I'm Harga." greeting above headline (rtbv5 bud #1 — welcome state)
- Esc key handler closes overlays cleanly (rtbv5 bud #9 — keyboard shortcuts)
- Logo bumped 16px → 18px for stronger brand anchor (case003 #7)
- Tender card now pure data; factsheet text moved to separate bot bubble (case002 — data/prose separation)
- Fallback factsheet text changed to descriptive, not first-person voice

#### Verification
- harga.roowang.com HTTP 200
- All changes confirmed live in served HTML
