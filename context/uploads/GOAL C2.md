# GOAL: Cycle 2 — Remedial Audit + Confirmatory Analysis

## Context

Cycle 1 is complete (17/17, 164 tests, 9 findings). Stage 0 passed (17/17). The unified dataset is solid (327,793 × 31, 183 tests). Three findings banked pre-Cycle 1 (F001-F003). Six more from Cycle 1 (F004-F009). Strongest signal: articulatory zone predicts diacritical entropy (F003, η²=0.44, p_bonf=0.023).

Two contamination violations were found in the Cycle 1 report (Meccan/Medinan reference, supervised annotation recommendation). A systematic remedial pass is required before Cycle 2 analysis begins.

The primary Cycle 2 deliverable is **word embeddings trained on the Quran only** and **letter semantic centroids** — the first approximation of each letter’s semantic direction.

## Critical Rules

1. **Read `docs/CYCLE2_PLAN.md` first.** It defines 14 milestones: 3 remedial (R0.1-R0.3), then 11 analytical (C2.1-C2.11). Follow it precisely.
1. **Remedial milestones execute FIRST.** R0.1 (contamination sweep), R0.2 (guardrails update), R0.3 (output integrity) — ALL THREE must complete before any C2 milestone begins. If R0.1 finds contamination in analytical code, assess impact before proceeding.
1. **One milestone at a time.** Complete each fully before starting the next. Dependency order is strict.
1. **Every milestone follows this sequence:**
- Read the milestone spec in CYCLE2_PLAN.md
- Write tests FIRST — confirm they are RED (failing) before implementation
- Write code in `src/analysis/` (or `scripts/` for R0)
- Run implementation
- Run tests — confirm GREEN
- Run `scripts/verify_milestone.sh` — independent verification
- Write outputs to `outputs/R0/` or `outputs/C2/`
- Write milestone marker to `milestones/R0.X.json` or `milestones/C2.X.json`
- Git commit
- Proceed to next
1. **Do NOT fabricate test results.** If tests fail, diagnose and fix. If unfixable after 3 attempts, document the failure and stop. A documented failure is infinitely more valuable than a fabricated pass. The M7 fabrication incident is the reason this rule exists.
1. **Do NOT interpret findings.** Compute, measure, report. No “this suggests…” or “this means…”. Interpretation requires human review at C2.11.
1. **Do NOT use external resources.** No pre-trained embeddings. No Arabic dictionaries. No translations. No external word lists. No morphological analyzers trained on non-Quranic data. No external semantic labels. These are all لغة. Read the Contamination Watchlist in CYCLE2_PLAN.md §end.
1. **Findings protocol**: Significant unexpected results (p < 0.01, effect > 0.3) filed as F010+ in `outputs/C2/findings/` with: number, one-sentence description, evidence, output file. No interpretation.
1. **The contamination check script** (R0.2) must be run before every commit from this point forward. If it flags anything, fix before committing.

## Execution Order

```
PHASE 0: REMEDIAL (must complete before any analysis)
R0.1  → Contamination Sweep (scan all code + docs, fix violations)
R0.2  → Self-Validation Framework (update CLAUDE.md, create contamination_check.sh)
R0.3  → Output Integrity Verification (spot-check C1 outputs + finding evidence chains)
[GATE: R0 complete, zero contamination, integrity confirmed]

PHASE 1: WORD EMBEDDINGS + SEMANTIC CENTROIDS
C2.1  → Word Embeddings (word2vec on Quran verse co-occurrence, 50D, from scratch)
C2.2  → Letter Semantic Centroids (mean word vector per letter)
C2.3  → Calibration Re-Test (do prep/actor centroids separate?)
C2.4  → Centroid Structure (clustering, Mantel tests vs zone/family/freq)

PHASE 2: DEEPENING CYCLE 1 FINDINGS
C2.5  → Zone-Entropy Decomposition (which zones drive F003?)
C2.6  → Positional Analysis (word-initial/medial/final profiles)
C2.7  → Positional Semantic Contribution (does root position modulate centroid?)
C2.8  → Phase Detection Redesign (PCA + HDBSCAN, recover known phases)
C2.9  → Length-Deconfounded Frequency (normalize, re-test couplings)

PHASE 3: SYNTHESIS
C2.10 → Cross-Analysis Synthesis (all interactions, new findings)
C2.11 → Cycle 2 Report — STOP HERE. Human review required.
```

## File Locations

- CYCLE2_PLAN.md: `docs/CYCLE2_PLAN.md`
- M7 dataset: `data/processed/letters_unified.csv`
- M8b embeddings: `outputs/M8b/`
- C1 outputs: `outputs/C1/`
- New code: `src/analysis/c2_XX_name.py` and `src/analysis/r0_XX_name.py`
- New tests: `tests/test_c2_XX_name.py` and `tests/test_r0_XX_name.py`
- R0 outputs: `outputs/R0/`
- C2 outputs: `outputs/C2/`
- Findings: `outputs/C2/findings/`
- Milestones: `milestones/R0.X.json` and `milestones/C2.X.json`

## Start

Begin with R0.1: Contamination Sweep. Read its specification in CYCLE2_PLAN.md. Scan every file. Fix every violation. Document everything. This is the foundation check before any new analysis.