# Enrichment Pipeline Architecture

## Overview

The SME directory enrichment pipeline augments 9,848 Malaysian SME records with missing fields (website, phone, email) using two strategies: Playwright-based Google Maps scraping and SearXNG meta-search. Dedup, quality scoring, and coverage gap analysis run downstream.

## Data Flow

```
Crawl Sources → ingestion (dedup/merge) → SQLite DB → enrichment → quality scoring → gap analysis
     │                 │                       │
  OSM/GMaps/YP    normalize.py            enrich_cache/
```

## Components

### 1. Database (`crawler/db.py`)
- **SQLite** at `crawler/data/sme_directory.db`
- 6 tables: `businesses`, `business_phones`, `business_sources`, `business_services`, `crawl_runs`, `tile_checkpoints`
- Row-level schema with UUID primary keys, timestamps, source tracking

### 2. Crawl Pipeline (`crawler/run.py`)
- CLI entry point: `python -m crawler.run {osm,gmaps,yp,quality,services,stats}`
- `ingest_businesses()` processes raw crawled data through dedup pipeline:
  1. Phone-based lookup → exact match
  2. Name+area fuzzy match (`rapidfuzz token_sort_ratio >= 85`) + proximity check (200m Haversine)
  3. Merge or insert

### 3. GMaps Enrichment (`crawler/enrich_websites.py`)
- **Target**: Businesses with `rating IS NOT NULL` (GMaps-sourced, ~6,578 records)
- **Method**: Playwright opens Google Maps, searches `"{name} {area} Malaysia"`
- **Extraction**: 5 cascading strategies (data-tooltip buttons → anchor hrefs → aria-label → body regex for phone → body domain scan)
- **Cache**: SHA256 key per business at `crawler/data/enrich_cache/` — 6,647 entries, 6,337 with data, 310 "no data" (never retried)
- **Ceiling**: 34% website coverage — OSM-only businesses (3,270) have no rating and are unreachable; remaining GMaps candidates already cached as no-website

### 4. SearXNG Enrichment (`crawler/searxng_enrich.py`)
- **Target**: Businesses without websites (gap-fill after GMaps ceiling)
- **Method**: HTTP GET to local SearXNG at `http://172.24.0.4:8080` — queries `'"{name}" "{area}" Malaysia'`
- **Scoring**: Conservative — requires score >= 3.0 with domain match or >= 5.0 without. Blocks social media/yellow pages/aggregator domains. Prefers MY TLDs
- **Status**: Only 10 benchmarked (9 found). Not scaled — this is the next obvious step for website gains

### 5. Normalization & Dedup (`crawler/normalize.py`)

| Function | Description |
|---|---|
| `normalize_phone(raw)` | Strips non-digits, matches MY mobile/landline patterns, normalizes to `+60XXXXXXXXX` |
| `normalize_name(name)` | Lowercases, strips Unicode accents (NFKD), removes Sdn Bhd/etc. suffixes |
| `is_duplicate(a, b)` | Exact phone match → exact name match → fuzzy name (>=85) + proximity (<200m) → (bool, reason) |
| `merge_records(existing, new)` | Fills nulls from new data, takes higher rating/review_count, prefers non-null coords |

### 6. Quality Scoring (`crawler/quality.py`)
- Composite 0-1 score per business:
  - Completeness (45%): 11 field weights (phone 25%, name 15%, address 15%, etc.)
  - Sources (25%): 1 source = 0.3, 2 = 0.7, 3+ = 1.0
  - Rating (20%): normalized `rating / 5.0`
  - Contactability (10%): can we reach them
- Also infers BuzzBuzz service category from business name/category

### 7. Coverage Gap Analysis (`crawler/coverage_gaps.py`)
- Per-category×area cluster analysis of missing fields
- 8 dimensions (phone, website, email, rating, quality, outreach, service, coords)
- Prioritizes enrichment targets by impact (dimension weight × gap size)

## Current State (Phase 0)

| Metric | Value |
|---|---|
| Total SMEs | 9,848 |
| With website | 3,344 (34.0%) |
| With phone | 7,895 (80.2%) |
| With email | 75 (0.8%) |
| GMaps enrichment cached | 6,647 entries (6,337 with data) |
| SearXNG benchmarked | 10 (9 found) |
| Avg quality score | 0.562 |

## Success/Failure Patterns

**GMaps Enrichment:**
- Hit rate decays sharply with each batch (31% → 14% → 13% → cache replay)
- 87% "hit rate" in background mode is misleading — mostly cached replays
- OSM-only businesses (3,270) are a hard ceiling — no rating field, no GMaps detail page
- Cached "no data" entries are never retried, creating permanent ceiling

**SearXNG:**
- Conservative scoring avoids false positives but may miss valid websites
- Only 10 benchmarked — not enough data to assess true hit rate
- Needs query pattern optimization (different phrasing, without location, etc.)

**Dedup:**
- Phone-based dedup is strongest signal (exact match)
- Fuzzy name + proximity works well for close neighbors but may miss >200m duplicates
- No address normalization yet (Jalan/Jln, Lorong/Lor, etc.)

## Next Steps (Phase 1+)

1. **Scale SearXNG**: batch enrichment across all 7,122 missing-website businesses
2. **Alternative sources**: YP.my, MY business directories, e-commerce platforms
3. **Manual curation**: high-value targets (solar_ev, supplier categories)
4. **Address dedup**: normalize street types, abbreviations
