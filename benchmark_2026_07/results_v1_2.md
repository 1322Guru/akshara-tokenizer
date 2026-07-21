# AksharaTokenizer v1.2 Stage 4 verification (2026-07-20)

Model: `akshara_tokenizer_v1_2.model`, sha256 `02161e9f865eae3e083d3ccb121ea46e242e32ee115052a029afbf341a4d294d`, vocab 64,000.
It ships as package data with its map `akshara_tokenizer_v1_2.map.json`, which binds to the
model by sha256; `AksharaTokenizer.load()` refuses a mismatched pair.

Eval: FLORES-200 devtest, same `eval_<script>.txt` files and `manifest.md` as the v1.1
benchmark. The fertility and split numbers below regenerate from
`results_v1_2_fertility.csv` and `results_v1_2_split.csv` via `run_fertility_v1_2.py` and
`measure_split_v1_2.py` in this directory.

## Mapping verification, full corpus

All 22,500,000 lines reconstructed, not a sample.

| | |
|---|---|
| lines | 22,500,000 |
| exact reconstruction | 22,499,824 |
| mismatch | 176 |
| exact | 99.999218 % |

Per language mismatches: hi 0, pa 26, ta 58, te 32, bn 51, kn 9. In every language the
mismatch count equals the contaminated-line count exactly, so there are zero mapping errors.

Contamination means the source text itself carries private-use codepoints, which collide
with the internal mapping alphabet and make the line's segmentation ambiguous. Example at
pa:927973, where the source holds a run of U+F020, a codepoint the table also assigns to a
Telugu akshara. The library already refuses such input at encode time via `_guard`, so this
is contained rather than latent.

## The 0.0045 percent unaligned lines from the recovery scan

Not the `max_sentence_length` skips, and not contamination. They were **lines containing tab
characters**. The recovery walk split units on the akshara delimiter and on spaces only, so
a unit such as `'3\tਪੰ'` failed to match. Treating tab as a separator drops clean walk
failures from 131 to 0 over 2.4M lines.

This never corrupted the table: failing lines were skipped, not mislearned, and majority
voting guarded the rest. The full-corpus reconstruction above does not use the walk at all.

Separating the three populations:

| population | count | mechanism |
|---|---:|---|
| tab-bearing lines | about 1,000 | diagnostic walk limitation, no data defect |
| contaminated lines | 176 | private-use codepoints in the source text |
| `max_sentence_length` skips | 13,948 | SentencePiece training filter over the 6M sample, unrelated to the scan |

## Fertility, FLORES-200 devtest

Measured per line. Encoding a whole file at once makes every newline an unmapped unit that
byte-falls-back, which inflates v1.2 byte fallback to about 2.8 percent as a pure artifact
of the 1,012 line breaks. Per-line measurement removes it.

Tokens per whitespace-delimited word:

| script | v1.2 (64k) | v1.1 (16k) | Qwen3-14B |
|---|---:|---:|---:|
| devanagari | **1.374** | 2.451 | 4.757 |
| gurmukhi | **1.445** | 2.684 | 7.758 |
| tamil | **1.953** | 5.007 | 10.064 |
| telugu | **2.001** | 3.710 | 11.406 |
| bengali | **1.797** | 3.384 | 7.117 |
| kannada | **2.058** | 4.166 | 11.876 |
| OVERALL Indic | **1.717** | 3.411 | 8.398 |
| english (info) | 2.151 | 5.084 | **1.261** |

Tokens per akshara:

| script | v1.2 | v1.1 | Qwen3-14B |
|---|---:|---:|---:|
| devanagari | **0.405** | 0.722 | 1.401 |
| gurmukhi | **0.397** | 0.737 | 2.130 |
| tamil | **0.325** | 0.834 | 1.676 |
| telugu | **0.435** | 0.807 | 2.482 |
| bengali | **0.420** | 0.791 | 1.664 |
| kannada | **0.406** | 0.822 | 2.344 |
| OVERALL Indic | **0.395** | 0.785 | 1.933 |

Byte-fallback percent: devanagari 0.017, gurmukhi 0.040, tamil 0.000, telugu 0.018,
bengali 0.000, kannada 0.009, english 0.064. v1.1 for the same files: 0.769, 0.729, 0.021,
0.081, 0.085, 0.358, 0.139.

## Akshara split rate

Definition and method as in the v1.1 measurement. One correction: with
`out_type="immutable_proto"` in sentencepiece 0.2.1, `piece.begin` and `piece.end` are
character offsets, not byte offsets. Spans are therefore computed in characters. Recomputing
the v1.1 column with this method **reproduces the published v1.1 table exactly**, which
validates the method before it is applied to v1.2.

| script | model | aksharas | split | split % | sub-piece | byte-fallback |
|---|---|---:|---:|---:|---:|---:|
| devanagari | v1.2 | 61,398 | 58 | **0.0945** | 56 | 2 |
| devanagari | v1.1 | 61,398 | 1,038 | 1.6906 | 876 | 162 |
| gurmukhi | v1.2 | 68,467 | 229 | **0.3345** | 224 | 5 |
| gurmukhi | v1.1 | 68,467 | 640 | 0.9348 | 470 | 170 |
| tamil | v1.2 | 83,861 | 0 | **0.0000** | 0 | 0 |
| tamil | v1.1 | 83,861 | 123 | 0.1467 | 117 | 6 |
| telugu | v1.2 | 60,639 | 39 | **0.0643** | 37 | 2 |
| telugu | v1.1 | 60,639 | 2,214 | 3.6511 | 2,197 | 17 |
| bengali | v1.2 | 63,842 | 46 | **0.0721** | 46 | 0 |
| bengali | v1.1 | 63,842 | 1,115 | 1.7465 | 1,095 | 20 |
| kannada | v1.2 | 64,996 | 75 | **0.1154** | 74 | 1 |
| kannada | v1.1 | 64,996 | 2,353 | 3.6202 | 2,273 | 80 |
| OVERALL | v1.2 | 403,203 | 447 | **0.1109** | 437 | 10 |
| OVERALL | v1.1 | 403,203 | 7,483 | 1.8559 | 7,028 | 455 |

Mechanism: a kept akshara is a single codepoint in the mapped stream, so no piece boundary
can fall inside it. The residual 437 sub-piece splits are aksharas the Stage 2 coverage trim
dropped, which pass through as literal text and can be covered by more than one piece. The
split rate is therefore a direct readout of the coverage trim, not of vocabulary pressure.

## Round-trip, byte-identical from ids alone

`decode(encode(text)) == text` as raw bytes, reconstructed from ids with no side channel.

| set | result |
|---|---|
| 20-string probe set (six scripts, mixed script, nukta, conjuncts, whitespace edges, tabs, newlines) | **20 / 20** |
| FLORES devtest, 250 lines per script, 7 scripts | **1,750 / 1,750** |

v1.1 and v1 could not do this at all: the published table records "no" for every script,
because the space-join conflates akshara and word boundaries and the model normalizes
whitespace. v1.2 is the first losslessly invertible AksharaTokenizer.

## Multi-akshara pieces

| aksharas per piece | pieces |
|---|---:|
| 0 | 2,167 |
| 1 | 16,303 |
| 2 | 16,740 |
| 3 | 14,673 |
| 4 | 8,570 |
| 5 | 3,286 |
| 6 | 1,191 |
| 7 | 458 |
| 8 | 192 |
| 9 | 88 |
| 10 | 43 |

**45,274 of 64,000 pieces span two or more aksharas**, maximum 14. Byte pieces 256.

This is the structural change. The v1.1 benchmark recorded that under its recipe
SentencePiece could not merge across space-delimited aksharas, capping the achievable
vocabulary near the distinct-akshara count, about 17,145, and declaring 64k infeasible.
Mapping each akshara to one codepoint removes that ceiling: 64k trains cleanly and most of
the vocabulary is genuinely multi-akshara.

## Gurmukhi and Bengali, the two weak spots in the v1.1 sweep

Both improve on every metric.

| metric | script | v1.1 | v1.2 | change |
|---|---|---:|---:|---|
| split % | gurmukhi | 0.9348 | 0.3345 | 2.8x lower |
| byte-fallback % | gurmukhi | 0.729 | 0.040 | 18x lower |
| fertility | gurmukhi | 2.684 | 1.445 | 46 % fewer tokens |
| split % | bengali | 1.7465 | 0.0721 | 24x lower |
| byte-fallback % | bengali | 0.085 | 0.000 | eliminated |
| fertility | bengali | 3.384 | 1.797 | 47 % fewer tokens |

Bengali is now among the cleanest scripts, with zero byte-fallback splits.

Gurmukhi beats v1.1 but remains the weakest of the six in v1.2, at 0.3345 percent against a
0.1109 percent overall. The cause is specific and identified: Gurmukhi nukta forms absent
from the 14,601 map. On FLORES the unmapped Gurmukhi occurrences are ਫ਼ 130, ਸ਼ਿ 53, ਸ਼ਾਂ 44,
ਖ਼ 40 and a tail, about 401 of 94,373 aksharas, 0.42 percent. They still decode exactly, so
this costs tokens rather than correctness.

## required_chars retrain pass (2026-07-20), targeting the Gurmukhi gap

A retrain was run to close the Gurmukhi residual: the FLORES aksharas absent from the map
were decomposed into their 168 constituent characters and added to `required_chars`, with
every other setting identical (unigram, vocab 64,000, character_coverage 1.0,
input_sentence_size 6,000,000). Wall 362.1 s, peak RSS 14,662 MB, model
`akshara_tokenizer_v1_2b.model` sha `fcf8a02d...`.

**It changed nothing.** The retrained vocabulary is identical to v1.2 piece for piece
(64,000 shared, 0 different) despite a distinct model sha, and every Stage 4 metric is
identical to the count: Gurmukhi split 229 in both, overall split 447 in both, per-script
fertility identical to three decimals. Round-trip 1,750 / 1,750.

The reason is that `required_chars` is a no-op under `character_coverage=1.0`. Full coverage
already forces every character present in the sampled corpus into the vocabulary, and all
168 additions were already single-character pieces in v1.2 (168 / 168). `required_chars`
only guards against a character being absent from the 6M sample, which none of these were.

### Root cause of the Gurmukhi gap: a normalization mismatch, not coverage

The absent Gurmukhi aksharas do not byte-fall-back; they already encode with zero byte
fallback, as 2 to 3 sub-pieces. The cause is precomposed versus decomposed forms. FLORES
uses precomposed Gurmukhi nukta letters, U+0A36 SHA, U+0A5E FA, U+0A59 KHHA, while the map
holds their NFC-decomposed equivalents, U+0A38 U+0A3C for SHA and so on. So the visually
identical akshara misses the map by codepoint. Of 401 absent Gurmukhi occurrences, 381 have
their NFC form in the map. The single-codepoint precomposed letters (ਫ਼ ਖ਼ ਗ਼, 172 occurrences)
are covered and do not split; the 224 splits are the ਸ਼ plus vowel combinations, where SHA is
precomposed and its vowel does not merge into one piece.

No retrain on this corpus can fix this, because the fix is at the normalization layer, not
the vocabulary.

### Decision: ship v1.2 as-is (2026-07-20)

v1.2 ships unchanged, with byte-identical round-trip preserved. No NFC normalization and no
map aliasing are added to the library. The alternative, folding precomposed nukta letters to
their decomposed forms at encode time, would drop Gurmukhi split from 0.3345 to about 0.007
percent but would make round-trip NFC-identical rather than byte-identical for
precomposed-nukta input; byte-identity is kept as the stronger contract and the Gurmukhi cost
is accepted.

### Documented behavior: precomposed Gurmukhi nukta letters

Precomposed Gurmukhi nukta letters (U+0A36 SHA, U+0A5E FA, U+0A59 KHHA) encode to 2 or 3
pieces rather than 1, because the map holds their decomposed equivalents (for example SHA as
U+0A38 U+0A3C). This costs tokens, never correctness: these aksharas carry zero byte
fallback and round-trip remains byte-identical. On FLORES this affects 0.33 percent of
Gurmukhi aksharas, the 224 SHA-plus-vowel combinations. Users who prefer efficiency over
byte-identity may NFC-normalize their input before encoding.

## Per-script comparison table for the README

Fertility (tokens per word). v1.2b omitted because it equals v1.2 exactly.

| script | v1.2 | v1.1 (shipped) | Qwen3-14B |
|---|---:|---:|---:|
| devanagari | 1.374 | 2.451 | 4.757 |
| gurmukhi | 1.445 | 2.684 | 7.758 |
| tamil | 1.953 | 5.007 | 10.064 |
| telugu | 2.001 | 3.710 | 11.406 |
| bengali | 1.797 | 3.384 | 7.117 |
| kannada | 2.058 | 4.166 | 11.876 |
| OVERALL Indic | 1.717 | 3.411 | 8.398 |

Akshara split percent (lower is better):

| script | v1.2 | v1.1 (shipped) |
|---|---:|---:|
| devanagari | 0.0945 | 1.6906 |
| gurmukhi | 0.3345 | 0.9348 |
| tamil | 0.0000 | 0.1467 |
| telugu | 0.0643 | 3.6511 |
| bengali | 0.0721 | 1.7465 |
| kannada | 0.1154 | 3.6202 |
| OVERALL | 0.1109 | 1.8559 |

## Verdict

Shipped as the 1.2.0 release. The required_chars retrain does not change the model, so the
original v1.2 (sha `02161e9f...`) is the release model. `akshara_tokenizer_v1_2b.*` was
discarded on 2026-07-20.

Supporting: every metric beats shipped v1.1 on every script; byte-identical round-trip,
which no previous version could do; overall Indic fertility 1.717 against v1.1 3.411 and
Qwen3-14B 8.398; split rate 16.7x lower overall; mapping verified against the full 22.5M
line corpus at 99.999218 percent with all 176 exceptions explained as source contamination.

Not blocking, but should be tracked:
- Gurmukhi nukta forms are missing from the map. Worth a v1.2.1 map extension and retrain if
  Punjabi is a priority surface. Lossless today, just less efficient.
- English fertility 2.151 remains well behind Qwen3-14B 1.261. Expected for an Indic-first
  tokenizer and unchanged in character from v1.1.
- 176 contaminated corpus lines exist. `_guard` already rejects private-use input, so no
  action is required for correctness.
