# Pre-registration: Whisper tokenizer fertility against AksharaTokenizer v1.2

Written 2026-08-17, BEFORE any tokenizer was loaded and before any Whisper
number existed. Nothing below may be revised once measurement starts. If a
result argues for a different rule, that argument belongs in a new document.

## Statistic

Fertility, defined as tokens per whitespace word, measured as Whisper divided
by AksharaTokenizer v1.2, reported per script, on FLORES-200 devtest, all
1,012 lines per script.

Words are counted by whitespace split over the whole eval file, and tokens are
accumulated per line, which is the code path the committed v1.2 harness uses.

## Verdict rule

The verdict is the MEDIAN of the six per-script ratios.

  median ratio >= 4.0   pursue
  median ratio <= 2.0   drop
  otherwise             park

The six scripts are devanagari, gurmukhi, tamil, telugu, bengali, kannada.
English is measured for context but is NOT part of the median.

## Stated limitation

A tokenizer cannot be swapped into Whisper without retraining the decoder.
Whisper's decoder embeddings are tied to its own vocabulary, so replacing the
tokenizer invalidates every learned token embedding and the model would have to
be retrained to use a different one. This measurement therefore BOUNDS the size
of the available prize. It does not deliver that prize, and no number produced
here should be read as a demonstrated speedup, cost saving or quality gain in
Whisper itself.

## Fixed inputs

  v1.2 model sha256  02161e9f865eae3e083d3ccb121ea46e242e32ee115052a029afbf341a4d294d
  v1.2 map   sha256  5653f2cf29e8bcf456877851a71e3a4ebf254cee1129ecdca4a4120b5ef9d160
  eval files         benchmark_2026_07/eval_<script>.txt, 1,012 lines each
  whisper model      openai/whisper-large-v3, apache-2.0, tokenizer files only

## Validation gate, to run before any Whisper number is reported

The v1.2 side must reproduce the published figures to within 0.0005:

  deva 1.3741, guru 1.4446, taml 1.9533, telu 2.0006,
  beng 1.7973, knda 2.0583, overall 1.7168

A mismatch beyond that tolerance exits non-zero and no comparison is reported.

## Whisper fairness guards, all mandatory

  add_special_tokens=False, no_padding(), no_truncation()

Whisper prepends startoftranscript, a language tag, a task tag and
notimestamps, and appends endoftext. Across 1,012 short lines those five
special tokens per line are a large inflation and are the single most likely
way this measurement comes out wrong. The token count for one line WITH and
WITHOUT the guard will be reported so the difference is visible rather than
assumed.
