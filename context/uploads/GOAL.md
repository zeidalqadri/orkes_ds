# GOAL: Cycle 1 Exploratory Analysis

## Context

Stage 0 calibration is PASSED (17/17). The unified dataset is built (327,793 rows × 31 columns). Three findings already banked (F001 diacritical predictability, F002 geometric-distributional independence, F003 frequency in confidence not geometry).

You are now executing Cycle 1: the exploratory analysis across all four layers of the full dataset.

## Critical Rules

1. **Read `docs/CYCLE1_PLAN.md` first.** It defines 17 milestones (C1.1 through C1.17), each with exact inputs, outputs, verification criteria, and dependencies. Follow it precisely.
1. **One milestone at a time.** Complete C1.1 fully before starting C1.2. Do not batch. Do not skip ahead. Do not work on a milestone whose dependencies are incomplete.
1. **Every milestone follows this sequence:**
- Read the milestone spec in CYCLE1_PLAN.md
- Write the code in `src/analysis/`
- Write tests in `tests/` — tests must be RED before implementation (run them, confirm they fail, then implement)
- Run implementation
- Run tests — confirm GREEN
- Run `scripts/verify_milestone.sh` — independent pytest verification
- Write output files to `outputs/C1/`
- Write milestone marker to `milestones/C1.X.json` with results summary
- Git commit with descriptive message
- **Only then** proceed to next milestone
1. **Do NOT fabricate test results.** If tests fail, diagnose and fix. If you cannot fix after 3 attempts, write the failure into the milestone JSON and stop. A documented failure is infinitely more valuable than a fabricated pass.
1. **Do NOT interpret findings.** Compute, measure, report. If a correlation is r=0.7 with p<0.001, report that. Do not write “this suggests that…” or “this means…”. Interpretation happens at C1.17 and requires human review.
1. **Verification for every output:**
- Row counts match expected values
- No inf/nan in any numeric column
- Spot-checks against raw data (pick 3 random instances, trace from source XML through to output, confirm values match)
- Statistical tests include effect sizes, not just p-values
- Bonferroni correction applied whenever multiple comparisons are made
1. **Findings protocol.** If any analysis produces a result that is clearly significant (p < 0.01, effect size > 0.3) and was not anticipated, file it as F00X in `outputs/C1/findings/` with:
- Finding number (sequential after F003)
- One-sentence description
- Evidence (test statistic, p-value, effect size)
- Output file containing the full data
- No interpretation — just the observation

## Milestone Execution Order

```
C1.1  → Letter Frequency Atlas
C1.2  → Diacritical Entropy
C1.3  → PMI Landscape: Word-Level
C1.4  → PMI Landscape: Verse-Level
C1.5  → Frequency Arcs (depends: C1.1)
C1.6  → Inter-Arrival Analysis (depends: C1.1)
C1.7  → Co-Frequency Matrix (depends: C1.1)
C1.8  → Diacritical Melody Extraction (depends: C1.2)
C1.9  → Conjunction/Opposition Atlas (depends: C1.3 + C1.4)
C1.10 → Phase Detection: Full Alphabet (depends: M8b embeddings)
C1.11 → Embedding Space Visualization (depends: M8b embeddings)
C1.12 → Geometric vs Distributional Distance (depends: M6 + C1.9 + C1.1)
C1.13 → Articulatory Zone Profiling (depends: M5 + C1.1 + C1.2)
C1.14 → Frequency Coupled Systems (depends: C1.5 + C1.7)
C1.15 → Sonic Weight Contouring (depends: C1.8 + C1.1 + M5)
C1.16 → Cross-Track Interaction Summary (depends: ALL above)
C1.17 → Cycle 1 Findings Report (depends: C1.16) — STOP HERE, human review required
```

## File Locations

- Source data: `data/source/quran-uthmani-tanzil.xml`
- M7 unified dataset: `data/processed/letters_unified.csv`
- M8a PMI: `src/calibration/pmi.py`
- M8b embeddings: `outputs/M8b/` (model_best.pt, embedding_matrix.pt, vocabulary.json)
- Geometric assignments: from M6 columns in unified dataset
- Makhraj assignments: from M5 columns in unified dataset
- New code: `src/analysis/c1_XX_name.py`
- New tests: `tests/test_c1_XX_name.py`
- Outputs: `outputs/C1/`
- Findings: `outputs/C1/findings/`
- Milestones: `milestones/C1.X.json`

## Start

Begin with C1.1: Letter Frequency Atlas. Read its specification in CYCLE1_PLAN.md. Write the tests first (they must fail). Then implement. Then verify.