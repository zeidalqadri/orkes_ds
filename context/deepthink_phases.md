# DeepThink: Deferred Phases Plan

**Current state:** Phase 1 (exact-match SQLite cache) is live — MD5 hash, session + global TTL, intent gating. Verified, working, no flow tampering.

---

## Phase 2: Embeddings-Based Semantic Matching

**Goal:** Cache hits on paraphrases — "Salaam" ≈ "Hi" ≈ "Hello there" without fuzzy regex.

**Approach:**
- On cache miss, compute embedding of user message (ONNX all-MiniLM-L6-v2 via `ruvector`)
- Compare (cosine sim) against embeddings of recent global cache entries
- Threshold: ≥0.92 similarity → serve cached response with `similarity` metadata flag
- Store embedding alongside each global cache entry (`response_cache.db` gets a `embedding BLOB` column)
- On cache write, compute + store embedding (zero extra LLM calls, just a cheap ONNX inference)

**Why 0.92:** High enough to avoid false positives on context-dependent queries ("price of steel" ≠ "price of wood"), low enough to catch true paraphrases.

**Anti-flow-tamper:**
- Only applies to `_CACHE_ELIGIBLE_INTENTS` (research, price_check, greeting, market_intelligence)
- Never on add_to_bid, confirm_purchase, comparison
- Miss below threshold → passes through to LLM as today

| Dimension | Phase 1 | Phase 2 |
|-----------|---------|---------|
| Match type | Exact string (MD5) | Cosine ≥0.92 |
| Deps | None | ruvector + ONNX model |
| Cache hit rate | ~5-10% | ~20-30% (estimated) |
| Latency per miss | 0ms | +2-5ms (embedding) |

---

## Phase 3: Circuit Breaker + Stale Cache Fallback

**Goal:** When ALL LLM providers are unreachable, serve **any** stale cache entry for the same intent instead of returning an error.

**Approach:**
- Track provider error count per 60s window
- After 3 consecutive failures across all providers → circuit opens
- On open circuit: scan cache for same intent (any query), return most recent entry with `stale: true` metadata
- Circuit resets after 30s (or first successful health check)
- Stale entries are clearly flagged to user: "Based on previously researched data (X minutes old)"

**Why not tamper:**
- Circuit only opens during total provider outage — better to serve stale data than "server unreachable"
- User can always re-ask to force fresh lookup
- Stale flag is transparent

| Dimension | Without Phase 3 | With Phase 3 |
|-----------|----------------|--------------|
| Total outage UX | "Server unreachable" | "Based on data from X min ago" |
| Time to response | 60s timeout → error | <10ms (cache hit) |
| User trust | Eroded | Preserved |

---

## Phase 4: Pattern-Based First-Level Responses (No LLM)

**Goal:** Greetings, status checks, and simple intents skip LLM entirely — answered from templates.

**Approach:**
- Precompile intent→template map in a JSON file (`cache_templates.json`):
  ```json
  {
    "greeting": {
      "patterns": ["halo", "hai", "salaam", "hello", "hi", "pagi"],
      "response": {
        "type": "greeting",
        "message": "Halo! Saya Harga, asisten penilaian harga Anda. Ada yang bisa saya bantu?"
      }
    },
    "help": {
      "patterns": ["bantuan", "help", "how to use", "apa bisa"],
      "response": {
        "type": "help",
        "message": "Saya bisa membantu: mencari harga pasar, menganalisis tender, membandingkan penawaran..."
      }
    }
  }
  ```
- Check template map BEFORE cache lookup (fastest path)
- Template match → return instantly, no DB hit, no LLM call
- Templates are pure text, not cached LLM output — zero overhead

**Why not tamper:**
- Only applies to well-defined low-intent patterns (greetings, help)
- All substantive queries (pricing, research, bids) pass through to normal cache → LLM pipeline
- Templates are curated, not AI-generated — predictable, safe

| Dimension | Without Phase 4 | With Phase 4 |
|-----------|----------------|--------------|
| Greeting latency | ~10-30s (LLM council) | <1ms (template) |
| Server unreachable risk | Every greeting calls LLM | Zero |
| Cost per greeting | ~100-500 tokens | Zero |

---

## Phase 5: Cache Dashboard (Observability)

**Goal:** Operator can see hit rates, clear stale entries, warm common queries.

**Approach:**
- Simple Flask endpoint: `GET /admin/cache`
- Shows:
  - Total/session/global entry counts
  - Hit rate (hits / (hits + misses)) per intent
  - Top 10 most-hit queries
  - "Clear all" / "Clear by session" buttons
  - DB size on disk
- JSON endpoint for prometheus/esg integration: `GET /admin/cache/stats`

---

## Phase 6: Cache Warming (Optional - Low Priority)

**Goal:** Pre-populate cache with common industry queries to absorb first-wave traffic.

**Approach:**
- Cron job runs daily at 0600
- Reads `warm_queries.jsonl` (curated set of ~50 common queries per industry sector)
- Runs each through the normal pipeline (LLM council)
- Stores results in cache
- Subsequent user queries with same/similar intent hit the warmed cache

**Tradeoff:** Costs ~50 LLM council runs per day. Recommended only after Phase 2-3 verify positive ROI.

---

## Execution Priority

```
Week 1:  Phase 2 (embeddings) — highest ROI, moderate effort
Week 2:  Phase 3 (circuit breaker) — high ROI for server unreachable problem
Week 3:  Phase 4 (templates) — trivial effort, eliminates cheapest failure mode
Anytime: Phase 5 (dashboard) — when debugging cache behavior
If ROI+ : Phase 6 (warming) — after 2 weeks of Phase 2 hit rate data
```

**Recommend:** Do Phases 2 → 3 → 4 sequentially. Phase 5 on demand. Phase 6 only if data justifies it.
