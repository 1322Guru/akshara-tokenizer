# IYRA Akshara Tokenizer (IAT)

Linguistically-correct tokenization for Brahmic (Indic) scripts. It has two layers:
a rule-based Akshara segmenter that never splits an orthographic syllable, and a
trained SentencePiece model on top of it. Version 1.2 makes the model layer lossless:
`decode(encode(text))` returns the original text, byte for byte.

Against sarvam-1, the closest Indic-specific tokenizer by vocabulary budget, v1.2 uses
fewer tokens on all six supported scripts. See Fertility below.

## Supported Scripts

Rule-based segmentation covers six scripts:

| Script     | Languages                |
|------------|--------------------------|
| Devanagari | Hindi, Sanskrit, Marathi |
| Gurmukhi   | Punjabi                  |
| Tamil      | Tamil                    |
| Telugu     | Telugu                   |
| Bengali    | Bengali                  |
| Kannada    | Kannada                  |

## Why Akshara instead of BPE?

Byte-level BPE tokenizers split Brahmic text mid-character. A conjunct such as
ज्ञा, or a consonant plus vowel sign such as ਪੰ, is one orthographic syllable
(one Akshara), but BPE sees only UTF-8 bytes and cuts wherever its merges fall.
Captured output below: the same strings through the Qwen3-14B tokenizer and
through this tokenizer's segmenter. Each BPE token is decoded independently; a
`�` is a token that holds only a fragment of one character's bytes.

| Input | Qwen3-14B BPE tokens | Akshara segments |
|-------|----------------------|------------------|
| ज्ञान (Hindi) | `['ज', '्�', '�', 'ा�', '�']` (5 tokens) | `['ज्ञा', 'न']` (2 units) |
| ਪੰਜਾਬ (Punjabi) | `['ਪ', '�', '�', 'ਜ', '�', '�', 'ਬ']` (7 tokens) | `['ਪੰ', 'ਜਾ', 'ਬ']` (3 units) |
| நியாயம் (Tamil) | `['�', '�', 'ி�', '�', '�', '�', 'ய', 'ம', '்']` (9 tokens) | `['நி', 'யா', 'ய', 'ம்']` (4 units) |

The rule-based segmenter never splits an Akshara: that guarantee is exact, for
every input. In v1.2 the model layer is exact for covered aksharas too, and by a
different mechanism than v1.1. Before SentencePiece sees the text, each Akshara the
map covers is replaced by a single private-use codepoint, so no token boundary can
fall inside a covered Akshara: the split is structurally impossible, not merely
improbable. v1.1's guarantee was statistical, since aksharas too rare for its
vocabulary decomposed into sub-pieces. The residual 0.1109 percent of aksharas that
still split on FLORES-200 devtest are exactly the tail the coverage trim dropped
from the 14,601-entry map, which pass through as literal text; this is a coverage-trim
tail, not vocabulary pressure. Per-script split rates run 0.00 to 0.33 percent (see
`benchmark_2026_07/results_v1_2.md`).

## Round-trip is lossless (new in v1.2)

`decode(encode(text))` is byte-identical, reconstructed from the id stream alone with
no side channel. Verified on a 20-string probe set covering the six scripts, mixed
script, nukta forms, conjuncts, and whitespace edges (20 of 20), and on 1,750
FLORES-200 devtest lines, 250 each from the six Indic scripts and English
(1,750 of 1,750). Neither v1.1 nor the earlier v1 model could round-trip at all: their
pipeline space-joins aksharas and the model normalizes whitespace.

## Pipeline

Two layers: a rule-based Akshara segmenter (pure Unicode rules, no model), then the
trained SentencePiece model over the mapped sequence. One real example end to end,
with the actual ids from the shipped 64,000-piece v1.2 model:

```
Unicode text     "न्याय दर्शन"
       |
rule-based akshara segmenter
       |
akshara sequence ['न्या', 'य', ' ', 'द', 'र्श', 'न']
       |
each akshara mapped to one private-use codepoint (internal), then
SentencePiece (64k vocab, byte_fallback)
       |
pieces           ['न्या', 'य', '▁दर्शन']
token ids        [7645, 531, 7572]
       |
decode(ids)      "न्याय दर्शन"   (byte-identical)
```

`दर्शन` (three aksharas द, र्श, न, with its leading space) is a single token: v1.2
learns pieces that span whole aksharas. 45,274 of the 64,000 vocabulary pieces cover
two or more aksharas.

## Model

This release bundles one trained SentencePiece model (byte_fallback enabled):

| Model | Vocab | Trained scripts | In 1.2.0 package | File |
|-------|------:|-----------------|------------------|------|
| v1.2 (six-script) | 64,000 | all six | yes | `akshara_tokenizer/model/akshara_tokenizer_v1_2.model` and `.map.json` |
| v1.1 (six-script) | 16,000 | all six | no | `akshara_tokenizer/model/akshara_tokenizer_v1_1.model` |

The v1.2 ids are not decodable without the mapping table. Each piece is built from
private-use codepoints; the map (`akshara_tokenizer_v1_2.map.json`) translates those
back to aksharas. The map ships next to the model and is bound to it by sha256, so
`load()` refuses a mismatched pair. Do not store ids without the matching model and map.

The v1.1 model file remains in the repository and on HuggingFace but is not bundled in
the 1.2.0 wheel; see Versions and compatibility below.

## Fertility (verified)

FLORES-200 devtest, tokens per whitespace word (lower is better). Numbers from
`benchmark_2026_07/results_v1_2.md`, reproducible with
`benchmark_2026_07/run_fertility_v1_2.py`.

| Script (language)  | v1.2 (64k) | v1.1 (16k) | Qwen3-14B |
|--------------------|-----------:|-----------:|----------:|
| Devanagari (Hindi) | 1.374      | 2.451      | 4.757     |
| Gurmukhi (Punjabi) | 1.445      | 2.684      | 7.758     |
| Tamil (Tamil)      | 1.953      | 5.007      | 10.064    |
| Telugu (Telugu)    | 2.001      | 3.710      | 11.406    |
| Bengali (Bengali)  | 1.797      | 3.384      | 7.117     |
| Kannada (Kannada)  | 2.058      | 4.166      | 11.876    |
| Overall (six Indic)| 1.717      | 3.411      | 8.398     |
| English (info)     | 2.151      | 5.084      | 1.261     |

![Fertility by script on FLORES-200 devtest, AksharaTokenizer v1.2 vs v1.1 vs Qwen3-14B](https://raw.githubusercontent.com/1322Guru/akshara-tokenizer/v1.2/assets/fertility_v1_2.svg)

v1.2 roughly halves v1.1's token count on every Indic script and stays far below
Qwen3-14B. On English, Qwen3 is more efficient, as expected for an English-centric
byte-level BPE. Byte-fallback under v1.2 is near zero on all six scripts (0.00 to 0.04
percent).

### Against Indic-specific tokenizers

Qwen3-14B is a general multilingual BPE and a weak baseline for an Indic claim. The
comparison that matters is against tokenizers built for Indian languages. Same FLORES-200
devtest, 1,012 lines per script, tokens per whitespace word.

| Script     | v1.2 (64k) | sarvam-1 (68k) | sarvam-30b (262k) | Krutrim-2 (131k) |
|------------|-----------:|---------------:|------------------:|-----------------:|
| Devanagari | **1.374**  | 1.402          | 1.386             | 1.950            |
| Gurmukhi   | **1.445**  | 1.683          | 1.631             | 3.187            |
| Tamil      | **1.953**  | 2.169          | 2.374             | 3.614            |
| Telugu     | **2.001**  | 2.140          | 2.326             | 3.714            |
| Bengali    | 1.797      | 2.065          | **1.684**         | 2.927            |
| Kannada    | **2.058**  | 2.377          | 2.542             | 3.820            |

Budget-matched against sarvam-1 (68,096 slots, the closest budget to v1.2's 64,000),
v1.2 uses fewer tokens on all six scripts: Devanagari -2.00, Gurmukhi -14.15, Tamil
-9.96, Telugu -6.52, Bengali -12.97, Kannada -13.40 percent.

Against sarvam-30b (262,144 slots, 4.1x the budget), v1.2 wins five of six: Devanagari
-0.85, Gurmukhi -11.43, Tamil -17.74, Telugu -13.99, Bengali +6.76, Kannada -19.02
percent.

**One caveat, stated plainly: sarvam and Krutrim are full LLM tokenizers carrying
English, code and multilingual coverage in one vocabulary, while v1.2 spends 92.25
percent of its 64,000 slots on Indic aksharas. A native-script win therefore partly
reflects that specialisation, not engineering alone.**

### Round-trip across tokenizers

Byte-identical `decode(encode(x))` out of 1,012 lines per script.

| Script     | v1.2 | Qwen3-14B | sarvam-1 |
|------------|-----:|----------:|---------:|
| Devanagari | 1012 | 919       | 1007     |
| Gurmukhi   | 1012 | 439       | 1012     |
| Tamil      | 1012 | 1010      | 1012     |
| Telugu     | 1012 | 1011      | 1001     |
| Bengali    | 1012 | 403       | 1012     |
| Kannada    | 1012 | 1005      | 999      |

Qwen3's shortfall is not data loss. Qwen3 applies Unicode NFC normalization inside its
tokenizer, so for text containing canonical-decomposition singletons, mainly nukta
characters, the output is canonically equivalent to the input and renders identically
but is not byte-identical. That is a reasonable design choice, verified against stock
`Qwen/Qwen3-14B`. The tradeoff is explicit: NFC gives canonicalization, byte-preservation
gives exact reconstruction. This tokenizer chooses the latter.

### Latin and romanized input

This tokenizer is built for native Brahmic script and the numbers above reflect that. On
Latin-script input the advantage inverts, and this is a design consequence rather than a
bug: 92.25 percent of the vocabulary is Indic aksharas, leaving 2,251 slots (3.52 percent)
for Latin pieces at a mean length of 3.44 characters.

On Dakshina human romanizations, 600 matched sentence pairs per language, v1.2 uses more
tokens than Qwen3-14B: romanized Hindi +23.4, Punjabi +16.0, Tamil +12.8 percent.

On code-switched Hinglish, 600 human-written sentences, tokens per whitespace word:

| Tokenizer  | vocab   | Hinglish |
|------------|--------:|---------:|
| sarvam-30b | 262,144 | 1.448    |
| Krutrim-2  | 131,072 | 1.696    |
| Qwen3-14B  | 151,670 | 1.733    |
| sarvam-1   |  68,096 | 2.261    |
| v1.2       |  64,000 | 2.377    |

The ordering tracks vocabulary size closely, which suggests a budget constraint rather
than a defect: at 64,000 slots, covering six Brahmic scripts at akshara granularity and
covering Latin well are competing demands. The only competitor at a comparable budget,
sarvam-1, is 4.9 percent better on Hinglish while using more tokens than v1.2 on all six
native scripts and on all three romanized languages.

If your workload is predominantly romanized or code-switched Latin text, a large
general-purpose tokenizer will serve you better. If it is native script, this one will
not.

Detail in `benchmark_2026_07/results_dakshina_romanized.md` and
`results_competitor_comparison.md`.

## Akshara split rate

FLORES-200 devtest, percent of aksharas whose token boundaries fall inside them (lower
is better). Numbers from `benchmark_2026_07/results_v1_2.md`, reproducible with
`benchmark_2026_07/measure_split_v1_2.py`.

| Script     | v1.2 (64k) | v1.1 (16k) |
|------------|-----------:|-----------:|
| Devanagari | 0.0945     | 1.6906     |
| Gurmukhi   | 0.3345     | 0.9348     |
| Tamil      | 0.0000     | 0.1467     |
| Telugu     | 0.0643     | 3.6511     |
| Bengali    | 0.0721     | 1.7465     |
| Kannada    | 0.1154     | 3.6202     |
| Overall    | 0.1109     | 1.8559     |

![Akshara split rate by script for v1.2 vs v1.1](https://raw.githubusercontent.com/1322Guru/akshara-tokenizer/v1.2/assets/split_rate_v1_2.svg)

Both charts are generated from `benchmark_2026_07/results_v1_2_fertility.csv` and
`results_v1_2_split.csv` by `benchmark_2026_07/make_charts_v1_2.py`, so they reproduce
from the shipped data.

## Benchmarks and results

Every number above traces to a results file in this repository:

- `benchmark_2026_07/results_v1_2.md` fertility and split rate against v1.1 and Qwen3
- `benchmark_2026_07/results_competitor_comparison.md` against sarvam-1, sarvam-30b and Krutrim-2
- `benchmark_2026_07/results_bengali_diagnostic.md` normalization robustness
- `benchmark_2026_07/results_qwen_roundtrip_check.md` Qwen3 round-trip verified against stock
- `benchmark_2026_07/results_dakshina_romanized.md` romanized Indic on Dakshina
- `benchmark_2026_07/results_arm_n_normalization.md` whether corpus rebalancing can close the precomposed nukta penalty
- `benchmark_2026_07/groundtruth_20260801/` the scripts and raw output behind the competitor numbers

Evaluation corpora are third-party and are not vendored here. They are referenced by
selection rule and by hash manifest, so the sets are reproducible without redistributing
the text.

## Install

Requires Python >=3.10 (as declared in `pyproject.toml`).

```bash
pip install akshara-tokenizer            # rule-based segmenter only
pip install "akshara-tokenizer[model]"   # includes sentencepiece, needed for the model
```

Or from source:

```bash
git clone https://github.com/1322Guru/akshara-tokenizer
cd akshara-tokenizer
pip install ".[model]"
```

The base install is all you need for `segment_aksharas` and `count_aksharas`. The
`model` extra is needed to encode with the trained SentencePiece model.

## Usage

The trained tokenizer (segment, map, SentencePiece, all hidden behind one class):

```python
from akshara_tokenizer import AksharaTokenizer

tok = AksharaTokenizer.load()               # bundled v1.2 model and map, no path needed

ids = tok.encode("न्याय दर्शन")             # [7645, 531, 7572]
text = tok.decode(ids)                       # "न्याय दर्शन"   (byte-identical)

tok.pieces("ਪੰਜਾਬ")                          # ["ਪੰਜਾਬ"]   readable aksharas, never private-use codepoints

# batch: a list in gives a list of lists out
tok.encode(["न्याय दर्शन", "தமிழ் மொழி"])    # [[7645, 531, 7572], [14049, 5131]]
tok.decode([[7645, 531, 7572], [14049, 5131]])  # ["न्याय दर्शन", "தமிழ் மொழி"]
```

Rule-based segmentation, no model needed (base install):

```python
from akshara_tokenizer import segment_aksharas, count_aksharas

segment_aksharas("ਨਿਆਯ ਦਰਸ਼ਨ")
# ["ਨਿ", "ਆ", "ਯ", " ", "ਦ", "ਰ", "ਸ਼", "ਨ"]

segment_aksharas("ज्ञान")
# ["ज्ञा", "न"]

count_aksharas("ਪੰਜਾਬ")
# 3
```

Input containing private-use codepoints (U+E000 to U+F8FF and the supplementary
private-use planes) is rejected with a `ValueError` that names the offending codepoint
and its index, since those collide with the internal mapping alphabet.

## Akshara Formation Rules

1. C + virama + C forms a single conjunct (Devanagari, Telugu, Bengali, Kannada).
2. C + vowel sign forms one Akshara.
3. C + virama alone is a dead consonant and a complete Akshara.
4. An independent vowel is its own Akshara.
5. Anusvara, visarga, nukta, addak, tippi, bindi, and candrabindu attach to the
   preceding Akshara.
6. Latin letters, digits, and punctuation are one token each.

## Precomposed nukta letters (Gurmukhi and Bengali)

Precomposed nukta letters encode to 2 or 3 pieces rather than 1, because the map holds
their decomposed equivalents: Gurmukhi U+0A36 SHA as U+0A38 followed by U+0A3C, Bengali
U+09DF YYA as U+09AF followed by U+09BC. This costs tokens, never correctness: these
aksharas carry zero byte-fallback and round-trip remains byte-identical. On FLORES-200 it
affects 0.33 percent of Gurmukhi aksharas.

Gurmukhi and Bengali pay the same penalty, and NFC-normalizing the input recovers it:

| Script   | as is  | NFC    | change        |
|----------|-------:|-------:|--------------:|
| Gurmukhi | 1.4446 | 1.3619 | -5.72 percent |
| Bengali  | 1.7973 | 1.6912 | -5.90 percent |

Round-trip is unaffected by normalization form: 1,012 of 1,012 lines in all eighteen
cells, six scripts across as-is, NFC and NFD input.

NFD input goes the other way and costs tokens, up to 33.61 percent on Kannada. That is
not specific to this tokenizer: sarvam-1 degrades 37.91 percent on the same input, so it
is a general Brahmic-NFD effect. Under NFD, Bengali is the single cell where v1.2 loses
to the budget-matched sarvam-1, by 1.85 percent.

Corpus rebalancing was tested as an alternative at three levels and recovers at most 41.7
percent of the Gurmukhi penalty while degrading other scripts, so the NFC recommendation
above is a measured conclusion rather than an untested workaround. See
`benchmark_2026_07/results_arm_n_normalization.md`.

Detail in `benchmark_2026_07/results_bengali_diagnostic.md`.

## Versions and compatibility

v1.1 and v1.2 produce different, incompatible id streams. Nothing in the API records
which model produced a stream, so decoding v1.1 ids with the v1.2 model returns silent
garbage rather than an error. If you already have a corpus tokenized with v1.1, pin
`akshara-tokenizer==1.1.0` and keep using it rather than upgrading in place.

The v1.1 model file is present in this repository
(`akshara_tokenizer/model/akshara_tokenizer_v1_1.model`) and on HuggingFace, but is not
bundled in the 1.2.0 package. To install a build that includes it, pin
`akshara-tokenizer==1.1.0`. v1.1 is available three ways:

- PyPI: `pip install "akshara-tokenizer==1.1.0"`
- git tag `v1.1`: https://github.com/1322Guru/akshara-tokenizer/tree/v1.1
- HuggingFace: https://huggingface.co/GursimranSinghBasra/akshara-tokenizer

## Run Tests

pytest is not part of the base install; get it via the dev extra, then run the suite:

```bash
pip install ".[dev,model]"
python -m pytest tests/ -v
```

## Script-level Notes

| Script     | Conjuncts | Notes |
|------------|-----------|-------|
| Devanagari | Yes | Standard C + virama + C conjuncts |
| Gurmukhi   | No  | Virama creates dead consonants; addak doubles the next consonant |
| Tamil      | No  | Pulli always creates a dead consonant |
| Telugu     | Yes | Conjuncts via virama |
| Bengali    | Yes | Hasanta conjuncts |
| Kannada    | Yes | Conjuncts via virama |

## Direction

Akshara-based segmentation is one instance of a more general idea: tokenizing on the
orthographic units a writing system is built from, rather than on bytes. The same
principle extends to other syllable-block writing systems.

## Patent and Copyright

Patent pending: Indian provisional patent application 202611071450.
Copyright 2026 Gursimran Singh.

## License

Apache License 2.0. See `LICENSE` and `NOTICE`.
