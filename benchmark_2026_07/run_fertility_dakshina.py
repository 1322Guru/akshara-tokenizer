#!/usr/bin/env python3
"""Dakshina romanized-vs-native fertility benchmark: v1.2 (64k), v1.1 (16k), Qwen3-14B.

Companion to run_fertility_v1_2.py, which measures FLORES-200 native script only. This one
answers a different question: what the tokenizer costs on HUMAN-romanized Indic text, the
form users actually type. It is a separate file by design; run_fertility_v1_2.py is not
modified and its published numbers are unaffected.

Why Dakshina rather than a romanized split of a pretraining corpus: AI4Bharat Sangraha does
carry romanized splits (config `synthetic`, e.g. hin_Latn), but they are MACHINE
transliterations with an idiosyncratic scheme ("haye" for है, "ack" for एक, "joe" for जो).
Dakshina's romanizations are human-produced, so English loanwords keep English spelling
("Ribosome", "November", "hiking") and native spelling varies the way real writing does.

Data: dakshina_dataset_v1.0/<L>/romanized/<L>.romanized.rejoined.tsv
  10,000 lines, two tab-separated fields, native <TAB> roman, the SAME sentence in both.
  The sibling *.aligned.tsv is word-level alignment and is deliberately NOT used.
  Matched pairs matter: roman and native fertility are then measured on identical content,
  so the difference is the script and not the sample.

Filter (applied to the NATIVE side only, so one decision governs both sides):
  40 <= chars <= 200 and >= 6 whitespace words. Up to 600 pairs per language, in file
  order, no shuffle, so the set is reproducible from the file alone.

Metrics match run_fertility_v1_2.py: encode PER LINE, then divide total tokens by total
words and by total chars. Byte-fallback is the share of tokens whose piece is <0xXX>.

Usage:
  python3 run_fertility_dakshina.py \
      --dakshina-root /path/to/dakshina_dataset_v1.0 \
      --qwen-tokenizer /path/to/qwen/tokenizer.json
"""
import argparse
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

import sentencepiece as spm
from importlib.resources import files as _pkg_files

from akshara_tokenizer import segment_aksharas
from akshara_tokenizer import AksharaTokenizer

LANGS = {"hi": "Hindi (Devanagari)", "pa": "Punjabi (Gurmukhi)", "ta": "Tamil"}
_BYTE = re.compile(r'^<0x[0-9A-Fa-f]{2}>$')

ap = argparse.ArgumentParser(description="AksharaTokenizer Dakshina romanized fertility benchmark")
ap.add_argument("--dakshina-root", required=True,
                help="path to an extracted dakshina_dataset_v1.0 directory")
ap.add_argument("--qwen-tokenizer", default=os.environ.get("QWEN_TOKENIZER_JSON"),
                help="path to a Qwen3 tokenizer.json for the BPE baseline column")
ap.add_argument("--out", default=os.path.join(HERE, "results_dakshina_fertility.csv"))
ap.add_argument("--pairs", type=int, default=600, help="max matched pairs per language")
args = ap.parse_args()


def _v11_model():
    return str(_pkg_files("akshara_tokenizer").joinpath("model", "akshara_tokenizer_v1_1.model"))


def load_pairs(root, lang, want):
    """Matched native/roman sentence pairs, filtered on the native side."""
    path = os.path.join(root, lang, "romanized", f"{lang}.romanized.rejoined.tsv")
    pairs = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 2:
                continue
            native, roman = parts[0].strip(), parts[1].strip()
            if not native or not roman:
                continue
            if not (40 <= len(native) <= 200):
                continue
            if len(native.split()) < 6:
                continue
            pairs.append((native, roman))
            if len(pairs) >= want:
                break
    return pairs


def main():
    v12 = AksharaTokenizer.load()
    sp12 = v12._sp
    sp11 = spm.SentencePieceProcessor(model_file=_v11_model())

    qwen = None
    if args.qwen_tokenizer:
        from tokenizers import Tokenizer
        qwen = Tokenizer.from_file(args.qwen_tokenizer)
        # Fine-tuned checkpoints bake padding and truncation to 2048 into tokenizer.json.
        # Left as loaded, every encode returns 2048 ids and fertility is meaningless
        # (about 116 tokens per word). Disable both before measuring.
        qwen.no_padding()
        qwen.no_truncation()

    fields = ["language", "side", "tokenizer", "lines", "chars", "words", "tokens",
              "tok_per_100char", "fertility_tok_per_word", "bytefallback_pct",
              "roundtrip_ok", "roundtrip_n"]
    rows = []

    for lang, label in LANGS.items():
        pairs = load_pairs(args.dakshina_root, lang, args.pairs)
        if not pairs:
            print(f"{lang}: no matched pairs found, skipping", file=sys.stderr)
            continue

        for side, idx in (("roman", 1), ("native", 0)):
            lines = [p[idx] for p in pairs]
            chars = sum(len(x) for x in lines)
            words = sum(len(x.split()) for x in lines)

            ids12, bf12, rt12 = [], 0, 0
            ids11, bf11, rt11 = [], 0, 0
            idsq, rtq = [], 0
            for x in lines:
                a = v12.encode(x)
                ids12 += a
                bf12 += sum(1 for i in a if _BYTE.match(sp12.id_to_piece(i)))
                rt12 += (v12.decode(a) == x)

                b = sp11.encode(" ".join(segment_aksharas(x)))
                ids11 += b
                bf11 += sum(1 for i in b if _BYTE.match(sp11.id_to_piece(i)))
                rt11 += (sp11.decode(b) == x)

                if qwen is not None:
                    c = qwen.encode(x, add_special_tokens=False).ids
                    idsq += c
                    rtq += (qwen.decode(c) == x)

            cols = [("akshara_v1_2_64k", ids12, 100.0 * bf12 / max(len(ids12), 1), rt12),
                    ("akshara_v1_1_16k", ids11, 100.0 * bf11 / max(len(ids11), 1), rt11)]
            if qwen is not None:
                cols.append(("qwen3_14b", idsq, 0.0, rtq))

            for name, ids, bf, rt in cols:
                rows.append({
                    "language": label, "side": side, "tokenizer": name,
                    "lines": len(lines), "chars": chars, "words": words,
                    "tokens": len(ids),
                    "tok_per_100char": round(100.0 * len(ids) / chars, 4),
                    "fertility_tok_per_word": round(len(ids) / words, 4),
                    "bytefallback_pct": round(bf, 4),
                    "roundtrip_ok": rt, "roundtrip_n": len(lines),
                })

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    for r in rows:
        print(r["language"], r["side"], r["tokenizer"],
              "| fert", r["fertility_tok_per_word"],
              "| t/100c", r["tok_per_100char"],
              "| bf%", r["bytefallback_pct"],
              "| rt", f"{r['roundtrip_ok']}/{r['roundtrip_n']}")

    print("\nROMAN-side overhead, v1.2 vs Qwen:")
    for lang, label in LANGS.items():
        a = next((r for r in rows if r["language"] == label and r["side"] == "roman"
                  and r["tokenizer"] == "akshara_v1_2_64k"), None)
        q = next((r for r in rows if r["language"] == label and r["side"] == "roman"
                  and r["tokenizer"] == "qwen3_14b"), None)
        if a and q and q["tokens"]:
            print(f"  {label:22} {100.0 * (a['tokens'] - q['tokens']) / q['tokens']:+6.1f}%")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
