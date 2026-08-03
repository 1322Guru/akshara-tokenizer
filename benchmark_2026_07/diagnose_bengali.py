#!/usr/bin/env python3
"""Normalization-robustness check for AksharaTokenizer v1.2.

Started as a Bengali-gap diagnostic. The full competitor table showed v1.2 beats the
budget-matched sarvam-1 (68k) on Bengali by 12.97 percent and loses only to sarvam-30b
(262k, 4.1x the budget), so there was no Bengali-specific defect to chase. The question
that remained, and that this script answers, is whether v1.2's fertility and round-trip
depend on the Unicode normalization form of the input.

Measures, per native script:
  - map coverage: distinct aksharas in the eval text that are present in the map versus
    those that fall through to sub-akshara SentencePiece splitting
  - fertility and round-trip on the text as is, on NFC(text) and on NFD(text)
  - NFC-unstable map entries, and whether the map holds both forms of any character

Read-only. Nothing in the package, the v1.2 artifacts or the published results is
modified. Fertility is measured PER LINE with whitespace words, matching
run_fertility_competitors.py, so the as-is column reproduces the published figures.

Usage:
  python3 diagnose_bengali.py
"""
import json
import os
import sys
import unicodedata as ud
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

from akshara_tokenizer import AksharaTokenizer, segment_aksharas

SCRIPTS = ["devanagari", "gurmukhi", "tamil", "telugu", "bengali", "kannada"]
COVERAGE_SCRIPTS = ["bengali", "kannada", "telugu"]

# Unicode blocks, used only to attribute a map entry to a script for reporting.
BLOCKS = [
    ("devanagari", 0x0900, 0x097F), ("bengali", 0x0980, 0x09FF),
    ("gurmukhi", 0x0A00, 0x0A7F), ("gujarati", 0x0A80, 0x0AFF),
    ("oriya", 0x0B00, 0x0B7F), ("tamil", 0x0B80, 0x0BFF),
    ("telugu", 0x0C00, 0x0C7F), ("kannada", 0x0C80, 0x0CFF),
    ("malayalam", 0x0D00, 0x0D7F),
]


def script_of(s):
    for ch in s:
        cp = ord(ch)
        for name, lo, hi in BLOCKS:
            if lo <= cp <= hi:
                return name
    return "other"


def lines_of(script):
    p = os.path.join(HERE, f"eval_{script}.txt")
    return [l.rstrip("\n") for l in open(p, encoding="utf-8") if l.strip()]


def measure(tok, lines):
    """Fertility (tok per whitespace word) and round-trip count, per line."""
    ntok = nword = rt = 0
    for x in lines:
        ids = tok.encode(x)
        ntok += len(ids)
        nword += len(x.split())
        rt += (tok.decode(ids) == x)
    return {"tokens": ntok, "words": nword, "fertility": ntok / nword,
            "roundtrip_ok": rt, "n": len(lines)}


def main():
    tok = AksharaTokenizer.load()
    a2p = tok._a2p
    mp = json.load(open(os.path.join(
        REPO, "akshara_tokenizer", "model", "akshara_tokenizer_v1_2.map.json"),
        encoding="utf-8"))
    entries = list(mp["aksharas"].keys())

    # ---- STEP 2: map entry counts and eval coverage ----------------------
    print("=== map entries per script ===")
    per_script = Counter(script_of(k) for k in entries)
    print(f"  total {len(entries)}")
    for k, v in per_script.most_common():
        print(f"    {k:12} {v:6}")

    # Whitespace is deliberately not a map entry: SentencePiece handles word boundaries
    # itself. Counting it as a fall-through makes occurrence-weighted coverage look like
    # 77 percent when the space alone is 22 percent of all segmented units, so it is
    # excluded here and the exclusion is stated in the results file.
    print("\n=== eval coverage: distinct aksharas in map vs falling through ===")
    print("  (whitespace-only units excluded; they are not map entries by design)")
    print(f"  {'script':10}{'distinct':>10}{'in map':>9}{'fallthru':>10}"
          f"{'in map %':>10}{'fallthru %':>12}{'occ fallthru %':>16}")
    for s in COVERAGE_SCRIPTS:
        counts = Counter()
        for x in lines_of(s):
            counts.update(a for a in segment_aksharas(x) if a.strip())
        distinct = len(counts)
        inmap = sum(1 for a in counts if a in a2p)
        occ_total = sum(counts.values())
        occ_out = sum(n for a, n in counts.items() if a not in a2p)
        print(f"  {s:10}{distinct:>10}{inmap:>9}{distinct - inmap:>10}"
              f"{100.0 * inmap / distinct:>9.2f}%{100.0 * (distinct - inmap) / distinct:>11.2f}%"
              f"{100.0 * occ_out / occ_total:>15.4f}%")

    # ---- STEP 3: normalization robustness --------------------------------
    forms = [("as_is", lambda t: t),
             ("NFC", lambda t: ud.normalize("NFC", t)),
             ("NFD", lambda t: ud.normalize("NFD", t))]

    res = {}
    for s in SCRIPTS:
        base = lines_of(s)
        res[s] = {name: measure(tok, [f(x) for x in base]) for name, f in forms}

    print("\n=== fertility (tokens per whitespace word) ===")
    print(f"  {'script':12}{'as is':>10}{'NFC':>10}{'NFD':>10}"
          f"{'NFC delta':>12}{'NFD delta':>12}")
    for s in SCRIPTS:
        r = res[s]
        a, c, d = r["as_is"]["fertility"], r["NFC"]["fertility"], r["NFD"]["fertility"]
        print(f"  {s:12}{a:>10.4f}{c:>10.4f}{d:>10.4f}"
              f"{100.0 * (c - a) / a:>11.2f}%{100.0 * (d - a) / a:>11.2f}%")

    print("\n=== round-trip, decode(encode(x)) == x ===")
    print(f"  {'script':12}{'n':>6}{'as is':>10}{'NFC':>10}{'NFD':>10}")
    for s in SCRIPTS:
        r = res[s]
        print(f"  {s:12}{r['as_is']['n']:>6}{r['as_is']['roundtrip_ok']:>10}"
              f"{r['NFC']['roundtrip_ok']:>10}{r['NFD']['roundtrip_ok']:>10}")

    # ---- map entry normalization stability -------------------------------
    print("\n=== map entries by normalization stability ===")
    print(f"  {'script':12}{'entries':>9}{'NFC-unstable':>14}{'NFD-unstable':>14}")
    stab = {}
    for k in entries:
        s = script_of(k)
        d = stab.setdefault(s, {"n": 0, "nfc": 0, "nfd": 0})
        d["n"] += 1
        d["nfc"] += (ud.normalize("NFC", k) != k)
        d["nfd"] += (ud.normalize("NFD", k) != k)
    for s in SCRIPTS + ["other"]:
        if s in stab:
            d = stab[s]
            print(f"  {s:12}{d['n']:>9}{d['nfc']:>14}{d['nfd']:>14}")
    tot = {"n": len(entries),
           "nfc": sum(d["nfc"] for d in stab.values()),
           "nfd": sum(d["nfd"] for d in stab.values())}
    print(f"  {'TOTAL':12}{tot['n']:>9}{tot['nfc']:>14}{tot['nfd']:>14}")

    # ---- both forms present? ---------------------------------------------
    print("\n=== does the map hold BOTH forms of the same character? ===")
    eset = set(entries)
    dual_nfc = [k for k in entries if ud.normalize("NFC", k) != k
                and ud.normalize("NFC", k) in eset]
    dual_nfd = [k for k in entries if ud.normalize("NFD", k) != k
                and ud.normalize("NFD", k) in eset]
    print(f"  entries whose NFC form is ALSO a separate entry: {len(dual_nfc)}")
    for k in dual_nfc[:20]:
        n = ud.normalize("NFC", k)
        print(f"    {k!r} ({' '.join('U+%04X' % ord(c) for c in k)})  and  "
              f"{n!r} ({' '.join('U+%04X' % ord(c) for c in n)})")
    print(f"  entries whose NFD form is ALSO a separate entry: {len(dual_nfd)}")
    for k in dual_nfd[:20]:
        n = ud.normalize("NFD", k)
        print(f"    {k!r} ({' '.join('U+%04X' % ord(c) for c in k)})  and  "
              f"{n!r} ({' '.join('U+%04X' % ord(c) for c in n)})")
    # dual_nfc and dual_nfd list the SAME pairs from opposite sides, so union them
    # before counting or the total doubles.
    pairs = {frozenset((k, ud.normalize("NFC", k))) for k in dual_nfc}
    pairs |= {frozenset((k, ud.normalize("NFD", k))) for k in dual_nfd}
    print(f"  distinct duplicated-form PAIRS: {len(pairs)}")
    print(f"  redundant slots consumed (one per pair): {len(pairs)}")
    by_script = Counter(script_of(sorted(p)[0]) for p in pairs)
    for k, v in by_script.most_common():
        print(f"    {k:12} {v:3} pair(s)")

    # ---- which form dominates each eval file ------------------------------
    print("\n=== dominant normalization form per eval file ===")
    print(f"  {'script':12}{'n':>6}{'== NFC':>9}{'== NFD':>9}{'neither':>9}  verdict")
    for s in SCRIPTS:
        L = lines_of(s)
        c = sum(1 for x in L if ud.normalize("NFC", x) == x)
        d = sum(1 for x in L if ud.normalize("NFD", x) == x)
        neither = sum(1 for x in L if ud.normalize("NFC", x) != x
                      and ud.normalize("NFD", x) != x)
        v = "NFC" if c > d else ("NFD" if d > c else "both (no unstable chars)")
        print(f"  {s:12}{len(L):>6}{c:>9}{d:>9}{neither:>9}  {v}")

    # ---- fair-comparison cross-check --------------------------------------
    # v1.2 gains from NFC input. The competitor numbers were measured on as-is text,
    # so the honest question is whether the competitors gain from NFC too. Measure
    # them on the same three forms rather than comparing v1.2-on-NFC to a rival on
    # as-is text, which would not be a like-for-like claim.
    comp = {
        "sarvam-1": "/mnt/c/GuruAI-Data/competitor_tokenizers/sarvamai__sarvam-1/tokenizer.json",
        "sarvam-30b": "/mnt/c/GuruAI-Data/competitor_tokenizers/sarvamai__sarvam-30b/tokenizer.json",
    }
    avail = {k: v for k, v in comp.items() if os.path.isfile(v)}
    if not avail:
        print("\n(competitor tokenizers not present, skipping cross-check)")
        return 0

    from tokenizers import Tokenizer
    hf = {}
    for name, path in avail.items():
        t = Tokenizer.from_file(path)
        t.no_padding()          # fine-tune checkpoints bake padding into tokenizer.json
        t.no_truncation()
        hf[name] = t

    print("\n=== cross-check: do the competitors gain from NFC too? (fertility) ===")
    print(f"  {'script':12}{'tokenizer':12}{'as is':>10}{'NFC':>10}{'NFD':>10}{'NFC delta':>12}")
    dump = {}
    for s in SCRIPTS:
        base = lines_of(s)
        r = res[s]
        dump[s] = {"v1.2": {f: r[f]["fertility"] for f in ("as_is", "NFC", "NFD")}}
        print(f"  {s:12}{'v1.2':12}{r['as_is']['fertility']:>10.4f}"
              f"{r['NFC']['fertility']:>10.4f}{r['NFD']['fertility']:>10.4f}"
              f"{100.0 * (r['NFC']['fertility'] - r['as_is']['fertility']) / r['as_is']['fertility']:>11.2f}%")
        for name, t in hf.items():
            f3 = {}
            for fname, fn in forms:
                L = [fn(x) for x in base]
                ntok = sum(len(t.encode(x, add_special_tokens=False).ids) for x in L)
                nword = sum(len(x.split()) for x in L)
                f3[fname] = ntok / nword
            dump[s][name] = f3
            print(f"  {'':12}{name:12}{f3['as_is']:>10.4f}{f3['NFC']:>10.4f}"
                  f"{f3['NFD']:>10.4f}"
                  f"{100.0 * (f3['NFC'] - f3['as_is']) / f3['as_is']:>11.2f}%")

    # full-precision floats, so the writeup does not re-derive deltas from rounded prints
    print("\n=== derived: v1.2 relative to each competitor, per normalization form ===")
    for f in ("as_is", "NFC", "NFD"):
        print(f"  --- {f} ---")
        w1 = w3 = 0
        for s in SCRIPTS:
            a = dump[s]["v1.2"][f]
            b, c = dump[s]["sarvam-1"][f], dump[s]["sarvam-30b"][f]
            r1, r3 = 100.0 * (a - b) / b, 100.0 * (a - c) / c
            w1 += r1 < 0
            w3 += r3 < 0
            print(f"    {s:12} vs sarvam-1 {r1:+8.2f}%   vs sarvam-30b {r3:+8.2f}%")
        print(f"    v1.2 wins {w1}/6 vs sarvam-1, {w3}/6 vs sarvam-30b")

    out = os.path.join(HERE, "diagnose_bengali_out.json")
    json.dump(dump, open(out, "w", encoding="utf-8"), indent=1)
    print(f"\nWROTE {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
