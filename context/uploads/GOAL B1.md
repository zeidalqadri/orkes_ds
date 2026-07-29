# GOAL: Path B Phase 1 — Contextual Word Embeddings + Gate 2 Re-Test

## Context

Cycle 3 complete. 49 milestones. Gate 2 FAILED: 1/28 letters verified per-word at p < 0.01 (threshold: 20/28). Root-level prediction works (F024, cos sim 0.486 vs null 0.364, p=0.0). The signal exists at aggregate level but doesn’t compose per-word with the current setup.

**Hypothesis**: The bottleneck is the static 50D PPMI+SVD word embeddings, not the letter signal itself. The M8b contextual model (2L/4H/128D) already encodes phase-sensitive letter information — it passed calibration. But we never used it for word-level representations. We used a separate, cruder method (co-occurrence counts).

**Intervention**: Extract contextual word embeddings from the existing M8b model (forward pass only — no new training). Recompute everything downstream with these richer representations. Re-test Gate 2.

## What This Session Does

1. Extract contextual word embeddings from M8b (one forward pass)
1. Recompute phase-specific semantic centroids in 128D space
1. Re-run root decomposition — does F024 get stronger?
1. Re-run cross-word verification — does Gate 2 move?
1. Run frequency-stratified verification — does the signal exist in well-attested words?
1. Decision: proceed to B2, B3, or Final Stage (or accept boundary)

## Critical Rules

1. **No new model training.** M8b model weights are frozen. This is inference only.
1. **No external resources.** Same constraints as always.
1. **Red tests first** for every new module.
1. **Run `scripts/contamination_check.sh` before every commit.**
1. **Do NOT fabricate results.** If Gate 2 still fails, report honestly.
1. **Preserve all Cycle 3 outputs.** Path B outputs go to `outputs/B1/`. Nothing in `outputs/C3/` is modified.

## Milestones

### B1.1 — Extract Contextual Word Embeddings

**Question**: What 128D vector does the M8b model assign to each word instance in context?

**Input**: M8b model (`outputs/M8b/model_best.pt`) + M7 dataset

**Method**:

- For each verse in the corpus:
  - Tokenize into the M8b vocabulary (~250 character-level tokens)
  - Forward pass through the frozen M8b model
  - For each word (defined by text spacing): pool the hidden states of its constituent character tokens (mean pooling)
  - This produces one 128D vector per word instance, contextualized by the verse it appears in
- The same word type in different verses gets different vectors — this is the key advantage over static PPMI+SVD
- Also compute per-word-type average (mean across all instances) for comparison

**Output**:

- `outputs/B1/contextual_word_vectors.pt` — tensor of shape (N_word_instances, 128), with index mapping to (surah, verse, word_position)
- `outputs/B1/word_type_averages.pt` — tensor of shape (N_word_types, 128), mean of all instances per type
- `outputs/B1/word_type_averages.csv` — human-readable with word text and instance count

**Verification**:

- Total word instances should match M7 word count
- Spot-check 5 word instances: trace through M8b manually (or compare to M8b embedding_matrix for individual characters)
- Verify that the same word type in different verses produces DIFFERENT vectors (cosine similarity < 1.0 between instances)
- Verify that the same word type’s instances are MORE similar to each other than to random other words (mean within-type similarity > mean between-type similarity)

**Size**: Small. One forward pass (~30 seconds GPU). ~160MB output.

-----

### B1.2 — Recompute Phase-Specific Centroids

**Question**: Do phase-specific semantic centroids look different in 128D contextual space vs 50D static space?

**Input**: B1.1 (contextual word vectors) + C3.6 (word-phase mapping) + C2.8 (HDBSCAN phase assignments)

**Method**:

- For each letter form, for each HDBSCAN phase:
  - Collect all word instances where this letter appears in this phase
  - For each word instance, use its contextual vector (from B1.1), not the static type vector
  - Compute centroid (mean) of these contextual vectors
  - Compute dispersion (mean distance from centroid)
- Compare to C3.7 centroids: are the 128D contextual centroids more tightly clustered (lower dispersion)?

**Output**:

- `outputs/B1/phase_centroids_contextual.json` — per (letter, phase): centroid (128D), word instance count, dispersion, top 5 nearest word instances
- `outputs/B1/centroid_comparison.json` — per (letter, phase): dispersion in 50D static vs 128D contextual, cosine similarity between the two centroids

**Verification**:

- Same number of (letter, phase) pairs as C3.7 (268)
- Word instance counts ≥ word type counts (instances ≥ types, since types are unique but instances repeat)
- Dispersion comparison: if contextual centroids are tighter, the representations are more phase-coherent

**Size**: Small. Aggregation over existing data.

-----

### B1.3 — Root Decomposition Re-Test

**Question**: Does F024 (root-level prediction) get stronger with contextual centroids?

**Input**: B1.2 (contextual phase centroids) + C3.6 (word-phase mapping) + morphological baseline roots

**Method**:

- Identical to C3.8, but using 128D contextual phase centroids instead of 50D static
- Per root: compose letter phase centroids → predicted root direction
- Per root: compute observed root direction from contextual word vectors (mean of all instances of words in this root family)
- Cosine similarity between predicted and observed
- Cross-validate: same 80/20 root split as C3.8
- Null baseline: random phase assignment (same as C3.8)
- **Key comparison**: C3.8 result (cos sim 0.486 vs null 0.364) vs B1.3 result

**Output**:

- `outputs/B1/root_decomposition_contextual.json` — per root: predicted, observed, cosine similarity
- `outputs/B1/root_decomposition_comparison.json` — C3.8 vs B1.3 side-by-side

**Verification**:

- Same roots as C3.8 (same computational discovery)
- Same cross-validation split (same random seed)
- Null baseline recomputed (may differ slightly due to 128D vs 50D space)
- If cos sim improves: contextual representations capture more letter-phase signal. If unchanged: the improvement is in the embedding space geometry, not in the composition quality.

**Size**: Small. Same computation as C3.8, different vectors.

-----

### B1.4 — Cross-Word Verification Re-Test (Gate 2 Retry)

**Question**: Does Gate 2 pass with contextual word embeddings?

**Input**: B1.2 (contextual phase centroids) + B1.1 (contextual word vectors) + C3.6 (word-phase mapping)

**Method**:

- Identical to C3.9, but using contextual centroids and contextual word vectors
- Per (letter, phase): compose all letter-phase centroids → predicted word direction
- Compare to actual contextual word vector (cosine similarity)
- Consistency score: proportion above threshold
- Permutation test: random phase assignment, 1000 permutations, p < 0.01
- **Three variants run in parallel**:
  
  **Variant A — Full vocabulary, equal weight** (direct comparison to C3.9):
  - All 4,092 word types, each weighted equally
  - Gate 2 criterion: 20/28 base letters with at least one verified phase
  
  **Variant B — Frequency-weighted**:
  - Words weighted by log(frequency): high-frequency words count more
  - Same criterion
  
  **Variant C — Frequency-stratified**:
  - Stratum 1: words with ≥50 instances (most reliable embeddings)
  - Stratum 2: words with 10-49 instances
  - Stratum 3: words with 3-9 instances
  - Report Gate 2 pass rate PER STRATUM
  - If Stratum 1 passes (20+ letters) but Stratum 3 fails: the signal exists in well-attested words

**Output**:

- `outputs/B1/gate2_variant_A.json` — full results, direct comparison to C3.9
- `outputs/B1/gate2_variant_B.json` — frequency-weighted results
- `outputs/B1/gate2_variant_C.json` — per-stratum results
- `outputs/B1/gate2_comparison.json` — C3.9 (1/28) vs B1.4 variants side-by-side

**Verification**:

- Variant A uses identical method to C3.9 except embedding source — any improvement is attributable to the embeddings
- Permutation tests use same number of permutations (1000) and same threshold (p < 0.01)
- All three variants reported regardless of outcome — no cherry-picking the best result

**Size**: Medium. Per-word composition and permutation testing across full vocabulary × 3 variants.

-----

### B1.5 — Decision Report

**Question**: What did Phase B1 achieve? What’s next?

**Input**: B1.1-B1.4 results + all prior findings

**Output**: `outputs/B1/decision_report.md`:

**Section 1: Results comparison**

- F024 original (50D) vs B1.3 (128D contextual): root-level improvement?
- Gate 2 original (1/28) vs B1.4 Variant A: per-word improvement?
- Gate 2 Variant B (weighted): different from A?
- Gate 2 Variant C (stratified): does signal exist in high-frequency stratum?

**Section 2: Decision**

```
IF Variant A ≥ 20/28 → Gate 2 PASS → Proceed to Final Stage
IF Variant A 10-19 AND Variant C Stratum 1 ≥ 20/28 → Partial PASS
   → Proceed to Final Stage on verified letters only
   → Document which letters are unverified
IF Variant A 10-19 AND Stratum 1 < 20 → PARTIAL
   → Proceed to Phase B2 (learned composition)
IF Variant A < 10 AND no stratum improvement → FAIL
   → Proceed to Phase B3 (model scale-up)
   → Or accept boundary and publish Path A
```

**Section 3: If proceeding to Final Stage**

- Which letters have verified directions?
- Which surah-opening letters are verified vs unverified?
- Can الم be composed? (requires ا, ل, م to have verified phases)
- Caveats for the Final Stage report

**Verification**:

- Decision follows the decision tree exactly — no ad-hoc justifications
- All numbers referenced from specific output files
- Honest about what moved and what didn’t

**Size**: Small. Synthesis.

-----

## Execution Order

```
B1.1 → Extract contextual word vectors (forward pass)
B1.2 → Recompute phase centroids (128D)
B1.3 → Root decomposition re-test (F024 comparison)
B1.4 → Gate 2 re-test (3 variants)
B1.5 → Decision report
[DECISION: Final Stage / B2 / B3 / Accept boundary]
```

All five milestones. One session. No new training. The existing M8b model does the work.

## Start

Begin with B1.1: contextual word embedding extraction. Read the spec above. Write red tests first. The M8b model is at `outputs/M8b/model_best.pt`, vocabulary at `outputs/M8b/vocabulary.json`.