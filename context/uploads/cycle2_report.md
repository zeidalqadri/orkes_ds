# Cycle 2 Findings Report

**Project**: تعلّ — The Weight of Letters
**Date**: 2026-05-27
**Milestones**: R0.1-R0.3 (remedial) + C2.1-C2.10 (analytical)
**Status**: AWAITING HUMAN REVIEW — Do not proceed to Cycle 3 without operator approval.

---

## 1. Numbered Findings

### F010: Word-Level Centroids Are Structured But Do Not Separate Functional Groups
- **Source**: C2.2-C2.4 (centroid analysis)
- **Evidence**:
  - 36 letter centroids in 50D word-embedding space
  - Z = -31.67 vs random baseline → centroids are NOT noise
  - Calibration: Hedges' g = -0.704 (prep vs actor, FAILED — 0Q had g = 1.73)
  - Mantel tests: zone r = -0.008 (p = 0.53), geometric r = -0.021 (p = 0.59), frequency r = 0.119 (p = 0.07)
  - K-means best k = 2 (silhouette 0.58), essentially separating إ from all others
- **Effect size**: g = -0.70 (reversed direction from calibration expectation)
- **Interpretation**: Word-level PPMI+SVD centroids capture distributional co-occurrence but not functional role. The centroids are real structure but reflect frequency/co-occurrence patterns rather than the prep/actor distinction visible in contextual embeddings.

### F011: Zone-Entropy Effect Replicates and Is Driven by Zone 1 vs Zone 5
- **Source**: C2.5 (zone-entropy decomposition)
- **Evidence**:
  - Kruskal-Wallis H = 20.12, p = 0.0012, η² = 0.47 (replicates C1 F003)
  - Zone 1 (glottal/semivowels): mean entropy 0.46 — most constrained
  - Zone 5 (tongue): mean entropy 1.86 — most flexible
  - Significant pairwise (Holm): Zone 1 vs Zone 5 (p = 0.002, Cliff's δ = -1.0), Zone 2 vs Zone 5 (p = 0.043, δ = -0.88)
  - All other pairs: p ≥ 0.28
- **Effect size**: η² = 0.47 (large), Cliff's δ = -1.0 (maximal) for Zone 1 vs 5
- **Interpretation**: The zone → entropy signal from C1 is robust. It is driven by the contrast between glottal/semivowel letters (which have near-zero diacritical entropy) and tongue letters (which use all diacritics flexibly). Zones 3-4 (pharyngeal) are intermediate and do not differ significantly from Zone 5.

### F012: 33/36 Letters Show Position-Dependent Diacritical Patterns
- **Source**: C2.6 (positional analysis)
- **Evidence**:
  - Chi-squared tests (diacritical distribution × word position) per letter
  - 33/36 significant after Holm correction
  - Most specialized: ة (ta marbuta) — entropy 0.014, 100% final position
  - Least specialized: ء (hamza) — entropy 1.57, most evenly distributed
  - 6 non-connecting letters identified from geometric data
- **Effect size**: Varies; Cramér's V ranges from 0.02 to 0.45
- **Interpretation**: Nearly universal position-dependence. Where a letter appears in a word constrains which diacritics it receives. This is expected from Arabic morphology but is discovered here purely from text spacing.

### F013: Positional Semantic Modulation Exists for 15/28 Letters
- **Source**: C2.7 (positional centroids)
- **Evidence**:
  - For each letter, computed separate centroids when appearing as C₁, C₂, C₃ (first, second, third consonant in word)
  - 15/28 tested letters (those with ≥10 words per position) show significant positional shift
  - Strongest modulation: ء (hamza, max inter-centroid distance 0.55)
  - Weakest modulation among significant: ل (lam, C₂-C₃ distance only 0.075 but C₁ diverges at 0.187)
- **Effect size**: Cosine distances 0.07–0.55 between positional centroids
- **Significance**: Permutation test (1000 permutations), Holm-corrected
- **Interpretation**: A letter's semantic contribution shifts depending on its consonantal position within the word. This is the first evidence that letters carry position-dependent semantic information in this corpus.

### F014: Phase Detection Succeeds — All 36 Letters Show Multiple Contextual Phases
- **Source**: C2.8 (phase detection redesign)
- **Evidence**:
  - PCA (80% variance) + HDBSCAN on 128D contextual embeddings from M8b
  - All 36 letters: 2–9 clusters (median ~6), vs degenerate k=6 in C1
  - Noise fractions: <1% for most letters (continuous usage is clustered, not noise)
  - Calibration: بـ (8 clusters, PASS — cluster 1 = kasra/initial = بِـ prefix, 36%)
  - Calibration: يـ (9 clusters, PASS — position AND diacritic separation)
  - Only outlier: ٱ (alif wasla) → 54 clusters, 33% noise — fragmented
  - PCA: most letters need 3–6 components for 80% variance
- **Effect size**: Not applicable (unsupervised clustering)
- **Interpretation**: The C1 GMM+BIC approach was fitting noise dimensions. PCA compression + HDBSCAN discovers genuine discrete phases. The بـ prefix phase (kasra + initial position, 36% of instances) is a real functional distinction recovered without any external label.

### F015: Surah-Length Confound Confirmed — 23 Genuine Frequency Couplings Survive
- **Source**: C2.9 (length-deconfounded frequency)
- **Evidence**:
  - Raw mean correlation: r = 0.959 → Deconfounded mean: r = -0.018
  - 23 significant pairs after Holm correction (from 630 raw)
  - Anchor: lam + alif-wasla r = 0.625 (SURVIVES, was r = 0.594 in C1 arcs)
  - Strongest anti-correlation: ا + ل = -0.606 (alif and lam trade off by surah!)
  - New coupling: ئ + ث = 0.449 (p_holm = 0.0003)
  - حـ + ٱ = 0.576 (ha + alif-wasla, related to definite article context)
- **Effect size**: Ranges from |r| = 0.42 to 0.63
- **Interpretation**: The massive C1 co-frequency signal (mean r = 0.96) was almost entirely surah-length artifact. After normalization, only 23 pairs show genuine coupling. The lam+alif-wasla morphological anchor is confirmed and strengthened. The ا-ل anti-correlation is new: surahs that use more bare alif use less lam (and vice versa), suggesting compositional structure.

### F016: Cross-Analysis Interactions Are Sparse
- **Source**: C2.10 (cross-analysis synthesis)
- **Evidence**:
  - 6 interactions tested, 0 significant after Holm correction
  - Strongest uncorrected: deconfounded coupling × centroid proximity (d = -1.10, p = 0.022 raw, p_holm = 0.13) — frequency-coupled pairs DO have closer centroids (mean 0.135 vs 0.291)
  - Zone × phase count: marginal (H = 10.27, p = 0.068, η² = 0.16)
  - Positional modulation × phase count: medium effect (d = 0.43) but not significant
  - All other interactions: null
- **Effect size**: d = -1.10 for coupling×proximity (large but insufficient n)
- **Interpretation**: The layers of Arabic letter structure remain largely independent even at Cycle 2 resolution. The one promising cross-layer signal (frequency coupling predicts centroid proximity) needs more statistical power.

---

## 2. Go/No-Go Assessment: Semantic Direction Extraction

### Verdict: CAUTIOUS GO

### Evidence For Feasibility
1. **Centroids are structured** (Z = -31.67 vs random) — word-level embeddings capture real distributional patterns
2. **15/28 letters show positional semantic modulation** — consonantal position shifts the centroid, meaning letters carry position-dependent semantic weight
3. **All 36 letters have multiple contextual phases** — HDBSCAN recovers discrete functional distinctions
4. **Phase calibration passes** — بـ splits into prefix/root, يـ splits by function
5. **Morphological anchor validated** — lam+alif-wasla coupling (r = 0.625) survives deconfounding
6. **23 genuine frequency couplings** — real inter-letter structure exists after removing confounds

### Evidence Against
1. **Word-level centroid calibration FAILS** — prep and actor centroids don't separate (g = -0.70 vs expected +1.73). The 50D word co-occurrence space doesn't resolve functional roles.

### Recommendation
Proceed to Cycle 3 using **phase-aware semantic directions** rather than whole-letter centroids:
- Compute phase-specific centroids using HDBSCAN cluster assignments on 128D contextual embeddings
- Each letter gets multiple semantic directions (one per phase)
- The prefix phase of بـ, the actor phase of يـ — these have distinct semantic profiles that the whole-letter centroid averages away
- Cross-word verification: test if letters in the same phase contribute consistent semantic direction to the words they appear in

---

## 3. Cycle 2 Summary Statistics

| Metric | Value |
|--------|-------|
| Milestones completed | 13 (R0.1-R0.3 + C2.1-C2.10) |
| New findings | 7 (F010-F016) |
| Word vocabulary | 4,092 types (min_count = 3) |
| Embedding dimension | 50 (word), 128 (contextual) |
| Letter centroids | 36, all non-random |
| Positional modulation | 15/28 significant |
| Phase clusters (median) | ~6 per letter |
| Deconfounded couplings | 23 (from 630 raw) |
| Cross-layer interactions | 0/6 significant (Holm) |
| Go/No-Go | CAUTIOUS GO |

---

## 4. Hypothesis Assessment

| C1 Hypothesis | Tested In | Result |
|---------------|-----------|--------|
| H1: Zone-entropy driven by throat zones | C2.5 | **Partially confirmed** — driven by Zone 1 (glottal) vs Zone 5 (tongue), not throat specifically |
| H2: Lam+alif-wasla reflects definite article | C2.9 | **Confirmed** — survives deconfounding (r = 0.625) |
| H3: Motif frequencies differ by surah position | — | Not tested in Cycle 2 (deferred) |
| H4: Frequency arc trends reflect compositional shifts | C2.9 | **Partially confirmed** — deconfounding reveals genuine couplings including ا-ل anti-correlation |
| H5: Alif variants occupy different embedding regions | C2.2 | **Confirmed** — إ is the only letter in K-means cluster 1; other alif forms in cluster 0 |

---

## 5. Cycle 3 Pre-Registered Hypotheses

### H6: Phase-aware centroids separate functional roles
**Prediction**: When computing centroids per HDBSCAN cluster (rather than per letter), the prep-phase centroid of بـ (cluster 1, kasra/initial) will separate from the root-phase centroid with Hedges' g > 1.0.
**Test**: LDA on phase-specific centroids for بـ, يـ, كـ, فـ, and actor triples.
**Falsification**: If g < 0.5, phase-aware centroids do not improve functional resolution.

### H7: Letters with more phases carry more semantic information per word
**Prediction**: Words containing letters with ≥6 phases have higher embedding variance than words containing only letters with ≤3 phases.
**Test**: Compare word embedding variance between groups, controlling for word length.
**Falsification**: No significant difference (p > 0.05 after correction).

### H8: The ا-ل anti-correlation reflects definite article morphology
**Prediction**: The ا+ل anti-correlation (r = -0.606) disappears when only counting ال-initial words, because the trade-off is between ا in non-ال contexts and ل in ال contexts.
**Test**: Separate ال-initial letter counts from other counts, re-compute correlation.
**Falsification**: Anti-correlation persists after ال-removal (not morphological).

### H9: Consonantal position modulates semantic direction consistently across words
**Prediction**: For the 15 letters with significant positional modulation, words sharing a letter in the same position (e.g., both have ب as C₁) will have more similar embeddings than words sharing the letter in different positions.
**Test**: Mean cosine similarity within-position vs across-position, permutation test.
**Falsification**: No within-position advantage (p > 0.05).

### H10: Phase structure correlates with surah-opening letter status
**Prediction**: The 14 surah-opening letters (الم، حم، etc.) show different phase structure than non-opening letters. Specifically, opening letters may show an additional "isolated" phase not seen in non-opening letters.
**Test**: Compare phase counts and noise fractions between opening and non-opening letters, Mann-Whitney U.
**Falsification**: No significant difference in phase structure.

---

## 6. References to Output Files

| Finding | Output Files |
|---------|-------------|
| F010 | `outputs/C2/centroid_analysis.json`, `outputs/C2/calibration_semantic.json`, `outputs/C2/centroid_structure/` |
| F011 | `outputs/C2/zone_entropy_decomposition.json` |
| F012 | `outputs/C2/positional_analysis.csv`, `outputs/C2/positional_anova.json`, `outputs/C2/positional_specialization.json` |
| F013 | `outputs/C2/positional_centroids.json`, `outputs/C2/position_modulation_summary.csv` |
| F014 | `outputs/C2/phases_v2/summary.json`, `outputs/C2/phases_v2/calibration_check.json`, `outputs/C2/phases_v2/per_letter/` |
| F015 | `outputs/C2/deconfounded_frequency.csv`, `outputs/C2/deconfounded_cofreq.csv`, `outputs/C2/deconfounded_clusters.json`, `outputs/C2/deconfounding_comparison.json` |
| F016 | `outputs/C2/cross_analysis.json` |

---

*This report was generated by automated analysis. All findings are correlational. No causal claims are made. Human review is required before Cycle 3 proceeds.*
