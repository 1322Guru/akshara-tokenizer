# Romanized-Indic fertility on Dakshina (2026-08-01)

Measurement only. No model, package or published artifact was changed. `results_v1_2.md`
and `run_fertility_v1_2.py` are untouched; this run uses a separate harness,
`run_fertility_dakshina.py`.

Question: does the Akshara tokenizer cost enough on romanized Indic input to justify a
retrain that gives Latin more vocabulary? A 28 July pass on AI4Bharat Sangraha's romanized
splits suggested it might, but those splits are machine transliterations with an
idiosyncratic scheme ("haye" for है, "ack" for एक, "joe" for जो), so the numbers measured a
romanization nobody types. This run repeats the measurement on human romanizations.

## Data

`dakshina_dataset_v1.0/<L>/romanized/<L>.romanized.rejoined.tsv`, 10,000 lines per
language, two tab-separated fields holding the SAME sentence in native script and in
human romanization. The sibling `*.aligned.tsv` is word-level alignment and was not used.

Matched pairs are the point: roman and native fertility are measured on identical content,
so any difference is the script rather than the sample. Filter, applied to the native side
only: 40 to 200 characters and at least 6 whitespace words. First 600 qualifying pairs per
language in file order, no shuffle.

| language | pairs | native mean chars | roman mean chars | native mean words | roman mean words |
|---|---:|---:|---:|---:|---:|
| Hindi | 600 | 97.0 | 107.1 | 18.56 | 18.56 |
| Punjabi | 600 | 96.5 | 116.7 | 18.75 | 18.71 |
| Tamil | 600 | 102.0 | 111.2 | 10.97 | 10.95 |

Word counts agree across sides to within 0.04, which is consistent with true sentence
alignment.

The romanizations are human rather than machine transliteration: English loanwords survive
untransliterated in the romanized side, including `Ribosome`, `alexis`, `hiking` and
`fencing`. A machine scheme would render these phonetically.

Source sentences are not reproduced here. The corpus is third-party and is referenced by
selection rule rather than vendored, in line with the rest of this benchmark.

## Method

Metrics and aggregation match `run_fertility_v1_2.py`: encode per line, then divide total
tokens by total words and by total characters. Byte-fallback is the share of tokens whose
piece is `<0xXX>`. Round-trip counts lines where `decode(encode(x))` is byte-identical.

Artifacts, by sha256:

- v1.2 model `02161e9f865eae3e083d3ccb121ea46e242e32ee115052a029afbf341a4d294d`
- v1.2 map `5653f2cf29e8bcf456877851a71e3a4ebf254cee1129ecdca4a4120b5ef9d160`
- v1.1 model `471e4f1205fb8955a49d85efba75f5fa34d2cf8c967600750a1ad2f82763bb28`
- Qwen3-14B `tokenizer.json` `856e9e5db667533ed06c0784cb290e397145e502a2897828f7085260a297b7da`

One trap worth recording: that Qwen `tokenizer.json` bakes padding and truncation to 2048
into the file. Left as loaded, every encode returns 2,048 ids and fertility comes out near
116 tokens per word. The harness calls `no_padding()` and `no_truncation()` before
measuring. Any future benchmark against a fine-tuned checkpoint's tokenizer needs the same.

## Hindi (Devanagari), n=600

| side | tokenizer | fertility | tok/100char | byte-fallback % | round-trip |
|---|---|---:|---:|---:|---|
| roman | **v1.2 (64k)** | 2.574 | 44.63 | 0.000 | 600/600 |
| roman | v1.1 (16k) | 4.823 | 83.61 | 0.000 | 0/600 |
| roman | Qwen3-14B | **2.086** | 36.16 | 0.000 | 600/600 |
| native | **v1.2 (64k)** | **1.438** | 27.51 | 0.000 | 600/600 |
| native | v1.1 (16k) | 2.475 | 47.34 | 0.392 | 0/600 |
| native | Qwen3-14B | 4.845 | 92.67 | 0.000 | 600/600 |

## Punjabi (Gurmukhi), n=600

| side | tokenizer | fertility | tok/100char | byte-fallback % | round-trip |
|---|---|---:|---:|---:|---|
| roman | **v1.2 (64k)** | 2.774 | 44.48 | 0.019 | 600/600 |
| roman | v1.1 (16k) | 5.300 | 84.99 | 0.197 | 0/600 |
| roman | Qwen3-14B | **2.392** | 38.36 | 0.000 | 600/600 |
| native | **v1.2 (64k)** | **1.451** | 28.21 | 0.037 | 600/600 |
| native | v1.1 (16k) | 2.677 | 52.06 | 0.369 | 0/600 |
| native | Qwen3-14B | 7.672 | 149.18 | 0.000 | 600/600 |

## Tamil, n=600

| side | tokenizer | fertility | tok/100char | byte-fallback % | round-trip |
|---|---|---:|---:|---:|---|
| roman | **v1.2 (64k)** | 4.537 | 44.68 | 0.000 | 600/600 |
| roman | v1.1 (16k) | 9.246 | 91.05 | 0.000 | 0/600 |
| roman | Qwen3-14B | **4.021** | 39.60 | 0.000 | 600/600 |
| native | **v1.2 (64k)** | **2.131** | 22.91 | 0.000 | 600/600 |
| native | v1.1 (16k) | 5.092 | 54.73 | 0.152 | 0/600 |
| native | Qwen3-14B | 10.227 | 109.93 | 0.000 | 600/600 |

## The deciding number

Roman-side token overhead, v1.2 against Qwen3-14B, on identical sentences:

| language | overhead | verdict against the 30 percent line |
|---|---:|---|
| Hindi | **+23.4 %** | **below 30** |
| Punjabi | **+16.0 %** | **below 30** |
| Tamil | **+12.8 %** | **below 30** |

**All three land below the line.** On human romanization the tokenizer is second-best by
13 to 23 percent, not by the margin that would justify disturbing a lossless, verified,
published artifact.

The synthetic-data worry that prompted this run turned out to be mostly unfounded. Sangraha
gave +22.2 / +22.1 / +12.1 percent for hi / pa / ta; Dakshina gives +23.4 / +16.0 / +12.8.
Hindi and Tamil barely moved. Punjabi improved by 6 points, so the earlier number was
slightly pessimistic. The conclusion is unchanged, and it now rests on text people actually
write.

Two findings that cut against a retrain:

- **Native-script performance is the reason the tokenizer exists, and it is large.** v1.2
  beats Qwen by 3.4x on Hindi, 5.3x on Punjabi and 4.8x on Tamil. Any reallocation of
  vocabulary to Latin is paid for out of the 58,844 Indic slots that produce that result.
- **Byte-fallback and losslessness are not the problem.** Byte-fallback peaks at 0.037
  percent, and v1.2 round-trips 600/600 on both sides in all three languages, 3,600 of
  3,600 lines. v1.1 round-trips 0/600 everywhere, as documented: its legacy path
  space-joins aksharas and the model normalises whitespace.

## Scope, and what is not settled here

This measures romanized Indic, not code-switched text. The 28 July run measured Hinglish
from `festvox/cmu_hinglish_dog` at **+42.3 percent**, the only figure above the line, and
English at +69.2 percent. Those are English-heavy inputs rather than romanized Indic, and
they are the case a Latin retrain would actually serve. If the demo's real traffic is
code-switched rather than romanized, this result does not settle the question and the
Hinglish number should be re-measured on a larger set before deciding.

Reproduce with:

```
python3 run_fertility_dakshina.py \
    --dakshina-root /path/to/dakshina_dataset_v1.0 \
    --qwen-tokenizer /path/to/qwen/tokenizer.json
```
