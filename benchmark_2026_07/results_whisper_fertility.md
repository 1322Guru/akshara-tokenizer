# Whisper large-v3 tokenizer fertility against AksharaTokenizer v1.2

Measured 2026-08-17, CPU only. Decision rule fixed in advance in
`PREREG_WHISPER.md` (sha256 `c6c3898ba448361941d23de0cc79b7a033e2a001ac794bbf4c92d980e0a6b13c`),
written before any tokenizer was loaded. Reproduce with:

    CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=4 nice -n 15 \
      python benchmark_2026_07/run_fertility_whisper.py

## Validation gate

The v1.2 side reuses the committed code path from `run_fertility_v1_2.py` and
reproduced every published figure before any Whisper number was reported.
Largest deviation 0.000044, tolerance 0.0005.

| script | published | measured | delta |
|---|---|---|---|
| devanagari | 1.3741 | 1.3741 | 0.000041 |
| gurmukhi | 1.4446 | 1.4446 | 0.000031 |
| tamil | 1.9533 | 1.9533 | 0.000036 |
| telugu | 2.0006 | 2.0006 | 0.000010 |
| bengali | 1.7973 | 1.7973 | 0.000044 |
| kannada | 2.0583 | 2.0583 | 0.000023 |
| OVERALL_INDIC | 1.7168 | 1.7168 | 0.000015 |

Inputs: v1.2 model sha256 `02161e9f...4d294d`, map sha256 `5653f2cf...f9d160`,
both confirmed unchanged. FLORES-200 devtest, 1,012 lines per script.

## Result

Fertility is tokens per whitespace word. Ratio is Whisper divided by v1.2.

| script | v1.2 | Whisper | ratio | v1.2 tok/100char | Whisper tok/100char | Whisper round-trip |
|---|---|---|---|---|---|---|
| devanagari | 1.3741 | 5.3270 | 3.8768 | 26.6748 | 103.4128 | 1012/1012 |
| gurmukhi | 1.4446 | 9.9822 | 6.9102 | 27.8368 | 192.3570 | 1012/1012 |
| tamil | 1.9533 | 7.9391 | 4.0645 | 21.1196 | 85.8410 | 1012/1012 |
| telugu | 2.0006 | 14.2046 | 7.1002 | 25.3795 | 180.1995 | 1012/1012 |
| bengali | 1.7973 | 13.1037 | 7.2906 | 26.9573 | 196.5345 | 1012/1012 |
| kannada | 2.0583 | 14.2035 | 6.9005 | 23.8150 | 164.3361 | 1012/1012 |
| english | 2.1505 | 1.2781 | 0.5943 | 35.4186 | 21.0493 | 1012/1012 |

English is context only and is excluded from the median, per the
pre-registration. It runs the other way: Whisper is 1.68x more efficient than
v1.2 on English, which is what an English-centric BPE should do and is a useful
check that the measurement is not simply biased in v1.2's favour.

**Median ratio over the six Indic scripts: 6.9054**

**Verdict: PURSUE** (rule: >= 4.0 pursue, <= 2.0 drop, otherwise park).

The median clears the threshold by a wide margin, but the spread matters: the
weakest script, Devanagari at 3.8768, sits BELOW the 4.0 pursue line on its own,
and Tamil at 4.0645 barely clears it. The case rests on Telugu, Bengali,
Kannada and Gurmukhi, all near or above 6.9.

## The special-token guard, shown rather than assumed

All three guards were applied: `add_special_tokens=False`, `no_padding()`,
`no_truncation()`. On one Devanagari line:

| condition | tokens |
|---|---|
| raw tokenizer, `add_special_tokens=True` | 106 |
| raw tokenizer, `add_special_tokens=False` | **103** |
| transformers wrapper, no language or task | 106 |
| transformers wrapper, `language=hindi, task=transcribe` | 108 |

The prediction that Whisper prepends four tokens and appends one is correct for
the transformers wrapper with language and task set, which yields
`<|startoftranscript|> <|hi|> <|transcribe|> <|notimestamps|>` plus a trailing
`<|endoftext|>`, five in total. The raw `tokenizer.json` post_processor is
narrower and carries only three, verbatim:

    "single": [ <|startoftranscript|>, <|notimestamps|>, A, <|endoftext|> ]

So the inflation this measurement avoided is 3 tokens per line against the raw
tokenizer and 5 per line against the realistic wrapper: between 3,036 and 5,060
phantom tokens across 1,012 lines. Unguarded, Devanagari fertility would have
read 5.48 instead of 5.3270, and the ratio 3.99 instead of 3.8768.

## Round-trip and normalization

`tokenizer.json` carries no normalizer. The field verbatim:

    "normalizer": null

`pre_tokenizer` and `decoder` are both `ByteLevel`, and `byte_fallback` is
`false`, which is normal for byte-level BPE since ByteLevel already maps every
byte into the vocabulary.

Round-trip was measured, not inferred: **1,012 of 1,012 lines byte-exact on all
seven scripts**, 7,084 lines in total, zero failures. This is the point where
Qwen3 fails. Qwen3 applies Unicode NFC inside its tokenizer, so precomposed
nukta forms come back re-composed and are not byte-identical, giving 919/1,012
on Devanagari and 439/1,012 on Gurmukhi. Whisper does not do this, because it
has no normalizer at all.

Note that `normalizer.json` ships in the repo separately. That is Whisper's
English text normalizer used for WER scoring. It is not applied by the
tokenizer and plays no part in these numbers.

## Context: Qwen3-14B on the same eval

Quoted from `results_v1_2_fertility.csv`, cross-checked against
`groundtruth_20260801/competitor_results.json`. Not re-measured here.

| script | v1.2 | Whisper | Qwen3-14B |
|---|---|---|---|
| devanagari | 1.3741 | 5.3270 | 4.7566 |
| gurmukhi | 1.4446 | 9.9822 | 7.7583 |
| tamil | 1.9533 | 7.9391 | 10.0643 |
| telugu | 2.0006 | 14.2046 | 11.4060 |
| bengali | 1.7973 | 13.1037 | 7.1165 |
| kannada | 2.0583 | 14.2035 | 11.8763 |

Whisper is worse than Qwen3-14B on Devanagari, Gurmukhi, Telugu, Bengali and
Kannada, and better on Tamil. Two figures quoted in the task request do not
match either committed source and were not used:

| script | figure in the request | committed value |
|---|---|---|
| devanagari | 4.754 | **4.7566** |
| tamil | 9.919 | **10.0643** |

Neither `9.919` nor `4.754` appears in any tracked file in this repository. The
committed CSV and the committed JSON agree with each other to six figures. No
telugu figure was supplied in the request; the committed value is 11.4060.

## Limitation, carried over verbatim from the pre-registration

A tokenizer cannot be swapped into Whisper without retraining the decoder.
Whisper's decoder embeddings are tied to its own vocabulary, so replacing the
tokenizer invalidates every learned token embedding and the model would have to
be retrained to use a different one. This measurement therefore BOUNDS the size
of the available prize. It does not deliver that prize, and no number produced
here should be read as a demonstrated speedup, cost saving or quality gain in
Whisper itself.

## Provenance

    openai/whisper-large-v3, apache-2.0, ungated, tokenizer files only, no weights
    tokenizer.json        2,480,617 bytes
    tokenizer_config.json   282,843 bytes
    vocab.json            1,036,558 bytes
    merges.txt              493,869 bytes
    special_tokens_map.json   2,072 bytes
    added_tokens.json        34,648 bytes
    normalizer.json          52,666 bytes
    vocab: 50,257 base + 1,609 added = 51,866
