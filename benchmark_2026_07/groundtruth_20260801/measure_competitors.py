#!/usr/bin/env python3
"""STEP 4: five tokenizers across native, romanized, code-switched and English.

Fairness rules applied to every HuggingFace tokenizer:
  add_special_tokens=False, no_padding(), no_truncation(), encode PER LINE.
Byte-fallback is reported only for v1.2 (SentencePiece, exposes <0xXX> pieces).
The HF tokenizers are byte-level BPE and have no fallback pieces by construction,
so the column is n/a rather than a measured zero.
"""
import json, re, sys
sys.path.insert(0, "/mnt/d/GuruAI/akshara_tokenizer")
from akshara_tokenizer.tokenizer import AksharaTokenizer
from tokenizers import Tokenizer

SCR = "/tmp/claude-1001/-mnt-d-GuruAI/720b6049-09fb-4708-bc14-14a5cba6a101/scratchpad"
C = "/mnt/c/GuruAI-Data/competitor_tokenizers"
S = json.load(open(f"{SCR}/competitor_sets.json"))

v12 = AksharaTokenizer.load()
sp12 = v12._sp
_BYTE = re.compile(r'^<0x[0-9A-Fa-f]{2}>$')

HF_PATHS = [
    ("sarvam-1",   f"{C}/sarvamai__sarvam-1/tokenizer.json"),
    ("sarvam-30b", f"{C}/sarvamai__sarvam-30b/tokenizer.json"),
    ("Krutrim-2",  f"{C}/krutrim-ai-labs__Krutrim-2-instruct/tokenizer.json"),
    ("Qwen3-14B",  "/mnt/d/GuruAI/models/finetuned/guruai-qwen3-14b-nyaya-1681/tokenizer.json"),
]
HF = {}
for name, p in HF_PATHS:
    t = Tokenizer.from_file(p)
    t.no_padding()
    t.no_truncation()
    HF[name] = t

VOCAB = {"v1.2 (64k)": sp12.get_piece_size()}
for n, t in HF.items():
    VOCAB[n] = t.get_vocab_size()

CATS = ["native_devanagari", "native_gurmukhi", "native_tamil",
        "native_telugu", "native_bengali", "native_kannada",
        "romanized_hindi", "romanized_punjabi", "romanized_tamil",
        "hinglish_cmu_28jul", "hinglish_findnitai_human", "english_flores200"]

results = {}
for cat in CATS:
    lines = S[cat]
    words = sum(len(x.split()) for x in lines)
    chars = sum(len(x) for x in lines)
    n = len(lines)
    row = {}

    tok = bf = rt = 0
    for x in lines:
        ids = v12.encode(x)
        tok += len(ids)
        bf += sum(1 for i in ids if _BYTE.match(sp12.id_to_piece(i)))
        rt += (v12.decode(ids) == x)
    row["v1.2 (64k)"] = {"tokens": tok, "fertility": tok / words,
                         "tok_per_100char": 100.0 * tok / chars,
                         "bytefallback_pct": 100.0 * bf / max(tok, 1),
                         "roundtrip_ok": rt, "n": n}

    for name, t in HF.items():
        tok = rt = 0
        for x in lines:
            ids = t.encode(x, add_special_tokens=False).ids
            tok += len(ids)
            rt += (t.decode(ids) == x)
        row[name] = {"tokens": tok, "fertility": tok / words,
                     "tok_per_100char": 100.0 * tok / chars,
                     "bytefallback_pct": None, "roundtrip_ok": rt, "n": n}

    results[cat] = {"n": n, "words": words, "chars": chars, "tok": row}
    best = min(row.items(), key=lambda kv: kv[1]["fertility"])[0]
    print(f"\n{cat}  n={n}")
    for k, v in row.items():
        bfs = "n/a" if v["bytefallback_pct"] is None else f"{v['bytefallback_pct']:.3f}"
        mark = "  <-- best" if k == best else ""
        print(f"   {k:12} fert {v['fertility']:7.3f}  t/100c {v['tok_per_100char']:7.2f}  "
              f"bf {bfs:>6}  rt {v['roundtrip_ok']}/{v['n']}{mark}")

json.dump({"vocab": VOCAB, "results": results}, open(f"{SCR}/competitor_results.json", "w"), indent=1)
print("\nwrote competitor_results.json")
print("\nvocab sizes:", VOCAB)
