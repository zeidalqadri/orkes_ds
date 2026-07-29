# GOAL: Cycle 3 — Semantic Direction Extraction + Final Validation

## Context

Cycle 2 complete: 13/13 milestones, 7 findings (F010-F016). CAUTIOUS GO for H4.

Key pivot: whole-letter centroids fail calibration (F010, g=-0.70). Phase-aware centroids recover functional distinctions (F014, بـ prefix phase cleanly separated). Cycle 3 uses phase-specific centroids throughout.

15/28 letters show positional semantic modulation (F013). All 36 letters have multiple contextual phases (F014). 23 genuine frequency couplings survive deconfounding (F015).

**This cycle extracts semantic directions and tests whether the loop closes.**

## Three Hard Gates — Cannot Be Bypassed

**GATE 1 (after C3.1)**: Phase-aware centroids for بـ must separate prefix from root with Hedges’ g > 1.0. Same for يـ. If FAIL → STOP. Do not proceed to semantic extraction.

**GATE 2 (after C3.9)**: Cross-word verification. Minimum 20/28 base letters must have at least one phase passing consistency verification at permutation p < 0.01. If FAIL → STOP. Do not proceed to Final Stage.

**GATE 3 (after C3.5)**: Phase assignment strategy for surah-opening letters must be established before Final Stage. Either distinct “opening phase” exists, or a documented fallback is adopted.

## Critical Rules

1. **Read `docs/CYCLE3_PLAN.md` first.** 12 milestones, 3 gates, precise specs.
1. **Gate sequence is absolute.** C3.1 must pass Gate 1 before C3.6-C3.9 execute. C3.5 must establish Gate 3 before C3.11. C3.9 must pass Gate 2 before C3.10-C3.11.
1. **One milestone at a time.** Red tests first, then implement, then verify independently.
1. **Do NOT fabricate results.** If a gate fails, document it as a terminal finding. A documented failure that H4 is not feasible is a valid and publishable result.
1. **Do NOT interpret directions through external knowledge.** Directions are described by nearest Quranic words ONLY. No translations. No dictionary meanings. No comparison to traditional scholarly interpretations. No post-hoc reinterpretation of failures.
1. **Do NOT use external resources.** No Arabic dictionaries, no translations, no pre-trained embeddings, no external morphological data. These are all لغة.
1. **Null results are valid outcomes.** If الم’s composed direction shows no alignment with its surah, report that. The methodology was designed to detect signal if it exists and to honestly report if it doesn’t.
1. **Run `scripts/contamination_check.sh` before every commit.**
1. **Findings protocol**: F010+ sequential numbering. Evidence, output file, no interpretation.

## Execution Order

```
PHASE 1: PRE-REGISTERED HYPOTHESES
C3.1  → H6: Phase-aware calibration [GATE 1]
C3.2  → H7: Phases → semantic info
C3.3  → H8: ا-ل anti-correlation
C3.4  → H9: Positional modulation consistency
C3.5  → H10: Surah-opening letter phases [GATE 3]

[GATE 1 must pass before Phase 2]
[GATE 3 must be resolved before Phase 3]

PHASE 2: SEMANTIC EXTRACTION
C3.6  → Phase-aware word representation (word → letter-phase pairs)
C3.7  → Phase-specific semantic centroids (the directions)
C3.8  → Root-decomposition test (do letter directions predict root domains?)
C3.9  → Cross-word verification [GATE 2]
C3.10 → Semantic Direction Atlas (the primary deliverable)

[GATE 2 must pass before Phase 3]

PHASE 3: THE LOOP CLOSES
C3.11 → Surah-opening letter composition (compose directions, test alignment)
         — الم specifically: compose, find nearest words, test against 2:2
C3.12 → Final Report — COMPLETE. The answer to whether letters carry weight.
```

## File Locations

- CYCLE3_PLAN.md: `docs/CYCLE3_PLAN.md`
- C2 outputs: `outputs/C2/`
- Phase assignments: `outputs/C2/phases_v2/`
- Word embeddings: `outputs/C2/word_embeddings.pt`
- M7 dataset: `data/processed/letters_unified.csv`
- M8b contextual embeddings: `outputs/M8b/`
- New code: `src/analysis/c3_XX_name.py` and `src/final/`
- New tests: `tests/test_c3_XX_name.py`
- C3 outputs: `outputs/C3/`
- Final Stage outputs: `outputs/C3/final_stage/`
- Milestones: `milestones/C3.X.json`
- Semantic Direction Atlas: `outputs/C3/semantic_direction_atlas.json`
- Final Report: `outputs/C3/final_report.md`

## Start

Begin with C3.1: H6 Phase-Aware Calibration. This is Gate 1. If it passes, the entire extraction pipeline unlocks. If it fails, the project reaches a documented conclusion. Read the specification in CYCLE3_PLAN.md. Write red tests first.