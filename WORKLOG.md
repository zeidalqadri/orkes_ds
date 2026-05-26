# Active Work
Project: /home/the_bomb/orkes_ds2
Task: تعلّ — Cycle 1 Exploratory Analysis (17 milestones)
Status: in-progress
Updated: 2026-05-26T18:45 UTC

### 11. PROJECT: تعلّ — The Weight of Letters

**M0-M6: COMPLETE** (2026-05-25 — 2026-05-26)
- All foundation milestones done. See completed section for details.

**M7: Unified Multi-Layer Dataset — COMPLETE** (2026-05-26)
- 327,793 rows x 31 columns across 7 layers
- Tests: 45/45 M7 tests, 183/183 total suite

**M8: PMI Computation — COMPLETE** (2026-05-26)
- 25 PMI tests, hand-verifiable arithmetic. 208/208 green. Commit `576df4f`.

**M8b: Character-Level Embeddings — COMPLETE** (2026-05-26)
- 2L/4H/128D transformer, 408K params, factored embeddings (letter + diac)
- 250 tokens: (letter, primary_diac, has_shadda) triples
- 3 masking tasks (mask letter, mask diac, mask both) at equal probability
- 10% verse-level holdout, early stopped epoch 29 (best: 19)
- Val loss 4.27 vs random baseline 5.78 (26% improvement)
- Embedding cosine sim [-0.18, 0.63] — structure present, not collapsed
- All seeds pinned (42), artifacts with SHA-256 in manifest.json
- 236/236 tests green (28 M8b + 208 prior). Commit `863d4a8`.
- Finding F001 filed: Diacritical head 35% > letter head 21% improvement (grammar more locally predictable than root selection)

**M9: Stage 0 Calibration Gate — 17/17 PASS** (2026-05-26)
- Gate: **OPEN** — all 17 tests pass. Ready for Cycle 1.

**Cycle 1: All 17 Milestones COMPLETE** (2026-05-26)
- C1.1-C1.17: ALL PASS. 9 findings (F001-F009). 5 Cycle 2 hypotheses pre-registered.
- Strongest signal: Zone → Entropy (η²=0.44, p_bonf=0.023)
- Report: `outputs/C1/cycle1_report.md`
- **STOP**: Human review required before Cycle 2.

### Setup
- tala repo at /home/the_bomb/orkes/tala/ (permanent location)
- Python 3.12, standard library + numpy (PMI), PyTorch (embeddings only)

## Completed
- ### 10. Yellowpages memory set to 1GB (2026-05-21)
- ### 9. rag-server Memory Pressure Fix (2026-05-21)
- ### 8. Harga fix: Import button dims after import (multi-chat guard)
- ### 7. PM2 restart loop fix + 14 restarts investigation (env var leak: max_memory_restart)
- ### 6. Context Overflow Fix (2026-05-08)
- ### 5. PM2 restart loop fix (max_memory_restart type corruption) (2026-05-08)
- ### 4. Auto-babysit loop (inbox polling, intent detection, self-OOD)
- ### 3. Persistent agent memory (shared memory architecture, AgentDB, RVF)
