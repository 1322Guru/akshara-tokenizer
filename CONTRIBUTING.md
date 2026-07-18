# Contributing to AksharaTokenizer

Thank you for your interest in contributing.  The project is small and focused:
a linguistically-correct Akshara boundary tokenizer for Brahmic/Indic scripts.
Contributions that add scripts, fix boundary rules, or improve test coverage
are most welcome.

---

## Adding a New Script

Each script requires three additions:

### 1. Extend `unicode_tables.py`

Add an entry to the `SCRIPTS` dict:

```python
SCRIPTS["my_script"] = {
    "consonants": {0xXXXX, 0xXXXX, ...},        # consonant code points
    "independent_vowels": {0xXXXX, ...},          # vowels that start a new Akshara
    "vowel_signs": {0xXXXX, ...},                 # dependent vowel diacritics
    "virama": 0xXXXX,                             # virama / killer / pulli code point
    "combining": {0xXXXX, ...},                   # anusvara, visarga, nukta, etc.
    "uses_conjuncts": True,                        # True = virama joins two consonants
                                                   # False = virama creates dead consonant
}
```

Look up code points at https://www.unicode.org/charts/. Find the script's
block, identify each character category, and add only the code points you
have verified.

### 2. Add test cases in `tests/test_boundary.py`

Add at least one test per formation rule:

```python
def test_my_script_basic():
    # CV syllable
    assert segment_aksharas("\uXXXX\uXXXX") == ["\uXXXX\uXXXX"]

def test_my_script_conjunct():
    # C + virama + C → single conjunct (if uses_conjuncts=True)
    assert segment_aksharas("\uXXXX\uXXXX\uXXXX") == ["\uXXXX\uXXXX\uXXXX"]

def test_my_script_dead_consonant():
    # C + virama → dead consonant Akshara (if uses_conjuncts=False)
    assert segment_aksharas("\uXXXX\uXXXX") == ["\uXXXX\uXXXX"]
```

Cover: CV syllable, dead consonant, conjunct (if applicable), independent
vowel, anusvara attachment, mixed Latin+script.

### 3. Update `README.md`

Add the script to the "Supported Scripts" table and note any script-specific
quirks in the "Script-level Notes" section.

---

## Running Tests

All tests live in `tests/test_boundary.py`.  Run them with pytest:

```bash
# From the repo root
python -m pytest tests/ -v
```

All 34 tests (and any you add) must pass before submitting a PR.

To check a specific script:

```bash
python -m pytest tests/ -v -k "punjabi"
python -m pytest tests/ -v -k "tamil"
```

---

## Pull Request Process

1. **Fork** the repository and create a branch from `master`:
   ```bash
   git checkout -b add-sinhala-script
   ```

2. **Make your changes** following the "Adding a New Script" guide above.

3. **Run the full test suite** and confirm all tests pass:
   ```bash
   python -m pytest tests/ -v
   ```

4. **Run the fertility benchmark** to confirm numbers are sane (supply the
   FLORES-200 devtest locally):
   ```bash
   python benchmark_2026_07/run_fertility_v1_1.py --eval-dir <flores-eval-dir>
   ```

5. **Open a PR** against `master` with:
   - A description of which script you are adding and its Unicode block range.
   - The fertility results from the benchmark for at least three sample sentences.
   - A note about `uses_conjuncts` and any unusual combining marks.

6. A maintainer will review within a few days.  For complex scripts, expect
   back-and-forth on edge cases. Brahmic scripts have real complexity and
   correctness matters more than speed of merge.

---

## Code Style

- Pure Python stdlib only, no external dependencies in the core library.
- Type annotations on all public functions (`str`, `list[str]`, `int`).
- Keep `unicode_tables.py` data-only (no logic).  All logic lives in `boundary.py`.
- Comments in English.  Unicode examples in docstrings are encouraged.

---

## Reporting Bugs

Open a GitHub issue with:
- The input string (as a Python string literal with `\uXXXX` escapes so the
  code points are visible).
- The actual output of `segment_aksharas()`.
- The expected output and why.

Example:

```
Input:    "ੱਕ"  (Gurmukhi addak + ka)
Actual:   ["ੱ", "ਕ"]
Expected: ["ੱਕ"]  (addak attaches to following consonant)
```

---

## License

By contributing you agree that your code is released under the Apache 2.0
license (same as the project).
