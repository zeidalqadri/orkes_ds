# Cycle 2 Plan — تعلّ (The Weight of Letters)

**Date**: 2026-05-27
**Basis**: Cycle 1 report (9 findings, 17/17 milestones PASS)
**Operator directives**: Normalize frequencies, deconfound co-frequency, word embeddings as critical deliverable

---

## Scope

### In scope
- **A**: Deconfounded frequency analysis (normalized by surah length)
- **B**: Zone-entropy decomposition (H1 from Cycle 1)
- **C**: Word embeddings → letter centroids (critical deliverable, go/no-go gate)

### Dropped
- **H3** (Meccan/Medinan diacritical motif framing) — dropped entirely
- **H4** (arc trends by surah ordering) — subsumed into Part A positional work
- **Embedding model improvement** (report Priority 5) — premature; current model passed calibration; word embeddings in Part C are a separate system

---

## Part A: Deconfounded Frequency Analysis

**Problem**: Surah-level letter frequencies are dominated by surah length (F004: mean r=0.96 spurious). Only 7 multi-letter arc clusters survived deconfounding in Cycle 1.

**Method**:
1. Normalize all surah-level letter counts by surah length (letters per 1000 characters or proportion)
2. Re-compute co-frequency matrix on normalized values
3. Re-run Pearson correlations across all letter pairs
4. Identify which couplings remain significant after normalization

**Anchor**: Lam + alif-wasla (r=0.59 in Cycle 1 arc-level analysis). This has a clear structural explanation — the definite article morpheme (ال). It should survive normalization.

**Question**: What ELSE survives? Any couplings without obvious morphological explanation are candidates for deeper investigation.

**Deliverables**:
- `outputs/C2/normalized_cofreq.csv` — normalized co-frequency matrix
- `outputs/C2/surviving_couplings.json` — pairs with significant correlation after normalization, with effect sizes
- Comparison table: Cycle 1 raw vs Cycle 2 normalized correlations for all pairs

**Success**: Lam+alif-wasla remains significant. At least 1 additional coupling identified or confirmed null.

---

## Part B: Zone-Entropy Decomposition (H1)

**Problem**: Zone predicts diacritical entropy (F003: eta-squared=0.44, p_bonf=0.023) but we don't know which zones drive it.

**Method**:
1. Post-hoc pairwise zone comparisons with Holm correction
2. Compute per-zone entropy distributions (boxplot data)
3. Check for outlier letters driving the effect (leave-one-out sensitivity)
4. Test H1 specifically: throat zones (2-4) vs tongue zone (5)

**Deliverables**:
- `outputs/C2/zone_pairwise.json` — all pairwise comparisons with Holm-corrected p-values
- `outputs/C2/zone_entropy_detail.json` — per-zone distributions, outlier analysis
- Narrative: which zones drive the effect, is it outlier-driven or robust

**Success**: Effect localizable to specific zone contrast(s). Mechanism interpretable.

---

## Part C: Word Embeddings → Letter Centroids (CRITICAL)

**Problem**: Cycle 1 used character-level contextual embeddings (M8b: 2L/4H/128D). These learned grammar (diacritical head 34.4%) better than letter identity (20.9%). A complementary approach: use word-level embeddings and derive letter representations by aggregating over words containing each letter.

**Method**:
1. Train word-level embeddings on the Quranic text (word2vec/CBOW or skip-gram, or use existing Arabic word vectors if available and appropriate)
2. For each letter, compute its centroid: average embedding of all words containing that letter (weighted by letter frequency within word, or unweighted — test both)
3. Analyze centroid structure:
   - **Distinct directions**: Do letter centroids occupy different regions of embedding space? (pairwise cosine distances vs random baseline)
   - **Interpretable clustering**: Do known functional categories (sun letters vs moon letters, root-heavy vs grammatical, vowel-carriers vs consonants) form clusters?
   - **Separation**: Silhouette score of known categories. Compare to permutation baseline.
4. Cross-reference with Cycle 1 findings:
   - Do articulatory zones map to embedding space regions? (connects to F003)
   - Do variant families cluster? (connects to H5)

**Deliverables**:
- `outputs/C2/word_embeddings_model/` — trained word vectors
- `outputs/C2/letter_centroids.json` — 36 letter centroid vectors + metadata
- `outputs/C2/centroid_structure.json` — pairwise distances, clustering metrics, category separation scores
- Visualization: 2D projection (UMAP/t-SNE) of letter centroids colored by zone, category

**Go/No-Go Gate**:
- **GO** (centroids show meaningful structure): Distinct directions, interpretable clustering, category separation above permutation baseline → Phase 5 (semantic extraction) feasible in Cycle 3
- **NO-GO** (centroids are noise): Understand WHY before proceeding — is the corpus too small? Are word embeddings the wrong level? Do we need subword? Report the null and its implications.

---

## Milestone Sequence

| ID | Part | Task | Verify |
|----|------|------|--------|
| C2.1 | A | Normalize surah frequencies by length | Sum of normalized freqs per surah = 1.0 (or consistent) |
| C2.2 | A | Re-compute co-frequency on normalized values | Matrix is 36x36, diagonal = 1.0 |
| C2.3 | A | Identify surviving couplings | Lam+alif-wasla significant; full list with effect sizes |
| C2.4 | B | Zone pairwise comparisons (Holm) | All pairs tested, p-values corrected |
| C2.5 | B | Outlier/sensitivity analysis | Leave-one-out effect sizes reported |
| C2.6 | B | H1 test: throat vs tongue | Directional test with effect size |
| C2.7 | C | Train word embeddings | Model converges, vocabulary covers corpus |
| C2.8 | C | Compute letter centroids | 36 vectors, coverage stats |
| C2.9 | C | Centroid structure analysis | Distances, clustering, silhouette vs baseline |
| C2.10 | C | Cross-reference with Cycle 1 | Zone mapping, variant clustering |
| C2.11 | — | Cycle 2 report | Findings numbered F010+, go/no-go decision stated |

---

## Constraints

- All statistical tests must report effect sizes, not just p-values
- Multiple comparisons corrected (Bonferroni or Holm as appropriate)
- Normalization method documented and justified
- Word embedding hyperparameters logged (dimensions, window, epochs, min_count)
- No causal claims — all correlational
- Report sent to operator via Telegram when complete
