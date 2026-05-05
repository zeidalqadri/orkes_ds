# Alternative Enrichment & Coverage Gap Analysis

## Methodology (adapted from SEO.md)
Systematic, audit-driven approach applied to alumni enrichment:

1. **Audit first, act second** — always measure current coverage before any enrichment
2. **Source comparison** — evaluate enrichment sources like competitors (who yields best data, where are the gaps)
3. **Tiered weekly execution** — foundation gaps first, then optimization, then scale
4. **Pattern recognition** — look for clusters (by area/service/readiness) that reveal high-value targets
5. **Compounding execution** — systematic weekly batches that improve over time

---

## Phase 1: Coverage Gap Audit

**Goal**: Complete picture of enrichment status across all dimensions.

### By Location
- Aggregate businesses by state/district/postcode
- Calculate field coverage % (website, phone, email, social) per area
- Identify density clusters and data deserts

### By Service Type
- Covergage % per service type (27 types)
- Outreach readiness distribution (hot/warm/cool/cold) per type
- Which types have most unscoreable ("cold") leads

### By Data Field
- Field-level completeness: website 3.9%, phone 78.6%, etc.
- Which fields are most impactful to fill next
- Cost/benefit: phone-only gap vs email gap vs website gap

### Output
- Priority list of gaps ranked by enrichment impact
- Heat map (state/area) of enrichment deserts
- Service-type coverage matrix

---

## Phase 2: Source Evaluation

**Goal**: Systematically compare enrichment sources, pick best for each gap.

### Sources to evaluate (like GBP competitor analysis)
| Source | Status | Fields | Cost | Risk |
|--------|--------|--------|------|------|
| YP.my (proxied) | Blocked → test proxy | Website, phone | $ | Cloudflare bypass |
| Google organic (SearXNG) | Available | Website, phone, social | Free | Rate limits |
| Other MY directories | Untested | Varies | Free/low | Unknown hit rate |
| WhatsApp lookup | Untested | WA-registered? | $ | Limited utility |

### Per-source evaluation
- Hit rate sample (test 100 businesses per source)
- Field yield (what % get website? phone? both?)
- Cost per enriched record
- Overlap rate (new data vs duplicate)

---

## Phase 3: Targeted Enrichment

**Goal**: Fill gaps by priority, using best source per gap type.

### Week 1-2: High-impact fills
1. Run coverage gap audit (Phase 1) — data we already have
2. Test top 2 enrichment sources (Phase 2) — 100 each
3. Choose primary enrichment approach based on results
4. Dispatch first batch (500-1000 businesses) using chosen source

### Week 3-4: Scale
5. Full enrichment run (all businesses missing critical fields)
6. Re-audit coverage — measure delta
7. Identify remaining gaps, repeat with next-best source

### Ongoing
8. Weekly enrichment batches (500-1000/wk)
9. Weekly re-audit to track improvement
10. Retry blocked sources periodically (some may unblock)

---

## Key Metrics (track weekly)
- Coverage % per field (website, phone, email, social)
- Coverage % per service type
- Source hit rate (what % yield new data)
- Enriched records per week
- Cost per enriched record
- New "hot" leads added per batch
