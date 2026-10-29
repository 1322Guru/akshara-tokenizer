# AksharaTokenizer v1 fertility benchmark (2026-07-13)

## Setup
- Eval corpus: FLORES-200 devtest, 1012 sentences per language (URLs and sha256 in manifest.md). Held out from AksharaTokenizer training (training corpus: AI4Bharat Sangraha "verified", splits hin/pan/tam).
- AksharaTokenizer v1: segmenter `akshara_tokenizer.boundary.segment_aksharas` (submodule commit 1665c23); SentencePiece unigram model `model/akshara_tokenizer_v1.model` (vocab 7000, unk_id 0, byte_fallback=True); sentencepiece 0.2.1. Encode: `sp.encode(' '.join(segment_aksharas(text)))`.
  - Note: `phase2_train.py` requests vocab_size=100000; the shipped model on disk has vocab 7000.
- Qwen3-14B: base `tokenizer.json` from `unsloth/Qwen3-14B` snapshot b8755c0b (vocab 151669 incl. added tokens); tokenizers 0.22.2. Encode: byte-level BPE, add_special_tokens=False.
- Akshara-count denominator (shared by both tokenizers): `count_aksharas(text)` = total segmentation units (aksharas plus spaces/punctuation/Latin, each non-Indic char one unit).
- Deterministic, single pass over each file, no sampling. Raw values (including tokens_per_100char and token counts) in results.csv.

## Coverage
- Rule-based segmenter (`segment_aksharas`) covers 6 scripts: devanagari, gurmukhi, tamil, telugu, bengali, kannada.
- Trained SentencePiece model covers 3 scripts: Hindi (devanagari), Punjabi (gurmukhi), Tamil. Telugu, Bengali, Kannada were not in SP training.

## Section A: trained scripts (Hindi, Punjabi, Tamil)

Fertility (tokens per whitespace-delimited word):

| script (language)  | akshara_v1_sp | qwen3_14b |
|--------------------|--------------:|----------:|
| devanagari (Hindi) | 2.45          | 4.77      |
| gurmukhi (Punjabi) | 2.68          | 7.80      |
| tamil (Tamil)      | 5.01          | 10.06     |

Tokens per akshara:

| script (language)  | akshara_v1_sp | qwen3_14b |
|--------------------|--------------:|----------:|
| devanagari (Hindi) | 0.72          | 1.40      |
| gurmukhi (Punjabi) | 0.74          | 2.14      |
| tamil (Tamil)      | 0.83          | 1.68      |

byte-fallback % (akshara_v1_sp): Hindi 0.77, Punjabi 0.73, Tamil 0.02. Qwen3: na (byte-level BPE, no UNK/byte-fallback).

## Section B: untrained scripts (Telugu, Bengali, Kannada)

AksharaTokenizer v1 SP model was not trained on these scripts; the numbers below show byte-fallback behavior. These numbers are input for a v1.1 training decision, not a release claim.

Fertility (tokens per word):

| script (language) | akshara_v1_sp | qwen3_14b |
|-------------------|--------------:|----------:|
| telugu (Telugu)   | 7.81          | 11.41     |
| bengali (Bengali) | 18.87         | 7.16      |
| kannada (Kannada) | 13.26         | 11.88     |

Tokens per akshara:

| script (language) | akshara_v1_sp | qwen3_14b |
|-------------------|--------------:|----------:|
| telugu (Telugu)   | 1.59          | 2.32      |
| bengali (Bengali) | 4.40          | 1.67      |
| kannada (Kannada) | 2.53          | 2.26      |

byte-fallback % (akshara_v1_sp), prominent:

| script  | byte-fallback % |
|---------|----------------:|
| telugu  | 22.47           |
| bengali | 79.90           |
| kannada | 53.62           |

Qwen3: na.

## English (informational only; IYRA is EN-primary)

English: minimal training exposure (5 repeated sentences).

| metric                | akshara_v1_sp | qwen3_14b |
|-----------------------|--------------:|----------:|
| fertility (tok/word)  | 5.08          | 1.26      |
| tokens per akshara    | 0.84          | 0.21      |
| byte-fallback %       | 0.15          | na        |

## Round-trip: decode(encode(text)) == text (byte-identical)

| script     | akshara_v1_sp | qwen3_14b |
|------------|:-------------:|:---------:|
| devanagari | no            | no        |
| gurmukhi   | no            | no        |
| tamil      | no            | no        |
| telugu     | no            | no        |
| bengali    | no            | no        |
| kannada    | no            | no        |
| english    | no            | yes       |

Notes:
- akshara_v1_sp: no for all files. The v1 pipeline ships no detokenizer; the space-join conflates akshara boundaries with word boundaries, and the SP model normalizes whitespace (remove_extra_whitespaces=True, add_dummy_prefix=True). The SP-layer check `sp.decode(ids) == ' '.join(segment_aksharas(text))` is also no for all files, for the same whitespace-normalization reason.
- qwen3_14b: english yes (byte-identical). The 6 Indic files are no under byte-identical equality but equal under Unicode NFC and NFKC normalization; decode decomposes some precomposed nukta forms (e.g., Hindi output length 132213 vs input 132091).
