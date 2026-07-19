#!/usr/bin/env python3
"""Akshara split-rate measurement for the shipped v1.1 model on FLORES-200 devtest.

Definition: an akshara is "split" when the model's token boundaries fall inside it,
whether via sub-akshara pieces or via byte_fallback pieces. The two mechanisms are
counted separately. Measured over the same eval_<script>.txt files (FLORES-200
devtest, supplied locally) used for the published fertility numbers.

Method: each line is segmented with segment_aksharas and space-joined exactly as in
the v1.1 encode pipeline. Piece boundaries are taken as UTF-8 byte offsets from
SentencePiece's proto output (piece.begin / piece.end) and compared against each
akshara's byte span in the joined text. An akshara counts as split when a piece
boundary falls strictly inside its span, or when any byte_fallback piece begins
inside it (byte pieces carry zero-width spans, so byte-tiled characters produce no
internal boundary and need the second test).

Requires the protobuf package for proto output: pip install protobuf
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

import sentencepiece as spm
from importlib.resources import files as _pkg_files
from akshara_tokenizer.boundary import segment_aksharas

SCRIPTS = ["devanagari", "gurmukhi", "tamil", "telugu", "bengali", "kannada"]
WS = (" ", "\n", "\t", "\r")

model_path = str(_pkg_files("akshara_tokenizer").joinpath("model", "akshara_tokenizer_v1_1.model"))
sp = spm.SentencePieceProcessor(model_file=model_path)

print(f"{'script':<12} {'aksharas':>9} {'split':>7} {'split%':>7} {'subpiece':>9} {'bytefall':>9}")
tot_a = tot_s = tot_sub = tot_bf = 0
for script in SCRIPTS:
    path = os.path.join(HERE, f"eval_{script}.txt")
    if not os.path.exists(path):
        print(f"{script:<12} MISSING {path}")
        continue
    n_aks = n_split = n_sub = n_bf = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            aks = segment_aksharas(line.rstrip("\n"))
            joined = " ".join(aks)
            spans = []
            pos = 0
            for i, a in enumerate(aks):
                if i > 0:
                    pos += 1  # the joining space
                blen = len(a.encode("utf-8"))
                if a not in WS:
                    spans.append((pos, pos + blen))
                pos += blen
            pieces = sp.encode(joined, out_type="proto").pieces
            bounds = set()
            for pc in pieces:
                bounds.add(pc.begin)
                bounds.add(pc.end)
            byte_begins = [pc.begin for pc in pieces if sp.is_byte(pc.id)]
            for s, e in spans:
                n_aks += 1
                has_byte = any(s <= b < e for b in byte_begins)
                has_internal = any(s < b < e for b in bounds)
                if has_byte or has_internal:
                    n_split += 1
                    if has_byte:
                        n_bf += 1
                    else:
                        n_sub += 1
    pct = 100.0 * n_split / n_aks if n_aks else 0.0
    print(f"{script:<12} {n_aks:>9} {n_split:>7} {pct:>6.3f}% {n_sub:>9} {n_bf:>9}")
    tot_a += n_aks; tot_s += n_split; tot_sub += n_sub; tot_bf += n_bf

pct = 100.0 * tot_s / tot_a if tot_a else 0.0
print(f"{'OVERALL':<12} {tot_a:>9} {tot_s:>7} {pct:>6.3f}% {tot_sub:>9} {tot_bf:>9}")
