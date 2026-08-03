"""Count occurrences of the 30 PUA symbols of the 15 duplicated-form pairs in a corpus.

Run on the frozen base set to size the arm N balancing before anything is built. Also
counts, per pair, how many LINES contain the precomposed symbol and how many contain the
decomposed one, since the substitution operates on lines, not on raw symbol counts.

Usage: python3 count_dual_forms.py <corpus_dir>
"""
# ---- paths -------------------------------------------------------------------
# Every absolute path is an env-var-backed constant so this script is portable. The
# fallbacks are the machine these results were produced on.
#   AKSHARA_SWEEP       scratch tree for corpora, models and result JSON
#   AKSHARA_V12_MAPPED  the v1.2 PUA-mapped corpus and its charset pickles
#   AKSHARA_REPO        checkout root of the akshara-tokenizer repository
#   AKSHARA_SETS        frozen competitor eval selection (competitor_sets.json)
import os as _os
SWEEP = _os.environ.get("AKSHARA_SWEEP", "/mnt/c/GuruAI-Data/akshara_v1_3_sweep")
V12_MAPPED_DIR = _os.environ.get("AKSHARA_V12_MAPPED", "/mnt/c/GuruAI-Data/akshara_v1_2/mapped")
REPO_ROOT = _os.environ.get("AKSHARA_REPO", "/mnt/d/GuruAI/akshara_tokenizer")
SETS_JSON = _os.environ.get(
    "AKSHARA_SETS",
    "/mnt/c/GuruAI-Data/akshara_competitor_groundtruth_20260801/competitor_sets.json")
# ------------------------------------------------------------------------------
import json
import os
import sys
from collections import Counter

PAIRS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "dual_form_pairs.json"), encoding="utf-8"))
LANGS = ["hi", "pa", "ta", "te", "bn", "kn"]


def main():
    corpus = sys.argv[1] if len(sys.argv) > 1 else f"{SWEEP}/base_6m"
    sym_pre = {chr(p["pre_pua"]): i for i, p in enumerate(PAIRS)}
    sym_dec = {chr(p["dec_pua"]): i for i, p in enumerate(PAIRS)}
    occ_pre = Counter(); occ_dec = Counter()
    lines_pre = Counter(); lines_dec = Counter()
    total_lines = 0

    for lang in LANGS:
        path = os.path.join(corpus, f"{lang}.txt")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                total_lines += 1
                seen_p = set(); seen_d = set()
                for ch in line:
                    i = sym_pre.get(ch)
                    if i is not None:
                        occ_pre[i] += 1; seen_p.add(i); continue
                    i = sym_dec.get(ch)
                    if i is not None:
                        occ_dec[i] += 1; seen_d.add(i)
                for i in seen_p: lines_pre[i] += 1
                for i in seen_d: lines_dec[i] += 1

    print(f"corpus={corpus}  total_lines={total_lines:,}\n")
    hdr = f"{'#':>3} {'scr':5} {'precomposed':16} {'occ_pre':>12} {'occ_dec':>12} {'pre/dec':>9} {'lines_pre':>11} {'lines_dec':>11}"
    print(hdr)
    out = []
    for i, p in enumerate(PAIRS):
        cp = " ".join(f"U+{ord(c):04X}" for c in p["pre"])
        op, od = occ_pre[i], occ_dec[i]
        ratio = (op / od) if od else float("inf")
        print(f"{i:>3} {p['script']:5} {cp:16} {op:>12,} {od:>12,} {ratio:>9.4f} "
              f"{lines_pre[i]:>11,} {lines_dec[i]:>11,}")
        out.append({"idx": i, "script": p["script"], "pre": p["pre"], "dec": p["dec"],
                    "pre_pua": p["pre_pua"], "dec_pua": p["dec_pua"],
                    "occ_pre": op, "occ_dec": od,
                    "lines_pre": lines_pre[i], "lines_dec": lines_dec[i]})
    print(f"\nTOTALS  occ_pre={sum(occ_pre.values()):,}  occ_dec={sum(occ_dec.values()):,}")
    dst = f"{SWEEP}/results/dual_form_counts.json"
    json.dump({"corpus": corpus, "total_lines": total_lines, "pairs": out},
              open(dst, "w"), indent=1)
    print(f"WROTE {dst}")


if __name__ == "__main__":
    main()
