Done. W19 synthesis report written to `context/synthesizer/CONNECTIONS.md`. GOAL cleared, STATE updated.

### 5 Non-Obvious Connections Found

1. **Pipeline Starvation** (HIGH) — 3,008 tenders ingested, 352 matched, but only **1 deal** in pipeline (RM75k ABB, stuck 53 days). The entire scraper→pricing pipeline has no bridge to deal progression.

2. **Dual-DB Silent Staleness** (HIGH) — Scraper writes to `orkes/yellowpages/tenders/tenders.db`, harga reads from `orkes-or/yellowpages/tenders/tenders.db` via symlink. They're **different files** (different inodes, 28KB delta). New scrapes don't reach harga.

3. **SmartGEP Line Items Orphaned** (MEDIUM) — `_extract_smartgep_line_items()` exists in bridge.py but is **never called**. All 1,378 SmartGEP tenders show `line_items: []`. Meanwhile 10,955 price_sheet_rows JSON files sit on disk unused.

4. **Security Debt on Public URL** (MEDIUM) — 4 critical/high issues (IDOR, CSRF, auth bypass via Escape key, 29 passwordless accounts) accepted as "internal tool risk" on a publicly accessible URL.

5. **Expert Fleet Decline** (LOW) — 9/17 experts stopped. Builder timeout fix ran 3x with same result — no reviewer verification loop.

Top-priority actions: unify DB paths, wire line item extraction, fix Escape key auth bypass.