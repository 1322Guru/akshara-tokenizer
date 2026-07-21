#!/usr/bin/env python3
"""Akshara split-rate measurement for v1.2 and v1.1 on FLORES-200 devtest.

An akshara is "split" when token boundaries fall inside it, whether via sub-akshara
pieces or via byte_fallback. The two mechanisms are counted separately. Measured over
the same eval_<script>.txt files used for the fertility numbers.

For v1.2 an akshara that the map keeps is a single private-use codepoint in the stream
fed to SentencePiece, so no piece boundary can fall inside it; the residual splits are
the aksharas the Stage 2 coverage trim dropped, which pass through as literal text.

Offset note: with out_type="immutable_proto" in sentencepiece 0.2.1, piece.begin and
piece.end are CHARACTER offsets into the normalized text, not byte offsets. Spans are
therefore computed in characters. The v1.1 column is recomputed here with the same
method and reproduces measure_split_v1_1.py, which validates it.
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

from akshara_tokenizer import segment_aksharas
from akshara_tokenizer import AksharaTokenizer

ap = argparse.ArgumentParser(description="AksharaTokenizer v1.2 split-rate benchmark")
ap.add_argument("--eval-dir", default=HERE)
ap.add_argument("--out", default=os.path.join(HERE, "results_v1_2_split.csv"))
args = ap.parse_args()

INDIC = ["devanagari", "gurmukhi", "tamil", "telugu", "bengali", "kannada"]
WS = (" ", "\n", "\t", "\r")

v12 = AksharaTokenizer.load()
sp12, a2p = v12._sp, v12._a2p
sp11 = spm.SentencePieceProcessor(
    model_file=str(_pkg_files("akshara_tokenizer").joinpath("model", "akshara_tokenizer_v1_1.model")))


def _count(sp, text, spans):
    pieces = sp.encode(text, out_type="immutable_proto").pieces
    bounds, byte_starts = set(), []
    for pc in pieces:
        bounds.add(pc.begin)
        bounds.add(pc.end)
        if pc.piece.startswith("<0x"):
            byte_starts.append(pc.begin)
    n_split = n_sub = n_bf = 0
    for begin, end in spans:
        inner = any(begin < b < end for b in bounds)
        byted = any(begin <= b < end for b in byte_starts)
        if inner or byted:
            n_split += 1
            n_bf += 1 if byted else 0
            n_sub += 0 if byted else 1
    return len(spans), n_split, n_sub, n_bf


def split_v12(line):
    aks = segment_aksharas(line)
    parts = [a2p.get(a, a) for a in aks]
    mapped = "".join(parts)
    spans, pos = [], 0
    for a, mp in zip(aks, parts):
        if a not in WS:
            spans.append((pos, pos + len(mp)))
        pos += len(mp)
    return _count(sp12, mapped, spans)


def split_v11(line):
    aks = segment_aksharas(line)
    joined = " ".join(aks)
    spans, pos = [], 0
    for i, a in enumerate(aks):
        if i:
            pos += 1
        if a not in WS:
            spans.append((pos, pos + len(a)))
        pos += len(a)
    return _count(sp11, joined, spans)


rows = []
tot = {"v1.2": [0, 0, 0, 0], "v1.1": [0, 0, 0, 0]}
print(f"{'script':<12} {'model':<6} {'aksharas':>9} {'split':>7} {'split%':>8} {'subpiece':>9} {'bytefall':>9}")
for script in INDIC:
    path = os.path.join(args.eval_dir, f"eval_{script}.txt")
    if not os.path.exists(path):
        print(f"WARN missing {path}")
        continue
    lines = [ln.rstrip("\n") for ln in open(path, encoding="utf-8")]
    for label, fn in (("v1.2", split_v12), ("v1.1", split_v11)):
        a = s = sub = bf = 0
        for line in lines:
            r = fn(line)
            a += r[0]; s += r[1]; sub += r[2]; bf += r[3]
        pct = 100.0 * s / a if a else 0.0
        print(f"{script:<12} {label:<6} {a:>9,} {s:>7,} {pct:>8.4f} {sub:>9,} {bf:>9,}")
        rows.append({"script": script, "model": label, "aksharas": a, "split": s,
                     "split_pct": round(pct, 4), "subpiece": sub, "bytefallback": bf})
        t = tot[label]
        t[0] += a; t[1] += s; t[2] += sub; t[3] += bf

for label in ("v1.2", "v1.1"):
    t = tot[label]
    pct = 100.0 * t[1] / t[0] if t[0] else 0.0
    print(f"{'OVERALL':<12} {label:<6} {t[0]:>9,} {t[1]:>7,} {pct:>8.4f} {t[2]:>9,} {t[3]:>9,}")
    rows.append({"script": "OVERALL", "model": label, "aksharas": t[0], "split": t[1],
                 "split_pct": round(pct, 4), "subpiece": t[2], "bytefallback": t[3]})

with open(args.out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["script", "model", "aksharas", "split", "split_pct", "subpiece", "bytefallback"])
    w.writeheader()
    w.writerows(rows)
print(f"WROTE {args.out}")
