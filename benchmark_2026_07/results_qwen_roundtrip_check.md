# Qwen3-14B round-trip: verification against the stock tokenizer (2026-08-02)

Measurement only. Nothing in the package, the v1.2 artifacts or any published result was
modified. Tokenizer files only were downloaded; no model weights.

`results_competitor_comparison.md` reports that Qwen3-14B round-trips poorly on Gurmukhi
(439/1,012) and Bengali (403/1,012). That was measured with a **fine-tuned checkpoint's**
`tokenizer.json`, so the finding could have been an artifact of the fine-tune rather than a
property of Qwen3. This note tests it against the stock `Qwen/Qwen3-14B` tokenizer.

`Qwen/Qwen3-14B` is not gated (`gated: False`, licence apache-2.0). No licence was accepted.
`special_tokens_map.json` is **absent from the stock repo**; recent Qwen releases fold
special-token definitions into `tokenizer_config.json`. Only `tokenizer.json` drives
round-trip behaviour, so its absence does not affect the test.

## Verdict

**YES. The failure reproduces exactly on the stock tokenizer. It is not an artifact of the
fine-tune.**

Stock and fine-tune produce **identical round-trip counts on all six scripts** and disagree
on **zero of 7,084 lines**.

## The mechanism, and it is not what was hypothesised

The hypothesis put to this test was that the fine-tune had acquired a normalizer the stock
tokenizer lacks. **Refuted.** Both files carry the same normalizer:

| field | stock | fine-tune | identical |
|---|---|---|---|
| `normalizer` | `{"type": "NFC"}` | `{"type": "NFC"}` | **yes** |
| `model.vocab` | 151,643 entries | 151,643 entries | **yes** |
| `model.merges` | 151,387 | 151,387 | **yes** |
| `pre_tokenizer` | Sequence(Split, ByteLevel) | same shape, differing ByteLevel flags | no |
| `decoder` | ByteLevel, `add_prefix_space=false`, `use_regex=false` | ByteLevel, `add_prefix_space=true`, `use_regex=true` | no |
| `post_processor` | ByteLevel | TemplateProcessing | no |
| `truncation` | `null` | `max_length: 2048` | no |
| `padding` | `null` | `Fixed: 2048`, `pad_token: <\|PAD_TOKEN\|>` | no |
| `added_tokens` | 26 | 27, adds `<\|PAD_TOKEN\|>` | no |

The fine-tune does differ in several fields, but **none of them affects round-trip
identity**: they are padding, truncation, a post-processor template and ByteLevel flags. The
NFC normalizer that causes the failure is present in **both**, and is stock Qwen3 behaviour.

### Minimal case: single characters

Each character encoded then decoded in isolation.

| group | codepoint | NFC-stable | stock | fine-tune | NFC form |
|---|---|---|---|---|---|
| Gurmukhi | U+0A36 ਸ਼ | no | **fail** | **fail** | U+0A38 U+0A3C |
| Gurmukhi | U+0A59 ਖ਼ | no | **fail** | **fail** | U+0A16 U+0A3C |
| Gurmukhi | U+0A5A ਗ਼ | no | **fail** | **fail** | U+0A17 U+0A3C |
| Gurmukhi | U+0A5B ਜ਼ | no | **fail** | **fail** | U+0A1C U+0A3C |
| Gurmukhi | U+0A5E ਫ਼ | no | **fail** | **fail** | U+0A2B U+0A3C |
| Gurmukhi | U+0A5C ੜ | yes | pass | pass | unchanged |
| Bengali | U+09DC ড় | no | **fail** | **fail** | U+09A1 U+09BC |
| Bengali | U+09DD ঢ় | no | **fail** | **fail** | U+09A2 U+09BC |
| Bengali | U+09DF য় | no | **fail** | **fail** | U+09AF U+09BC |
| Devanagari control | U+0929 ऩ | yes | pass | pass | unchanged |
| Devanagari control | U+0931 ऱ | yes | pass | pass | unchanged |
| Devanagari control | U+0934 ऴ | yes | pass | pass | unchanged |
| plain, no nukta | U+0A15 ਕ | yes | pass | pass | unchanged |
| plain, no nukta | U+0995 ক | yes | pass | pass | unchanged |
| plain, no nukta | U+0915 क | yes | pass | pass | unchanged |

The correspondence is exact: **every character that fails is NFC-unstable, and every
character that is NFC-stable passes.** The plain controls all pass, so the cause is not
something general about Indic handling.

Note the hypothesis was half right about which characters, and wrong about the direction.
These letters are **canonically decomposed by NFC, not composed**. Unicode marks U+0A36,
U+0A59 to U+0A5B, U+0A5E, U+09DC, U+09DD and U+09DF as canonical-decomposition singletons,
so NFC replaces the precomposed letter with base plus nukta U+0A3C or U+09BC. The failing
lines lose the precomposed codepoint and gain the combining nukta, which is what the byte
diffs show. U+0A5C ੜ is a genuine independent Gurmukhi letter with no decomposition, which
is why it survives, and the three Devanagari controls are likewise NFC-stable.

## Round-trip, six scripts, full 1,012-line eval files

| script | n | stock | fine-tune | NFC-stable lines |
|---|---:|---:|---:|---:|
| Devanagari | 1,012 | 919 | 919 | 919 |
| Gurmukhi | 1,012 | **439** | **439** | 439 |
| Tamil | 1,012 | 1,010 | 1,010 | 1,010 |
| Telugu | 1,012 | 1,011 | 1,011 | 1,011 |
| Bengali | 1,012 | **403** | **403** | 403 |
| Kannada | 1,012 | 1,005 | 1,005 | 1,005 |

**The round-trip count equals the NFC-stable line count exactly, in every script.** That is
the whole explanation: a line survives if and only if it was already in NFC.

Stronger still, across all seven eval files including English, **7,084 of 7,084 outputs are
byte-identical to NFC of the input**. The transformation is exactly NFC, not lossy
corruption. Nothing is dropped or garbled; text is silently converted to a different but
canonically equivalent encoding.

## Failing line diagnosis

Gurmukhi, stock tokenizer, first three failures:

- lost `U+0A36`, gained `U+0A3C`, output equals NFC of input
- lost `U+0A36`, output equals NFC of input
- lost `U+0A5E` and `U+0A5B`, gained `U+0A3C` and `U+0A2B`, output equals NFC of input

Bengali, stock tokenizer, first three failures:

- lost `U+09DC` and `U+09DF`, gained `U+09BC`, output equals NFC of input
- lost `U+09DF`, gained `U+09BC`, output equals NFC of input
- lost `U+09DF`, gained `U+09BC`, output equals NFC of input

In every case the output is byte-identical to `unicodedata.normalize("NFC", input)`.

## Proposed wording for the claim

The current sentence in `results_competitor_comparison.md` says Qwen "loses bytes on over
half those lines", which is wrong: nothing is lost, the text is normalized. Replace with:

> Qwen3-14B applies Unicode NFC normalization inside its tokenizer, so `decode(encode(x))`
> is not byte-identical for text containing precomposed nukta characters. NFC canonically
> decomposes Gurmukhi U+0A36, U+0A59 to U+0A5B and U+0A5E, and Bengali U+09DC, U+09DD and
> U+09DF, into base letter plus combining nukta. On FLORES-200 devtest that affects 573 of
> 1,012 Gurmukhi lines and 609 of 1,012 Bengali lines. The output is canonically equivalent
> to the input and renders identically; it is not corruption. It does mean the tokenizer
> cannot be used where byte-exact reconstruction is required. This is stock Qwen3 behaviour,
> verified against `Qwen/Qwen3-14B` and not an artifact of any fine-tune.

For contrast, v1.2 round-trips **573/573** NFC-unstable Gurmukhi lines and **609/609**
NFC-unstable Bengali lines, because its lossless path preserves the input encoding rather
than normalizing it. That contrast is the real point and it survives the correction.

## Step 7: downstream implication

**Not applicable, and the concern is dismissed.** Step 7 was conditional on the normalizer
being present in the fine-tune but absent from stock. It is present in **both**, identically,
and the two tokenizers disagree on zero of 7,084 lines. The IYRA fine-tune's tokenizer was
not modified in any way that changes text handling; the differing fields are padding,
truncation, a post-processor template and ByteLevel flags.

The training toolchain did add `<|PAD_TOKEN|>` and bake `padding: Fixed 2048` plus
`truncation: 2048` into `tokenizer.json`. That is a real and separate defect, already
documented in the benchmark harnesses: loaded as-is, every encode returns 2,048 ids and
fertility comes out near 116 tokens per word. It affects measurement, not text fidelity, and
it is why every harness here calls `no_padding()` and `no_truncation()`.

The NFC behaviour is inherited from upstream Qwen3 and would apply to any Qwen3-based system
handling Gurmukhi or Bengali. Whether that matters for IYRA depends on whether byte-exact
round-trip is required anywhere in that pipeline, which is outside the scope of this note.

## Reproduce

```
python3 verify_qwen_roundtrip.py \
    --stock    /mnt/c/GuruAI-Data/competitor_tokenizers/qwen3-14b-stock/tokenizer.json \
    --finetune /mnt/d/GuruAI/models/finetuned/guruai-qwen3-14b-nyaya-1681/tokenizer.json
```

| artifact | sha256 |
|---|---|
| stock `Qwen/Qwen3-14B` `tokenizer.json` | `aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4` |
| stock `tokenizer_config.json` | `d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101` |
| fine-tune `tokenizer.json` | `856e9e5db667533ed06c0784cb290e397145e502a2897828f7085260a297b7da` |

Stock vocab 151,669. Fine-tune vocab 151,670, the extra entry being `<|PAD_TOKEN|>`.
