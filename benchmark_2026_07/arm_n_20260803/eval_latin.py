"""Latin-side evaluation for a sweep arm: Dakshina romanized, Hinglish, English.

Confirms an arm made no unintended change to Latin handling. Categories come from the
FROZEN selection in competitor_sets.json, the same rows that produced the published
competitor numbers, so these are comparable to results_competitor_comparison.md.

Usage: python3 eval_latin.py <model_path> <label> [--json out.json]
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
import argparse
import json
import sys

REPO = REPO_ROOT
MAP = f"{REPO}/akshara_tokenizer/model/akshara_tokenizer_v1_2.map.json"
SETS = SETS_JSON
sys.path.insert(0, REPO)

import sentencepiece as spm
from akshara_tokenizer import AksharaTokenizer

CATS = ["romanized_hindi", "romanized_punjabi", "romanized_tamil",
        "hinglish_findnitai_human", "hinglish_cmu_28jul", "english_flores200"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("label")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    mapping = json.load(open(MAP, encoding="utf-8"))          # read-only
    a2p = {k: chr(int(v)) for k, v in mapping["aksharas"].items()}
    sp = spm.SentencePieceProcessor(model_file=a.model)
    tok = AksharaTokenizer(sp, a2p, model_sha256=None, version="arm")

    sets = json.load(open(SETS, encoding="utf-8"))
    res = {}
    print(f"=== {a.label} : Latin side ===")
    print(f"  {'category':26}{'n':>6}{'fert':>9}{'rt':>7}")
    for c in CATS:
        lines = sets[c]
        ntok = nword = rt = 0
        for x in lines:
            ids = tok.encode(x)
            ntok += len(ids)
            nword += len(x.split())
            rt += (tok.decode(ids) == x)
        res[c] = {"n": len(lines), "tokens": ntok, "words": nword,
                  "fertility": ntok / nword, "roundtrip_ok": rt}
        print(f"  {c:26}{len(lines):>6}{ntok / nword:>9.4f}{rt:>7}")
    if a.json:
        json.dump({"label": a.label, "model": a.model, "categories": res},
                  open(a.json, "w"), indent=1)
        print(f"WROTE {a.json}")


if __name__ == "__main__":
    main()
