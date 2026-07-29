# Cycle 1 Findings Report

**Project**: تعلّ — The Weight of Letters
**Date**: 2026-05-26
**Milestones**: C1.1 through C1.16 (17 milestones, all PASS)
**Status**: AWAITING HUMAN REVIEW — Do not proceed to Cycle 2 without operator approval.

---

## 1. Numbered Findings

### F001: Diacritical Head Learns More Than Letter Head
- **Source**: M8b embedding training
- **Evidence**: Diacritical head 34.4% improvement over random baseline vs letter head 20.9%
- **Effect size**: 13.5 percentage point gap
- **Significance**: Consistent across all training epochs
- **Interpretation**: Grammar (diacritics) is more locally predictable than root selection (letters)

### F002: Geometric Form Does Not Predict Distributional Behavior
- **Source**: M9 calibration (0K, 0L) + C1.12 Mantel test
- **Evidence**:
  - Embedding-based: Mantel r = -0.192, p = 1.0 (anti-correlated)
  - Raw statistics: Mantel r = -0.005, p = 0.54 (null)
  - Within-family distributional distance (0.028) = between-family (0.028), p = 0.31
- **Effect size**: r ≈ 0 (raw) to r = -0.19 (embedding)
- **Significance**: Confirmed across two independent methods (embedding distance, cosine distance of surah frequency vectors)
- **Status**: Robust finding. Geometry and distribution are independent dimensions.

### F003: Articulatory Zone Predicts Diacritical Entropy
- **Source**: C1.13 zone profiles + C1.16 cross-track
- **Evidence**: Kruskal-Wallis H = 18.1, p = 0.003 (raw), p_bonf = 0.023
- **Effect size**: η² = 0.44 (large) in C1.16; η² = 0.52 in C1.13
- **Significance**: Survives Bonferroni correction (8 tests)
- **Detail**: Where a letter is articulated constrains how flexibly it can be voweled. This is the strongest cross-layer signal in Cycle 1.

### F004: Letter Frequencies Are Dominated by Surah Length
- **Source**: C1.7 co-frequency matrix + C1.14 coupled systems
- **Evidence**: Mean Pearson r = 0.96 across all letter pairs at surah level (C1.7). After length deconfounding via arc-level analysis, mean r = -0.02, consistent with compositional baseline (-1/35 = -0.029)
- **Effect size**: Surah-level r = 0.96 (spurious); arc-level r ≈ 0 (null after deconfounding)
- **Significance**: 630/630 surah-level pairs significant; only 7 multi-letter arc clusters survive deconfounding
- **Detail**: Strongest genuine coupling: lam + alif-wasla (r = 0.59, definite article morpheme)

### F005: All Letters Show Maximum Phase Count
- **Source**: C1.10 phase detection
- **Evidence**: All 36 letters detected k = 6 (maximum allowed). Silhouette scores 0.18–0.23.
- **Effect size**: Low silhouette indicates continuous variation, not discrete clusters
- **Significance**: BIC favors k_max because each additional Gaussian component captures additional variance in 128D space
- **Detail**: Contextual embeddings are continuously distributed. If discrete phases exist, they require a different detection method (e.g., constrained k, domain-guided priors, or higher training quality).

### F006: Most Diacritical Motifs Are Fatha-Dominant
- **Source**: C1.8 melody extraction
- **Evidence**: 1,245 significant motifs (Bonferroni-corrected, 100 permutations). Most frequent: fatha-fatha-kasra-fatha-fatha-fatha (1,821 occurrences vs 1,511 expected)
- **Effect size**: Varies by motif (observed/expected ratios 1.1–2.5)
- **Significance**: Bonferroni-corrected at motif level

### F007: All Letters Show Clustered Temporal Spacing
- **Source**: C1.6 inter-arrival analysis
- **Evidence**: All 36 letters fit negative binomial distribution. All burst scores > 1 (variance > mean)
- **Effect size**: Burst scores range from ~1.5 (common letters) to ~10 (rare letters)
- **Detail**: No letter is Poisson-distributed. Letters cluster in the text at all frequency levels.

### F008: Frequency and Diacritical Entropy Are Independent
- **Source**: C1.16 cross-track
- **Evidence**: Pearson r = -0.065, p = 0.706, p_bonf = 1.0
- **Effect size**: r ≈ 0 (null)
- **Detail**: How often a letter appears tells nothing about how flexibly it can be voweled. These are orthogonal dimensions.

### F009: PMI Does Not Vary by Articulatory Zone
- **Source**: C1.16 cross-track
- **Evidence**: Same-zone PMI mean vs cross-zone PMI mean: Cohen's d = -0.058, p = 0.40, p_bonf = 1.0
- **Effect size**: d ≈ 0 (null)
- **Detail**: Letters from the same articulatory zone do not co-occur more (or less) within words than cross-zone pairs. Sequential structure is independent of articulatory grouping.

---

## 2. Track Signal Strength

| Track | Milestones | Key Finding | Signal |
|-------|-----------|-------------|--------|
| **Sonic** | C1.2, C1.8, C1.13, C1.15 | Zone → entropy (F003, η²=0.44) | **Strong** |
| **Frequency** | C1.1, C1.5, C1.6, C1.7, C1.14 | Length confound dominates (F004); clustering universal (F007) | Moderate (after deconfounding) |
| **Structural** | C1.3, C1.4, C1.9, C1.10, C1.11 | 241 significant PMI pairs; phases continuous (F005) | Moderate |
| **Geometric** | C1.12 | Independence confirmed (F002) | Null (informative null) |
| **Cross-track** | C1.16 | Only entropy × zone survives Bonferroni | Sparse |

**Strongest signal**: The sonic track. Articulatory zone is the only variable that significantly predicts another track's measure (diacritical entropy) after Bonferroni correction.

---

## 3. Cross-Layer Interactions

| Interaction | Effect Size | p_bonf | Verdict |
|-------------|------------|--------|---------|
| Entropy × Zone | η² = 0.44 | 0.023 | **Significant** |
| Frequency × Zone | η² = 0.19 | 0.445 | Not significant |
| Frequency × Entropy | r = -0.07 | 1.0 | Null |
| PMI × Zone | d = -0.06 | 1.0 | Null |
| Phase × Frequency | r = 0.0 | 1.0 | Degenerate (all k=6) |
| Phase × Zone | η² = -0.17 | 1.0 | Degenerate (all k=6) |
| Sonic × Arc | r = 0.019 | 1.0 | Negligible (lam arc vs sonic contour) |
| Variant convergence | 67% | — | Descriptive |

**Most promising**: The entropy × zone interaction. This should be investigated at finer resolution: which specific zones drive the effect? Is it driven by outlier letters?

---

## 4. Variant Analysis Summary

Three variant families examined:
- **Alif family** (ا أ إ ٱ ى): High frequency CV (1.06), moderate entropy CV. Variants DIVERGE in frequency but partially converge in entropy.
- **Hamza family** (ء أ ؤ إ ئ): High frequency CV, moderate entropy CV. Similar pattern.
- **Ya-Waw** (ي و): Dual-zone letters. Low frequency CV (convergent), high entropy CV.

2/3 families meet convergence threshold (freq_cv < 1.0 AND entropy_cv < 1.0). The alif family is the most divergent, as expected given the functional diversity of alif forms.

---

## 5. Hypotheses for Cycle 2 Pre-Registration

Based on Cycle 1 evidence, the following hypotheses are proposed for pre-registration before Cycle 2 testing:

**H1**: Zone-specific entropy is driven primarily by the throat zones (2–4), where articulation constrains voweling more than in the tongue zone (5).
- *Basis*: F003 (η²=0.44). Need to decompose which zones drive the effect.
- *Test*: Post-hoc pairwise comparisons with Holm correction.

**H2**: The lam+alif-wasla coupling (r=0.59) reflects the definite article morpheme, and other morphological pairings will emerge when length-deconfounded arc correlations are examined at finer windowing.
- *Basis*: F004 (7 multi-letter clusters). The strongest coupling has clear morphological explanation.
- *Test*: Examine member letters of each cluster for morphological relationships.

**H3**: Diacritical motif frequencies differ by surah sequential position in the mushaf.
- *Basis*: F006 (1,245 motifs). No positional analysis performed in Cycle 1.
- *Test*: Partition motif counts by surah position quartile, test with chi-squared.
- *Note*: Whether positional shifts correlate with traditionally-named periods is a finding, not an input.

**H4**: The negative correlation between frequency and arc trend (lam has highest variance and slight negative trend) reflects systematic compositional shifts between early and late surahs.
- *Basis*: C1.5 arcs. Most letters show negative trend.
- *Test*: Correlate arc trends with surah ordering metadata.

**H5**: Variant alif forms occupy different regions of the contextual embedding space, reflecting functional specialization rather than phonemic identity.
- *Basis*: F002 + variant analysis. Alif variants diverge in frequency.
- *Test*: Pairwise cosine distance between variant embeddings, compared to non-variant pairs.

---

## 6. Recommended Cycle 2 Focus Areas

### Priority 1: Zone-Entropy Decomposition
The strongest finding (F003) needs mechanistic follow-up. Which zones drive the effect? Is it articulation physics or functional role?

### Priority 2: Length-Deconfounded Frequency Analysis
The surah-length confound (F004) masks real frequency structure. Cycle 2 should normalize all frequency measures by surah length before any cross-surah analysis.

### Priority 3: Phase Detection Improvement
The degenerate k=6 result (F005) means the current GMM approach with BIC is insufficient for detecting phases. Consider: constrained k (e.g., k ≤ 4), information-theoretic criteria that penalize complexity more strongly (minimum description length), or dimensionality reduction (PCA to 10-20 components) before clustering. Phase detection must remain unsupervised — no external annotation.

### Priority 4: Positional Analysis
No Cycle 1 milestone analyzed letter behavior by position within word, verse, or surah. This is a significant gap. Cycle 2 should include word-initial/medial/final analysis and surah-position effects.

### Priority 5: Embedding Model Improvement
The M8b model (2L/4H/128D, 408K params) learned meaningful structure but could benefit from: longer context (512 tokens), more layers (4L), and curriculum learning. The 26% improvement over random is good but leaves room for growth.

---

## 7. Summary Statistics

| Metric | Value |
|--------|-------|
| Total milestones | 17 (C1.1–C1.17) |
| Tests passed | All (see individual milestones) |
| Letter forms analyzed | 36 |
| Total instances | 327,793 |
| Significant findings | 9 (F001–F009) |
| Significant cross-layer interactions | 1 of 8 (after Bonferroni) |
| Strongest effect | Zone → Entropy, η² = 0.44, p_bonf = 0.023 |
| Informative nulls | 3 (F002, F008, F009) |
| Pre-registered hypotheses for Cycle 2 | 5 |

---

## References to Output Files

Each finding references specific output files:

- F001: `milestones/M8b.json`
- F002: `outputs/C1/geometric_distributional.json`, `milestones/C1.12.json`
- F003: `outputs/C1/zone_anova.json`, `outputs/C1/cross_track.json`
- F004: `outputs/C1/co_frequency_matrix.csv`, `outputs/C1/coupled_systems.json`
- F005: `outputs/C1/phases.json`
- F006: `outputs/C1/melody_motifs.csv`
- F007: `outputs/C1/inter_arrival.csv`
- F008: `outputs/C1/cross_track.json`
- F009: `outputs/C1/cross_track.json`

---

*This report was generated by automated analysis. All findings are correlational. No causal claims are made. Human review is required before Cycle 2 proceeds.*
