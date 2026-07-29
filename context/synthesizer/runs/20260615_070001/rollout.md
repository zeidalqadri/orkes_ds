W25 synthesis complete. CONNECTIONS.md written with 5 insights, 10 action items, 6 risks.

**Key findings this week:**

1. **CRITICAL — eperolehan false negatives**: The `insufficient_data` classifier kills eperolehan partial tenders at 12x SmartGEP's rate (21.1% vs 1.7%). ~80 matchable Malaysian government tenders potentially lost. Needs source-specific thresholds.

2. **HIGH — Etimad is noise**: 76% of the DB, 0% commercial conversion ever, still ingesting ~109/day. System self-quarantined it into "watching" but operator hasn't formalized the decision.

3. **HIGH — Expert knowledge duplication**: Scout and crawler independently stored 6+ identical learnings. Builder cycling through "Fix timeout" and "Build X" 3x each. Zero W23b consolidation actions completed.

4. **HIGH — 20-day user blackout**: 371 actionable tenders (68 matched + 300 draft + 3 analyzed) closing Jun 15-30 with nobody reviewing them. Single deal frozen 89 days.

5. **MEDIUM — Memory anomaly**: rag-server dropped from 1,248MB to 450MB, embed-server from 1,345MB to 219MB. If indices aren't fully loaded, matching quality is silently degraded.

W24 action item completion: 1.5/9 (17%). Most action was system-driven, not operator-driven.