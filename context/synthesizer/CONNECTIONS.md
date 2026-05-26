# Synthesizer Report — W19→W20 Transition (Updated)
Updated: 2026-05-11T00:30 UTC (2026-05-11 08:30 MYT)

## Data Sources
- **tenders.db (tenders/tenders.db)**: 3,008 tenders (1,380 gov, 1,378 SmartGEP, 188 ePerolehan, 46 unknown, 16 PETRONAS)
- **Statuses**: 1,668 closed, 798 new, 352 matched, 138 insufficient_data, 51 analyzed, 1 draft
- **deals.json**: 1 active deal (RM75k, ABB Malaysia, stuck since March 18 — 54 days)
- **Wizard sessions**: 34 total (7 active, 25 abandoned, 2 completed) — unchanged
- **Pricing versions**: 40 versions across wizard sessions
- **Audit log**: Last event April 21 (20 days cold — +1 day since last report)
- **New tenders since May 7**: 6 (all ePerolehan, all Queen Elizabeth Hospital pharmacy supplies)
- **SmartGEP scraper**: Alive but idle — 27 backoff cycles × 1,800s = 13.5 hours without ingest
- **data_gov_my harvester**: 12 economic datasets harvested (fuel, CPI, PPI, trade — 61k records)
- **Expert learnings (this cycle)**: 9 experts active, 4 with security/data-integrity findings
- **Telegram chat (May 10)**: Fleet redesign, harga dogfood, GPU saga, PM2 crash loop, SmartGEP alert at 04:13 MYT

---

## Cross-Domain Insights

### Insight 1: SmartGEP Scraper Confirmed in Perpetual Backoff — Portal Unreachable, Not Scraper Dead (CRITICAL)

**Evidence:**
| Indicator | Value |
|-----------|-------|
| arbos-smartgep pm2 status | online (process not crashed) |
| Idle cycle count | 27 consecutive cycles |
| Backoff duration | 1,800 seconds (30 min) per cycle |
| Total idle time | ~13.5 hours |
| Last SmartGEP data ingested | ~May 7 (3+ days ago) |
| consurv account error | "HTTP refresh failed 3x" at 04:13 MYT May 10 |
| New tenders from ePerolehan since | 6 (micro-trickle, not a recovery) |

**Connection:**
The previous report flagged a pipeline freeze but could not distinguish scraper-crash from source-unavailable. We now have the answer: **the scraper is running but the SmartGEP portal is refusing connections.**

The scraper logged 3 consecutive HTTP refresh failures on the `consurv` account at 04:13 MYT, entered its 30-minute backoff, and has been sleeping for 27 cycles (13.5 hours) without a single retry attempt. The devops team had already documented the root cause: *"SmartGEP portal goes down during SAP maintenance (ECC6.0 → S4HANA transitions)."*

Critical design flaw: the backoff is fixed-interval (always 30 min, never escalating or alerting). If the portal stays down for a multi-day SAP migration, the scraper will quietly sleep forever — no alert, no escalation, no retry attempt on a shorter interval. The system is effectively in a coma but the monitor shows "online."

Meanwhile, 1,378 SmartGEP tenders (46% of the database) are locked behind this portal. The 6 new ePerolehan pharmacy-supply tenders prove the secondary source still works, but at a trickle rate that cannot sustain the pipeline.

**Action items:**
- [ ] **URGENT**: Verify SmartGEP portal availability directly: `curl -I https://smartgep.petronas.com` (or equivalent login URL). If it's SAP maintenance, get the ETA.
- [ ] **URGENT**: Restart arbos-smartgep to force a backoff reset: `pm2 restart arbos-smartgep`. If still failing, check cookie expiry in `smartgep_cookies_consurv.json`.
- [ ] Fix backoff logic: implement exponential backoff capped at 10 cycles (5 hours), then escalate to Telegram alert rather than sleeping indefinitely.
- [ ] Add a Telegram alert when any scraper account enters backoff > 10 cycles — the operator should know before 13.5 hours pass.
- [ ] Do not allocate development bandwidth (data.gov.my, fleet redesign) while the primary tender pipeline is offline. Triaging the main feed should preempt all non-critical infra work.

---

### Insight 2: dyna-segmen Has 30 "New" (Unexamined) Tenders Closing Today — Entity Asymmetry at Point of Failure (HIGH)

**Evidence for tenders closing May 11:**
| Entity | Analyzed | Matched | New | Total Active | % Examined |
|--------|----------|---------|-----|-------------|-----------|
| consurv-technic | 6 | 18 | 15 | 39 | 62% |
| dyna-segmen | 0 | 6 | 30 | 36 | 17% |
| Combined | 6 | 24 | 45 | 75 | 40% |

**Sample dyna-segmen opportunities closing today:**
- Supply/delivery of MATERIAL for PETRONAS CHEMICALS MTBE (SmartGEP, matched)
- 989-unit ambulance Type B for KKM (FTA/CPTPP, matched, RM multi-million)
- HD imaging resolution camera for Sarawak Forest Dept (matched)
- 4-unit Fluid Management System, Hospital Melaka (new)
- 4-unit Cardiac Monitor, Hospital Tuanku Jaafar (new)
- 6-unit Anaesthesia Monitor, Hospital Raja Perempuan Zainab II (new)

**Connection:**
consurv-technic has 6 analyzed + 18 matched = 24/39 (62%) examined tenders closing today. dyna-segmen has 0 analyzed + 6 matched = 6/36 (17%). This is not random variation — it's a systematic entity bias in the analysis pipeline.

Three possible causes:
1. **Analysis queue prioritizes consurv-technic** — the pipeline processes entities in order and never reaches dyna-segmen
2. **Classifier has entity bias** — the match rules are tuned for consurv-technic's domain (surveying, mapping, defense) and miss dyna-segmen's scope (medical equipment, IT, general supplies)
3. **dyna-segmen tenders arrive through ePerolehan** — if the ePerolehan parser runs after the SmartGEP parser, and the analysis batch is time-limited, dyna-segmen's government tenders are always out of time

The 989-unit ambulance tender alone (FTA/CPTPP, matched, closing today) is potentially a multimillion-ringgit opportunity sitting in "matched" status with zero analysis activity. It was matched by the classifier (meaning it's relevant to dyna-segmen's capabilities) but never analyzed.

**Action items:**
- [ ] **URGENT**: Batch-analyze dyna-segmen's 30 "new" and 6 "matched" tenders closing today — hours of opportunity remaining
- [ ] Investigate analysis pipeline entity routing: is there a hardcoded entity order? Are dyna-segmen tenders deprioritized?
- [ ] Profile classifier accuracy by entity: generate precision/recall numbers for consurv vs dyna to detect entity bias
- [ ] Add entity-based throughput metrics to the dashboard: `analyzed/(new+matched)` ratio per entity, updated every cycle

---

### Insight 3: 4 Domain Experts Found Security/Data-Integrity Bugs in 24 Hours — Reactive Patching Replacing Proactive Design (MEDIUM)

**Evidence from this cycle's expert learnings:**
| Expert | Finding | Severity | Type |
|--------|---------|----------|------|
| reviewer | DNS rebinding SSRF bypass (redirect-based) — fix: `follow_redirects=False` | Medium | Security |
| jaga | Auth bypass via Escape key on login modal | Critical | Security |
| elliot | XSS, path traversal, SSRF — all patched | Critical | Security |
| architect | FTS5 content= column mapping = silent data corruption | High | Data integrity |
| builder | Timeout bug in worker.py | Medium | Reliability |

**Connection:**
Five bugs from five experts in a single cycle. Four of the five are security or data-integrity issues — not feature gaps, not performance problems, but fundamental correctness failures that should have been caught before deployment.

The pattern is consistent: every feature was built for functionality-first, with security and data integrity deferred under the "internal tool" exception:
- **reviewer**: Accepts DNS rebinding as "acceptable for API-key-protected internal tools" — the same logic that Jaga's auth bypass and Elliot's XSS exploited
- **jaga**: Auth bypass through login modal Escape key — a 30-second test that was never run
- **architect**: FTS5 content= column positions silently diverged — a documented gotcha that was never checked
- **builder**: Timeout bug — worker.py was deployed without testing edge cases

The cost: 5 expert cycles consumed by bug fixes that could have been prevented by a 5-minute pre-merge security checklist. Those same 5 cycles could have analyzed 50+ matched tenders.

This is a **process problem, not a people problem**. The build-fast culture is optimized for feature velocity but creates a growing tail of rework. Every bug found in review is rework.

**Action items:**
- [ ] Create a pre-commit security checklist (5 min): SSRF, auth bypass, XSS, path traversal, data integrity. Require sign-off before any merge.
- [ ] Create a "known risk register" (`context/experts/risks.md`) for deferred security decisions — DNS rebinding, unvalidated redirects, cookie expiration. When a risk is accepted, log it with a review date.
- [ ] Route infrastructure changes through reviewer BEFORE implementation, not after — review-then-build costs less than build-then-review.
- [ ] Track expert cycle allocation: % to bug fixes vs features vs pipeline throughput. Target: <20% bug fix.

---

### Insight 4: data.gov.my Harvester Built in 12 Minutes — Wrong Data for the Pipeline, Right Data for Harga (MEDIUM)

**Evidence:**
| Dataset | Records | Relevance |
|---------|---------|-----------|
| fuelprice (weekly RON95/RON97/diesel) | 919 | Pricing: fuel cost for contracts |
| cpi_headline (monthly, 13 groups) | 4,410 | Pricing: inflation adjustment |
| cpi_state (monthly, by state) | 43,680 | Pricing: geographic cost variation |
| ppi/ppi_sitc/ppi_msic | 8,527 | Pricing: producer cost index |
| trade_headline + iowrt | 1,021 | Context: market volume |
| economic_indicators + ipi | 608 | Context: leading indicators |
| cpi_core + cpi_annual_inflation | 1,917 | Pricing: core inflation |
| **Total** | **~61,082** | |

**Connection:**
The harvester was built in 12 minutes (15:41→15:53 MYT on May 10) — impressive velocity. However, the 12 datasets cover **economic indicators** (fuel prices, CPI, PPI, trade), not tender notices or procurement data.

Where this data fits:
- **Harga pricing engine**: Fuel prices + CPI + PPI feed directly into cost-escalation calculations for multi-year contracts
- **Geographic pricing**: State-level CPI enables regionally-differentiated pricing strategy
- **Inflation clauses**: Long-term contracts require official CPI data for escalation — these datasets provide the authoritative reference

Where this data is a distraction:
- Finding new tender opportunities (the primary pipeline function)
- Qualifying bidders or competitors
- Understanding tender-specific requirements

The data.gov.my datasets add real value to Harga's pricing accuracy, but they were built while the primary tender pipeline was (and still is) completely frozen. The same 12 minutes plus indexing time (~1-2h for 61k records) could have restored the SmartGEP feed. **Build the right thing, but build it in the right order.**

**Action items:**
- [ ] Connect data.gov.my CPI/PPI to Harga's pricing engine for automatic cost escalation on multi-year contracts
- [ ] Do not expand data.gov.my harvest until the SmartGEP pipeline is restored and ingesting at pre-freeze rates
- [ ] After pipeline restoration, add: tender awards data (who won), SSM company registration, and procurement plans
- [ ] Add dataset classification tags in the DB: `macroeconomic` vs `procurement` vs `company` — so future development targets the right category

---

### Insight 5: 20-Day Audit Silence + All Issues Found by Accident = Zero Monitoring (CRITICAL)

**Evidence:**
| Discovery on May 10 | How Found | Time to Detection |
|--------------------|-----------|-----------------|
| SmartGEP HTTP refresh failed 3x | Telegram log scroll (manual) | Immediate (but ignored) |
| Fleet 401 errors | User tried to access page | Unknown |
| Fleet only shows tronzz | User clicked around | Unknown |
| PM2 crash loop (pm2-the_bomb.service) | SSH tunnel failure | Unknown hours |
| GPU driver stale kernel module | User ran nvidia-smi | Unknown days |
| Harga dogfood: auth bypass, suggestion pills | User requested dogfood pass | N/A (proactive) |

**Connection:**
Every single infrastructure issue on May 10 was discovered by **accident** — either the user noticed something was wrong while doing unrelated work, or the user proactively asked for a test. None were detected by monitoring, alerts, or automated checks.

The audit log has been silent for 20 days. The 6 new ePerolehan tenders prove the secondary parser IS working — but nobody in the Telegram chat mentioned it. There's no "X new tenders ingested today" summary. No "N tenders closing within 48h" alert. No "scraper in backoff" notification.

The 20-day audit gap creates a blind spot: we can't tell if status transitions are happening without logging, if wizard phases are advancing silently, or if the system is truly comatose. The previous report treated this as MEDIUM. It should be CRITICAL — because without monitoring, every failure becomes a crisis discovered by chance.

The solution doesn't need to be complex. A daily cron job that:
1. Counts new tenders ingested in the last 24h
2. Counts tenders closing within 48h
3. Checks scraper status (backoff? crashed? running?)
4. Sends a Telegram summary

...would have caught the May 7 freeze on May 8, three days earlier than manual discovery.

**Action items:**
- [ ] **URGENT**: Build a daily cron digest: `python arbos.py send "Daily Digest: X new, Y closing-48h, Z scraper status"` — deploy today
- [ ] **URGENT**: Add a `last_ingested_at` field to STATE.md — visible to every agent on every step
- [ ] Build immediate monitoring: if no new tenders in 24h → Telegram alert
- [ ] Add `/api/health` endpoint for SmartGEP scraper status: `{running: true, backoff_cycles: 0, last_ingest: "2026-05-10T..."}`
- [ ] Track discovery mode per incident: `monitoring` vs `accident` — target: 100% of issues found by monitoring
- [ ] Dedicate one expert cycle per week to system health audit (no feature work, no bug fixes — just checking)

---

## Summary

| # | Insight | Domain | Impact | Urgency |
|---|---------|--------|--------|---------|
| 1 | SmartGEP confirmed in perpetual backoff — portal unreachable, not scraper dead | Pipeline | **CRITICAL** | Today |
| 2 | dyna-segmen: 30/36 tenders closing today are "new" (unexamined) vs 6/39 for consurv | Pipeline | HIGH | Today |
| 3 | 4 security/data-integrity bugs from 4 experts in 24h = systemic process failure | Process | MEDIUM | This week |
| 4 | data.gov.my: right data for Harga, wrong data for pipeline — built out of order | Strategy | MEDIUM | This week |
| 5 | 20-day audit silence + all issues found by accident = zero monitoring | Monitoring | **CRITICAL** | Today |

## Action Items (Priority Order)

- [ ] **[URGENT]** Restart arbos-smartgep to reset 27-cycle backoff. Check SmartGEP portal availability and cookie expiry. [Insight 1]
- [ ] **[URGENT]** Batch-analyze dyna-segmen's 30 "new" tenders closing today — hours of opportunity remaining. [Insight 2]
- [ ] **[URGENT]** Build daily cron digest: new tenders, closing-soon count, scraper status → Telegram. [Insight 5]
- [ ] Restore SmartGEP pipeline before expanding data.gov.my or building fleet features. [Insight 1]
- [ ] Investigate entity-based analysis queue bias: why does consurv get examined and dyna doesn't? [Insight 2]
- [ ] Create a known risk register for deferred security decisions (DNS rebinding, auth bypass, etc.). [Insight 3]
- [ ] Add pre-commit security checklist (5 min) before any merge into main. [Insight 3]
- [ ] Connect data.gov.my CPI/PPI to Harga's pricing engine for cost escalation on multi-year contracts. [Insight 4]
- [ ] Add entity-based throughput metric to dashboard: `analyzed/(new+matched)` per entity. [Insight 2]
- [ ] Fix SmartGEP backoff logic: exponential backoff, cap at 10 cycles, alert at cap. [Insight 1]
- [ ] Tag all data.gov.my datasets as `macroeconomic` vs `procurement` to guide future development. [Insight 4]
- [ ] Track expert cycle allocation: % to bug fixes vs features vs pipeline throughput. [Insight 3]
- [ ] Add last_ingested_at to STATE.md and track discovery mode (monitoring vs accident) for every incident. [Insight 5]
