# Competitor benchmark ground truth, 1 August 2026

These are the scripts and the raw output that produced the numbers in
`../results_competitor_comparison.md` on 1 August 2026. They are preserved here for
provenance, so the published figures can be traced to the run that generated them.

| file | what it is |
|---|---|
| `build_competitor_sets.py` | builds the frozen evaluation selection |
| `measure_competitors.py` | measures every tokenizer over that selection |
| `competitor_results.json` | raw output of that run, the source of the published numbers |

`competitor_sets.json`, the frozen evaluation selection itself, is deliberately **not**
included, because it contains third-party corpus text. The selection is reproducible by
running `build_competitor_sets.py`, and the Hinglish portion is verifiable line by line
against `../hinglish_findnitai_manifest.json`, which carries sha256 hashes only and no
corpus text.
