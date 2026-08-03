#!/usr/bin/env python3
"""Verify or refute the Qwen3-14B round-trip failure reported in
results_competitor_comparison.md, testing the STOCK Qwen/Qwen3-14B tokenizer against the
local fine-tune's tokenizer.

The claim under test: "Qwen3-14B round-trips poorly on Gurmukhi (439/1,012) and Bengali
(403/1,012)". That was measured with a fine-tuned checkpoint's tokenizer.json, so it could
be an artifact of the fine-tune rather than a property of Qwen3.

Tokenizer files only. No weights are downloaded. Read-only: nothing in the package, the
v1.2 artifacts or the published results is modified.

Usage:
  python3 verify_qwen_roundtrip.py \
      --stock     /mnt/c/GuruAI-Data/competitor_tokenizers/qwen3-14b-stock/tokenizer.json \
      --finetune  /mnt/d/GuruAI/models/finetuned/guruai-qwen3-14b-nyaya-1681/tokenizer.json
"""
import argparse
import json
import os
import sys
import unicodedata as ud

HERE = os.path.dirname(os.path.abspath(__file__))

DEFAULT_STOCK = "/mnt/c/GuruAI-Data/competitor_tokenizers/qwen3-14b-stock/tokenizer.json"
DEFAULT_FINETUNE = "/mnt/d/GuruAI/models/finetuned/guruai-qwen3-14b-nyaya-1681/tokenizer.json"

SCRIPTS = ["devanagari", "gurmukhi", "tamil", "telugu", "bengali", "kannada"]

# Minimal probe set. Precomposed nukta letters that NFC decomposes, plus controls that
# NFC leaves alone. If the controls fail too, the normalization hypothesis is wrong.
PROBE = [
    ("Gurmukhi", 0x0A36), ("Gurmukhi", 0x0A59), ("Gurmukhi", 0x0A5A),
    ("Gurmukhi", 0x0A5B), ("Gurmukhi", 0x0A5E), ("Gurmukhi", 0x0A5C),
    ("Bengali", 0x09DC), ("Bengali", 0x09DD), ("Bengali", 0x09DF),
    ("Devanagari ctrl", 0x0929), ("Devanagari ctrl", 0x0931), ("Devanagari ctrl", 0x0934),
    ("plain, no nukta", 0x0A15), ("plain, no nukta", 0x0995), ("plain, no nukta", 0x0915),
]


def load(path):
    from tokenizers import Tokenizer
    t = Tokenizer.from_file(path)
    t.no_padding()
    t.no_truncation()
    return t


def structural_diff(stock_path, ft_path):
    S = json.load(open(stock_path, encoding="utf-8"))
    F = json.load(open(ft_path, encoding="utf-8"))
    out = {}
    for field in ["normalizer", "pre_tokenizer", "decoder", "post_processor",
                  "truncation", "padding"]:
        out[field] = {"stock": S.get(field, "<absent>"), "finetune": F.get(field, "<absent>"),
                      "identical": S.get(field, "<absent>") == F.get(field, "<absent>")}
    sa = {t["content"] for t in S.get("added_tokens", [])}
    fa = {t["content"] for t in F.get("added_tokens", [])}
    out["added_tokens"] = {"stock_count": len(sa), "finetune_count": len(fa),
                           "only_in_finetune": sorted(fa - sa), "only_in_stock": sorted(sa - fa)}
    out["vocab_identical"] = S["model"]["vocab"] == F["model"]["vocab"]
    out["merges_identical"] = S["model"].get("merges") == F["model"].get("merges")
    return out


def probe_chars(toks):
    rows = []
    for grp, cp in PROBE:
        ch = chr(cp)
        nfc = ud.normalize("NFC", ch)
        row = {"group": grp, "cp": f"U+{cp:04X}", "char": ch,
               "nfc_stable": nfc == ch,
               "nfc_form": " ".join(f"U+{ord(c):04X}" for c in nfc)}
        for name, t in toks.items():
            ids = t.encode(ch, add_special_tokens=False).ids
            row[name] = (t.decode(ids) == ch)
        rows.append(row)
    return rows


def roundtrip_scripts(toks, eval_dir):
    res = {}
    for s in SCRIPTS:
        p = os.path.join(eval_dir, f"eval_{s}.txt")
        lines = [l.rstrip("\n") for l in open(p, encoding="utf-8") if l.strip()]
        r = {"n": len(lines)}
        for name, t in toks.items():
            ok = 0
            for x in lines:
                ids = t.encode(x, add_special_tokens=False).ids
                ok += (t.decode(ids) == x)
            r[name] = ok
        # how many lines are already NFC-stable: the ceiling for an NFC normalizer
        r["nfc_stable_lines"] = sum(1 for x in lines if ud.normalize("NFC", x) == x)
        res[s] = r
    return res


def failing_examples(tok, eval_dir, script, k=3):
    p = os.path.join(eval_dir, f"eval_{script}.txt")
    lines = [l.rstrip("\n") for l in open(p, encoding="utf-8") if l.strip()]
    out = []
    for x in lines:
        ids = tok.encode(x, add_special_tokens=False).ids
        y = tok.decode(ids)
        if y == x:
            continue
        diffs = []
        for a, b in zip(x, y):
            if a != b:
                diffs.append((a, b))
        # codepoints present in input but not output
        lost = [c for c in set(x) - set(y)]
        gained = [c for c in set(y) - set(x)]
        out.append({
            "input_prefix": x[:60],
            "in_bytes": x.encode("utf-8")[:40].hex(),
            "out_bytes": y.encode("utf-8")[:40].hex(),
            "lost_codepoints": [f"U+{ord(c):04X}" for c in lost],
            "gained_codepoints": [f"U+{ord(c):04X}" for c in gained],
            "output_equals_nfc_of_input": (y == ud.normalize("NFC", x)),
        })
        if len(out) >= k:
            break
    return out


def main():
    ap = argparse.ArgumentParser(description="Qwen3-14B round-trip verification")
    ap.add_argument("--stock", default=DEFAULT_STOCK)
    ap.add_argument("--finetune", default=DEFAULT_FINETUNE)
    ap.add_argument("--eval-dir", default=HERE)
    args = ap.parse_args()

    toks = {"stock": load(args.stock), "finetune": load(args.finetune)}

    print("=== structural diff ===")
    d = structural_diff(args.stock, args.finetune)
    for f in ["normalizer", "pre_tokenizer", "decoder", "post_processor", "truncation", "padding"]:
        print(f"  {f:15} identical={d[f]['identical']}")
        if not d[f]["identical"]:
            print(f"      stock    : {json.dumps(d[f]['stock'], ensure_ascii=False)[:150]}")
            print(f"      finetune : {json.dumps(d[f]['finetune'], ensure_ascii=False)[:150]}")
    print(f"  added_tokens    only_in_finetune={d['added_tokens']['only_in_finetune']}")
    print(f"  vocab identical={d['vocab_identical']}  merges identical={d['merges_identical']}")

    print("\n=== minimal case: single characters ===")
    print(f"  {'group':17}{'cp':9}{'nfc_stable':12}{'stock':8}{'finetune':10}nfc_form")
    for r in probe_chars(toks):
        print(f"  {r['group']:17}{r['cp']:9}{str(r['nfc_stable']):12}"
              f"{str(r['stock']):8}{str(r['finetune']):10}{r['nfc_form']}")

    print("\n=== round-trip, six scripts, full eval files ===")
    print(f"  {'script':14}{'n':>6}{'stock':>9}{'finetune':>10}{'nfc_stable':>12}")
    rt = roundtrip_scripts(toks, args.eval_dir)
    for s, r in rt.items():
        print(f"  {s:14}{r['n']:>6}{r['stock']:>9}{r['finetune']:>10}{r['nfc_stable_lines']:>12}")

    print("\n=== failing line diagnosis ===")
    for script in ("gurmukhi", "bengali"):
        print(f"  --- {script} (stock tokenizer) ---")
        for e in failing_examples(toks["stock"], args.eval_dir, script, 3):
            print(f"    input : {e['input_prefix']}")
            print(f"    in    : {e['in_bytes']}")
            print(f"    out   : {e['out_bytes']}")
            print(f"    lost  : {e['lost_codepoints']}   gained: {e['gained_codepoints']}")
            print(f"    output == NFC(input): {e['output_equals_nfc_of_input']}")
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
