#!/usr/bin/env python3
"""Whisper large-v3 tokenizer fertility against AksharaTokenizer v1.2.

Bounds the size of the prize for an akshara-aware tokenizer in a speech model.
It does NOT deliver that prize: see benchmark_2026_07/PREREG_WHISPER.md, which
was written before this script ran and fixes the statistic, the verdict rule and
the limitation.

CPU only, by construction. The box is training on GPU 0 and nothing here may
allocate on it.

The v1.2 side deliberately reuses the committed harness code path from
run_fertility_v1_2.py (AksharaTokenizer.load(), accumulate ids per line split on
"\n", words by whitespace split over the whole file) so the numbers are directly
comparable, and it refuses to report anything until it reproduces the published
figures to within 0.0005.
"""
import json
import os
import statistics
import sys

# CPU only. Set before anything can import a CUDA runtime.
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("MKL_NUM_THREADS", "4")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

try:                                    # only if torch is present at all
    import torch
    torch.set_num_threads(4)
except Exception:
    pass

from akshara_tokenizer import AksharaTokenizer
from tokenizers import Tokenizer

WHISPER_DIR = os.environ.get("WHISPER_TOK_DIR", "/home/guru/whisper_tok")
WHISPER_JSON = os.path.join(WHISPER_DIR, "tokenizer.json")

INDIC = ["devanagari", "gurmukhi", "tamil", "telugu", "bengali", "kannada"]
SCRIPTS = INDIC + ["english"]

# Published v1.2 figures. The gate, not decoration.
PUBLISHED = {"devanagari": 1.3741, "gurmukhi": 1.4446, "tamil": 1.9533,
             "telugu": 2.0006, "bengali": 1.7973, "kannada": 2.0583}
PUBLISHED_OVERALL = 1.7168
TOL = 0.0005

# Context only, quoted from benchmark_2026_07/results_v1_2_fertility.csv and
# cross-checked against groundtruth_20260801/competitor_results.json. NOT
# re-measured here.
QWEN3_14B = {"devanagari": 4.7566, "gurmukhi": 7.7583, "tamil": 10.0643,
             "telugu": 11.4060, "bengali": 7.1165, "kannada": 11.8763}


def load_text(script):
    with open(os.path.join(HERE, "eval_%s.txt" % script), encoding="utf-8") as fh:
        return fh.read()


def main():
    out = {}

    # ---- v1.2, committed code path -------------------------------------
    v12 = AksharaTokenizer.load()

    # ---- whisper, all three fairness guards ----------------------------
    wt = Tokenizer.from_file(WHISPER_JSON)
    wt.no_padding()
    wt.no_truncation()

    tj = json.load(open(WHISPER_JSON))
    normalizer_field = tj.get("normalizer")
    print("whisper tokenizer.json normalizer field, verbatim: %s"
          % json.dumps(normalizer_field, ensure_ascii=False))
    print("whisper vocab: %d base + %d added = %d"
          % (len(tj["model"]["vocab"]), len(tj["added_tokens"]),
             len(tj["model"]["vocab"]) + len(tj["added_tokens"])))
    print()

    # ---- the special-token guard, shown rather than assumed -------------
    probe = load_text("devanagari").split("\n")[0]
    with_special = wt.encode(probe, add_special_tokens=True)
    without_special = wt.encode(probe, add_special_tokens=False)
    print("=== special-token guard, one devanagari line ===")
    print("line: %s" % probe[:70])
    print("WITH    add_special_tokens=True : %d tokens" % len(with_special.ids))
    print("WITHOUT add_special_tokens=False: %d tokens" % len(without_special.ids))
    print("difference: %d tokens per line" % (len(with_special.ids) - len(without_special.ids)))
    extra = [t for t in with_special.tokens if t not in without_special.tokens]
    print("tokens added by the wrapper: %s" % extra)
    print("across 1,012 lines that is %d phantom tokens"
          % (1012 * (len(with_special.ids) - len(without_special.ids))))
    print()
    guard = {"with": len(with_special.ids), "without": len(without_special.ids),
             "extra_tokens": extra, "line": probe}

    # ---- measure --------------------------------------------------------
    for script in SCRIPTS:
        text = load_text(script)
        n_chars = len(text)
        n_words = len(text.split())
        lines = text.split("\n")           # committed path, keeps the empty tail

        ids12 = []
        idsw = []
        for line in lines:
            ids12 += v12.encode(line)
            idsw += wt.encode(line, add_special_tokens=False).ids

        # round-trip, byte exact, over the 1,012 real lines
        real = text.splitlines()
        rt_ok = 0
        rt_fail_examples = []
        for line in real:
            enc = wt.encode(line, add_special_tokens=False)
            dec = wt.decode(enc.ids)
            if dec == line:
                rt_ok += 1
            elif len(rt_fail_examples) < 3:
                rt_fail_examples.append({"orig": line[:60], "dec": dec[:60]})

        out[script] = {
            "chars": n_chars, "words": n_words, "lines": len(real),
            "v12_tokens": len(ids12), "whisper_tokens": len(idsw),
            "v12_fert": len(ids12) / n_words,
            "whisper_fert": len(idsw) / n_words,
            "ratio": (len(idsw) / n_words) / (len(ids12) / n_words),
            "v12_per100char": 100.0 * len(ids12) / n_chars,
            "whisper_per100char": 100.0 * len(idsw) / n_chars,
            "roundtrip_ok": rt_ok, "roundtrip_total": len(real),
            "roundtrip_fail_examples": rt_fail_examples,
        }

    # ---- VALIDATION GATE, before anything else is trusted ---------------
    print("=== validation gate: v1.2 against published figures ===")
    bad = []
    for script, want in PUBLISHED.items():
        got = out[script]["v12_fert"]
        delta = abs(got - want)
        flag = "ok" if delta <= TOL else "MISMATCH"
        if delta > TOL:
            bad.append((script, want, got, delta))
        print("  %-11s published %.4f  measured %.4f  delta %.6f  %s"
              % (script, want, got, delta, flag))

    tot_tok = sum(out[s]["v12_tokens"] for s in INDIC)
    tot_wrd = sum(out[s]["words"] for s in INDIC)
    ov = tot_tok / tot_wrd
    d_ov = abs(ov - PUBLISHED_OVERALL)
    print("  %-11s published %.4f  measured %.4f  delta %.6f  %s"
          % ("OVERALL", PUBLISHED_OVERALL, ov, d_ov,
             "ok" if d_ov <= TOL else "MISMATCH"))
    if d_ov > TOL:
        bad.append(("OVERALL", PUBLISHED_OVERALL, ov, d_ov))

    if bad:
        print("\nGATE FAILED: %d figure(s) outside %.4f. Reporting nothing."
              % (len(bad), TOL))
        return 1
    print("GATE PASSED\n")

    # ---- results --------------------------------------------------------
    ratios = [out[s]["ratio"] for s in INDIC]
    median = statistics.median(ratios)

    print("=== fertility, tokens per whitespace word ===")
    print("%-11s %8s %9s %8s %10s %10s %12s" %
          ("script", "v1.2", "whisper", "ratio", "v1.2/100c", "whis/100c", "whis RT"))
    for s in SCRIPTS:
        r = out[s]
        print("%-11s %8.4f %9.4f %8.4f %10.4f %10.4f %8d/%d" %
              (s, r["v12_fert"], r["whisper_fert"], r["ratio"],
               r["v12_per100char"], r["whisper_per100char"],
               r["roundtrip_ok"], r["roundtrip_total"]))

    print("\nmedian ratio over the six Indic scripts: %.4f" % median)
    if median >= 4.0:
        verdict = "PURSUE"
    elif median <= 2.0:
        verdict = "DROP"
    else:
        verdict = "PARK"
    print("pre-registered verdict: %s  (>=4.0 pursue, <=2.0 drop, else park)" % verdict)

    payload = {"per_script": out, "median_ratio": median, "verdict": verdict,
               "guard": guard, "normalizer_field": normalizer_field,
               "qwen3_14b_context": QWEN3_14B}
    with open(os.path.join(HERE, "results_whisper_fertility.json"), "w",
              encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    print("\nWROTE results_whisper_fertility.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
