# AksharaTokenizer v1.1 fertility benchmark (2026-07-14)

> Release note: the model referenced below by its build-time name `akshara_v1_1_test_16k.model` is the file shipped in this release as `akshara_tokenizer_v1_1.model`, identical by sha256 471e4f12...bb28. The build-time name is kept unchanged in the body.

Status note (17 Jul 2026): this benchmark was run as a private test build, when v1 (vocab 7000) was still the shipped artifact. As of this release, the v1.1 16,000-vocab model benchmarked here is the publicly released model; v1 remains the originally filed artifact and is not distributed.

## Setup
- Eval corpus: FLORES-200 devtest, 1012 sentences per language (URLs and sha256 in manifest.md). Held out from all AksharaTokenizer training.
- Segmenter: `akshara_tokenizer.boundary.segment_aksharas`, v1.1-fixed working tree over submodule commit 1665c23 (adds telugu/kannada anusvara + visarga + candrabindu and devanagari/gurmukhi/bengali candrabindu, so those combining marks attach to the preceding akshara instead of segmenting standalone; 34 unit tests pass). Encode: `sp.encode(' '.join(segment_aksharas(text)))`.
- akshara_v1_7k: shipped model `model/akshara_tokenizer_v1.model` (vocab 7000, byte_fallback=True), trained on Hindi/Punjabi/Tamil only (pre-fix segmentation).
- akshara_v1_1_16k: candidate `akshara_v1_1_test_16k.model` (vocab 16000, sha256 471e4f12..., byte_fallback=True), SentencePiece unigram trained on all six scripts (v1's hi/pa/ta segmented corpora + new sentence-split, v1.1-segmented te/bn/kn). Recipe: character_coverage 0.99995, max_sentencepiece_length 8, hard_vocab_limit true, shuffle_input_sentence true, input_sentence_size 2,000,000. Train: 212 s wall, 12.90 GB peak RSS. sentencepiece 0.2.1.
- Qwen3-14B: base `tokenizer.json` from `unsloth/Qwen3-14B` snapshot b8755c0b (vocab 151669); tokenizers 0.22.2; byte-level BPE, add_special_tokens=False.
- Akshara-count denominator (shared): `count_aksharas(text)` = total segmentation units. Deterministic, single pass, no sampling. Raw values in results_v1_1.csv.

## Vocabulary ceiling finding (important)
- The originally requested 64k and 128k candidates are architecturally infeasible under this recipe and were dropped.
- With `split_by_whitespace=True` on akshara-segmented input and `max_sentencepiece_length=8`, SentencePiece cannot merge pieces across the space-delimited aksharas, so the achievable vocabulary is bounded by the distinct-akshara count present in the sampled training data.
- Measured cap with `hard_vocab_limit=True`: about 17,145 pieces at input_sentence_size 2,000,000 (14,316 at 1,000,000). SentencePiece errors out ("Vocabulary size too high, set it to <= 17145") for any vocab above that.
- The full six-script akshara union is 70,236 (hi 22,251, pa 7,987, ta 5,934, te 18,045, bn 11,655, kn 16,021). 128,000 exceeds the entire inventory; 64,000 meets or approaches it and would require input_sentence_size near the full 11.74M-line corpus (peak RSS ~20 GB, above this machine's RAM ceiling). Both are infeasible under this design. 16,000 sits just under the measured cap and trains cleanly.

## Coverage
- Segmenter covers all six scripts: devanagari, gurmukhi, tamil, telugu, bengali, kannada.
- akshara_v1_1_16k SP model covers all six scripts (Telugu, Bengali, Kannada are now trained). akshara_v1_7k covers three (Hindi, Punjabi, Tamil); its Telugu/Bengali/Kannada numbers reflect byte-fallback behavior, not trained coverage.

## Section A: scripts trained in v1 (Hindi, Punjabi, Tamil)
These were trained in both v1 and the candidate, so v1 and 16k are near-identical here; the small differences come from the candrabindu handling and the larger vocab.

Fertility (tokens per whitespace-delimited word):

| script (language)  | akshara_v1_7k | akshara_v1_1_16k | qwen3_14b |
|--------------------|--------------:|-----------------:|----------:|
| devanagari (Hindi) | 2.45          | 2.45             | 4.77      |
| gurmukhi (Punjabi) | 2.68          | 2.68             | 7.80      |
| tamil (Tamil)      | 5.01          | 5.01             | 10.06     |

Tokens per akshara:

| script (language)  | akshara_v1_7k | akshara_v1_1_16k | qwen3_14b |
|--------------------|--------------:|-----------------:|----------:|
| devanagari (Hindi) | 0.72          | 0.72             | 1.40      |
| gurmukhi (Punjabi) | 0.74          | 0.74             | 2.14      |
| tamil (Tamil)      | 0.83          | 0.83             | 1.68      |

byte-fallback %: Hindi 0.77 / 0.77, Punjabi 0.73 / 0.73, Tamil 0.02 / 0.02 (v1 / 16k). Qwen3: na (byte-level BPE, no UNK/byte-fallback).

## Section B: scripts newly trained in the candidate (Telugu, Bengali, Kannada)
For v1 these three scripts were untrained (byte-fallback). The candidate trains them on v1.1-segmented data with the anusvara fix, which is the headline improvement.

Fertility (tokens per word):

| script (language) | akshara_v1_7k (untrained) | akshara_v1_1_16k (trained) | qwen3_14b | 16k vs v1 |
|-------------------|--------------------------:|---------------------------:|----------:|----------:|
| telugu (Telugu)   | 7.50                      | 3.71                       | 11.41     | -50.5%    |
| bengali (Bengali) | 18.86                     | 3.38                       | 7.16      | -82.1%    |
| kannada (Kannada) | 13.08                     | 4.17                       | 11.88     | -68.1%    |

Tokens per akshara:

| script (language) | akshara_v1_7k | akshara_v1_1_16k | qwen3_14b |
|-------------------|--------------:|-----------------:|----------:|
| telugu (Telugu)   | 1.63          | 0.81             | 2.48      |
| bengali (Bengali) | 4.41          | 0.79             | 1.68      |
| kannada (Kannada) | 2.58          | 0.82             | 2.34      |

byte-fallback %:

| script  | akshara_v1_7k | akshara_v1_1_16k |
|---------|--------------:|-----------------:|
| telugu  | 23.41         | 0.08             |
| bengali | 79.94         | 0.09             |
| kannada | 54.37         | 0.36             |

Qwen3: na. The candidate cuts byte-fallback from tens of percent to under 0.4% on all three scripts and brings their fertility below Qwen3 on every script (Telugu 3.71 vs 11.41, Bengali 3.38 vs 7.16, Kannada 4.17 vs 11.88).

## English (informational only; IYRA is EN-primary)
FLORES English devtest, full file.

| metric                | akshara_v1_7k | akshara_v1_1_16k | qwen3_14b |
|-----------------------|--------------:|-----------------:|----------:|
| fertility (tok/word)  | 5.08          | 5.08             | 1.26      |
| tokens per akshara    | 0.84          | 0.84             | 0.21      |
| byte-fallback %       | 0.15          | 0.14             | na        |

Qwen3 is far more efficient on English, as expected for an English-centric BBPE. The akshara tokenizers are Indic-first.

## Round-trip: decode(encode(text)) == text (byte-identical)

| script     | akshara_v1_7k | akshara_v1_1_16k | qwen3_14b |
|------------|:-------------:|:----------------:|:---------:|
| devanagari | no            | no               | no        |
| gurmukhi   | no            | no               | no        |
| tamil      | no            | no               | no        |
| telugu     | no            | no               | no        |
| bengali    | no            | no               | no        |
| kannada    | no            | no               | no        |
| english    | no            | no               | yes       |

Notes:
- Both akshara models: no for all files. The pipeline ships no detokenizer; the space-join conflates akshara boundaries with word boundaries, and the SP model normalizes whitespace (remove_extra_whitespaces=True, add_dummy_prefix=True). The SP-layer check `sp.decode(ids) == ' '.join(segment_aksharas(text))` is also no for the same whitespace-normalization reason. This is a pipeline property, unchanged from v1.
- qwen3_14b: english yes (byte-identical); the six Indic files are no under byte-identical equality but equal under NFC/NFKC (decode decomposes some precomposed nukta forms).

## Summary
- The v1.1 segmentation fix plus six-script training gives large gains on Telugu, Bengali, and Kannada (fertility down 50 to 82 percent, byte-fallback down from 23 to 80 percent to under 0.4 percent) while leaving Hindi, Punjabi, Tamil, and English essentially unchanged.
- The achievable vocabulary is capped near the distinct-akshara count (about 17,145 at this sample size; 70,236 union across six scripts), so the akshara-constrained unigram design cannot reach a 64k or 128k vocabulary from this corpus. 16k is a representative in-budget candidate.
