"""Evaluate one sweep arm: fertility, round-trip, split rate, vocabulary composition.

Measurement matches the committed harnesses exactly:
  - fertility  : run_fertility_competitors.py, encode PER LINE, tokens / whitespace words
  - split rate : measure_split_v1_2.py, CHARACTER offsets via out_type="immutable_proto"

The v1.2 map is read READ-ONLY and its akshara table is reused verbatim. The tokenizer is
constructed directly rather than through from_files(), because from_files() binds the map
to the v1.2 model by sha256 and would refuse an arm model. Nothing about the akshara to
PUA assignment changes, which is what makes arms comparable.

VOCABULARY CLASSIFIER, canonical rule for this sweep:
  Decode each vocab piece back through the PUA map, strip the SentencePiece meta symbol
  U+2581, then classify by first match in this order:
      special        piece is <unk>, <s>, </s> or <pad>
      byte_fallback  piece matches <0xXX>
      indic          decoded text contains at least one codepoint in U+0900 to U+0D7F
      latin          no Indic, and contains at least one ASCII letter
      digit          no Indic and no ASCII letter, and contains at least one digit
      other          everything else (punctuation, symbols, whitespace)
  Denominator is always the full 64,000 slots. "Indic share" means the indic bucket over
  64,000. A piece mixing Indic and Latin counts as indic, since it occupies a slot that
  only Indic text can use.

Usage: python3 eval_arm.py <model_path> <label> [--json out.json]
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
import os
import re
import sys
import unicodedata as ud

REPO = REPO_ROOT
EVAL = os.path.join(REPO, "benchmark_2026_07")
MAP = os.path.join(REPO, "akshara_tokenizer", "model", "akshara_tokenizer_v1_2.map.json")
sys.path.insert(0, REPO)

import sentencepiece as spm
from akshara_tokenizer import AksharaTokenizer, segment_aksharas

SCRIPTS = ["devanagari", "gurmukhi", "tamil", "telugu", "bengali", "kannada"]
PUBLISHED = {"devanagari": 1.374, "gurmukhi": 1.445, "tamil": 1.953,
             "telugu": 2.001, "bengali": 1.797, "kannada": 2.058}
META = "▁"
BF = re.compile(r"^<0x[0-9A-F]{2}>$")
SPECIAL = {"<unk>", "<s>", "</s>", "<pad>"}
WS = (" ", "\n", "\t", "\r")


def load_arm(model_path):
    mapping = json.load(open(MAP, encoding="utf-8"))          # read-only
    a2p = {k: chr(int(v)) for k, v in mapping["aksharas"].items()}
    sp = spm.SentencePieceProcessor(model_file=model_path)
    return AksharaTokenizer(sp, a2p, model_sha256=None, version="arm"), sp, a2p


def lines_of(script):
    p = os.path.join(EVAL, f"eval_{script}.txt")
    return [l.rstrip("\n") for l in open(p, encoding="utf-8") if l.strip()]


def fertility(tok, lines):
    ntok = nword = rt = 0
    for x in lines:
        ids = tok.encode(x)
        ntok += len(ids)
        nword += len(x.split())
        rt += (tok.decode(ids) == x)
    return {"tokens": ntok, "words": nword, "fertility": ntok / nword,
            "roundtrip_ok": rt, "n": len(lines)}


def split_rate(sp, a2p, lines):
    tot = spl = sub = bf = 0
    for line in lines:
        aks = segment_aksharas(line)
        parts = [a2p.get(a, a) for a in aks]
        mapped = "".join(parts)
        spans, pos = [], 0
        for a, mp in zip(aks, parts):
            if a not in WS:
                spans.append((pos, pos + len(mp)))
            pos += len(mp)
        pieces = sp.encode(mapped, out_type="immutable_proto").pieces
        bounds, byte_starts = set(), []
        for pc in pieces:
            bounds.add(pc.begin)
            bounds.add(pc.end)
            if pc.piece.startswith("<0x"):
                byte_starts.append(pc.begin)
        for b, e in spans:
            inner = any(b < x < e for x in bounds)
            byted = any(b <= x < e for x in byte_starts)
            if inner or byted:
                spl += 1
                bf += 1 if byted else 0
                sub += 0 if byted else 1
        tot += len(spans)
    return {"aksharas": tot, "split": spl, "split_pct": 100.0 * spl / tot if tot else 0.0,
            "subpiece": sub, "bytefallback": bf}


def vocab_composition(sp, a2p):
    p2a = {v: k for k, v in a2p.items()}
    n = sp.get_piece_size()
    counts = {k: 0 for k in ("special", "byte_fallback", "indic", "latin", "digit", "other")}
    latin_len = []
    for i in range(n):
        p = sp.id_to_piece(i)
        if p in SPECIAL:
            counts["special"] += 1
            continue
        if BF.match(p):
            counts["byte_fallback"] += 1
            continue
        s = "".join(p2a.get(c, c) for c in p).replace(META, "")
        if any(0x0900 <= ord(c) <= 0x0D7F for c in s):
            counts["indic"] += 1
        elif any(c.isascii() and c.isalpha() for c in s):
            counts["latin"] += 1
            latin_len.append(len(s))
        elif any(c.isdigit() for c in s):
            counts["digit"] += 1
        else:
            counts["other"] += 1
    out = {"vocab_size": n, "counts": counts,
           "indic_pct": 100.0 * counts["indic"] / n,
           "latin_pct": 100.0 * counts["latin"] / n,
           "latin_mean_len": (sum(latin_len) / len(latin_len)) if latin_len else 0.0}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("label")
    ap.add_argument("--json", default=None)
    ap.add_argument("--forms", action="store_true", help="also measure NFC and NFD")
    a = ap.parse_args()

    tok, sp, a2p = load_arm(a.model)
    res = {"label": a.label, "model": a.model, "scripts": {}}

    print(f"=== {a.label} ===")
    print(f"  {'script':12}{'fert':>9}{'published':>11}{'delta%':>9}{'rt':>7}{'split%':>9}")
    for s in SCRIPTS:
        L = lines_of(s)
        f = fertility(tok, L)
        sr = split_rate(sp, a2p, L)
        d = 100.0 * (f["fertility"] - PUBLISHED[s]) / PUBLISHED[s]
        res["scripts"][s] = {"as_is": f, "split": sr, "delta_vs_published_pct": d}
        print(f"  {s:12}{f['fertility']:>9.4f}{PUBLISHED[s]:>11.3f}{d:>8.2f}%"
              f"{f['roundtrip_ok']:>7}{sr['split_pct']:>9.4f}")
        if a.forms:
            for name, fn in (("NFC", lambda t: ud.normalize("NFC", t)),
                             ("NFD", lambda t: ud.normalize("NFD", t))):
                res["scripts"][s][name] = fertility(tok, [fn(x) for x in L])

    res["vocab"] = vocab_composition(sp, a2p)
    v = res["vocab"]
    print(f"  vocab {v['vocab_size']}  indic {v['counts']['indic']} ({v['indic_pct']:.2f}%)"
          f"  latin {v['counts']['latin']} ({v['latin_pct']:.2f}%, mean len {v['latin_mean_len']:.2f})"
          f"  bf {v['counts']['byte_fallback']}  digit {v['counts']['digit']}"
          f"  other {v['counts']['other']}  special {v['counts']['special']}")

    if a.json:
        json.dump(res, open(a.json, "w"), indent=1)
        print(f"WROTE {a.json}")


if __name__ == "__main__":
    main()
