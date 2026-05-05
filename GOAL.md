# Goal: MI&BI Superiority via 10k SME Database

Transform the 9,848-SME directory into a full-spectrum Market Intelligence & Business Intelligence platform.

## Current State (2026-04-29)

| Metric | Value | Target |
|--------|-------|--------|
| Total SMEs | 9,848 | 50,000 |
| Phone coverage | 80% | 95% |
| Website coverage | 33% | 80% |
| Email coverage | <1% | 50% |
| City coverage | 4% | 100% |
| Geographic scope | Selangor only | All MY states + regional |
| Vertical categories | 6 | 15+ |
| External enrichment sources | SearXNG, GMaps, OSM | 10+ (LinkedIn, SSM, etc.) |
| Intel system | Basic SearXNG → Obsidian | Automated BI dashboards + alerts |

## Strategic Pillars

1. **Data Completeness** — fill critical field gaps (website, email, city/subcategory)
2. **Data Depth** — add new dimensions (decision-makers, techstack, financials, pricing)
3. **Geographic Expansion** — all Malaysian states → ASEAN
4. **Vertical Expansion** — Tier 2-3 categories (pest control, security, roof, etc.)
5. **MI Layer** — competitive intel, pricing, trends, sentiment, news
6. **BI Layer** — automated insights, dashboards, lead scoring, gap detection

## Execution Plan

### Phase 0: Finish Current Enrichment Cycle (~1 week)
- [x] Complete website enrichment for remaining ~5,060 businesses (all batches) — GMaps ceiling reached at 34%; 6,647 cached
- [x] Audit enrichment quality: false positive rate, field accuracy — report saved to `data/phase0_report.txt`
- [x] Build dedup/normalization pipeline for enriched data — `crawler/normalize.py` with phone/name/fuzzy+proximity matching
- [x] Re-measure coverage after enrichment, update quality scores — coverage gap report generated; avg quality 0.562
- [x] Document current enrichment architecture, success/failure patterns — `docs/enrichment-architecture.md`

### Phase 1: New Data Sources (~2 weeks)
- [ ] **LinkedIn enrichment**: discover company pages, key employees for each SME
- [ ] **SSM Malaysia**: batch lookup for registration numbers, business type, status
- [ ] **Email discovery**: hunter.io/skrapp/rocketreach API for decision-maker emails
- [ ] **News/media monitoring**: news API pipeline for SME mentions
- [ ] **Social presence detection**: FB/IG/TikTok page discovery
- [ ] **Pricing intelligence**: scrape competitor price lists, estimate SME price ranges

### Phase 2: Geographic & Vertical Expansion (~3 weeks)
- [ ] **Penang**: crawl GMaps + OSM for all categories
- [ ] **Johor**: crawl GMaps + OSM for all categories
- [ ] **Perak/Kedah/Melaka/Negeri Sembilan**: phased roll-out
- [ ] **East Malaysia (Sabah/Sarawak)**: adapt for local directories
- [ ] **New verticals**: pest_control, roof_waterproofing, security_systems, flood_response, gas_emergency, appliance_repair, cleaning_restoration, moving_relocation
- [ ] **Multi-language**: search in BM, Chinese dialects, Tamil for local discovery
- [ ] **New local directories**: thinkoflocal.my, myshop.malaysia, etc.

### Phase 3: BI Layer (~2 weeks)
- [ ] **Automated weekly BI report**: coverage trends, new discoveries, enrichment deltas
- [ ] **Lead scoring v2**: incorporate email presence, social signals, news mentions, decision-maker data
- [ ] **Market gap analysis**: category × area × data completeness heatmap
- [ ] **Competitive positioning**: per-category density maps, service overlap, pricing tiers
- [ ] **Pricing intelligence dashboard**: estimated price ranges by category × area

### Phase 4: International MI&BI (~ongoing)
- [ ] **Singapore**: SME directory enrichment (data.gov.sg, sginfo.com)
- [ ] **Thailand**: SME data discovery
- [ ] **Indonesia**: SME data discovery
- [ ] **Alumni pipeline integration**: link SME data to alumni discovery platform

## Key Metrics

| KPI | Current | Phase 0 | Phase 1 | Phase 2 | Phase 3 |
|-----|---------|---------|---------|---------|---------|
| Total SMEs | 9,848 | 9,848 | 12,000 | 30,000 | 50,000+ |
| Website coverage | 33% | 70% | 75% | 80% | 85% |
| Email coverage | <1% | <1% | 40% | 50% | 60% |
| States covered | 1 | 1 | 3 | 10+ | 14+MY + regional |
| Categories | 6 | 6 | 6 | 12 | 15+ |
| Data sources | 3 | 5 | 8 | 12 | 15+ |
| BI reports | 0 | manual | manual | automated | automated + alerts |
