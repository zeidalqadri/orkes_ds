# Synthesizer Report — W30 Cross-Domain Synthesis (2026-07-20)
Updated: 2026-07-20T07:30 UTC (2026-07-20 15:30 MYT)

## Data Sources
- Tender DB: `/home/the_bomb/orkes/yellowpages/tenders/tenders.db` — 8,266 tenders (DOWN from 29,229 in W29)
- sec.db: `/home/the_bomb/orkes_sec/data/sec.db` — 5,773 tenders (NEW — separate sec-* platform DB)
- Deals: `/home/the_bomb/orkes/yellowpages/deals.json` — 1 deal (frozen 124 days, 96 days past expected close)
- PM2 fleet: 33 processes (UP from 14 in W29 — +19 new processes)
- Expert learnings from 11 experts (provided in goal prompt)
- W29 (Jul 13) baseline report
- Telegram operational logs (Jul 13-20)

---

## Cross-Domain Insights

### Insight 1: Tender Platform Forked — 20,963 Tenders Vanished from Primary DB While a Parallel sec-* DB Holds 5,773 (CRITICAL)

**Evidence:**

The primary tenders.db dropped from 29,229 (W29) to 8,266 — a 72% reduction. Simultaneously, a new `sec.db` at `/home/the_bomb/orkes_sec/data/sec.db` holds 5,773 tenders with its own FTS indexes, products, brands, and alert system.

| Metric | W29 | W30 | Change |
|--------|-----|-----|--------|
| Primary DB (tenders.db) | 29,229 | 8,266 | -20,963 (-72%) |
| sec.db tenders | — | 5,773 | NEW |
| Combined total | 29,229 | 14,039 | -15,190 (-52%) |
| Unaccounted loss | — | 15,190 | Purged or lost |

15,190 tenders are not in either database. This is either:
- (a) Intentional cleanup of historical/closed tenders (the W29 CRITICAL action "clean dead matched" finally executed at scale), or
- (b) A data loss event during the sec-* platform deployment

The primary DB's monthly creation pattern (Mar: 1, Apr: 887, May: 530, Jun: 3,229, Jul: 3,619) totals 8,266 — matching the current count exactly. This suggests the DB may have been rebuilt from scratch rather than cleaned incrementally.

**Connection:**

The architect's learning about "bridge function pattern (tender_to_dict / dict_to_tender) eliminates changes to 3 downstream modules" and "researching existing `_load_tender`/`_save_tender` call count (~70 sites)" indicates active migration planning was underway. The sec-tenders-api (351MB memory, 8 restarts) serves from sec.db — this is a live parallel system, not a backup.

The reviewer's learning "Always verify builder's claims against actual code — builder claimed WebDAV size cap was added but it wasn't in the code" is a warning: we need to verify whether this data migration was intentional and complete.

**Action items:**
- [ ] **[CRITICAL]** Determine if the 15,190 missing tenders were intentionally purged or lost — check git logs and Telegram history for the migration event
- [ ] **[CRITICAL]** Clarify the relationship between tenders.db and sec.db — are they meant to coexist, or is sec.db the successor? Which is the source of truth?
- [ ] **[HIGH]** Verify the sec-tenders-api is serving correct data — cross-check a sample of tenders between both DBs

---

### Insight 2: Fleet Doubled (14 to 33) — The sec-* Subsystem Consumes 892MB (31% of Fleet Memory) with Zero Expert Documentation (HIGH)

**Evidence:**

12 new `sec-*` processes appeared since W29, plus 7 other new processes:

| New Process | Memory | Restarts | Role (inferred) |
|-------------|--------|----------|-----------------|
| sec-tenders-api | 351MB | 8 | Tender API (sec.db backend) |
| sec-guardian | 254MB | 0 | Security/monitoring |
| sec-harga-v8 | 85MB | **40** | Harga v8 (RESTART LOOP) |
| sec-agent | 83MB | 23 | Agent process |
| sec-harga-v8-scheduler | 19MB | 1 | Scheduler |
| sec-sched-api | 19MB | 1 | Scheduling API |
| sec-scheduler | 17MB | 1 | Scheduler worker |
| sec-proxy | 16MB | 1 | Proxy/gateway |
| sec-products-api | 12MB | 1 | Products API |
| sec-analytics | 11MB | 1 | Analytics |
| sec-documents | 10MB | 1 | Document service |
| sec-failsafe | 9MB | 1 | Failsafe watchdog |
| scheduler-worker | 283MB | 1 | Job scheduler |
| comcen | 12MB | 19 | Command center |
| buzzbuzz | 14MB | 0 | Returned (was missing W29) |
| mondokroma | 10MB | 0 | New |
| putri | 8MB | 0 | New |
| harga-v8-scheduler | 7MB | 0 | Harga scheduling |
| download-retry | 0MB | 1 | STOPPED |

Total fleet memory: **2,840MB** (2.8GB). sec-* alone: 892MB (31%).

**No expert logged this deployment.** The builder's learnings are still corrupted ("Fix timeout" x3, "Build X" x3). The conductor's learnings show no orchestration of this rollout. This is the largest architectural change since synthesis tracking began, and it happened in a documentation blind spot.

**Connection:**

The devops learning "pm2 restart doesn't kill background threads: may need `pm2 delete yellowpages && pm2 start`" and the Telegram logs showing pm2 dump updates and port collision fixes (comcen: port 3638→3645, pm2-failsafe orphan cleanup) confirm active infrastructure work this week. But infrastructure work without documentation creates the exact "trust without verify" pattern the reviewer flagged.

**Action items:**
- [ ] **[HIGH]** Document the sec-* subsystem: what it does, why it exists, how it relates to yellowpages
- [ ] **[HIGH]** Fix sec-harga-v8 restart loop (40 restarts) — check for `max_memory_restart` env var leak (known PM2 pattern from MEMORY.md)
- [ ] **[MEDIUM]** Investigate comcen's 19 restarts — the port was fixed to 3645, but restarts suggest ongoing instability

---

### Insight 3: Closing-Date Guard — 4th Consecutive Week Unimplemented, Now the Longest-Running CRITICAL Item (CRITICAL)

**Evidence:**

| Week | Matched Total | Past Close | % Dead | Recommendation |
|------|--------------|-----------|--------|----------------|
| W27 | 851 | — | — | "Add closing-date guard" (1st) |
| W28 | — | — | — | (repeated) |
| W29 | 4,676 | 3,335 | 71% | "3rd consecutive recommendation" |
| W30 | 6,577 | 4,568 | **69%** | **4th consecutive recommendation** |

The matched count grew from 4,676 to 6,577 (+1,901 / +41%) but the dead ratio barely changed (71% → 69%). New tenders are still being matched and left in `matched` status after their closing dates pass.

Of 6,577 matched tenders, only **368 are actionable** (closing date in the future). Only **365 close within 30 days** — meaning nearly all actionable tenders are urgent.

The DB purge removed 20,963 tenders but did NOT fix the ingestion pipeline. This is symptomatic treatment: cleaning the mess without stopping the source.

**Connection:**

The analyst's learning "Writing a Python audit script and running it in one step is more reliable than trying to do incremental file-by-file analysis" captures why this keeps failing — the closing-date guard requires a code change to the ingestion pipeline, not a one-time SQL cleanup. No expert has been assigned this as a GOAL.

W29 Insight 5 identified: "the ones that succeed are atomic and self-contained. The ones that fail require cross-expert coordination that doesn't exist." The closing-date guard is a textbook example.

**Action items:**
- [ ] **[CRITICAL]** Write a builder GOAL.md entry: "Add `if closing_date < today: status='closed'` guard to tender ingestion — single code change, one file"
- [ ] **[HIGH]** Run cleanup SQL now: `UPDATE tenders SET status='closed' WHERE status='matched' AND closing_date < date('now')` — clears 4,568 dead tenders from primary DB

---

### Insight 4: Ingestion Shifted to Burst Mode — 50:1 Daily Variance Suggests Scraper Schedule Change (MEDIUM)

**Evidence:**

Daily ingestion since W29, broken by source:

| Date | SmartGEP | etimad | eperolehan | Other | Total |
|------|----------|--------|------------|-------|-------|
| Jul 13 | 8 | 127 | 54 | 5 | 194 |
| Jul 14 | 708 | 169 | — | — | 877 |
| Jul 15 | 25 | — | — | — | 25 |
| Jul 16 | 1,384 | — | 5 | 38 | 1,427 |
| Jul 17 | 11 | 308 | — | — | 319 |
| Jul 18 | — | 10 | — | — | 10 |
| Jul 19 | 2 | 102 | — | — | 104 |

SmartGEP shows extreme burst behavior: 1,384 on Jul 16, then 11 and 2 on consecutive days. etimad bursts similarly (308 on Jul 17, then 10 on Jul 18). eperolehan barely contributed (59 total in 7 days vs 1,441 historical).

W29 reported 130/day normal rate. W30 averages 422/day but the median is ~194 — the mean is skewed by two massive burst days.

**Connection:**

The devops learning "SmartGEP scraper: 5 accounts, full scrape cycle ~5 hours" and "bridge ingest runs as callback after each account completes" explains the burst pattern — when the scraper runs, it dumps hundreds at once. But the multi-day gaps (Jul 18: 10 total) suggest the scraper isn't running daily.

The smartgep-guardian restart loop fix (Telegram Jul 16: "auth profile 0 bytes caused JSONDecodeError") may have caused some of the gap — if the guardian was crashing, scrapes wouldn't trigger.

**Action items:**
- [ ] **[MEDIUM]** Verify smartgep-guardian scrape frequency — is it supposed to run daily? Check cron/pm2 schedule
- [ ] **[LOW]** Add ingestion rate alerting — daily count below 50 should trigger notification (4th week recommending)

---

### Insight 5: W29 Action Completion — 1 of 10 Partial, 0 of 10 Full (CRITICAL REGRESSION)

**Evidence:**

| # | W29 Action | Status W30 | Evidence |
|---|-----------|-----------|----------|
| 1 | [CRITICAL] Fix Escape key auth bypass | UNKNOWN | No evidence of fix in code; v2.html Escape handler is for sidebar |
| 2 | [CRITICAL] Clean dead matched (SQL) | PARTIAL | DB purged 20,963 tenders, but 4,568 dead matched remain |
| 3 | [CRITICAL] Add closing-date guard | NOT DONE | 69% of matched still past-close (4th week) |
| 4 | [HIGH] Restore bridge-memory | NOT DONE | Still missing (4th week) |
| 5 | [HIGH] Verify SmartGEP Jul 10-11 | UNKNOWN | Guardian was fixed Jul 16 but no retroactive check |
| 6 | [HIGH] Finding-to-fix pipeline | NOT DONE | No evidence of implementation |
| 7 | [MEDIUM] Merge scout/crawler learnings | NOT DONE | Still duplicated in this week's data (6th week) |
| 8 | [MEDIUM] Purge builder learnings | NOT DONE | Still corrupted — "Fix timeout" x3, "Build X" x3 (4th week) |
| 9 | [MEDIUM] Ingestion rate monitoring | NOT DONE | Jul 18 (10 tenders) went undetected |
| 10 | [LOW] Stale-tender auto-expire | PARTIAL | Purge may have been manual version of this |

**Completion: ~1/10 partial (10%)** — down from 40% (W29), 30% (W27), 10% (W26).

Trend: W25=17%, W26=30%, W27=10%, W29=40%, W30=10%. Average: 21%. **79% of synthesis recommendations decay into noise.**

**Connection:**

The conductor's learning is the systemic explanation: "conductor announced builder was 'BUILDING' but never wrote the GOAL file. Wasted 3 steps waiting." The synthesis produces recommendations. Nobody converts them to GOAL.md entries. The operator reads the Telegram summary but doesn't assign work. This is the "finding without fixing" pattern from W29, now confirmed as the dominant failure mode of the synthesis loop itself.

The architect's learning "Providing concrete code snippets in the spec (not just prose) makes builder handoff unambiguous" suggests a fix: synthesis action items should include the exact code change, not just a description.

**Action items:**
- [ ] **[HIGH]** Convert the top 3 CRITICAL items into concrete GOAL.md entries for specific experts — with code snippets, not prose
- [ ] **[MEDIUM]** Establish a "synthesis → GOAL.md" automation: after CONNECTIONS.md is written, auto-generate GOAL.md entries for items tagged CRITICAL or HIGH

---

## Recurring Expert Patterns (Cross-Pollination)

### Failure Patterns

| Pattern | Observed In | Frequency | Trend vs W29 |
|---------|------------|-----------|-------------|
| **Finding without fixing** | synthesis (79% decay), conductor (no GOAL writes), builder (corrupted) | System-wide | ESCALATING — now the #1 systemic issue |
| **Infrastructure blind spots** | sec-* (undocumented deployment), tenders.db (unexplained purge) | System-wide | NEW — worse than W29 |
| **Step overloading** | analyst (14-20), builder (loop) | 2 experts | Persistent |
| **Trust without verify** | reviewer (stale worktree), architect (FTS5), builder (unverified claims) | 3 experts | Persistent |
| **Knowledge drain** | builder (corrupted, 4th week), scout/crawler (unmerged, 6th week) | 2 experts | Persistent, worsening |

### Successful Patterns

| Pattern | Origin | Evidence |
|---------|--------|----------|
| **Atomic operational fixes** | devops/Telegram | pm2-failsafe port fix, comcen port fix, smartgep-guardian auth fix — all done in single focused steps |
| **Failure loop diagnosis** | synthesizer/Telegram | Jul 15 failure loop (model error + memory watchdog) diagnosed and resolved cleanly |
| **Guardian self-healing** | smartgep-guardian | Auth profile crash fixed with atomic write pattern — prevents future 0-byte files |

---

## Fleet Health Snapshot

| Component | Status | Restarts | Memory | Trend vs W29 |
|-----------|--------|----------|--------|-------------|
| yellowpages | online | 8 | 32MB | Improved (W29: 341MB, 14 restarts) |
| harga | online | 12 | 12MB | Stable |
| rag-server | online | 0 | 356MB | Improved (W29: 1 restart) |
| embed-server | online | 1 | 152MB | Stable |
| ocr-server | online | 8 | 664MB | Improved memory (W29: 1,214MB) |
| arbos-orkes | online | 16 | 70MB | Improved (W29: 59 restarts, 183MB) |
| arbos-orkes_ds2 | online | 0 | 32MB | Improved (W29: 5 restarts) |
| arbos-Orkes_Buzz2 | online | 12 | 34MB | Stable |
| token-carousel | online | 0 | 128MB | Stable (W29: 2 restarts) |
| arbos-tronzz | online | 1 | 32MB | Stable |
| smartgep-guardian | online | 0 | 32MB | Stable |
| permauth | online | 1 | 66MB | Stable |
| bayu-main | online | 1 | 15MB | Stable |
| pm2-failsafe | online | 0 | 6MB | Stable |
| **sec-tenders-api** | online | 8 | 351MB | **NEW** |
| **sec-guardian** | online | 0 | 254MB | **NEW** |
| **sec-harga-v8** | online | **40** | 85MB | **NEW — RESTART LOOP** |
| **sec-agent** | online | 23 | 83MB | **NEW** |
| **scheduler-worker** | online | 1 | 283MB | **NEW** |
| **comcen** | online | 19 | 12MB | **NEW — unstable** |
| Other 13 processes | online/stopped | 0-1 | 7-19MB | NEW — stable |
| bridge-memory | **MISSING** | — | — | 4th week missing |
| campaign-orchestrator | **MISSING** | — | — | 4th week missing |
| copark | **MISSING** | — | — | 4th week missing |

**Total fleet memory: 2,840MB** (sec-*: 892MB / 31%, legacy: 1,948MB / 69%)

---

## Pipeline Throughput

| Metric | W29 | W30 | Trend |
|--------|-----|-----|-------|
| Primary DB tenders | 29,229 | 8,266 | **-20,963 (-72%)** — major purge |
| sec.db tenders | — | 5,773 | NEW parallel DB |
| Combined total | 29,229 | 14,039 | -15,190 (-52%) |
| matched | 4,676 | 6,577 | +1,901 (+41%) |
| matched (actionable) | 1,341 | 368 | **-973 (-73%)** — actionable window closing |
| matched (past close) | 3,335 | 4,568 | +1,233 — dead tenders still growing |
| closed | 23,927 | 940 | -22,987 — bulk of purge was closed tenders |
| draft | 190 | 296 | +106 — drafts accumulating again |
| analyzed | — | 177 | New status visible |
| new (untriaged) | 131 | 85 | -46 — slight improvement |
| awarded | 99 | 98 | Stable (historical) |
| Ingestion rate (7d) | ~130/day | ~422/day (bursty) | UP but high variance (10-1,427) |
| Deal pipeline | 1 deal, frozen 117d | 1 deal, frozen 124d | No movement (96d past close) |
| PM2 processes | 14 | 33 | +19 (+136%) |
| Fleet memory | ~1,600MB est. | 2,840MB | +78% |

---

## W29 Action Item Tracking (4-Week Carryover Items)

Items recommended 3+ consecutive weeks without implementation:

| Item | Weeks Recommended | Status |
|------|-------------------|--------|
| Closing-date guard on ingestion | **4 weeks** (W27-W30) | NOT DONE |
| Restore bridge-memory | **4 weeks** (W27-W30) | NOT DONE |
| Purge builder learnings | **4 weeks** (W28-W30) | NOT DONE |
| Merge scout/crawler learnings | **6 weeks** (W25-W30) | NOT DONE |
| Stale-tender auto-expire | **6 weeks** (W25-W30) | NOT DONE |
| Ingestion rate alerting | **4 weeks** (W27-W30) | NOT DONE |

These 6 items have accumulated **28 total recommendation-weeks** with zero completion. The synthesis loop is producing recommendations that nobody reads or acts on.

---

## Summary

| # | Insight | Domain | Impact | Urgency |
|---|---------|--------|--------|---------|
| 1 | Tender platform forked — 20,963 tenders vanished, sec.db holds 5,773 separately, 15,190 unaccounted | Data/Architecture | CRITICAL | Investigate immediately |
| 2 | Fleet doubled 14→33 with undocumented sec-* subsystem (892MB, 12 processes, 1 restart loop) | Infrastructure | HIGH | This week |
| 3 | Closing-date guard: 4th consecutive week, 69% of matched still dead, longest-running CRITICAL | Data Quality | CRITICAL | Overdue |
| 4 | Ingestion shifted to burst mode (50:1 daily variance) after guardian crash fix | Pipeline | MEDIUM | Monitor |
| 5 | Synthesis action completion regressed to 10%, 79% of recommendations decay — synthesis loop itself is broken | Process | CRITICAL | Systemic |

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| 15,190 missing tenders represent data loss, not cleanup | Medium | Unrecoverable historical data | Verify against backups, check git logs for migration commits |
| sec-* and yellowpages diverge into incompatible systems | High | Duplicate work, data inconsistency | Document architecture, define source of truth |
| sec-harga-v8 restart loop (40) cascades or corrupts data | Medium | Service degradation | Check max_memory_restart env var leak |
| Synthesis recommendations ignored indefinitely | High (proven) | Synthesis loop becomes overhead with no value | Auto-convert to GOAL.md entries |
| bridge-memory outage (4 weeks) means 5 projects lost shared context | High | Agents duplicate work, lose cross-project memory | Restart from ecosystem config |
| Fleet at 2.8GB with no memory budget — next OOM will cascade | Medium | Multiple process kills | Set memory budgets for sec-* processes |

## Action Items (Priority Order)

1. [ ] **[CRITICAL]** Investigate the 15,190 missing tenders — intentional purge or data loss? Check git logs, backups, migration scripts [Insight 1]
2. [ ] **[CRITICAL]** Define source of truth: tenders.db vs sec.db — which system owns tender data going forward? [Insight 1]
3. [ ] **[CRITICAL]** Write builder GOAL.md: closing-date guard on ingestion (4th consecutive week, include code snippet) [Insight 3]
4. [ ] **[CRITICAL]** Fix synthesis-to-action pipeline: top CRITICAL items must become GOAL.md entries, not prose recommendations [Insight 5]
5. [ ] **[HIGH]** Fix sec-harga-v8 restart loop (40 restarts) — likely max_memory_restart env var leak [Insight 2]
6. [ ] **[HIGH]** Document sec-* subsystem architecture — 12 processes, 892MB, zero documentation [Insight 2]
7. [ ] **[HIGH]** Restore bridge-memory (4th consecutive week) [Carryover]
8. [ ] **[HIGH]** Run cleanup: `UPDATE tenders SET status='closed' WHERE status='matched' AND closing_date < date('now')` — 4,568 dead tenders [Insight 3]
9. [ ] **[MEDIUM]** Purge builder learnings.md (4th week) — extract real learnings from retro history [Carryover]
10. [ ] **[MEDIUM]** Merge scout + crawler learnings (6th week) [Carryover]
11. [ ] **[LOW]** Add ingestion rate alerting (4th week) [Carryover]
12. [ ] **[LOW]** Investigate deal-0e24b965 — 124 days old, 96 days past close, functionally dead [Pipeline]
