# Cycle 1: Exploratory Analysis — Milestone Plan

## Principle

Every milestone produces one artifact, has one verification method, and answers one question. No milestone does two things. If a milestone feels large, it’s two milestones.

## Dependencies

```
M7 (unified dataset) ──┬── C1.1 (letter frequency atlas)
                        ├── C1.2 (diacritical entropy)
                        ├── C1.3 (PMI landscape — word-level)
                        └── C1.4 (PMI landscape — verse-level)

C1.1 ──┬── C1.5 (frequency arcs)
       ├── C1.6 (inter-arrival analysis)
       └── C1.7 (co-frequency matrix)

C1.2 ──── C1.8 (diacritical melody extraction)

C1.3 + C1.4 ──── C1.9 (conjunction/opposition atlas)

M8b (embeddings) ──┬── C1.10 (phase detection — full alphabet)
                   └── C1.11 (embedding space visualization)

M6 (geometry) + C1.9 ──── C1.12 (geometric distance vs. distributional distance — F002 follow-up)

C1.1 + C1.2 + M5 (makhraj) ──── C1.13 (articulatory zone profiling)

C1.5 + C1.7 ──── C1.14 (frequency coupled systems)

C1.8 + C1.1 ──── C1.15 (sonic weight contouring)

All C1.1-C1.15 ──── C1.16 (cross-track interaction summary)

C1.16 ──── C1.17 (Cycle 1 findings report + Cycle 2 recommendation)
```

-----

## Track A: Frequency (C1.1, C1.5, C1.6, C1.7, C1.14)

### C1.1 — Letter Frequency Atlas

**Input**: M7 unified dataset (327,793 rows)
**Question**: What is the complete frequency profile of each letter form?
**Output**: `outputs/C1/frequency_atlas.csv` — one row per letter form (36 rows), columns:

- raw_count, relative_frequency, frequency_rank
- surah_frequency_vector (114 values — stored as separate CSV or JSON)
- surah_frequency_variance, surah_frequency_entropy
- presence_breadth (how many of 114 surahs contain this letter)
- verse_presence_rate (proportion of 6,236 verses containing this letter)
  **Verification**:
- All 36 letter form counts sum to 327,793
- Rank 1 = lam (38,550), rank 2 = noon (27,380), rank 3 = meem (27,071)
- Presence_breadth for ا = 114 (appears in every surah)
- Spot-check 3 surah frequency values against manual count from M7 dataset
  **Size**: Small. Pure aggregation over existing dataset.

### C1.5 — Frequency Arcs

**Input**: C1.1 + M7 dataset
**Question**: How does each letter’s frequency change across the sequential flow of the mushaf?
**Output**: `outputs/C1/frequency_arcs.csv` — per letter, sliding-window frequency (window = 500 letters, step = 100 letters), producing a brightness curve across the text

- arc_trend: linear regression slope (increasing/decreasing/flat)
- arc_variance: variance of the arc values
- arc_periodicity: dominant frequency from autocorrelation (if any)
  **Verification**:
- Arc length = floor((327,793 - 500) / 100) + 1 for each letter
- Sum of all letter frequencies in any window = window size (500)
- Letters with high arc_variance are genuinely variable (spot-check 3 against raw data)
- Autocorrelation computed correctly: lag-0 = 1.0 for all letters
  **Size**: Medium. Sliding window computation.

### C1.6 — Inter-Arrival Analysis

**Input**: M7 dataset (mushaf_position column)
**Question**: What is the temporal spacing pattern for each letter?
**Output**: `outputs/C1/inter_arrival.csv` — per letter form:

- mean_inter_arrival (average gap in letter-positions between successive occurrences)
- inter_arrival_std
- inter_arrival_cv (coefficient of variation — std/mean)
- burst_score: ratio of observed clustering to Poisson expectation
- distribution_fit: which distribution best fits the inter-arrival times (geometric, Poisson, negative binomial) with goodness-of-fit metric
  **Verification**:
- mean_inter_arrival × count ≈ 327,793 for each letter (within rounding)
- High-frequency letters have small mean_inter_arrival
- burst_score > 1 means more clustered than random; spot-check against raw gaps
  **Size**: Medium. Per-letter gap computation.

### C1.7 — Co-Frequency Matrix

**Input**: C1.1 (surah frequency vectors)
**Question**: Which letters brighten and dim together across surahs?
**Output**: `outputs/C1/co_frequency_matrix.csv` — 36×36 Pearson correlation matrix of surah frequency vectors

- Also: `co_frequency_significant.csv` — pairs with |r| > 0.3 and p < 0.01 (Bonferroni-corrected)
  **Verification**:
- Diagonal = 1.0
- Matrix is symmetric
- Spot-check 3 high-correlation pairs: do their surah frequency vectors visually track together?
- Spot-check 3 anti-correlated pairs: do they visually oppose?
  **Size**: Small. 36×36 correlation of 114-element vectors.

### C1.14 — Frequency Coupled Systems

**Input**: C1.5 (arcs) + C1.7 (co-frequency matrix)
**Question**: Are there letter pairs or groups that form frequency-coupled systems — rising and falling together, or in opposition?
**Output**: `outputs/C1/coupled_systems.json` — identified clusters of co-varying letters, with:

- cluster membership
- mean intra-cluster correlation
- strongest opposition pairs (anti-correlated clusters)
- visualization: arc overlay plots for top 3 coupled systems
  **Verification**:
- Every letter appears in exactly one cluster
- Intra-cluster correlations all positive (> 0)
- Inter-cluster correlations lower than intra-cluster
- Visual inspection: do overlaid arcs actually track together?
  **Size**: Small. Clustering on 36×36 matrix.

-----

## Track B: Sonic (C1.2, C1.8, C1.13, C1.15)

### C1.2 — Diacritical Entropy

**Input**: M7 dataset
**Question**: How flexible is each letter’s voweling? Which letters accept diverse diacritics and which are specialized?
**Output**: `outputs/C1/diacritical_entropy.csv` — per letter form:

- entropy: Shannon entropy of diacritical distribution (higher = more flexible)
- dominant_diacritic: most frequent diacritic for this letter
- dominant_ratio: proportion of instances carrying the dominant diacritic
- entropy_rank: rank from highest (most flexible) to lowest (most specialized)
  **Verification**:
- Entropy = 0 only if letter always carries the same diacritic (unlikely for any letter)
- Letters with high bare rate (like alif forms) should show different entropy from heavily-voweled letters
- Spot-check: compute entropy by hand for 2 letters from their diacritical distribution in M7
  **Size**: Small. Per-letter aggregation.

### C1.8 — Diacritical Melody Extraction

**Input**: M7 dataset + C1.2
**Question**: What is the diacritical contour of each verse — the sequence of vowel marks stripped of host letters?
**Output**: `outputs/C1/melodies.csv` — per verse:

- melody_string: the sequence of primary diacritics (e.g., “fatha-kasra-damma-sukoon-fatha-…”)
- melody_length: number of diacritical events
- melody_entropy: Shannon entropy of diacritic distribution within this verse
- duration_weighted_melody: melody with each diacritic weighted by its duration value
  **Output**: `outputs/C1/melody_motifs.csv` — recurring diacritical subsequences (length 3-6) that appear more frequently than expected by chance (compared to shuffled baseline, 1000 permutations)
  **Verification**:
- melody_length per verse ≤ letter count per verse
- Total melody events across all verses = total non-bare letter instances
- At least some motifs significant at p < 0.01 (Bonferroni-corrected) — or document absence as finding
- Spot-check 3 verse melodies against raw diacritical sequence in M7
  **Size**: Medium. Per-verse extraction + motif detection with permutation.

### C1.13 — Articulatory Zone Profiling

**Input**: M7 + M5 (makhraj zones) + C1.1 (frequency) + C1.2 (entropy)
**Question**: Do the 7 articulatory zones have distinct distributional profiles?
**Output**: `outputs/C1/zone_profiles.csv` — per zone:

- total_frequency: sum of all letters in this zone
- mean_diacritical_entropy: average voweling flexibility
- positional_preferences: proportion of word-initial / medial / final instances
- mean_inter_arrival: average spacing of zone-member letters
  **Output**: `outputs/C1/zone_anova.json` — ANOVA/Kruskal-Wallis tests:
- Does zone predict frequency? (F-stat, p-value)
- Does zone predict diacritical entropy? (F-stat, p-value)
- Does zone predict word position? (χ², p-value)
  **Verification**:
- Zone frequencies sum to 327,793
- Zone 5 (tongue) should be highest frequency (48.7% from M5)
- Statistical tests use correct degrees of freedom (6 zones = df=6)
- Effect sizes reported (eta-squared or equivalent)
  **Size**: Small. Aggregation + 3 statistical tests.

### C1.15 — Sonic Weight Contouring

**Input**: C1.8 (melodies) + C1.1 (frequency) + M5 (makhraj)
**Question**: What is the acoustic weight distribution across the text?
**Output**: `outputs/C1/sonic_weight.csv` — per letter instance (327,793 rows):

- sonic_weight: computed from articulatory_effort (zone depth proxy) × vowel_openness × duration_weight × multiplicity (shadda=2)
  **Output**: `outputs/C1/sonic_weight_contour.csv` — sliding window average sonic weight (window=100 letters, step=20)
- Identifies peaks (heavy passages) and valleys (light passages)
- Reports positions of top 20 heaviest and lightest windows
  **Verification**:
- sonic_weight > 0 for all instances
- Shadda instances have weight ≥ 2× non-shadda equivalent
- Zone 2/3 letters (throat) have higher articulatory weight than zone 6 (lips)
- Contour length consistent with window/step parameters
  **Size**: Medium. Per-instance computation + sliding window.

-----

## Track C: Structural (C1.3, C1.4, C1.9, C1.10, C1.11)

### C1.3 — PMI Landscape: Word-Level

**Input**: M7 dataset + M8a PMI infrastructure
**Question**: Which letter-to-letter transitions within words are statistically over- or under-represented?
**Output**: Already partially computed in M8a. Extend to:

- `outputs/C1/pmi_word.csv` — full PMI matrix for within-word bigrams (36×36)
- `outputs/C1/pmi_word_significant.csv` — pairs with |PMI| > 1.0 and count > 50
- Top 20 conjunctions, top 20 oppositions
  **Verification**:
- Matrix values are finite (no inf/nan)
- Known conjunction بـ→ال confirmed in top ranks
- Known opposition ن→ل confirmed in negative ranks
- PMI(a,b) and PMI(b,a) may differ (asymmetric bigrams) — document
  **Size**: Small. Extends existing M8a computation.

### C1.4 — PMI Landscape: Verse-Level

**Input**: M7 dataset
**Question**: Which letters co-occur within the same verse more (or less) than expected?
**Output**: `outputs/C1/pmi_verse.csv` — 36×36 PMI matrix for verse-level co-occurrence (both letters present in same verse)

- `outputs/C1/pmi_verse_significant.csv` — significant pairs
- Comparison with word-level: which conjunctions/oppositions persist across scales?
  **Verification**:
- Most verse-level PMIs should be less extreme than word-level (co-occurrence in same verse is weaker signal than adjacency)
- Some pairs may reverse sign between word and verse level — document these
- Matrix is symmetric (verse co-occurrence is undirected)
  **Size**: Small. Verse-level co-occurrence counting + PMI.

### C1.9 — Conjunction/Opposition Atlas

**Input**: C1.3 + C1.4
**Question**: What is the complete relational map of letter conjunctions and oppositions at both scales?
**Output**: `outputs/C1/conjunction_opposition_atlas.json`:

- Per letter pair: word_PMI, verse_PMI, classification (conjunction/opposition/neutral at each scale)
- Cross-scale consistency: pairs that are conjunctions at both scales, oppositions at both, or inconsistent
- Network visualization data: nodes = 36 letters, edges = significant PMI relationships
  **Verification**:
- 36×36 = 1,296 pairs (630 unique undirected for verse; 1,260 directed for word)
- Cross-scale agreement rate computed and documented
- Top 10 strongest conjunctions and oppositions listed with both PMI values
  **Size**: Small. Synthesis of C1.3 and C1.4.

### C1.10 — Phase Detection: Full Alphabet

**Input**: M8b embeddings + M7 dataset
**Question**: Which letters exhibit distinct contextual phases (multiple modes of usage)?
**Output**: `outputs/C1/phases.json` — per letter form:

- optimal_k: number of phases detected (GMM with BIC selection, k=1 to 6)
- phase_descriptions: per phase, the mean embedding vector + top 5 contextual features distinguishing this phase
- phase_sizes: proportion of instances in each phase
- silhouette_score: cluster quality
  **Verification**:
- Every letter has at least k=1 (single phase = no split)
- Calibration letters should confirm known phases: بـ should have k≥2 (prefix vs root), يـ should have k≥2 (actor vs consonant)
- No letter should have k>4 without strong BIC evidence (overfitting check)
- Phase assignments saved for all 327,793 instances (inspectable)
  **Size**: Medium-large. GMM fitting for 36 letter forms × up to 6 components.

### C1.11 — Embedding Space Visualization

**Input**: M8b embeddings
**Question**: What structure is visible in the learned embedding space?
**Output**: `outputs/C1/embedding_viz/`:

- `tsne_by_family.png` — t-SNE colored by geometric family
- `tsne_by_zone.png` — t-SNE colored by makhraj zone
- `tsne_by_frequency.png` — t-SNE sized by frequency rank
- `umap_combined.png` — UMAP with all three annotations
- `pca_variance.json` — PCA explained variance (how many dimensions carry structure?)
  **Verification**:
- Visualizations exist and are non-degenerate (not all points collapsed)
- PCA: first 10 components explain >50% of variance (structure exists) or document if not
- Visual inspection: do any groupings emerge? Document what is seen without interpreting it as confirming/denying hypotheses
  **Size**: Small. Dimensionality reduction + plotting.

-----

## Track D: Geometric (C1.12)

### C1.12 — Geometric Distance vs. Distributional Distance (F002 Follow-Up)

**Input**: M6 (geometric families) + C1.9 (conjunction/opposition atlas) + C1.1 (frequency)
**Question**: Does geometric proximity predict distributional proximity when measured from raw statistics (not embeddings)?
**Output**: `outputs/C1/geometric_distributional.json`:

- Geometric distance matrix: computed from family membership (same family = 0, different = 1) or from dot-count difference within families
- Distributional distance matrix: Jensen-Shannon divergence of PMI profiles (from C1.9), OR cosine distance of surah frequency vectors (from C1.1)
- Mantel test: correlation between geometric and distributional distance matrices (with permutation p-value, 10000 iterations)
- Within-family vs between-family distributional distance comparison (t-test or Mann-Whitney)
  **Verification**:
- Both distance matrices are 36×36, symmetric, zero diagonal
- Mantel test produces r and p-value; compare to F002’s r=-0.192 from embeddings
- If raw distributional distance also shows no correlation or negative correlation with geometry, F002 is confirmed as a robust finding across methods
- If raw distributional distance DOES correlate with geometry (contradicting F002), the discrepancy is documented as method-dependent
  **Size**: Small. Matrix comparison.

-----

## Track E: Variant Analysis (embedded in C1.1, C1.2, C1.10)

Variant analysis is not a separate track — it’s a lens applied within each track. The 36 letter forms include variants (أ/إ/آ/ا/ٱ etc.). Every track computation already operates on all 36 forms. The question “do variants of the same letter behave as one entity or as distinct entities?” is answerable from the outputs of C1.1 (do they have similar frequency profiles?), C1.2 (do they have similar entropy?), C1.10 (do they share phases or have distinct phases?), and C1.11 (do they cluster together in embedding space?).

No separate milestone needed. But C1.16 must synthesize variant findings explicitly.

-----

## Synthesis (C1.16, C1.17)

### C1.16 — Cross-Track Interaction Summary

**Input**: All C1.1-C1.15 outputs
**Question**: How do the four layers interact? Which cross-layer correlations are significant?
**Output**: `outputs/C1/cross_track.json`:

- Frequency × Entropy correlation: do frequent letters have higher or lower diacritical entropy?
- Frequency × Zone: frequency distribution per articulatory zone (beyond the simple count in C1.13)
- Entropy × Zone: does makhraj zone predict voweling flexibility?
- PMI × Zone: do same-zone letters have higher/lower PMI than cross-zone?
- Phase count × Frequency: do frequent letters have more phases?
- Phase count × Zone: do certain zones produce more multi-phase letters?
- Sonic weight × Frequency arc: do heavy passages coincide with particular letter frequency shifts?
- Variant convergence: for each variant family, summary of whether variants converge or diverge across all tracks
  **Verification**:
- Each correlation reported with effect size, p-value, confidence interval
- Bonferroni correction for multiple comparisons
- No causal claims — all correlations, documented as such
  **Size**: Medium. Correlation computation across all prior outputs.

### C1.17 — Cycle 1 Findings Report and Cycle 2 Recommendation

**Input**: C1.16 + all prior findings (F001, F002, F003, and any new findings)
**Question**: What did Cycle 1 find? What should Cycle 2 focus on?
**Output**: `outputs/C1/cycle1_report.md`:

- Numbered findings with evidence strength (effect size, significance)
- Which tracks showed strongest signal
- Which cross-layer interactions are most promising
- Specific hypotheses to pre-register for Cycle 2
- Recommended Cycle 2 focus areas
  **Verification**:
- Every finding references specific output files and test results
- No finding lacks a p-value and effect size
- Recommendations are justified by evidence, not intuition
- Human review required before Cycle 2 proceeds
  **Size**: Small. Synthesis document.

-----

## Execution Summary

|Milestone|Track |Depends On  |Size|Question                                         |
|---------|------|------------|----|-------------------------------------------------|
|C1.1     |Freq  |M7          |S   |What is each letter’s frequency profile?         |
|C1.2     |Sonic |M7          |S   |How flexible is each letter’s voweling?          |
|C1.3     |Struct|M7+M8a      |S   |Word-level PMI landscape?                        |
|C1.4     |Struct|M7          |S   |Verse-level PMI landscape?                       |
|C1.5     |Freq  |C1.1        |M   |How does frequency change across the mushaf?     |
|C1.6     |Freq  |C1.1        |M   |What is each letter’s temporal spacing pattern?  |
|C1.7     |Freq  |C1.1        |S   |Which letters co-vary in frequency across surahs?|
|C1.8     |Sonic |M7+C1.2     |M   |What is the diacritical melody of each verse?    |
|C1.9     |Struct|C1.3+C1.4   |S   |Complete conjunction/opposition atlas?           |
|C1.10    |Struct|M8b         |M-L |Which letters have multiple contextual phases?   |
|C1.11    |Struct|M8b         |S   |What structure is visible in embedding space?    |
|C1.12    |Geom  |M6+C1.9+C1.1|S   |Does geometry predict distribution (raw stats)?  |
|C1.13    |Sonic |M5+C1.1+C1.2|S   |Do articulatory zones have distinct profiles?    |
|C1.14    |Freq  |C1.5+C1.7   |S   |Are there frequency-coupled letter systems?      |
|C1.15    |Sonic |C1.8+C1.1+M5|M   |What is the sonic weight landscape?              |
|C1.16    |Cross |C1.1-C1.15  |M   |How do the four layers interact?                 |
|C1.17    |Synth |C1.16       |S   |What did we find? Where does Cycle 2 focus?      |

17 milestones. 8 small, 6 medium, 1 medium-large, 2 synthesis.
Estimated: 3-5 agent sessions if run sequentially.

**Critical constraint**: C1.17 requires human review before Cycle 2. The agent computes. The scientist decides.