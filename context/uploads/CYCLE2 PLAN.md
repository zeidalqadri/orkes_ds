# Cycle 2: Confirmatory Analysis — Milestone Plan

## Preamble: Remedial Audit

Cycle 1 produced 9 findings across 17 milestones. Before Cycle 2 proceeds, a systematic remedial pass is required to ensure no external contamination has entered the project and that all foundations are solid for the semantic direction work ahead.

-----

## R0: Remedial Milestones (Before Any Cycle 2 Analysis)

### R0.1 — Contamination Sweep

**Purpose**: Cycle 1’s report contained two contamination violations that must be corrected, and the full codebase must be audited for any others that entered unnoticed during 17 milestones of autonomous execution.

**Task**:

1. **Fix H3 in cycle1_report.md**: The phrase “early Medinan vs late Meccan” is an external classification from hadith-based historical tradition. The text does not label its surahs this way. Replace with: “diacritical motif frequencies differ by surah sequential position in the mushaf.” The observable variable is position in the sequence (surah 1 through 114), not a historically-derived period label.
1. **Fix Priority 3 in cycle1_report.md**: The phrase “supervised phase labels from linguistic annotation” recommends importing external لغة. Remove it entirely. The phase detection problem must be solved with unsupervised methods only.
1. **Full codebase scan**: Search every `.py`, `.md`, `.json`, and `.csv` header in the repo for any of the following contamination markers:
- “Meccan”, “Medinan”, “مكي”, “مدني”
- “juz”, “جزء”, “hizb”, “حزب”
- “asbab al-nuzul”, “occasion of revelation”
- “sahih”, “hadith”, “حديث”
- “tafsir”, “تفسير”
- “Ibn Kathir”, “Tabari”, “Qurtubi” or any scholar name used as authority
- “tajweed rule” used as data input (not as excluded item)
- “dictionary”, “lexicon”, “معجم” used as data source
- “muqatta’at”, “مقطعة”, “disconnected letters” (external label — should be “surah-opening letters”)
- Any reference to external Arabic corpus or pre-trained model used as data
- “sun letter”, “moon letter”, “شمسية”, “قمرية” (external grammar categories — assimilation detection must use structural context only)
1. **Document every finding**. For each contamination instance: file path, line number, the offending text, and the correction applied. If any contamination is found in analytical code (not just documentation), assess whether it affected outputs and flag for re-run.

**Exit**: `outputs/R0/contamination_audit.json` with full results. Zero contamination remaining.

### R0.2 — Self-Validation Framework Tightening

**Purpose**: As the project moves toward semantic direction extraction, the risk of circular reasoning increases. The framework must be strengthened with explicit guardrails.

**Task**:

1. **Add to CLAUDE.md — Semantic Direction Rules**:
   
   ```
   ## Semantic Direction Guardrails
   
   - A letter's semantic direction must be derived from the text's own 
     usage patterns, never from an external dictionary definition.
   - The meaning of a word is NOT an input. Word meanings are what we 
     are trying to explain through letter composition, not what we use 
     to derive letter directions.
   - Word co-occurrence within verses is the sole basis for word-level 
     distributional semantics. Two words are "related" if and only if 
     they appear in the same verses more than expected.
   - The word embedding space is an internal structure of the text. 
     It is not validated against any external semantic resource.
   - When computing a letter's centroid across word embeddings, ALL 
     words containing that letter contribute — not a selected subset.
   - If a proposed direction seems to match an external dictionary 
     meaning, that is noted as an observation, not used as validation.
     The direction stands or falls on cross-word consistency within 
     the text, not on agreement with external definitions.
   - Root semantic domains are observed from the text's usage patterns, 
     not imported from Arabic dictionaries. Two words from the same root 
     share a domain because they co-occur with similar words in the text, 
     not because a dictionary says they're related.
   ```
1. **Add to CLAUDE.md — Positional Analysis Rules**:
   
   ```
   ## Positional Analysis Rules
   
   - Surah sequence position (1-114) is admissible — it is the text's 
     own ordering.
   - No surah is labeled by historical period, theme, or external 
     classification.
   - If surahs cluster by their letter profiles, the clusters are 
     described by their members (surah numbers), never by external names.
   - Word position (initial/medial/final) is determined by the text's 
     own spacing, not by morphological parsing from external grammar.
   ```
1. **Add to CLAUDE.md — Phase Detection Rules**:
   
   ```
   ## Phase Detection Rules
   
   - Phases must be discovered unsupervised — no external labels, 
     no linguistic annotation, no functional categories imported 
     from grammar references.
   - If discovered phases correspond to known linguistic categories 
     (e.g., a phase matching "prefix usage"), that correspondence 
     is noted as a finding, not used as validation.
   - Phase detection methods must not assume a specific number of 
     phases per letter. The method discovers k, it does not impose k.
   ```
1. **Create `scripts/contamination_check.sh`**: An automated script that runs the contamination scan (item 3 above) and can be invoked before every commit. Add it to the git pre-commit hook.

**Exit**: Updated CLAUDE.md committed. `scripts/contamination_check.sh` working and tested. Pre-commit hook installed.

### R0.3 — Output Integrity Verification

**Purpose**: The M7 fabrication incident and the M3 count discrepancy show that autonomous outputs need systematic post-hoc verification. Before building on Cycle 1 outputs, verify their integrity.

**Task**:

1. **Spot-check C1 outputs against raw data**: For each of the 16 analytical milestones (C1.1-C1.16), pick 3 random data points from the output and trace them back to the M7 unified dataset and the source XML. Confirm the values match. Document each trace.
1. **Verify finding evidence chains**: For each of the 9 findings (F001-F009), confirm that the cited test statistic, p-value, and effect size can be reproduced from the cited output file. Re-run the computation if needed.
1. **Verify test independence**: Confirm that the 164 Cycle 1 tests actually test what they claim. Pick 5 tests at random, read the test code, and verify that they would fail if the output were wrong (not rubber-stamp tests).

**Exit**: `outputs/R0/integrity_audit.json` with trace results and any discrepancies found.

-----

## Cycle 2 Milestones

### Dependency Graph

```
R0 (remedial) ──── C2.1 (word embeddings)
                    │
                    ├── C2.2 (letter semantic centroids)
                    │     │
                    │     ├── C2.3 (calibration re-test with word embeddings)
                    │     │
                    │     └── C2.4 (centroid structure analysis)
                    │
                    ├── C2.5 (zone-entropy decomposition)
                    │
                    ├── C2.6 (positional analysis)
                    │     │
                    │     └── C2.7 (positional semantic contribution)
                    │
                    ├── C2.8 (phase detection redesign)
                    │
                    └── C2.9 (length-deconfounded frequency)

C2.2-C2.9 ──── C2.10 (cross-analysis synthesis)

C2.10 ──── C2.11 (Cycle 2 findings + pre-register Cycle 3 predictions)
           STOP: Human review required
```

-----

### C2.1 — Word Embeddings (Quran-Only)

**Question**: What is the internal semantic structure of the Quranic vocabulary, as derived from word co-occurrence alone?

**Input**: M7 unified dataset (verse-level word groupings)

**Method**:

- Extract all unique word forms from the text. A “word” is defined by the text’s own spacing (continuous characters between spaces). Proclitics attached to their host word are one word — the text wrote them as one unit.
- Build a word co-occurrence matrix: two words co-occur if they appear in the same verse. Weight by frequency (PPMI — Positive Pointwise Mutual Information).
- Train word2vec (skip-gram) on the verse-as-sentence paradigm: each verse is a “sentence,” word order within verse is the training signal.
- Embedding dimension: start at 50. The vocabulary is ~18,000 unique forms but many are rare. 50 dimensions is conservative for this corpus size.
- Window size: 5 (within-verse only — no cross-verse windows).
- Minimum word count: 3 (words appearing fewer than 3 times are excluded — too little context for meaningful embeddings).
- Training: 30 epochs. Save loss curve.

**Output**:

- `outputs/C2/word_embeddings.pt` — trained word vectors
- `outputs/C2/word_vocabulary.json` — word-to-index mapping with counts
- `outputs/C2/word_embedding_matrix.csv` — human-readable
- `outputs/C2/word_training_loss.json` — loss curve

**Verification**:

- Vocabulary size documented (expected ~18,000 forms, ~5,000-8,000 after min_count filter)
- Loss curve shows learning (decreasing) and plateaus (not memorizing)
- Sanity check: compute cosine similarity between 5 word pairs that should be related by co-occurrence (e.g., words from the same verse-level context) and 5 pairs that should be unrelated. Related pairs should have higher similarity. NOTE: “should be related” is determined by verse co-occurrence statistics, NOT by external meaning.
- No external data used at any point. No pre-trained vectors. No dictionary.

**Critical constraint**: The word embeddings encode distributional similarity — words that appear in similar verse contexts get similar vectors. This is NOT semantic similarity in the human sense. Two words may be distributionally similar because they serve similar grammatical roles, or because they appear in topically related verses. The embedding space is a map of the text’s internal co-occurrence structure. Do not interpret it as “meaning” — it is pattern.

**Size**: Medium. Training time depends on vocabulary size and epochs.

-----

### C2.2 — Letter Semantic Centroids

**Question**: When you average the word embeddings of all words containing a given letter, does the resulting centroid carry interpretable structure?

**Input**: C2.1 (word embeddings) + M7 (letter-to-word mapping)

**Method**:

- For each of the 36 letter forms, collect all words in the vocabulary that contain that letter.
- Compute the centroid (mean vector) of those words’ embeddings.
- This centroid is the letter’s **distributional semantic center** — the average position in word-embedding space of all words containing that letter.
- The direction from the origin to this centroid is the letter’s **distributional semantic direction** (first approximation).

**Output**:

- `outputs/C2/letter_centroids.csv` — 36 rows × 50 columns (one centroid per letter form)
- `outputs/C2/letter_centroid_metadata.json` — per letter: word count contributing to centroid, mean distance from centroid (dispersion), list of top 10 closest words and top 10 farthest words

**Verification**:

- Every letter form has a centroid (no missing)
- Word counts per letter sum correctly (each word contributes to multiple letters’ centroids)
- Centroid dispersion: high-frequency letters should have higher dispersion (more diverse word contexts) — verify correlation between frequency and dispersion
- No external semantic resource used. The centroids are purely distributional.

**Size**: Small. Averaging operations over pre-computed embeddings.

-----

### C2.3 — Calibration Re-Test: Semantic Separation

**Question**: Do the 8 calibration letters’ centroids separate prepositional from actor prefixes in word-embedding space?

**Input**: C2.2 (letter centroids for the 8 calibration letters)

**Method**:

- Extract the centroids for بـ لـ كـ فـ وـ (prepositional) and يـ تـ نـ (actor)
- Compute LDA or Fisher discriminant between the two groups
- Measure Hedges’ g effect size
- Check directional consistency: do all 5 prepositional centroids project to one side and all 3 actor centroids to the other?
- Compare to M9 calibration test 0Q result (g=1.73, perfect separation on discriminant axis)

**Output**:

- `outputs/C2/calibration_semantic.json` — Hedges’ g, projection values per letter, separation quality

**Verification**:

- Effect size reported with confidence interval
- Directional consistency checked (all prep on one side, all actor on the other, or not)
- Result compared to 0Q (character-level embeddings) — are word-level centroids more or less separating than character-level?
- If separation FAILS: this is a critical finding — word-level distributional similarity may not capture functional category. Document and assess before proceeding to C2.4.

**Size**: Small. 8 data points, 1 discriminant computation.

-----

### C2.4 — Centroid Structure Analysis

**Question**: What structure exists in the 36 letter centroids? Do they cluster, and if so, by what?

**Input**: C2.2 (all 36 centroids) + M5 (makhraj zones) + M6 (geometric families) + C1.1 (frequency)

**Method**:

- Visualize: PCA and t-SNE of the 36 centroids, colored by makhraj zone, by geometric family, by frequency band
- Cluster: hierarchical clustering (Ward linkage) on centroid distances. Cut at k=2 through k=10. Report silhouette scores.
- Correlation: Mantel test between centroid distance matrix and (a) articulatory zone distance, (b) geometric family distance, (c) frequency rank distance
- Pairwise centroid distances: which letters have the most similar semantic centroids? Which are most dissimilar?

**Output**:

- `outputs/C2/centroid_structure/` — visualizations (PCA, t-SNE colored by zone/family/freq)
- `outputs/C2/centroid_structure/clustering.json` — dendrogram data, silhouette scores per k
- `outputs/C2/centroid_structure/mantel_tests.json` — correlation with zone, family, frequency
- `outputs/C2/centroid_structure/pairwise_distances.csv` — 36×36 distance matrix

**Verification**:

- Visualizations exist and are non-degenerate
- Mantel tests have permutation p-values (10,000 iterations)
- Clustering is compared to zone/family groupings: do discovered clusters align with articulatory geography? With visual families? With neither (novel structure)?
- Document what is seen. Do not impose interpretation.

**Size**: Small-medium. Visualization + clustering + 3 Mantel tests.

-----

### C2.5 — Zone-Entropy Decomposition

**Question**: Which articulatory zones drive the F003 effect (zone predicts diacritical entropy)?

**Input**: C1.2 (diacritical entropy) + M5 (makhraj zones)

**Method**:

- Post-hoc pairwise comparisons between all zone pairs (Dunn’s test with Holm correction)
- Effect sizes for each pair (Cliff’s delta or rank-biserial)
- Identify which specific zone or zones are outliers driving the overall η²=0.44
- Examine individual letters within the driving zone(s): is the effect uniform across letters in the zone, or driven by specific letters?

**Output**:

- `outputs/C2/zone_entropy_decomposition.json` — pairwise p-values (Holm-corrected), effect sizes, zone means with CIs
- Per-zone letter-level entropy distributions

**Verification**:

- Pairwise tests use correct sample sizes (number of letters per zone, not number of instances)
- Holm correction applied (not Bonferroni — Holm is less conservative and appropriate for post-hoc)
- Effect sizes reported alongside p-values
- If the effect is driven by 1-2 specific letters rather than a whole zone, document that — the finding may be letter-specific rather than zone-specific

**Size**: Small. Post-hoc tests on existing data.

-----

### C2.6 — Positional Analysis

**Question**: Does a letter’s distributional profile change depending on its position within a word?

**Input**: M7 unified dataset (word_position column)

**Method**:

- For each letter form, partition its instances by word position: initial, medial, final
- Compare across positions: diacritical distribution (χ²), co-occurrence profile (cosine distance of PMI vectors), frequency contribution
- Global analysis: are certain letters position-specialized? (e.g., predominantly initial or predominantly final)
- Non-connector analysis: the 6 non-connecting letters (ا د ذ ر ز و) force a visual break. Does their positional distribution differ from connectors?

**Output**:

- `outputs/C2/positional_analysis.csv` — per letter × position: count, diacritical distribution, PMI profile summary
- `outputs/C2/positional_specialization.json` — letters ranked by positional entropy (high = evenly distributed, low = position-specialized)
- `outputs/C2/positional_anova.json` — does position predict diacritical distribution? (per-letter χ², Bonferroni-corrected)

**Verification**:

- Counts per position sum to total per letter
- Position categories are determined by text spacing (Premise 4), not morphological analysis
- Non-connectors identified from geometric features (M6), not from external grammar

**Size**: Medium. Per-letter × per-position analysis.

-----

### C2.7 — Positional Semantic Contribution

**Question**: Does a letter’s semantic centroid shift depending on its root position (C₁, C₂, C₃)?

**Input**: C2.2 (letter centroids) + M7 (letter positions) + internally-discovered roots (from morphological baseline)

**Method**:

- Using the computationally-discovered root clusters (from M7/baseline construction), identify letters that appear as C₁ in some roots, C₂ in others, C₃ in others
- For each letter with sufficient data (appears in ≥10 roots at each position), compute separate centroids: centroid_C1, centroid_C2, centroid_C3
- Compare: are the positional centroids different? (cosine distance between position-specific centroids vs. overall centroid)
- If positions produce different centroids, the letter’s semantic direction is position-modulated

**Output**:

- `outputs/C2/positional_centroids.json` — per letter: centroid_C1, centroid_C2, centroid_C3, distances between them, statistical test of difference
- `outputs/C2/position_modulation_summary.csv` — which letters show significant positional modulation

**Verification**:

- Root positions derived from internal pattern discovery, NOT from external morphological analysis
- Only letters with sufficient data (≥10 roots per position) are included
- Distance between positional centroids compared to a null distribution (random position assignment, 1000 permutations)
- If NO letters show significant modulation, that is a finding: position within root does not affect semantic contribution

**Critical constraint**: The “roots” used here are computationally-discovered consonantal clusters from the morphological baseline. They are NOT imported from an Arabic dictionary. If the baseline’s root discovery is too crude for this analysis, document that limitation rather than importing external root lists.

**Size**: Medium. Depends on quality of root discovery.

-----

### C2.8 — Phase Detection Redesign

**Question**: Can letter phases be detected with a method that doesn’t degenerate to k=max?

**Input**: M8b embeddings + M7 dataset

**Method**:

- **Step 1**: Dimensionality reduction. PCA on the 128D contextual embeddings, retaining components explaining 80% of variance. This compresses the space and removes noise dimensions that BIC was fitting in Cycle 1.
- **Step 2**: HDBSCAN on the reduced embeddings per letter. HDBSCAN does not require specifying k — it discovers clusters of varying density and assigns noise points. Minimum cluster size = 50 (letter instances are abundant).
- **Step 3**: For letters where HDBSCAN finds ≥2 clusters, characterize each cluster: what contextual features distinguish them? (word position, preceding/following letter, diacritical pattern)
- **Step 4**: Validation against known phases: does بـ split into prefix/root? Does يـ split into actor/consonant? These are the calibration anchors — if the method can’t recover known phases, it’s not working.

**Output**:

- `outputs/C2/phases_v2/` — per letter: cluster assignments, cluster sizes, noise proportion, distinguishing features per cluster
- `outputs/C2/phases_v2/summary.json` — letters with ≥2 phases, letters with 1 phase (homogeneous), letters with high noise (ambiguous)
- `outputs/C2/phases_v2/calibration_check.json` — بـ and يـ phase recovery check

**Verification**:

- HDBSCAN minimum_cluster_size documented and justified
- PCA variance retention threshold documented
- Known phases recovered for calibration letters (بـ, يـ) — if not, diagnose before accepting results for other letters
- Noise proportion per letter documented (high noise = the letter’s usage is continuous, not discrete)
- No external labels used for phase identification or validation

**Size**: Medium-large. Per-letter HDBSCAN with characterization.

-----

### C2.9 — Length-Deconfounded Frequency

**Question**: After normalizing for surah length, what genuine frequency coupling exists between letters?

**Input**: C1.1 (frequency atlas) + C1.7 (co-frequency matrix) + M7 dataset

**Method**:

- Compute per-letter frequency as proportion of total letters in each surah (not raw count)
- Re-compute the 36×36 co-frequency correlation matrix on proportions
- Re-run coupled system detection on the deconfounded matrix
- Compare to C1.7: which couplings survive deconfounding? Which were artifacts of surah length?
- The lam+alif-wasla coupling (r=0.59 in arc-level analysis) should persist — it’s morphological (definite article), not length-driven

**Output**:

- `outputs/C2/deconfounded_frequency.csv` — per letter × per surah: normalized frequency (proportion)
- `outputs/C2/deconfounded_cofreq.csv` — 36×36 correlation matrix on proportions
- `outputs/C2/deconfounded_clusters.json` — coupled systems after deconfounding
- `outputs/C2/deconfounding_comparison.json` — which pairs changed significantly between raw and deconfounded

**Verification**:

- Normalized frequencies per surah sum to 1.0 (within rounding)
- Mean cross-letter correlation should drop dramatically from r=0.96 to near zero
- Lam+alif-wasla coupling should survive (structural prediction)
- New couplings that emerge after deconfounding are potentially more interesting than those that disappear

**Size**: Small. Re-computation on existing data.

-----

### C2.10 — Cross-Analysis Synthesis

**Question**: How do Cycle 2 findings interact with each other and with Cycle 1 findings?

**Input**: All C2.1-C2.9 outputs + all C1 findings

**Method**:

- Does the centroid structure (C2.4) correlate with zone-entropy patterns (C2.5)?
- Do position-specialized letters (C2.6) have more phases (C2.8)?
- Do deconfounded frequency couplings (C2.9) align with centroid proximity (C2.4)?
- Do letters with strong positional semantic modulation (C2.7) also show multiple phases (C2.8)?
- Update the cross-layer interaction table from C1.16 with new interactions
- File any new findings as F010+

**Output**:

- `outputs/C2/cross_analysis.json` — updated interaction table
- `outputs/C2/findings/` — new findings filed

**Verification**:

- All interactions tested with effect sizes and corrected p-values
- No causal claims
- Each finding references specific output files

**Size**: Medium. Cross-referencing all prior outputs.

-----

### C2.11 — Cycle 2 Findings Report + Cycle 3 Pre-Registration

**Question**: What did Cycle 2 find? Are semantic directions feasible? What does Cycle 3 test?

**Input**: C2.10 + all prior findings

**Output**: `outputs/C2/cycle2_report.md`:

- All findings numbered and evidenced
- Assessment: do letter centroids carry enough structure for semantic direction extraction?
- Assessment: does positional modulation exist? How strong?
- Assessment: are letter phases recoverable? Which letters?
- Specific pre-registered predictions for Cycle 3 (the semantic extraction and cross-word verification cycle)
- Honest assessment of whether H4 (semantic directions) is feasible given the evidence

**Verification**:

- Every finding has p-value, effect size, output file reference
- Pre-registered predictions are specific and falsifiable
- Human review required before Cycle 3

**Critical output**: The go/no-go assessment for H4. If the centroids show no structure, if positions don’t modulate, if the word embeddings lack resolution — the honest answer may be that semantic directions are not extractable from this corpus at this embedding quality. That is a valid finding. Do not proceed to Cycle 3 if the evidence doesn’t support it.

**Size**: Small. Synthesis document.

-----

## Execution Summary

|Milestone|Depends On|Size|Question                                                       |
|---------|----------|----|---------------------------------------------------------------|
|R0.1     |—         |S   |Is the codebase contamination-free?                            |
|R0.2     |R0.1      |S   |Are self-validation guardrails sufficient?                     |
|R0.3     |R0.1      |M   |Are Cycle 1 outputs trustworthy?                               |
|C2.1     |R0        |M   |What is the text’s internal word-level co-occurrence structure?|
|C2.2     |C2.1      |S   |What is each letter’s distributional semantic center?          |
|C2.3     |C2.2      |S   |Do calibration letter centroids separate prep from actor?      |
|C2.4     |C2.2      |S-M |What structure exists in the 36 centroids?                     |
|C2.5     |C1.2+M5   |S   |Which zones drive the entropy effect?                          |
|C2.6     |M7        |M   |Does word position modulate letter behavior?                   |
|C2.7     |C2.2+C2.6 |M   |Does root position modulate semantic contribution?             |
|C2.8     |M8b       |M-L |Can phases be detected without degeneration?                   |
|C2.9     |C1.1+C1.7 |S   |What frequency couplings survive length normalization?         |
|C2.10    |C2.1-C2.9 |M   |How do all findings interact?                                  |
|C2.11    |C2.10     |S   |Is H4 feasible? What does Cycle 3 test?                        |

14 milestones: 3 remedial + 11 analytical. 5 small, 6 medium, 1 medium-large, 2 synthesis.

**Hard stop at C2.11.** Human review determines whether Cycle 3 (semantic extraction + cross-word verification + surah-opening letter validation) proceeds.

-----

## Contamination Watchlist for Cycle 2

The word embeddings (C2.1) are the highest contamination risk in Cycle 2. The following must be enforced:

1. **No pre-trained word vectors.** Not word2vec trained on Arabic Wikipedia, not FastText, not any external embedding. Train from scratch on Quranic verse co-occurrence only.
1. **No external word lists.** The vocabulary is whatever the text contains. No stopword removal (every word is data). No frequency filtering based on external knowledge.
1. **No semantic labels.** When examining centroids, do not label them with meanings from dictionaries. Describe them by their nearest neighbors in the embedding space (which are other Quranic words, not translations).
1. **No translation as proxy.** Do not use English or other translations to interpret what a centroid “means.” The centroid is a point in a space defined by Quranic co-occurrence. It has coordinates, not a dictionary entry.
1. **Word boundaries from the text’s spacing.** Do not re-tokenize based on external morphological analysis. If the text writes بِسْمِ as one unit, it’s one word. If it writes اللَّهِ as one unit, it’s one word.