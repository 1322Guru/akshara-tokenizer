# Arm N: can corpus rebalancing close the precomposed nukta penalty? (2026-08-02)

Measurement only. No model, package or published artifact was changed. The v1.2 map was
read read-only and never regenerated.

## The question

`results_bengali_diagnostic.md` measured a fertility penalty on text carrying precomposed
nukta letters: Gurmukhi loses 5.72 percent and Bengali 5.90 percent against the same text
in NFC. The cause is that both canonical forms of 15 characters occupy separate private-use
symbols in the map, so the SentencePiece unigram model learns separate and very unequal
probabilities for them.

There are two possible fixes. Aliasing the pairs at map level would force the two forms to
share one symbol, but the decoder would then have to pick one output form, so byte-exact
round-trip would be lost for the other. Byte-exact round-trip is the property that
distinguishes this tokenizer from a normalizing one, so that price is not acceptable.

This file tests the alternative: **can the penalty be closed by rebalancing the training
corpus alone, leaving the map untouched and round-trip intact?**

## The comparator is arm 0', not the shipped v1.2 model

**Every number below is measured against arm 0', a controlled baseline trained on the same
frozen base set as the arms. It is not the shipped v1.2 model, and the figures in this file
should not be read as v1.2 figures.**

Arm 0' differs from the published v1.2 numbers by **-0.12 to +0.13 percent**, purely because
it trains on a deterministically selected 6,000,000 lines rather than the reservoir draw the
shipped model used. That offset is corpus selection, not an arm effect. Comparing arms to
arm 0' removes it; comparing arms to the published numbers would not.

| script | arm 0' | published v1.2 | delta |
|---|---:|---:|---:|
| devanagari | 1.3732 | 1.374 | -0.06% |
| gurmukhi | 1.4440 | 1.445 | -0.07% |
| tamil | 1.9556 | 1.953 | +0.13% |
| telugu | 1.9988 | 2.001 | -0.11% |
| bengali | 1.7948 | 1.797 | -0.12% |
| kannada | 2.0561 | 2.058 | -0.09% |

Within a fixed corpus the pipeline is fully deterministic: three replicates produced
byte-identical vocabularies. So arm-to-arm differences carry no statistical noise at all,
and a 0.01 percent change is signal rather than variance.

## Method

**Base set.** One frozen selection of exactly 6,000,000 lines,
sha256 `1e0177866663a0f819bff69a894e8a20eb257a3f7fce1ace107aacd281c5781d`, built from the
v1.2 mapped corpus by proportional per-script quotas and even stride, no RNG. Every arm
trains on this set or on a substitution of it.

**No reservoir draw.** All arms train with `input_sentence_size=0`, so SentencePiece
consumes every line instead of sampling. If arms were instead added to the 22.5M pool and
sampled, the draw would change with the content and an arm difference could come from
either. This removes that confound.

**Substitution in place.** Line count is held at exactly 6,000,000. A line is eligible if it
contains at least one in-scope symbol in its dominant form; every k-th eligible line is
converted, k = round(1/f), a deterministic stride with no RNG. In a converted line every
in-scope dominant-form symbol is replaced by its paired alternate, whole-line and all-pairs,
which mirrors what a user sending non-NFC text actually produces.

**Byte guard.** 12 of the 15 pairs change UTF-8 length under substitution, because BMP
private-use codepoints are 3 bytes and plane-15 are 4. Any line whose post-substitution
length would exceed SentencePiece's 4,192-byte `max_sentence_length` is left unconverted, so
no arm can gain or lose a training line relative to another.

**All four models trained on exactly 5,997,116 sentences**, confirmed from the trainer logs.
The 2,884 lines dropped are over-length in the base set and are dropped identically in every
arm.

**Tamil is excluded, 11 of 15 pairs are in scope** (5 Devanagari, 4 Gurmukhi, 2 Bengali).
The corpus is uniformly NFC. For Devanagari, Gurmukhi and Bengali that means the precomposed
singletons are nearly absent, with pre/dec occurrence ratios of 0.0004 to 0.08. For Tamil
the relationship inverts, because NFC composes U+0BC6 U+0BBE into U+0BCA, so Tamil's
dominant form is already the one evaluation uses and its NFC delta is only -0.01 percent.
There is no Tamil penalty to recover, and converting Tamil would move it away from its
evaluation distribution. Tamil's four pairs were verified byte-for-byte identical across all
three arms.

**Three arms**, identical in every other respect: `f = 0.10`, `0.25`, `0.50`.

## The gates, fixed before the arms were built

1. **Recovery.** At least half the precomposed penalty on Gurmukhi and Bengali. Measured on
   arm 0' that is 2.863 percent and 2.986 percent respectively.
2. **Degradation.** No script worse than +0.05 percent as-is against arm 0'.
3. **Round-trip.** 1,012 of 1,012 in all eighteen cells, six scripts across as-is, NFC and
   NFD. Non-negotiable: an arm that breaks this is dead regardless of fertility.

## The substitution did what it was meant to

pre/dec occurrence ratio for the 11 in-scope pairs:

| script | precomposed | base | f=0.10 | f=0.25 | f=0.50 |
|---|---|---:|---:|---:|---:|
| beng | U+09DC | 0.0090 | 0.1247 | 0.3443 | 1.0186 |
| beng | U+09DF | 0.0041 | 0.1158 | 0.3384 | 1.0083 |
| deva | U+0931 | 0.0806 | 0.2428 | 0.4043 | 1.2616 |
| deva | U+095B | 0.0074 | 0.1163 | 0.3542 | 1.0055 |
| deva | U+095C | 0.0013 | 0.1093 | 0.3279 | 0.9779 |
| deva | U+095D | 0.0008 | 0.1132 | 0.3298 | 0.9800 |
| deva | U+095E | 0.0090 | 0.1134 | 0.3443 | 0.9980 |
| guru | U+0A36 | 0.0006 | 0.1087 | 0.3230 | 0.9485 |
| guru | U+0A36 U+0A3E | 0.0004 | 0.1085 | 0.3235 | 0.9574 |
| guru | U+0A36 U+0A41 | 0.0005 | 0.1090 | 0.3181 | 0.9558 |
| guru | U+0A5B | 0.0008 | 0.1076 | 0.3239 | 0.9548 |

At f=0.50 the two forms reach parity. The intended shift is verified, not assumed.

## Results

### As-is fertility, delta against arm 0'

Negative is better. Bold marks a breach of the +0.05 percent degradation gate.

| script | arm 0' | f=0.10 | f=0.25 | f=0.50 |
|---|---:|---:|---:|---:|
| devanagari | 1.3732 | -0.003% | +0.003% | **+0.199%** |
| gurmukhi | 1.4440 | -1.347% | -2.013% | -2.387% |
| tamil | 1.9556 | -0.018% | +0.021% | +0.037% |
| telugu | 1.9988 | +0.003% | **+0.059%** | **+0.109%** |
| bengali | 1.7948 | -0.383% | -0.920% | -1.031% |
| kannada | 2.0561 | +0.018% | **+0.066%** | **+0.088%** |

### Recovery against the 50 percent bar

| script | penalty on arm 0' | bar | f=0.10 | f=0.25 | f=0.50 |
|---|---:|---:|---:|---:|---:|
| gurmukhi | 5.726% | 2.863% | 1.347% (23.5%) | 2.013% (35.2%) | 2.387% (**41.7%**) |
| bengali | 5.973% | 2.986% | 0.383% (6.4%) | 0.920% (15.4%) | 1.031% (**17.3%**) |

### What the gain costs: NFC fertility, delta against arm 0'

| script | arm 0' NFC | f=0.10 | f=0.25 | f=0.50 |
|---|---:|---:|---:|---:|
| devanagari | 1.3660 | +0.066% | +0.123% | +0.405% |
| gurmukhi | 1.3613 | +0.150% | +0.286% | +0.564% |
| tamil | 1.9554 | -0.018% | +0.021% | +0.037% |
| telugu | 1.9983 | +0.003% | +0.059% | +0.109% |
| bengali | 1.6876 | +0.076% | +0.182% | +0.392% |
| kannada | 2.0539 | +0.018% | +0.067% | +0.088% |

### Round-trip

**1,012 of 1,012 in all eighteen cells, for every arm including arm 0'.** Substitution
changes training data only; the map is untouched and both forms remain mapped, so
`decode(encode(x))` still reconstructs whichever form the input carried. Byte-exactness was
never at risk and was confirmed empirically anyway.

### Latin side, unchanged

| category | arm 0' | f=0.10 | f=0.25 | f=0.50 |
|---|---:|---:|---:|---:|
| romanized hindi | 2.5779 | 2.5757 | 2.5743 | 2.5799 |
| romanized punjabi | 2.7790 | 2.7805 | 2.7795 | 2.7822 |
| romanized tamil | 4.5554 | 4.5388 | 4.5243 | 4.4757 |
| hinglish findnitai | 2.3907 | 2.3878 | 2.3854 | 2.3883 |
| hinglish cmu | 2.3503 | 2.3557 | 2.3472 | 2.3484 |
| english flores200 | 2.1795 | 2.1786 | 2.1750 | 2.1797 |

All within 1.8 percent, round-trip perfect. Vocabulary composition is essentially static
across arms: Indic 92.07 to 92.09 percent, Latin 2,249 to 2,255 pieces. Split rate is
identical to arm 0' on every script.

## Verdict: all three arms fail

| arm | f | degradation gate | recovery gate | round-trip |
|---|---|---|---|---|
| N-a | 0.10 | **PASS**, worst +0.018% | **FAIL** | 1012 x18 |
| N-b | 0.25 | **FAIL**, kannada +0.066% | **FAIL** | 1012 x18 |
| N-c | 0.50 | **FAIL**, devanagari +0.199% | **FAIL** | 1012 x18 |

**Recovery plateaus at 41.7 percent on Gurmukhi and 17.3 percent on Bengali, against a 50
percent bar, so no value of f passes.** The one arm that keeps degradation inside the gate,
f=0.10, recovers least. Raising f buys recovery at a rate that falls away sharply while
degradation keeps climbing.

The knee is visible in the Gurmukhi column: 0 to 1.347 to 2.013 to 2.387. Going from f=0.10
to f=0.25 buys 0.67 points; from 0.25 to 0.50 buys only 0.37. Meanwhile Devanagari
degradation goes 0.00, 0.00, +0.199. Even at parity the ceiling sits well below the bar.

## Mechanism

**Substitution moves information, it does not add it.** The corpus is a fixed 6,000,000
lines, so every occurrence the precomposed form gains, the decomposed form loses. The NFC
column is the direct evidence: as the precomposed form improves, Gurmukhi NFC fertility
degrades by 0.150, 0.286 and 0.564 percent across the three arms. The arm trades NFC
performance for precomposed performance rather than improving both.

This is why no value of f can pass. The penalty is not caused by a fixable imbalance in the
corpus. It is the cost of representing two canonical forms as two distinct symbols, which is
in turn the cost of byte-exact round-trip.

## Consequence

The NFC recommendation in the README and the model card is a measured conclusion, not an
untested workaround. Corpus rebalancing was tried at three levels and cannot replace it.
Closing the penalty properly would require map-level aliasing, which would end byte-exact
round-trip, and that trade is not worth making.

## Reproduce

Build artifacts live outside this repository, under
`/mnt/c/GuruAI-Data/akshara_v1_3_sweep/`: `build_base_6m.py`, `build_armN.py`,
`train_arm_fixed.py`, `eval_arm.py`, `eval_latin.py`, `count_dual_forms.py`. They are not
vendored here because they write multi-gigabyte corpora.

| artifact | sha256 |
|---|---|
| frozen 6M base set | `1e0177866663a0f819bff69a894e8a20eb257a3f7fce1ace107aacd281c5781d` |
| `akshara_tokenizer_v1_2.model` | `02161e9f865eae3e083d3ccb121ea46e242e32ee115052a029afbf341a4d294d` |
| `akshara_tokenizer_v1_2.map.json` | `5653f2cf29e8bcf456877851a71e3a4ebf254cee1129ecdca4a4120b5ef9d160` |
