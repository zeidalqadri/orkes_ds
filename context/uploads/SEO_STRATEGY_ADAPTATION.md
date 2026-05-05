# SEO.md Strategy Adaptation — Coverage Gap Analysis

## Original Source
`context/uploads/SEO.md` — 8-prompt Google Business Profile audit methodology for single businesses.

## Core Methodology (from SEO.md)
```
Competitor GBP Research → Structured Spreadsheets → Gap Identification → Optimization
```
Each prompt: "Open Chrome, go to GBP, extract data, put in spreadsheet, find gaps"

## Adaptation for Our Platform
We applied the same methodology at **mass scale** (9,848 businesses, not 1):

| SEO.md Prompt | Our Adaptation | Module/Data |
|--------------|----------------|-------------|
| 1. GBP Category Audit | Category coverage by cluster | quality.py SERVICE_PATTERNS |
| 2. GBP Attributes Audit | Data completeness by dimension | coverage_gaps.py DIMENSIONS |
| 3. Competitor Review Teardown | Rating/review coverage by area | coverage_gaps.py + outreach scoring |
| 4. Review Response Strategy | Outreach readiness scoring | outreach/scoring.py |
| 5. GBP Posts Strategy | N/A (no GBP posts data) | Future: GBP Playwright extraction |
| 6. Services Section Optimization | Service mapping coverage | quality.py service inference |
| 7. GBP Description Optimization | Website/email/description gaps | coverage_gaps.py dimensions |
| 8. GBP Photo Audit | Coordinate/address completeness | coverage_gaps.py dimensions |

## Output
`crawler/coverage_gaps.py` — CLI module generating structured gap reports.

## Key Findings
- Overall coverage: **61.2/100**
- **Service mapping**: 43.5% — biggest lever for improvement
  - electrical: 100% (saturated)
  - aircon: 31.1%, solar_ev: 34.1% (moderate)
  - handyman: 20.3%, plumbing: 16.5%, supplier: 5.9% (critical gaps)
- **Website**: 27.2% — SearXNG organic search can help
- **Phone**: 79.1% — proxied directories for the rest
- **Email**: 0.8% — low ROI to enrich at scale
- **Worst clusters**: handyman in JB/Penang, solar_ev in Ampang/Penang

## Recommended Prioritization
1. Expand service mapping patterns (handyman/supplier/plumbing keywords)
2. GBP metadata enrichment (Playwright: categories, attributes, description, photos)
3. Website enrichment (SearXNG)
4. Phone re-enrichment (proxied)
5. Cluster outreach
