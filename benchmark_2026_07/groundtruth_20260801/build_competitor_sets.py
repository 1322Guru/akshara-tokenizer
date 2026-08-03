#!/usr/bin/env python3
"""STEP 3: assemble every eval category for the competitor benchmark.

A. native   : benchmark_2026_07/eval_<script>.txt, the exact files results_v1_2.md used
              (verified identical to the full 1,012-line FLORES-200 devtest)
B. romanized: the SAME 600 matched Dakshina pairs per language built on 1 Aug, reused
              verbatim from dakshina_pairs.json (deterministic: file order, no shuffle)
C. hinglish : findnitai/english-to-hinglish, translation.hi_ng, filtered to source == 1
              (human annotated, NOT synthetic). Plus the original 28 Jul cmu_hinglish_dog
              200 kept as a separate category so that figure stays traceable.
D. english  : the same 200 FLORES English lines used on 28 Jul, from evalset.json
"""
import json, urllib.parse, urllib.request

SCR = "/tmp/claude-1001/-mnt-d-GuruAI/720b6049-09fb-4708-bc14-14a5cba6a101/scratchpad"
BENCH = "/mnt/d/GuruAI/akshara_tokenizer/benchmark_2026_07"
OUT = f"{SCR}/competitor_sets.json"
VIEWER = "https://datasets-server.huggingface.co/rows"

sets = {}

# ---- A. native, full devtest as used by results_v1_2.md ----
for script in ("devanagari", "gurmukhi", "tamil", "telugu", "bengali", "kannada"):
    lines = [l.rstrip("\n") for l in open(f"{BENCH}/eval_{script}.txt", encoding="utf-8") if l.strip()]
    sets[f"native_{script}"] = lines

# ---- B. romanized, reuse the exact 1 Aug selection ----
pairs = json.load(open(f"{SCR}/dakshina_pairs.json"))
for L, name in (("hi", "hindi"), ("pa", "punjabi"), ("ta", "tamil")):
    sets[f"romanized_{name}"] = [p["roman"] for p in pairs[L]]

# ---- C1. hinglish, 28 Jul cmu set, unchanged ----
old = json.load(open(f"{SCR}/evalset.json"))
sets["hinglish_cmu_28jul"] = old["code_switched_hinglish"]

# ---- D. english, 28 Jul FLORES 200, unchanged ----
sets["english_flores200"] = old["flores_english"]

# ---- C2. hinglish, new human-annotated set ----
def fetch(offset, length=100):
    q = urllib.parse.urlencode({"dataset": "findnitai/english-to-hinglish",
                                "config": "default", "split": "train",
                                "offset": offset, "length": length})
    with urllib.request.urlopen(f"{VIEWER}?{q}", timeout=120) as r:
        return json.load(r)

got, seen, offset = [], set(), 0
skipped_synthetic = 0
while len(got) < 600 and offset < 40000:
    try:
        d = fetch(offset)
    except Exception as e:
        print(f"    fetch error at {offset}: {e}")
        break
    rows = d.get("rows", [])
    if not rows:
        break
    for r in rows:
        tr = r["row"].get("translation") or {}
        if tr.get("source") != 1:            # human annotated only
            skipped_synthetic += 1
            continue
        t = " ".join(str(tr.get("hi_ng", "")).split())
        if not (40 <= len(t) <= 200):
            continue
        if len(t.split()) < 6:
            continue
        k = t.lower()
        if k in seen:
            continue
        seen.add(k)
        got.append(t)
        if len(got) >= 600:
            break
    offset += 100
sets["hinglish_findnitai_human"] = got
print(f"  hinglish_findnitai_human: kept {len(got)}, skipped {skipped_synthetic} non-source-1 rows")

json.dump(sets, open(OUT, "w"), ensure_ascii=False, indent=1)
print(f"\nwrote {OUT}\n")
print(f"{'category':30}{'n':>7}{'mean chars':>12}{'mean words':>12}")
for k, v in sets.items():
    if not v:
        print(f"{k:30}{0:>7}  EMPTY")
        continue
    mc = sum(len(x) for x in v) / len(v)
    mw = sum(len(x.split()) for x in v) / len(v)
    print(f"{k:30}{len(v):>7}{mc:>12.1f}{mw:>12.2f}")

print("\n=== 3 samples from the NEW hinglish set ===")
for s in sets["hinglish_findnitai_human"][:3]:
    print(f"  {s}")
