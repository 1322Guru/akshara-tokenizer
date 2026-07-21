#!/usr/bin/env python3
"""v1.2 fertility benchmark: AksharaTokenizer v1.2 vs the v1.1 model and an optional
Qwen3-14B baseline. FLORES-200 devtest eval files, deterministic single pass.

v1.2 encodes through the AksharaTokenizer class (segment, map each akshara to its
private-use codepoint, then SentencePiece). v1.1 uses its documented legacy pipeline
sp.encode(' '.join(segment_aksharas(text))). Both are measured per line, because
encoding a whole file at once turns every newline into an unmapped unit that
byte-falls-back and inflates the v1.2 byte-fallback rate by an artifact of the line
count. FLORES-200 data and the Qwen tokenizer are supplied locally; neither ships with
the repo (see manifest.md for provenance). The authoritative recorded numbers are in
results_v1_2.md; this script regenerates them on your own eval data.
"""
import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

import sentencepiece as spm
from importlib.resources import files as _pkg_files

from akshara_tokenizer import segment_aksharas, count_aksharas
from akshara_tokenizer import AksharaTokenizer

ap = argparse.ArgumentParser(description="AksharaTokenizer v1.2 fertility benchmark (FLORES-200)")
ap.add_argument("--eval-dir", default=HERE,
                help="directory holding eval_<script>.txt (FLORES-200 devtest, supplied locally)")
ap.add_argument("--qwen-tokenizer", default=os.environ.get("QWEN_TOKENIZER_JSON"),
                help="path to a Qwen3 tokenizer.json for the BPE baseline column; omit to skip it")
ap.add_argument("--out", default=os.path.join(HERE, "results_v1_2_fertility.csv"),
                help="output CSV path")
args = ap.parse_args()


def _v11_model():
    return str(_pkg_files("akshara_tokenizer").joinpath("model", "akshara_tokenizer_v1_1.model"))


v12 = AksharaTokenizer.load()
sp12 = v12._sp
sp11 = spm.SentencePieceProcessor(model_file=_v11_model())

qwen = None
if args.qwen_tokenizer:
    from tokenizers import Tokenizer
    qwen = Tokenizer.from_file(args.qwen_tokenizer)

SCRIPTS = ["devanagari", "gurmukhi", "tamil", "telugu", "bengali", "kannada", "english"]
INDIC = SCRIPTS[:6]


def bf_pct(sp, ids):
    if not ids:
        return 0.0
    return 100.0 * sum(1 for i in ids if sp.id_to_piece(i).startswith("<0x")) / len(ids)


FIELDS = ["script", "tokenizer", "tokens", "chars", "words", "aksharas",
          "tok_per_100char", "fertility_tok_per_word", "tok_per_akshara",
          "bytefallback_pct"]
rows = []
agg = {}

for script in SCRIPTS:
    path = os.path.join(args.eval_dir, f"eval_{script}.txt")
    if not os.path.exists(path):
        print(f"WARN missing eval file: {path}")
        continue
    text = open(path, encoding="utf-8").read()
    n_chars, n_words, n_aks = len(text), len(text.split()), count_aksharas(text)

    ids12, ids11, idsq = [], [], []
    for line in text.split("\n"):
        ids12 += v12.encode(line)
        ids11 += sp11.encode(" ".join(segment_aksharas(line)))
        if qwen is not None:
            idsq += qwen.encode(line, add_special_tokens=False).ids

    cols = [("akshara_v1_2_64k", ids12, bf_pct(sp12, ids12)),
            ("akshara_v1_1_16k", ids11, bf_pct(sp11, ids11))]
    if qwen is not None:
        cols.append(("qwen3_14b", idsq, None))

    for name, ids, bf in cols:
        rows.append({
            "script": script, "tokenizer": name, "tokens": len(ids),
            "chars": n_chars, "words": n_words, "aksharas": n_aks,
            "tok_per_100char": round(100.0 * len(ids) / n_chars, 4),
            "fertility_tok_per_word": round(len(ids) / n_words, 4),
            "tok_per_akshara": round(len(ids) / n_aks, 4),
            "bytefallback_pct": "na" if bf is None else round(bf, 4),
        })
        if script in INDIC:
            a = agg.setdefault(name, {"tokens": 0, "chars": 0, "words": 0, "aksharas": 0})
            a["tokens"] += len(ids); a["chars"] += n_chars
            a["words"] += n_words; a["aksharas"] += n_aks

for name, a in agg.items():
    rows.append({
        "script": "OVERALL_INDIC", "tokenizer": name, "tokens": a["tokens"],
        "chars": a["chars"], "words": a["words"], "aksharas": a["aksharas"],
        "tok_per_100char": round(100.0 * a["tokens"] / a["chars"], 4),
        "fertility_tok_per_word": round(a["tokens"] / a["words"], 4),
        "tok_per_akshara": round(a["tokens"] / a["aksharas"], 4),
        "bytefallback_pct": "",
    })

with open(args.out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(rows)
for r in rows:
    print(r["script"], r["tokenizer"], "| fert", r["fertility_tok_per_word"],
          "| tok/aksh", r["tok_per_akshara"], "| bf%", r["bytefallback_pct"])
print(f"WROTE {args.out}")
