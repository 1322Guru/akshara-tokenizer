# AksharaTokenizer v1.2: normalization robustness (2026-08-02)

Measurement only. Nothing in the package, the v1.2 model or map, or any published artifact
was modified. Reproduce with `diagnose_bengali.py`.

## Why this stopped being a Bengali investigation

This began as a diagnostic for one number: v1.2 loses Bengali to sarvam-30b, 1.7973 against
1.6836 fertility. Reading the complete Bengali row rather than the best competitor removed
the premise.

| tokenizer | vocab | Bengali fertility | vs v1.2 |
|---|---:|---:|---:|
| **v1.2** | 64,000 | **1.7973** | reference |
| sarvam-1 | 68,096 | 2.0652 | +14.90% |
| sarvam-30b | 262,144 | 1.6836 | -6.33% |
| Krutrim-2 | 131,072 | 2.9267 | +62.84% |
| Qwen3-14B | 151,670 | 7.1165 | +295.94% |

At a comparable vocabulary budget v1.2 beats sarvam-1 on Bengali by 12.97 percent, its
third-largest margin of the six scripts. Bengali is not a weak script for v1.2. The loss is
only to a tokenizer with 4.1 times the budget.

The question that remained, and the one this file answers, is whether v1.2's behaviour
depends on the Unicode normalization form of its input.

## Map coverage

Entries in `akshara_tokenizer_v1_2.map.json`, attributed by the first Indic codepoint in
each entry. Total 14,601.

| script | entries |
|---|---:|
| telugu | 4,008 |
| kannada | 3,314 |
| devanagari | 3,090 |
| **bengali** | **2,312** |
| gurmukhi | 961 |
| other | 459 |
| tamil | 370 |
| gujarati | 43 |
| malayalam | 36 |
| oriya | 8 |

Bengali at 2,312 is confirmed.

Coverage over FLORES-200 devtest. An akshara not in the map is passed to SentencePiece as
raw text and split at sub-akshara level. Whitespace-only units are excluded from these
counts: the space is not a map entry by design, because SentencePiece handles word
boundaries itself, and counting it as a fall-through would report occurrence-weighted
coverage as roughly 78 percent when the space alone is over 20 percent of all segmented
units.

| script | distinct aksharas | in map | falling through | in map | fall-through, occurrence weighted |
|---|---:|---:|---:|---:|---:|
| bengali | 1,149 | 1,112 | 37 | 96.78% | 0.0799% |
| kannada | 1,357 | 1,296 | 61 | 95.50% | 0.1154% |
| telugu | 1,446 | 1,409 | 37 | 97.44% | 0.0676% |

Coverage is not the problem. Bengali sits between the two controls on both measures, and by
occurrence more than 99.9 percent of aksharas are mapped in all three scripts.

## Normalization robustness

Fertility, tokens per whitespace word, measured per line on FLORES-200 devtest.

| script | as is | NFC | NFD | NFC delta | NFD delta |
|---|---:|---:|---:|---:|---:|
| devanagari | 1.3741 | 1.3668 | 1.3668 | -0.53% | -0.53% |
| gurmukhi | 1.4446 | **1.3619** | 1.3619 | **-5.72%** | -5.72% |
| tamil | 1.9533 | 1.9530 | 2.2330 | -0.01% | **+14.32%** |
| telugu | 2.0006 | 2.0002 | 2.0759 | -0.02% | +3.76% |
| bengali | 1.7973 | **1.6912** | 1.9468 | **-5.90%** | **+8.32%** |
| kannada | 2.0583 | 2.0562 | 2.7501 | -0.10% | **+33.61%** |

Round-trip, `decode(encode(x)) == x`, out of 1,012 lines per script.

| script | as is | NFC | NFD |
|---|---:|---:|---:|
| devanagari | 1012 | 1012 | 1012 |
| gurmukhi | 1012 | 1012 | 1012 |
| tamil | 1012 | 1012 | 1012 |
| telugu | 1012 | 1012 | 1012 |
| bengali | 1012 | 1012 | 1012 |
| kannada | 1012 | 1012 | 1012 |

**Round-trip is perfect in all eighteen cells.** Whatever form the input arrives in, v1.2
returns it byte-identical. Normalization form has no effect on losslessness.

**Fertility is a different story, and it is normalization dependent.**

### Map entries by normalization stability

| script | entries | NFC-unstable | NFD-unstable |
|---|---:|---:|---:|
| devanagari | 3,090 | 8 | 5 |
| gurmukhi | 961 | 4 | 4 |
| tamil | 370 | 4 | 65 |
| telugu | 4,008 | 0 | 170 |
| bengali | 2,312 | 2 | 229 |
| kannada | 3,314 | 0 | 752 |
| other | 459 | 0 | 95 |
| **total** | **14,601** | **18** | **1,321** |

### The map holds both forms of fifteen characters

Fifteen distinct pairs, where the map contains a character in one form and the same
character in its canonically equivalent other form as a separate entry.

| script | pairs |
|---|---:|
| devanagari | 5 |
| tamil | 4 |
| gurmukhi | 4 |
| bengali | 2 |

Examples:

- `ড়` U+09DC and `ড়` U+09A1 U+09BC (Bengali)
- `য়` U+09DF and `য়` U+09AF U+09BC (Bengali)
- `ਸ਼` U+0A36 and `ਸ਼` U+0A38 U+0A3C (Gurmukhi)
- `தொ` U+0BA4 U+0BCA and `தொ` U+0BA4 U+0BC6 U+0BBE (Tamil)

This consumes 15 redundant slots out of 64,000, which is 0.023 percent. The slot cost is
negligible. The cost that matters is that the two forms are separate private-use symbols to
the SentencePiece unigram model, so they carry separate and unequal probabilities. Whichever
form was rarer in the training corpus tokenizes worse.

### Which form dominates each eval file

Lines out of 1,012 that are already in each form.

| script | == NFC | == NFD | neither | dominant |
|---|---:|---:|---:|---|
| devanagari | 919 | 918 | 93 | NFC |
| gurmukhi | 439 | 439 | 573 | tie |
| tamil | 1,010 | 239 | 2 | NFC |
| telugu | 1,011 | 538 | 0 | NFC |
| bengali | 403 | 140 | 609 | NFC |
| kannada | 1,005 | 44 | 6 | NFC |

Bengali and Gurmukhi are the two scripts where a majority of FLORES lines are in neither
form, because those lines carry precomposed nukta letters that NFC decomposes. Those are
exactly the two scripts where NFC input improves v1.2 fertility by roughly 6 percent.

## Does a user feeding NFD text get worse results

**Round-trip: no.** 1012/1012 on every script under NFD.

**Fertility: yes, materially, on three scripts.** NFD costs Kannada 33.61 percent, Tamil
14.32 percent and Bengali 8.32 percent. That is a documented caveat, not a defect that
changes any competitive standing, because the competitors degrade under NFD as well.

NFD penalty relative to the same tokenizer on as-is text:

| script | v1.2 | sarvam-1 | sarvam-30b |
|---|---:|---:|---:|
| devanagari | -0.53% | -1.07% | -0.04% |
| gurmukhi | -5.72% | -9.34% | -0.53% |
| tamil | +14.32% | +7.78% | +5.42% |
| telugu | +3.76% | +7.62% | +1.95% |
| bengali | +8.32% | -7.44% | +5.80% |
| kannada | +33.61% | +37.91% | +12.97% |

sarvam-30b is the most normalization-stable of the three. v1.2 is more stable than sarvam-1
on Kannada and Telugu, less stable on Tamil and Bengali.

## The Bengali gap is a normalization artifact

Measuring all three tokenizers on the same normalization form removes the gap almost
entirely. v1.2 relative to each competitor, negative meaning v1.2 uses fewer tokens:

| script | vs sarvam-1, as is | vs sarvam-1, NFC | vs sarvam-30b, as is | vs sarvam-30b, NFC |
|---|---:|---:|---:|---:|
| devanagari | -2.00% | -1.46% | -0.85% | -1.32% |
| gurmukhi | -14.15% | -10.72% | -11.43% | -16.05% |
| tamil | -9.96% | -9.96% | -17.74% | -17.74% |
| telugu | -6.52% | -6.49% | -13.99% | -14.00% |
| **bengali** | **-12.97%** | **-6.15%** | **+6.76%** | **+0.27%** |
| kannada | -13.40% | -13.40% | -19.02% | -19.07% |
| **scripts won** | **6/6** | **6/6** | **5/6** | **5/6** |

On NFC-normalized input the Bengali gap to sarvam-30b collapses from 6.76 percent to 0.27
percent, which is a tie in practical terms. sarvam-30b barely moves under NFC on Bengali,
+0.19 percent, so it already handles both encodings equivalently. v1.2 gains 5.90 percent.
Nearly the whole gap was v1.2 paying for the precomposed nukta forms that dominate the
FLORES Bengali text.

Under NFD, Bengali is the one cell where v1.2 loses to the budget-matched sarvam-1, by 1.85
percent. That is v1.2's genuinely weakest result and it is worth stating plainly.

This is the same mechanism previously recorded for Gurmukhi. It is not Bengali-specific and
it is not a coverage failure.

## Verdict

Nothing about Bengali needs explaining as a Bengali problem. Budget-matched, v1.2 wins
Bengali by 12.97 percent as is and 6.15 percent on NFC. The loss to sarvam-30b is 4.1 times
the vocabulary budget plus a normalization mismatch, and normalizing the input removes the
second term entirely.

What is left is a general property, stated as a caveat rather than a bug:

1. Round-trip is normalization-independent and always exact. No caveat needed.
2. Fertility depends on the input's normalization form. NFC is the better form for v1.2 on
   every script measured. NFD costs up to 33.61 percent on Kannada.
3. Fifteen characters occupy two slots each because both canonical forms are mapped. The
   slot cost is negligible at 0.023 percent of vocabulary. The probability split is what
   costs fertility.

### Is Bengali-targeted work worth doing

No. A Bengali-targeted fix would be aimed at a gap that budget-matched measurement says does
not exist.

The change worth considering is not Bengali-specific and not a retrain. Aliasing the fifteen
duplicated-form pairs to a single private-use symbol at map level would let both encodings
share one probability, which is what recovers the roughly 6 percent that Bengali and
Gurmukhi currently lose on precomposed input. Estimated cost is 15 slots recovered out of
64,000, which is immaterial, and the work is a map edit plus a round-trip re-verification
rather than a corpus rebuild. It has a real tradeoff: aliasing means the decoder must pick
one output form, so byte-exact round-trip would be lost for whichever form is not chosen.
Given that exact reconstruction is the property that distinguishes this tokenizer from
Qwen3, that tradeoff should not be made casually. It is recorded here as an option, not a
recommendation.

The cheaper and safer alternative is to document that NFC input gives the best fertility and
leave the encoder alone.

## Reproduce

```
python3 diagnose_bengali.py
```

Reads `eval_<script>.txt` (FLORES-200 devtest, supplied locally, see `manifest.md`) and the
competitor tokenizer files. Writes `diagnose_bengali_out.json` with full-precision
fertilities. Competitor tokenizers are loaded with `no_padding()` and `no_truncation()`,
without which a checkpoint that bakes `padding: Fixed 2048` into `tokenizer.json` returns
2,048 ids per encode.

The as-is column reproduces the published figures in `results_competitor_comparison.md`
exactly at full precision.

| artifact | sha256 |
|---|---|
| `akshara_tokenizer_v1_2.model` | `02161e9f865eae3e083d3ccb121ea46e242e32ee115052a029afbf341a4d294d` |
| `akshara_tokenizer_v1_2.map.json` | `5653f2cf29e8bcf456877851a71e3a4ebf254cee1129ecdca4a4120b5ef9d160` |
