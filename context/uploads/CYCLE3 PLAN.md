# Cycle 3: Semantic Direction Extraction + Final Validation

## Preamble

Cycle 2 delivered the foundation: word embeddings, letter centroids, phase detection, positional modulation, deconfounded frequency. The verdict was CAUTIOUS GO for H4 (semantic directions), with the critical pivot from whole-letter centroids to phase-aware centroids.

Cycle 3 has three stages:

1. **Pre-registered hypothesis testing** (H6-H10 from Cycle 2)
1. **Semantic direction extraction** (phase-aware, with cross-word verification)
1. **Final Stage** (surah-opening letter composition — the closing of the loop)

Three hard gates control progression. No gate may be bypassed.

-----

## Gates

### Gate 1: H6 (Phase-Aware Calibration)

**Location**: After C3.1
**Condition**: Phase-aware centroids for بـ must separate prefix from root phases with Hedges’ g > 1.0. The same must hold for يـ (actor vs consonant).
**If PASS**: Proceed to semantic extraction (C3.6+)
**If FAIL**: Phase-aware centroids do not improve on whole-letter centroids. Semantic extraction is not feasible at current embedding quality. STOP. Document as terminal finding. Do not proceed.

### Gate 2: Cross-Word Verification

**Location**: After C3.9
**Condition**: For each letter-phase, the proposed semantic direction must compose coherently across all words where that letter appears in that phase. Consistency score above chance (permutation test, p < 0.01). Minimum 20/28 base letters must have at least one phase passing verification.
**If PASS**: Proceed to Final Stage (C3.11+)
**If FAIL**: Directions are not self-consistent across the vocabulary. Refine or document as negative finding. Do not proceed to Final Stage.

### Gate 3: H10 (Surah-Opening Letter Phase Strategy)

**Location**: After C3.5, before Final Stage
**Condition**: A phase assignment strategy for the surah-opening letters must be established. Either: (a) they form a distinct “isolated” phase per H10, and that phase’s centroid is used, or (b) they do not form a distinct phase, and a documented fallback strategy is adopted (e.g., phase-weighted average, or most probable phase from minimal context). The strategy must be decided before any Final Stage composition is performed.
**If distinct phase found**: Use it
**If no distinct phase**: Document fallback, assess whether Final Stage results are interpretable under the fallback

-----

## Dependency Graph

```
C2 outputs ──┬── C3.1 (H6: phase-aware calibration)
             │     │
             │     └── [GATE 1: g > 1.0 for بـ and يـ]
             │
             ├── C3.2 (H7: phases → semantic info)
             ├── C3.3 (H8: ا-ل anti-correlation)
             ├── C3.4 (H9: positional modulation consistency)
             └── C3.5 (H10: surah-opening letter phases)
                   │
                   └── [GATE 3: phase strategy established]

GATE 1 passed ──┬── C3.6 (phase-aware word embeddings)
                ├── C3.7 (phase-specific semantic centroids)
                ├── C3.8 (root-decomposition test)
                └── C3.9 (cross-word verification)
                      │
                      └── [GATE 2: 20/28 letters verified, p < 0.01]

GATE 2 + GATE 3 passed ──┬── C3.10 (semantic direction atlas)
                          └── C3.11 (Final Stage: surah-opening letter composition)

C3.11 ──── C3.12 (Final report)
           STOP: Complete. Human review of full results.
```

-----

## Phase 1: Pre-Registered Hypothesis Testing (C3.1-C3.5)

### C3.1 — H6: Phase-Aware Centroids Separate Functional Roles [GATE 1]

**Question**: Do phase-specific centroids resolve the F010 calibration failure?

**Input**: C2.8 (HDBSCAN phase assignments) + C2.1 (word embeddings) + M7 dataset

**Method**:

- For each calibration letter (بـ لـ كـ فـ وـ يـ تـ نـ), use the HDBSCAN cluster assignments from C2.8 to identify functional phases
- For بـ: isolate the prefix phase (cluster 1: kasra+initial, ~36% of instances) and the root phase (remaining clusters or largest non-prefix cluster)
- For each phase: collect all words where that letter appears in that phase. Compute the phase-specific centroid in word-embedding space.
- Compute Hedges’ g between prefix-phase centroid neighborhood and root-phase centroid neighborhood
- Repeat for يـ (actor phase vs consonant phase) and تـ and نـ
- Compute LDA across all 8 calibration letters using phase-specific centroids: do prepositional phases and actor phases separate?

**Output**:

- `outputs/C3/gate1_calibration.json` — per calibration letter: phase assignments, phase-specific centroids, Hedges’ g between functional phases, LDA results across categories

**Verification**:

- Primary gate metric: Hedges’ g > 1.0 for بـ (prefix vs root) AND يـ (actor vs consonant)
- Secondary: LDA separation between prepositional phases and actor phases for all 8 letters
- Phase assignments traced back to HDBSCAN outputs (no manual labeling — phases identified by their cluster properties, not by external names)
- If g < 0.5 for either بـ or يـ: GATE 1 FAILS. Document and stop.

**Size**: Small-medium. Centroid computation on subsets of existing embeddings.

-----

### C3.2 — H7: More Phases → More Semantic Information Per Word

**Question**: Do words containing multi-phase letters carry higher embedding variance?

**Input**: C2.8 (phase counts per letter) + C2.1 (word embeddings) + M7 dataset

**Method**:

- For each word, compute the mean phase count of its constituent letters
- Partition words into high-phase (mean phase count ≥ 6) and low-phase (≤ 3)
- Compare word embedding variance between groups (Mann-Whitney on per-word norms or dispersions)
- Control for word length (letters per word) — longer words mechanically contain more letters

**Output**:

- `outputs/C3/h7_phase_info.json` — group statistics, Mann-Whitney U, effect size, length-controlled analysis

**Verification**:

- Word length controlled (stratify by length or regress out)
- Effect size (Cliff’s delta) and p-value reported
- If null: multi-phase letters don’t contribute more semantic diversity. Document.

**Size**: Small.

-----

### C3.3 — H8: ا-ل Anti-Correlation Reflects Definite Article Morphology

**Question**: Does the ا+ل frequency anti-correlation (r=-0.606) disappear when ال-initial words are separated?

**Input**: C2.9 (deconfounded frequency) + M7 dataset

**Method**:

- Per surah, count ل instances that are part of ال-initial words vs other ل instances
- Per surah, count ا instances that are part of ال-initial words vs other ا instances
- Re-compute correlation between non-ال bare-ا frequency and non-ال ل frequency
- If anti-correlation disappears: the original signal was driven by the ال morpheme distributing ا and ل to different roles
- If anti-correlation persists: something beyond the definite article drives the trade-off

**Output**:

- `outputs/C3/h8_al_anticorrelation.json` — original r, ال-separated r, interpretation

**Verification**:

- ال-identification purely from text structure: word-initial ا or ٱ followed immediately by ل (structural, no external grammar)
- Both separated and unseparated correlations reported with CIs

**Size**: Small.

-----

### C3.4 — H9: Positional Modulation Consistent Across Words

**Question**: For letters with positional semantic shifts (F013), do words sharing a letter in the same position have more similar embeddings?

**Input**: C2.7 (positional centroids) + C2.1 (word embeddings) + M7 dataset

**Method**:

- For each of the 15 position-modulated letters:
  - Collect word pairs sharing this letter at the same consonantal position (both have ب as C₁)
  - Collect word pairs sharing this letter at different positions (one has ب as C₁, other as C₂)
  - Compute mean cosine similarity within-position vs across-position
  - Permutation test (1000 permutations of position labels): is within-position similarity significantly higher?

**Output**:

- `outputs/C3/h9_positional_consistency.json` — per letter: within-position similarity, across-position similarity, difference, permutation p-value

**Verification**:

- Only the 15 letters from F013 tested (pre-registered)
- Holm correction across 15 tests
- If within-position advantage is not significant for the majority: positional modulation exists (F013) but doesn’t consistently shape word semantics. The finding still stands but its utility for semantic extraction is limited.

**Size**: Medium. Pairwise similarity computation per letter.

-----

### C3.5 — H10: Surah-Opening Letter Phases [GATE 3]

**Question**: Do the 14 letters that open certain surahs show a distinct phase when they appear in those openings?

**Input**: C2.8 (HDBSCAN phase assignments) + M8b embeddings + M7 dataset

**Method**:

- Identify all instances of the 14 surah-opening letters that appear IN the opening positions (verse 1 of surahs with letter openings — e.g., the ا ل م of Al-Baqarah 2:1)
- These instances have unique properties: no standard diacritics (only maddah), no word context, no morphological role. They are contextually distinct from every other instance in the corpus.
- Check: do these instances cluster together in HDBSCAN output? Do they form their own phase?
- If YES: the “opening phase” centroid is the direction to use in the Final Stage
- If NO: document. Options for Final Stage fallback:
  - (a) Use the contextual embedding of the specific opening instance (not a centroid — just the raw embedding vector from M8b for that exact position)
  - (b) Use the whole-letter centroid (acknowledging F010’s limitation)
  - (c) Use a phase-weighted average (weighted by phase size, the “expected” direction)
  - Document the chosen fallback with justification

**Output**:

- `outputs/C3/h10_opening_phases.json` — per opening letter: cluster assignment(s) for opening instances, whether a distinct “opening phase” exists, phase strategy decision

**Verification**:

- Opening instances identified purely by position (verse index 1 or 0 of surahs containing letter openings) — no external label
- If distinct phase: its centroid saved for Final Stage
- If no distinct phase: fallback strategy documented with justification
- Mann-Whitney comparing phase counts and noise fractions between opening letters (14) and non-opening letters (14) as pre-registered

**Size**: Small. Focused analysis on a small number of instances.

-----

## Phase 2: Semantic Direction Extraction (C3.6-C3.10)

*Phase 2 executes ONLY if Gate 1 passes.*

### C3.6 — Phase-Aware Word Representation

**Question**: Can each word be represented as a composition of its letters’ phase-specific contributions?

**Input**: C2.8 (phase assignments) + C2.1 (word embeddings) + M7 dataset

**Method**:

- For each word in the vocabulary:
  - Identify the letters it contains
  - For each letter, look up which HDBSCAN phase that specific instance was assigned to
  - The word is now represented as a sequence of (letter, phase) pairs
- This is the foundation for root-decomposition and cross-word verification: each word’s letters are not generic — they carry specific phase identities.

**Output**:

- `outputs/C3/word_phase_mapping.json` — per word: list of (letter, phase_id) pairs
- `outputs/C3/word_phase_stats.json` — distribution statistics: how many unique (letter, phase) combinations, how many words per combination

**Verification**:

- Every word in the embedding vocabulary has a complete phase mapping
- No letter instance is unassigned (noise instances from HDBSCAN get a “noise” phase label — they are not discarded but flagged)
- Spot-check 10 words: trace letter instances from M7 through HDBSCAN assignment to this mapping

**Size**: Medium. Lookup and mapping across full vocabulary.

-----

### C3.7 — Phase-Specific Semantic Centroids

**Question**: What is the semantic direction of each letter in each phase?

**Input**: C3.6 (word-phase mapping) + C2.1 (word embeddings)

**Method**:

- For each letter form, for each HDBSCAN phase:
  - Collect all words where this letter appears in this phase
  - Compute the centroid (mean word embedding) of those words
  - This is the **phase-specific semantic centroid** — the letter’s semantic direction when it’s in this functional mode
- Also compute dispersion (mean distance from centroid) per phase — tight clustering = confident direction, wide dispersion = diffuse direction

**Output**:

- `outputs/C3/phase_centroids.csv` — one row per (letter, phase): centroid vector (50D), word count, dispersion, top 5 nearest words, top 5 farthest words
- `outputs/C3/phase_centroid_summary.json` — per letter: number of phases with centroids, phase sizes, dispersion comparison across phases

**Verification**:

- Total word contributions across all phases of a letter = total words containing that letter (no double-counting, no missing)
- Phase centroids for بـ prefix phase and بـ root phase should be distinctly different (cosine distance > 0.1) — this is the Gate 1 finding applied at full scale
- Phases with fewer than 10 word contributions are flagged as low-confidence

**Size**: Medium. Centroid computation per (letter × phase).

-----

### C3.8 — Root-Decomposition Test

**Question**: Can root semantic domains be predicted from the composition of their letters’ phase-specific directions?

**Input**: C3.7 (phase centroids) + C3.6 (word-phase mapping) + M7 (computationally-discovered roots from baseline)

**Method**:

- For each computationally-discovered root (consonantal cluster from the morphological baseline):
  - The root has 2-4 consonants, each with a phase assignment in each derived word
  - Compute the “predicted root direction” by averaging or summing the phase-specific centroids of its consonants (using the most frequent phase per consonant in that root’s words)
  - Compute the “observed root direction” as the centroid of all word embeddings derived from that root
  - Measure agreement: cosine similarity between predicted and observed root directions
- Cross-validate: hold out 20% of roots. Train the composition function (how phase centroids combine) on 80%. Test on held-out 20%.

**Output**:

- `outputs/C3/root_decomposition.json` — per root: predicted direction, observed direction, cosine similarity, word count
- `outputs/C3/root_decomposition_summary.json` — mean cosine similarity, distribution, cross-validation results, comparison to null (random phase assignment)

**Verification**:

- Roots are computationally discovered (from morphological baseline), NOT imported from an external dictionary
- Composition function is simple (mean of phase centroids) — not a learned model that could overfit
- Cross-validation uses held-out roots, not held-out words from the same roots
- Comparison to null: if random phase assignment produces similar cosine similarity, the phase information isn’t contributing. The real phases must significantly outperform random.

**Critical constraint**: The predicted direction comes from letter-level information only. The observed direction comes from word-level information only. If they correlate, letter-level structure predicts word-level structure. This is the core test of H4.

**Size**: Medium-large. Depends on number of discovered roots.

-----

### C3.9 — Cross-Word Verification [GATE 2]

**Question**: Does each letter’s phase-specific direction compose coherently across ALL words where that letter appears in that phase?

**Input**: C3.7 (phase centroids) + C3.6 (word-phase mapping) + C2.1 (word embeddings)

**Method**:

- For each letter, for each phase:
  - The phase centroid predicts a semantic direction
  - For each word containing this letter in this phase:
    - Compute the “expected word direction” by composing all letters’ phase centroids
    - Compare to the word’s actual embedding (cosine similarity)
  - Compute consistency score: proportion of words where cosine similarity between expected and actual exceeds a threshold (e.g., top 50th percentile of all pairwise cosine similarities in the embedding space)
  - Permutation test: randomly reassign phases (1000 permutations), recompute consistency. Real consistency must exceed 99th percentile of permutation distribution (p < 0.01).

**Output**:

- `outputs/C3/cross_word_verification.json` — per (letter, phase): consistency score, permutation p-value, number of words tested, number passing threshold
- `outputs/C3/cross_word_summary.json` — how many letter-phase pairs pass verification, how many fail, overall statistics

**Gate 2 criterion**:

- Minimum 20 of 28 base letters (excluding variant forms, counting base letter families) must have AT LEAST ONE phase passing verification at p < 0.01
- If fewer than 20: semantic directions are not self-consistent. Document as negative finding. Do not proceed to Final Stage.
- If 20+: proceed. Letters with no verified phase are documented but not assigned a direction.

**Verification**:

- Permutation test uses the same words, just shuffles phase assignments — controls for base rates
- Threshold for “consistent” defined relative to the embedding space, not absolute
- Every failing letter-phase documented with the specific words that broke consistency — these may reveal where the direction is wrong or where the word itself is unusual

**Size**: Large. Per-word composition and comparison across full vocabulary.

-----

### C3.10 — Semantic Direction Atlas

**Question**: What is the complete, verified set of letter semantic directions?

**Input**: C3.9 (verification results) + C3.7 (phase centroids) + all prior findings

**Output**: `outputs/C3/semantic_direction_atlas.json` — the primary deliverable:

- Per letter (28 base letters + variants where distinct):
  - Number of verified phases
  - Per verified phase: centroid vector, dispersion, word count, consistency score, p-value
  - The “primary direction”: the phase with highest consistency score, or the phase-weighted average if multiple phases pass
  - Nearest words to each phase centroid (the words that best exemplify each direction)
  - Positional modulation (from F013/C2.7): does the direction shift at C₁/C₂/C₃?
  - Letters with NO verified phase: listed with note “direction not established”

**Output**: `outputs/C3/semantic_direction_atlas_readable.md` — human-readable summary:

- Per letter: primary direction described by nearest words (NOT by external translations — by the Quranic words that cluster near the centroid)
- Letters grouped by direction similarity (which letters point in similar directions?)
- Letters with strong positional modulation noted
- Comparison to articulatory zones: do same-zone letters share directions?

**Verification**:

- Every direction backed by verification p-value < 0.01
- No external semantic labels applied. Directions described ONLY by their nearest Quranic words.
- Letters without verified directions clearly separated from those with
- The atlas is the input to the Final Stage — it must be complete and correct before proceeding

**Size**: Small. Compilation and formatting of prior outputs.

-----

## Phase 3: Final Stage — The Loop Closes (C3.11-C3.12)

*Phase 3 executes ONLY if Gate 2 AND Gate 3 pass.*

### C3.11 — Surah-Opening Letter Composition

**Question**: When you compose the independently-derived semantic directions of the letters that open certain surahs, what do they say? And is it consistent with the surahs they open?

**Input**: C3.10 (semantic direction atlas) + C3.5 (H10 — phase strategy for opening letters) + C2.1 (word embeddings) + M7 dataset

**Method**:

**Step 1: Compose directions for each opening set.**

- For each of the 14 distinct letter combinations that open surahs:
  - Look up each letter’s semantic direction from the atlas (using the opening-phase centroid if H10 found a distinct phase, or the documented fallback)
  - Compose the directions: sum or average the letter direction vectors to produce a “composed opening direction”
  - This vector represents what the opening letters “say” — their composite semantic direction

**Step 2: Characterize each composed direction.**

- For each composed direction vector, find the nearest words in the word-embedding space
- These are the Quranic words whose distributional profile most closely matches the composed letter directions
- Do NOT translate these words. List them in Arabic. Their verse contexts are the interpretation.

**Step 3: Test surah-content alignment.**

- For each opening set, compute the aggregate word-embedding vector of the surah(s) it opens (mean of all word embeddings in the surah body, excluding the opening verse itself)
- Measure cosine similarity between the composed opening direction and the surah body aggregate
- Compare to null: randomly compose 14 letter sets of matched sizes, compute their direction, measure similarity to the same surah bodies. 10,000 permutations.
- **Key metric**: Do the real opening compositions align with their surahs more than random compositions? (permutation p-value)

**Step 4: Cross-set consistency.**

- Surahs sharing the same opening letters (e.g., the six الم surahs): compute pairwise similarity of their surah body aggregates
- Compare to surahs with different opening letters
- Do same-opening surahs have more similar content profiles?

**Step 5: الم specifically.**

- Compose: direction(ا) + direction(ل) + direction(م)
- Nearest Quranic words to this composed vector
- Surah-content alignment for the six الم surahs
- The verse that immediately follows الم in Al-Baqarah is: ذَٰلِكَ الْكِتَابُ لَا رَيْبَ فِيهِ
- Compute the word-embedding aggregate of this verse (excluding الم)
- Cosine similarity between the الم composition and this verse’s aggregate
- This is the final test: does what الم “says” (from independently-derived directions) relate to what the text says next?

**Output**:

- `outputs/C3/final_stage/opening_compositions.json` — per set: composed vector, nearest words, surah alignment score
- `outputs/C3/final_stage/alignment_test.json` — permutation test results: real vs random alignment, p-value
- `outputs/C3/final_stage/cross_set_consistency.json` — same-opening vs different-opening surah similarity
- `outputs/C3/final_stage/alm_analysis.json` — الم composition, nearest words, alignment with 2:2
- `outputs/C3/final_stage/all_openings_summary.md` — human-readable summary of all 14 compositions

**Verification**:

- Directions used are ONLY from the verified atlas (C3.10). No direction was derived from the opening letters themselves.
- Surah body aggregates EXCLUDE the opening verse — no circular testing
- Permutation baseline uses random letter combinations of matched size — controls for the possibility that any 3 letters’ directions align with any surah
- Nearest words listed in Arabic only. No translations. No external meanings.
- The result — whether الم “speaks” coherently or not — is reported as found, not as confirmed. A null result (no alignment) is as publishable as a positive result.

**Size**: Medium. Composition + alignment + permutation testing.

-----

### C3.12 — Final Report

**Question**: What did we find? Does H4 hold?

**Input**: Everything.

**Output**: `outputs/C3/final_report.md`:

**Section 1: The complete finding inventory** (F001 through F0XX, all numbered, all evidenced)

**Section 2: H4 assessment**

- Did letters carry discoverable semantic directions? (How many passed verification?)
- Did the directions compose into root semantic domains? (Root-decomposition correlation)
- Did positional modulation exist? (How many letters, how strong?)
- Did the opening letter compositions align with their surahs? (Permutation p-value)
- Did الم say something consistent with what follows it?

**Section 3: The atlas**

- Per-letter direction summary (nearest words, not translations)
- Direction clusters (which letters point similarly?)
- Zone-direction correlation (does articulatory geography predict semantic direction?)

**Section 4: The opening compositions**

- Per opening set: composed direction, nearest words, alignment score
- الم in detail

**Section 5: What we did not find**

- Informative nulls documented
- Letters without verified directions
- Cross-layer interactions that were null
- The geometric independence finding (F002) — visual form does not predict function

**Section 6: Limitations**

- Corpus size (327,793 letters — small by ML standards)
- Embedding quality (2L/4H/128D contextual; 50D word-level)
- Phase detection resolution (HDBSCAN parameters affect results)
- The irreducible gap: we analyzed Unicode’s encoding, not the text itself
- No external validation was performed (by design) — the findings are internally consistent but untested against external knowledge

**Verification**:

- Every claim references specific output files and test results
- Every statistical claim has p-value, effect size, and confidence interval
- No causal claims
- No external interpretations imposed
- The report is the deliverable. It answers the question the whitepaper posed.

**Size**: Synthesis document. The most important single file in the project.

-----

## Execution Summary

|Milestone|Phase     |Depends On|Gate?     |Question                                      |
|---------|----------|----------|----------|----------------------------------------------|
|C3.1     |Hypotheses|C2.8      |**GATE 1**|Do phase-aware centroids separate functions?  |
|C3.2     |Hypotheses|C2.8+C2.1 |          |More phases → more semantic info?             |
|C3.3     |Hypotheses|C2.9      |          |Is ا-ل anti-correlation morphological?        |
|C3.4     |Hypotheses|C2.7+C2.1 |          |Positional modulation consistent across words?|
|C3.5     |Hypotheses|C2.8+M8b  |**GATE 3**|Do opening letters have a distinct phase?     |
|C3.6     |Extraction|Gate 1    |          |Phase-aware word representation               |
|C3.7     |Extraction|C3.6      |          |Phase-specific semantic centroids             |
|C3.8     |Extraction|C3.7      |          |Root-decomposition test                       |
|C3.9     |Extraction|C3.7      |**GATE 2**|Cross-word verification                       |
|C3.10    |Extraction|C3.9      |          |Semantic direction atlas                      |
|C3.11    |Final     |Gates 2+3 |          |Opening letter composition                    |
|C3.12    |Final     |All       |          |Does الم speak?                               |

12 milestones. 3 gates. The loop opens at C3.1. It closes at C3.11. C3.12 reports what was found.

-----

## Contamination Constraints for Cycle 3

The semantic extraction phase is the highest contamination risk in the entire project. The temptation to interpret directions through external Arabic knowledge is maximal. Enforce:

1. **Directions are described by their nearest Quranic words, never by translations or dictionary meanings.** A direction’s “meaning” is the words that cluster near it in the embedding space. Those words are Arabic. They stay Arabic.
1. **Root semantic domains are observed from word co-occurrence, not imported.** When the root-decomposition test checks whether letter directions predict root domains, the “domain” is the root’s centroid in word-embedding space — a distributional property, not a dictionary entry.
1. **The surah-opening compositions are not compared to traditional interpretations.** If الم’s composed direction aligns with its surah, that alignment is measured against the surah’s word-embedding aggregate. It is not measured against what scholars have said الم means.
1. **No post-hoc reinterpretation of failed directions.** If a letter’s direction fails cross-word verification, it fails. Do not search for an external explanation of why it failed. Do not redefine the direction to make it pass. Document the failure.
1. **The null result is a valid outcome.** If the Final Stage shows no alignment between opening compositions and surah content, that is reported. The text may not carry letter-level semantic directions. The methodology was designed to detect them if they exist and to honestly report if they don’t.