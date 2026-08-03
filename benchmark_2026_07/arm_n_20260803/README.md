# Arm N: code and result data (2026-08-03)

The scripts and per-arm result JSON behind `../results_arm_n_normalization.md`, which asks
whether the precomposed nukta fertility penalty can be closed by rebalancing the training
corpus without touching the map. The answer was no, and this directory is what makes that
answer checkable.

## What is here

| file | role |
|---|---|
| `build_base_6m.py` | builds the frozen 6,000,000-line base set from the v1.2 mapped corpus |
| `build_armN.py` | substitution builder, parameterised by f, with the byte guard and Tamil exclusion |
| `train_arm_fixed.py` | trains one arm with `input_sentence_size=0`, so no reservoir draw occurs |
| `train_arm.py` | reservoir-based trainer, used only for the noise-floor replicates |
| `run_armN.sh` | driver: builds and trains the three arms sequentially |
| `run_seeds.sh` | driver: the three noise-floor replicates |
| `eval_arm.py` | native fertility, round-trip, split rate, vocabulary composition |
| `eval_latin.py` | Latin side, from the frozen competitor selection |
| `count_dual_forms.py` | occurrence counts for the 30 symbols of the 15 duplicated-form pairs |
| `verify_arm_n.py` | recomputes every published number from the result JSON |
| `dual_form_pairs.json` | the 15 pairs and their private-use codepoints |
| `trainer_counts.txt` | the trainer lines evidencing that all four arms saw the same corpus size |
| `result_json/` | per-arm result JSON, the source for every number in the published file |

## What is deliberately not here

The frozen 6M base set, the three substituted corpora and the trained models are excluded
for size: the corpora are about 1.2 GB each and the models about 18 MB in total. They are
also third-party corpus text, which this repository does not vendor.

The base set is fully reproducible from `build_base_6m.py`, whose selection rule is
deterministic with no RNG, and is identified by

```
1e0177866663a0f819bff69a894e8a20eb257a3f7fce1ace107aacd281c5781d
```

Verify a rebuild against that hash before trusting any arm built on top of it.

## Paths

Every absolute path is an environment variable with the original machine's value as the
fallback, so the scripts run unmodified where they were written and are portable elsewhere.

| variable | meaning |
|---|---|
| `AKSHARA_SWEEP` | scratch tree for corpora, models and result JSON |
| `AKSHARA_V12_MAPPED` | the v1.2 PUA-mapped corpus and its charset pickles |
| `AKSHARA_REPO` | checkout root of this repository |
| `AKSHARA_SETS` | frozen competitor eval selection, `competitor_sets.json` |

## Regenerating the result

```bash
export AKSHARA_SWEEP=/path/to/scratch
export AKSHARA_V12_MAPPED=/path/to/akshara_v1_2/mapped
export AKSHARA_REPO=/path/to/akshara-tokenizer
export AKSHARA_SETS=/path/to/competitor_sets.json

# 1. build the frozen base set, then check it against the sha256 above
python3 build_base_6m.py

# 2. the controlled baseline, arm 0'
python3 train_arm_fixed.py 1 "$AKSHARA_SWEEP/models/arm0prime" "$AKSHARA_SWEEP/base_6m"

# 3. the three substitution arms, built and trained
bash run_armN.sh

# 4. evaluate, native side with all three normalization forms, then the Latin side
for a in arm0prime armNa armNb armNc; do
  python3 eval_arm.py "$AKSHARA_SWEEP/models/$a.model" "$a" --forms \
      --json result_json/${a}_forms.json
  python3 eval_latin.py "$AKSHARA_SWEEP/models/$a.model" "$a" \
      --json result_json/latin_${a}.json
done

# 5. occurrence counts, base set and each arm
python3 count_dual_forms.py "$AKSHARA_SWEEP/base_6m"
for a in armNa armNb armNc; do
  python3 count_dual_forms.py "$AKSHARA_SWEEP/corpus_$a"
done

# 6. confirm the published numbers still derive from the result JSON
python3 verify_arm_n.py
```

`verify_arm_n.py` recomputes every published value rather than grepping for it, because a
substring search cannot distinguish a fabricated number from a correctly rounded one, and
because the deltas and recovery percentages appear in no source file at all.

## Note on the comparator

Every number in the published file is measured against arm 0', a controlled baseline
trained on the frozen base set. It is not the shipped v1.2 model. Arm 0' differs from the
published v1.2 figures by -0.12 to +0.13 percent, purely because it trains on a
deterministically selected 6,000,000 lines rather than the reservoir draw the shipped model
used. Do not read arm 0' numbers as v1.2 numbers.
