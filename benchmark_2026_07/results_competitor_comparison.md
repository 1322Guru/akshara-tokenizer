# AksharaTokenizer v1.2 against Indic-specific tokenizers (2026-08-02)

Measurement only. No model, package or published artifact was changed. `results_v1_2.md`,
`run_fertility_v1_2.py` and `run_fertility_dakshina.py` are untouched; this run uses a
separate harness, `run_fertility_competitors.py`.

Earlier benchmarks compared v1.2 only against Qwen3-14B, a general multilingual BPE. That
is a weak baseline for an Indic claim. This run adds three tokenizers built for Indian
languages and asks whether the native-script advantage survives, and whether the
code-switching penalty found on 28 July is specific to v1.2 or general.

## A necessary caveat, stated once

**Sarvam and Krutrim are full LLM tokenizers carrying English, code and multilingual
coverage in one vocabulary, while v1.2 spends 92.25 percent of its 64,000 slots on Indic
aksharas. A native-script win therefore partly reflects specialisation rather than
engineering alone.** The comparison is still worth making, because it is the comparison a
reader will make, but it is not like for like.

### Vocabulary classifier

An earlier version of this file published **91.94 percent** for the Indic share. That figure
could not be reproduced under thirteen candidate classification rules, and no derivation for
it was recorded anywhere in this repository. **It is superseded by 92.25 percent**, measured
under the rule stated below so the number is checkable rather than asserted.

> Decode each vocabulary piece back through the PUA map, strip the SentencePiece meta symbol
> U+2581, then classify by **first match in this order**: `special` (`<unk>`, `<s>`, `</s>`,
> `<pad>`), `byte_fallback` (matches `<0xXX>`), `indic` (decoded text contains at least one
> codepoint in U+0900 to U+0D7F), `latin` (no Indic, contains at least one ASCII letter),
> `digit` (no Indic and no ASCII letter, contains a digit), `other` (everything else).
> The denominator is always the full 64,000 slots. A piece mixing Indic and Latin counts as
> `indic`, since only Indic text can use that slot.

Applied to the shipped v1.2 model:

| bucket | pieces | share |
|---|---:|---:|
| indic | 59,041 | 92.25% |
| latin | 2,251 | 3.52% (mean length 3.44 characters) |
| other | 1,926 | 3.01% |
| digit | 522 | 0.82% |
| byte_fallback | 256 | 0.40% |
| special | 4 | 0.01% |
| **total** | **64,000** | **100%** |

## Tokenizers

| tokenizer | vocab | kind | source |
|---|---:|---|---|
| AksharaTokenizer v1.2 | 64,000 | Akshara-mapped SentencePiece | this repo |
| sarvam-1 | 68,096 | Llama-style SentencePiece BPE | `sarvamai/sarvam-1` |
| sarvam-30b | 262,144 | byte-level BPE | `sarvamai/sarvam-30b` |
| Krutrim-2-instruct | 131,072 | byte-level BPE | `krutrim-ai-labs/Krutrim-2-instruct` |
| Qwen3-14B | 151,670 | byte-level BPE | local fine-tune checkpoint |

Tokenizer files only were downloaded, 59 MB total, zero weight files. None of the three
competitor repos is gated and no licence was accepted.

## Method

`add_special_tokens=False`, `no_padding()`, `no_truncation()`, encode per line. Fertility is
tokens per whitespace word; `t/100c` is tokens per 100 characters. Byte-fallback is reported
only for v1.2, which is SentencePiece and exposes `<0xXX>` pieces; the others are
byte-level BPE with no fallback pieces by construction, so the column is **n/a**, never a
measured zero.

Every tokenizer was sanity-checked on a short mixed string before the full run: no leading
special ids, no 2,048-token outputs, all round-trip. The local Qwen checkpoint bakes padding
and truncation to 2048 into `tokenizer.json` and was the only one needing correction.

**Validation gate.** Before any competitor was measured, v1.2 was re-measured on the six
native scripts and checked against the published `results_v1_2.md` figures. All seven match
to within 0.0004:

| | devanagari | gurmukhi | tamil | telugu | bengali | kannada | overall |
|---|---:|---:|---:|---:|---:|---:|---:|
| measured | 1.3741 | 1.4446 | 1.9533 | 2.0006 | 1.7973 | 2.0583 | 1.7168 |
| published | 1.374 | 1.445 | 1.953 | 2.001 | 1.797 | 2.058 | 1.717 |

**Table 1 uses the full 1,012-line FLORES-200 devtest, the same subset as
`results_v1_2.md`. It therefore does not match the 200-line spot checks reported on 28 July
and 1 August.** Those were smaller samples of the same data.

## Table 1: native script, FLORES-200 devtest, n=1,012 per script

Fertility (tokens per word), lower is better. Round-trip is byte-identical
`decode(encode(x))` out of 1,012.

| script | v1.2 (64k) | sarvam-1 (68k) | sarvam-30b (262k) | Krutrim-2 (131k) | Qwen3-14B (152k) |
|---|---:|---:|---:|---:|---:|
| Devanagari | **1.374** | 1.402 | 1.386 | 1.950 | 4.757 |
| Gurmukhi | **1.445** | 1.683 | 1.631 | 3.187 | 7.758 |
| Tamil | **1.953** | 2.169 | 2.374 | 3.614 | 10.064 |
| Telugu | **2.001** | 2.140 | 2.326 | 3.714 | 11.406 |
| Bengali | 1.797 | 2.065 | **1.684** | 2.927 | 7.116 |
| Kannada | **2.058** | 2.377 | 2.542 | 3.820 | 11.876 |

Byte-fallback, v1.2 only: Devanagari 0.017, Gurmukhi 0.040, Tamil 0.000, Telugu 0.018,
Bengali 0.000, Kannada 0.009 percent. All others n/a (byte-level BPE).

Tokens per 100 characters, same run. This is included for cross-script comparison only:
words differ in length across scripts, so tokens per word is not comparable between rows,
whereas tokens per 100 characters is. **It gives identical tokenizer-to-tokenizer ratios
within a row**, so it changes no conclusion drawn from the fertility table above.

| script | v1.2 (64k) | sarvam-1 (68k) | sarvam-30b (262k) | Krutrim-2 (131k) | Qwen3-14B (152k) |
|---|---:|---:|---:|---:|---:|
| Devanagari | **26.881** | 27.429 | 27.111 | 38.146 | 93.053 |
| Gurmukhi | **28.048** | 32.670 | 31.668 | 61.884 | 150.637 |
| Tamil | **21.258** | 23.609 | 25.841 | 39.328 | 109.534 |
| Telugu | **25.573** | 27.357 | 29.735 | 47.475 | 145.802 |
| Bengali | 27.169 | 31.217 | **25.449** | 44.241 | 107.573 |
| Kannada | **23.989** | 27.700 | 29.625 | 44.516 | 138.417 |

Round-trip: **v1.2 is 1,012/1,012 on all six scripts.** sarvam-30b and Krutrim-2 are also
perfect. sarvam-1 loses a few lines (Devanagari 1,007, Telugu 1,001, Kannada 999), so
imperfect round-trip is not unique to Qwen.

Qwen3-14B round-trip, out of 1,012 per script: Devanagari 919, Gurmukhi 439, Tamil 1,010,
Telugu 1,011, Bengali 403, Kannada 1,005.

Qwen3-14B applies Unicode NFC normalization inside its tokenizer. For text containing
canonical-decomposition singletons, mainly nukta characters in Devanagari, Gurmukhi and
Bengali, `decode(encode(x))` returns text that is canonically equivalent to the input and
renders identically, but is not byte-identical. This is stock Qwen3 behaviour, verified
against `Qwen/Qwen3-14B`, and it is a reasonable design choice. AksharaTokenizer instead
preserves the input encoding, so `decode(encode(x))` is byte-identical. The tradeoff is
explicit: NFC gives canonicalization, byte-preservation gives exact reconstruction. Full
verification in `results_qwen_roundtrip_check.md`.

## Table 2: romanized Indic, Dakshina human romanizations, n=600 per language

The same 600 matched pairs used in `results_dakshina_romanized.md`, reused verbatim.

| language | v1.2 (64k) | sarvam-1 (68k) | sarvam-30b (262k) | Krutrim-2 (131k) | Qwen3-14B (152k) |
|---|---:|---:|---:|---:|---:|
| romanized Hindi | 2.574 | 2.593 | **1.768** | 2.013 | 2.086 |
| romanized Punjabi | 2.774 | 2.915 | **2.050** | 2.287 | 2.392 |
| romanized Tamil | 4.537 | 4.709 | **3.551** | 3.877 | 4.021 |

v1.2 byte-fallback: 0.000, 0.019, 0.000 percent. Round-trip 600/600 for every tokenizer.

Note that **v1.2 beats sarvam-1 on all three romanized languages**, and sarvam-1 has a
slightly larger vocabulary. The tokenizers that beat v1.2 here are the ones with two to four
times the vocabulary budget.

## Table 3: code-switched and English

Two Hinglish sets are reported separately so the 28 July figure stays traceable.
`hinglish_cmu_28jul` is the original 200 from `festvox/cmu_hinglish_dog`.
`hinglish_findnitai_human` is 600 from `findnitai/english-to-hinglish`, filtered to
`source == 1`. Every row in the sampled prefix was already `source == 1`, so that filter
excluded nothing rather than removing synthetic data.

| category | n | v1.2 (64k) | sarvam-1 (68k) | sarvam-30b (262k) | Krutrim-2 (131k) | Qwen3-14B (152k) |
|---|---:|---:|---:|---:|---:|---:|
| Hinglish, CMU (28 Jul) | 200 | 2.340 | 2.167 | **1.375** | 1.618 | 1.645 |
| Hinglish, findnitai human | 600 | 2.377 | 2.261 | **1.448** | 1.696 | 1.733 |
| English, FLORES | 200 | 2.182 | 1.494 | **1.277** | 1.304 | 1.289 |

v1.2 byte-fallback: 0.000, 0.000, 0.125 percent. Round-trip is perfect for every tokenizer
on all three categories.

The two Hinglish sets agree closely for every tokenizer, within 0.09 fertility, despite
different provenance and a 3x size difference. Their English-function-word share is 7.02 and
6.13 percent respectively, against 1.82 percent for romanized Hindi, so both are genuinely
code-switched rather than merely romanized.

## Q1. Does v1.2 still lead on native script against Indic-specific tokenizers?

**Yes. Budget-matched, v1.2 wins all six scripts. Against a tokenizer with 4.1 times the
vocabulary it wins five of six.**

Comparing against the best competitor per script mixes vocabulary budgets from 68k to 262k
and understates the result, so the comparison is split into a budget-matched primary and a
larger-budget secondary.

### Primary: budget-matched, v1.2 (64k) against sarvam-1 (68k)

| script | v1.2 | sarvam-1 | v1.2 better by |
|---|---:|---:|---:|
| Gurmukhi | 1.445 | 1.683 | **14.15%** |
| Kannada | 2.058 | 2.377 | **13.40%** |
| Bengali | 1.797 | 2.065 | **12.97%** |
| Tamil | 1.953 | 2.169 | **9.96%** |
| Telugu | 2.001 | 2.140 | **6.52%** |
| Devanagari | 1.374 | 1.402 | 2.00% |

**v1.2 wins 6 of 6, including Bengali.**

### Secondary: v1.2 (64k) against sarvam-30b (262k, 4.1x the budget)

| script | v1.2 | sarvam-30b | margin |
|---|---:|---:|---|
| Kannada | 2.058 | 2.542 | **v1.2 better by 19.02%** |
| Tamil | 1.953 | 2.374 | **v1.2 better by 17.74%** |
| Telugu | 2.001 | 2.326 | **v1.2 better by 13.99%** |
| Gurmukhi | 1.445 | 1.631 | **v1.2 better by 11.43%** |
| Devanagari | 1.374 | 1.386 | v1.2 better by 0.85% |
| Bengali | 1.797 | 1.684 | **sarvam-30b better by 6.76%** |

**v1.2 wins 5 of 6, losing Bengali by 6.76 percent.**

### Context: sarvam-30b against sarvam-1, same vendor, 3.85x the budget

| script | sarvam-1 | sarvam-30b | effect of 3.85x vocabulary |
|---|---:|---:|---|
| Bengali | 2.065 | 1.684 | **18.48% better** |
| Gurmukhi | 1.683 | 1.631 | 3.07% better |
| Devanagari | 1.402 | 1.386 | 1.16% better |
| Kannada | 2.377 | 2.542 | 6.95% **worse** |
| Telugu | 2.140 | 2.326 | 8.69% **worse** |
| Tamil | 2.169 | 2.374 | 9.45% **worse** |

Quadrupling the vocabulary buys Sarvam a large gain on Bengali, close to nothing on
Devanagari and Gurmukhi, and an outright regression on Kannada, Telugu and Tamil. Their
incremental vocabulary appears disproportionately Bengali-weighted, which is the more
economical explanation for the one script v1.2 loses.

### The two close calls

Checked with a paired bootstrap, 2,000 resamples over the 1,012 lines:

- Devanagari, v1.2 minus sarvam-30b: **-0.0118, 95% CI [-0.0192, -0.0042]**. The interval
  excludes zero, so v1.2 is genuinely ahead, but by roughly one token per 85 words. This is
  a real but operationally negligible difference and should not be presented as a lead.
- Bengali, v1.2 minus sarvam-30b: **+0.1138, 95% CI [+0.1023, +0.1256]**. Clearly separable.
  **On as-is FLORES text the Bengali loss is real, not sampling noise.**

The Bengali loss was investigated in `results_bengali_diagnostic.md`. It is not a coverage
failure: 96.78 percent of distinct Bengali aksharas in the eval text are mapped and more
than 99.9 percent by occurrence. It is largely a normalization mismatch. FLORES Bengali is
predominantly not in NFC, only 403 of 1,012 lines, because it carries precomposed nukta
letters. Measuring all three tokenizers on NFC-normalized input closes the gap to sarvam-30b
from 6.76 percent to 0.27 percent, while v1.2's lead over sarvam-1 remains at 6.15 percent.
v1.2 round-trips 1,012/1,012 on all six scripts under as-is, NFC and NFD input alike.

## Q2. Do the competitors also pay a Hinglish penalty?

**Partly. The answer depends on vocabulary budget, and that is the finding that matters for
a v1.3 decision.**

Hinglish fertility on the larger 600-line set, with vocabulary size alongside:

| tokenizer | vocab | Hinglish fertility | vs v1.2 |
|---|---:|---:|---|
| **v1.2** | **64,000** | **2.377** | baseline |
| sarvam-1 | 68,096 | 2.261 | 4.9% better |
| Krutrim-2 | 131,072 | 1.696 | 28.6% better |
| Qwen3-14B | 151,670 | 1.733 | 27.1% better |
| sarvam-30b | 262,144 | 1.448 | 39.1% better |

Ranked by vocabulary, the ordering is almost monotonic. **sarvam-1, the only competitor with
a comparable vocabulary budget at 68k against v1.2's 64k, is only 4.9 percent better on
Hinglish and is worse than v1.2 on all three romanized languages and all six native
scripts.** The tokenizers that handle code-switching cleanly are the ones spending 131k to
262k slots.

So the code-switching penalty is not unique to v1.2, and it is not obviously an engineering
defect. On this evidence it looks like a vocabulary-budget constraint: at roughly 64k slots,
covering six Brahmic scripts at akshara granularity and covering Latin well appear to be
competing demands.

What this does not settle: whether reallocating some of v1.2's 58,844 Indic slots to Latin
would buy more on Hinglish than it costs on native script. That is a retrain experiment, not
an inference from these numbers. What the numbers do say is that matching sarvam-30b's
Hinglish performance while keeping a 64k vocabulary is not something any tokenizer in this
comparison has demonstrated.

## Where the eval set cannot support a claim

- **Devanagari native.** 0.8 percent apart. Statistically separable but operationally a tie.
  Do not claim a Devanagari lead over sarvam-30b.
- **v1.2 against sarvam-1 on romanized Hindi.** 2.574 against 2.593, 0.7 percent apart on 600
  lines. Not enough to rank them.
- **English at n=200.** The smallest set here. The ordering (sarvam-30b best, v1.2 worst by a
  wide margin) is large enough not to be in doubt, but the precise gaps between the four
  competitors, which span 1.277 to 1.494, rest on 200 lines.
- **Hinglish CMU at n=200** is retained only for traceability with 28 July. The 600-line
  findnitai set should be preferred for any claim, and the two agree closely.

## Reproducibility

Verified 2026-08-02. `run_fertility_competitors.py` regenerates every number in Tables 1, 2
and 3 except the archived category noted below, and reproduces them exactly: all 55
tokenizer-by-category token counts are identical to the original measurement, and all
round-trip counts match.

**One archived category the harness does not regenerate.** `hinglish_cmu_28jul` (n=200,
`festvox/cmu_hinglish_dog`) is retained in Table 3 as a 28 July measurement only. Its
selection came from a paginated API pull that is not deterministically reproducible, and the
corpus text is third-party and deliberately not vendored here, so the harness omits it rather
than emit a number it cannot stand behind. The 600-line `hinglish_findnitai_human` set is
the one to use for any claim; the two agree to within 0.09 fertility for every tokenizer.

### Command

```
python3 build_hinglish_set.py --out /mnt/c/GuruAI-Data/hinglish/hinglish_findnitai_600.json

python3 run_fertility_competitors.py \
    --dakshina-root  /mnt/c/GuruAI-Data/dakshina/dakshina_dataset_v1.0 \
    --competitor-dir /mnt/c/GuruAI-Data/competitor_tokenizers \
    --qwen-tokenizer /mnt/d/GuruAI/models/finetuned/guruai-qwen3-14b-nyaya-1681/tokenizer.json \
    --hinglish-set   /mnt/c/GuruAI-Data/hinglish/hinglish_findnitai_600.json
```

The harness self-checks v1.2 against the published `results_v1_2.md` native figures and
exits non-zero if that gate fails.

### Inputs

| input | path | provenance |
|---|---|---|
| native, 6 scripts | `benchmark_2026_07/eval_<script>.txt` | in repo, 1,012-line FLORES-200 devtest |
| English | `benchmark_2026_07/eval_english.txt`, first 200 lines | in repo |
| romanized, 3 languages | `<dakshina-root>/<L>/romanized/<L>.romanized.rejoined.tsv` | Dakshina v1.0, first 600 rows passing the native-side filter, file order, no shuffle |
| Hinglish, 600 | materialised outside the repo by `build_hinglish_set.py` | `findnitai/english-to-hinglish`, verified against the manifest below before measuring |

No third-party corpus text is stored in this repository. The Hinglish set is described by
`hinglish_findnitai_manifest.json`, which holds per-line and whole-set sha256 hashes, the
row count, the source dataset id and the exact filter rule, but no text. The harness refuses
to emit a Hinglish number if the materialised set does not match that manifest.

Manifest set sha256 `2ba089ba42f5a89b9287a762916a6aaa423c8c839655610d4f70e41830b43e66`,
600 rows.

### Artifact hashes

| artifact | sha256 |
|---|---|
| AksharaTokenizer v1.2 model | `02161e9f865eae3e083d3ccb121ea46e242e32ee115052a029afbf341a4d294d` |
| AksharaTokenizer v1.2 map | `5653f2cf29e8bcf456877851a71e3a4ebf254cee1129ecdca4a4120b5ef9d160` |
| sarvam-1 `tokenizer.json` | `bb5115a36ddb956a4ee0fd534e9870dd69157835622aec9c53062896f883c072` |
| sarvam-30b `tokenizer.json` | `a574ceaaff7c7a8f091179c53fd17ae33567089c099d4ff37d4cb3bc1a87e80e` |
| Krutrim-2-instruct `tokenizer.json` | `b0240ce510f08e6c2041724e9043e33be9d251d1e4a4d94eb68cd47b954b61d2` |
| Qwen3-14B `tokenizer.json` | `856e9e5db667533ed06c0784cb290e397145e502a2897828f7085260a297b7da` |

Only `tokenizer.json` is required from each competitor. No model weights were downloaded.
