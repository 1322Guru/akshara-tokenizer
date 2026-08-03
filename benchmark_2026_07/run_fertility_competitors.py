#!/usr/bin/env python3
"""Competitor benchmark: AksharaTokenizer v1.2 against Indic-specific tokenizers.

Regenerates the tables in results_competitor_comparison.md. Companion to
run_fertility_v1_2.py (native script, v1.2 vs v1.1 vs Qwen) and run_fertility_dakshina.py
(romanized Indic); neither of those is modified by this file.

Tokenizers, five:
  AksharaTokenizer v1.2 (64k)  packaged model + map, this repo
  sarvam-1        (68,096)     sarvamai/sarvam-1
  sarvam-30b      (262,144)    sarvamai/sarvam-30b
  Krutrim-2       (131,072)    krutrim-ai-labs/Krutrim-2-instruct
  Qwen3-14B       (151,670)    a local Qwen3 checkpoint's tokenizer.json
Only tokenizer.json is needed from each competitor. No model weights.

Categories, eleven:
  1-6   native_<script>   eval_<script>.txt, full 1,012-line FLORES-200 devtest, the same
                          files results_v1_2.md used
  7-9   romanized_<lang>  600 matched Dakshina pairs per language, roman side, rebuilt
                          deterministically from the Dakshina TSVs (file order, no shuffle)
  10    hinglish_findnitai_human  600 lines, materialised OUTSIDE the repo by
                          build_hinglish_set.py and verified against
                          hinglish_findnitai_manifest.json before use
  11    english_flores200 first 200 lines of eval_english.txt

NOT regenerated here: the 28 July hinglish_cmu_28jul set (n=200, festvox/cmu_hinglish_dog).
It is an archived measurement retained in results_competitor_comparison.md for traceability.
Its selection came from a paginated API pull that is not deterministically reproducible, and
the corpus text is third-party and deliberately not vendored, so this harness omits it
rather than emit a number it cannot stand behind.

Fairness rules, all load-bearing for the published numbers:
  add_special_tokens=False, no_padding(), no_truncation(), encode PER LINE never whole-file.
Byte-fallback is reported only for v1.2, which is SentencePiece and exposes <0xXX> pieces.
The competitors are byte-level BPE with no fallback pieces by construction, so their column
is "n/a (byte-level BPE)" rather than a measured zero.

Usage:
  python3 run_fertility_competitors.py \
      --dakshina-root    /mnt/c/GuruAI-Data/dakshina/dakshina_dataset_v1.0 \
      --competitor-dir   /mnt/c/GuruAI-Data/competitor_tokenizers \
      --qwen-tokenizer   /path/to/qwen/tokenizer.json \
      --hinglish-set     /mnt/c/GuruAI-Data/hinglish/hinglish_findnitai_600.json
"""
import argparse
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

from akshara_tokenizer import AksharaTokenizer

# ---- documented default paths, override on the command line -------------------------
DEFAULT_DAKSHINA = "/mnt/c/GuruAI-Data/dakshina/dakshina_dataset_v1.0"
DEFAULT_COMPETITOR_DIR = "/mnt/c/GuruAI-Data/competitor_tokenizers"
DEFAULT_QWEN = "/mnt/d/GuruAI/models/finetuned/guruai-qwen3-14b-nyaya-1681/tokenizer.json"
DEFAULT_HINGLISH = "/mnt/c/GuruAI-Data/hinglish/hinglish_findnitai_600.json"
MANIFEST = os.path.join(HERE, "hinglish_findnitai_manifest.json")

COMPETITOR_SUBDIRS = {
    "sarvam-1":   "sarvamai__sarvam-1",
    "sarvam-30b": "sarvamai__sarvam-30b",
    "Krutrim-2":  "krutrim-ai-labs__Krutrim-2-instruct",
}
NATIVE_SCRIPTS = ["devanagari", "gurmukhi", "tamil", "telugu", "bengali", "kannada"]
DAKSHINA_LANGS = [("hi", "hindi"), ("pa", "punjabi"), ("ta", "tamil")]
ENGLISH_N = 200
DAKSHINA_PAIRS = 600
_BYTE = re.compile(r'^<0x[0-9A-Fa-f]{2}>$')

# published v1.2 native figures, used as a self-check gate
PUBLISHED_NATIVE = {"devanagari": 1.374, "gurmukhi": 1.445, "tamil": 1.953,
                    "telugu": 2.001, "bengali": 1.797, "kannada": 2.058}
PUBLISHED_OVERALL = 1.717


def load_dakshina_roman(root, lang, want=DAKSHINA_PAIRS):
    """Roman side of the matched pairs. Same rule as run_fertility_dakshina.py: filter on
    the NATIVE side, 40 to 200 chars and at least 6 words, file order, no shuffle."""
    path = os.path.join(root, lang, "romanized", f"{lang}.romanized.rejoined.tsv")
    out = []
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
            out.append(roman)
            if len(out) >= want:
                break
    return out


def load_hinglish(path, manifest_path=MANIFEST):
    """Load the materialised Hinglish set and verify it against the repo manifest."""
    if not os.path.isfile(path):
        return None, (f"hinglish set not found at {path}. Materialise it first: "
                      f"python3 build_hinglish_set.py --out {path}")
    lines = json.load(open(path, encoding="utf-8"))
    sys.path.insert(0, HERE)
    from build_hinglish_set import verify
    ok, msg = verify(lines, manifest_path)
    if not ok:
        return None, f"hinglish set does not match manifest: {msg}"
    return lines, f"verified against manifest ({len(lines)} lines)"


def build_categories(args):
    cats = {}
    for s in NATIVE_SCRIPTS:
        p = os.path.join(HERE, f"eval_{s}.txt")
        cats[f"native_{s}"] = [l.rstrip("\n") for l in open(p, encoding="utf-8") if l.strip()]
    for code, name in DAKSHINA_LANGS:
        cats[f"romanized_{name}"] = load_dakshina_roman(args.dakshina_root, code)
    eng = [l.rstrip("\n") for l in open(os.path.join(HERE, "eval_english.txt"),
                                        encoding="utf-8") if l.strip()]
    cats["english_flores200"] = eng[:ENGLISH_N]
    return cats


def main():
    ap = argparse.ArgumentParser(description="AksharaTokenizer competitor benchmark")
    ap.add_argument("--dakshina-root", default=DEFAULT_DAKSHINA)
    ap.add_argument("--competitor-dir", default=DEFAULT_COMPETITOR_DIR)
    ap.add_argument("--qwen-tokenizer", default=os.environ.get("QWEN_TOKENIZER_JSON", DEFAULT_QWEN))
    ap.add_argument("--hinglish-set", default=DEFAULT_HINGLISH)
    ap.add_argument("--out", default=os.path.join(HERE, "results_competitor_fertility.csv"))
    args = ap.parse_args()

    from tokenizers import Tokenizer

    v12 = AksharaTokenizer.load()
    sp12 = v12._sp

    hf = {}
    for name, sub in COMPETITOR_SUBDIRS.items():
        p = os.path.join(args.competitor_dir, sub, "tokenizer.json")
        if not os.path.isfile(p):
            print(f"missing competitor tokenizer: {p}", file=sys.stderr)
            sys.exit(2)
        hf[name] = Tokenizer.from_file(p)
    hf["Qwen3-14B"] = Tokenizer.from_file(args.qwen_tokenizer)
    for t in hf.values():
        # Fine-tuned checkpoints can bake padding and truncation to 2048 into
        # tokenizer.json. Left as loaded, every encode returns 2048 ids and fertility is
        # meaningless (about 116 tokens per word).
        t.no_padding()
        t.no_truncation()

    vocab = {"v1.2 (64k)": sp12.get_piece_size()}
    vocab.update({k: t.get_vocab_size() for k, t in hf.items()})
    print("vocab sizes:")
    for k, v in vocab.items():
        print(f"  {k:12} {v:>9,}")

    cats = build_categories(args)
    hing, hmsg = load_hinglish(args.hinglish_set)
    if hing is None:
        print(f"\nWARNING: {hmsg}\n  Hinglish category SKIPPED, no number emitted.",
              file=sys.stderr)
    else:
        cats["hinglish_findnitai_human"] = hing
        print(f"\nhinglish: {hmsg}")

    order = ([f"native_{s}" for s in NATIVE_SCRIPTS]
             + [f"romanized_{n}" for _, n in DAKSHINA_LANGS]
             + (["hinglish_findnitai_human"] if hing is not None else [])
             + ["english_flores200"])

    fields = ["category", "tokenizer", "vocab", "lines", "chars", "words", "tokens",
              "tok_per_100char", "fertility_tok_per_word", "bytefallback_pct",
              "roundtrip_ok", "roundtrip_n"]
    rows = []
    nat_tok = nat_words = 0

    for cat in order:
        lines = cats[cat]
        chars = sum(len(x) for x in lines)
        words = sum(len(x.split()) for x in lines)

        tok = bf = rt = 0
        for x in lines:
            ids = v12.encode(x)
            tok += len(ids)
            bf += sum(1 for i in ids if _BYTE.match(sp12.id_to_piece(i)))
            rt += (v12.decode(ids) == x)
        if cat.startswith("native_"):
            nat_tok += tok
            nat_words += words
        rows.append({"category": cat, "tokenizer": "v1.2 (64k)", "vocab": vocab["v1.2 (64k)"],
                     "lines": len(lines), "chars": chars, "words": words, "tokens": tok,
                     "tok_per_100char": round(100.0 * tok / chars, 4),
                     "fertility_tok_per_word": round(tok / words, 4),
                     "bytefallback_pct": round(100.0 * bf / max(tok, 1), 4),
                     "roundtrip_ok": rt, "roundtrip_n": len(lines)})

        for name, t in hf.items():
            tok = rt = 0
            for x in lines:
                ids = t.encode(x, add_special_tokens=False).ids
                tok += len(ids)
                rt += (t.decode(ids) == x)
            rows.append({"category": cat, "tokenizer": name, "vocab": vocab[name],
                         "lines": len(lines), "chars": chars, "words": words, "tokens": tok,
                         "tok_per_100char": round(100.0 * tok / chars, 4),
                         "fertility_tok_per_word": round(tok / words, 4),
                         "bytefallback_pct": "n/a (byte-level BPE)",
                         "roundtrip_ok": rt, "roundtrip_n": len(lines)})

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print()
    for cat in order:
        sub = [r for r in rows if r["category"] == cat]
        print(f"{cat}  n={sub[0]['lines']}")
        for r in sub:
            bfs = r["bytefallback_pct"]
            bfs = f"{bfs:.3f}" if isinstance(bfs, float) else "n/a"
            print(f"   {r['tokenizer']:12} fert {r['fertility_tok_per_word']:7.3f}  "
                  f"t/100c {r['tok_per_100char']:7.2f}  bf {bfs:>6}  "
                  f"rt {r['roundtrip_ok']}/{r['roundtrip_n']}")
        print()

    # self-check gate against the published v1.2 native figures
    print("gate: v1.2 native vs results_v1_2.md")
    ok = True
    for s, pub in PUBLISHED_NATIVE.items():
        got = next(r["fertility_tok_per_word"] for r in rows
                   if r["category"] == f"native_{s}" and r["tokenizer"] == "v1.2 (64k)")
        good = abs(got - pub) < 0.0006
        ok &= good
        print(f"  {s:12} {got:.4f} vs {pub:.3f}  {'MATCH' if good else 'MISMATCH'}")
    overall = nat_tok / nat_words
    good = abs(overall - PUBLISHED_OVERALL) < 0.0006
    ok &= good
    print(f"  {'overall':12} {overall:.4f} vs {PUBLISHED_OVERALL:.3f}  {'MATCH' if good else 'MISMATCH'}")
    print(f"  GATE: {'PASS' if ok else 'FAIL'}")
    print(f"\nwrote {args.out}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
