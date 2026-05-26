# Arbos State
Updated: 2026-05-26T02:30 UTC

## Status: IDLE — M3 complete

### M1 Summary
- **src/parser/extract_letters.py**: Parses Tanzil XML → 327,793 letter instances
- **tests/test_extract_letters.py**: 22/22 tests pass ✓
- Fixed verse_index bug: Bismillah segments correctly use verse_index=0
- Output: data/processed/letters.csv
- milestones/M1.json: written and valid

### M2 Summary
- **src/parser/extract_diacritics.py**: 21 diacritic types extracted per letter
- **tests/test_extract_diacritics.py**: 29/29 tests pass ✓
- All 21 VR001 diacritic counts match exactly
- has_shadda=23,016 (matches VR001)
- ة never sukoon, all vocalized
- is_bare=74,658 within range
- Output: data/processed/letters_with_diacritics.csv
- milestones/M2.json: written and valid

### M3 Summary — Shadda Decomposition (NEW)
- **src/parser/decompose_shadda.py**: Consonantal skeleton extraction
  - 23,016 shadda instances classified structurally (no external letter lists)
  - 18,596 true_doubling, 2,945 ال-assimilation, 1,475 noon-assimilation (idghaam)
  - shadow_diacritic_1=sukoon, shadow_diacritic_2=vowel extracted from diacritics
  - visual_count=1, sonic_count=2 for all shadda letters
- **495 gap verified**: has_shadda=23,016 - primary_diacritic(shadda)=22,521 = 495 shadda+tanween co-occurrences. Tanween takes precedence in primary_diacritic; has_shadda remains True. All 495 still properly decomposed.
- **tests/test_decompose_shadda.py**: 48/48 pass ✓
- **tests/test_shadda.py**: 43/43 pass ✓
- Output: data/processed/letters_with_shadda.csv
- milestones/M3.json: written

### Setup
- tala repo at /tmp/tala-stage/
- Python 3.12, standard library only
