"""Verify every number published in results_arm_n_normalization.md by DERIVATION.

Not a substring grep. Substring matching cannot tell a fabricated number from a correctly
rounded one, and it produces false failures here because the result JSON holds
full-precision floats (1.37320123...) while the published tables round to four decimals,
and because the delta and recovery percentages are derived and appear in no source file at
all. This script recomputes each published value from the result JSON and asserts the
rounded form is present in the markdown.

Usage:
  python3 verify_arm_n.py [--results DIR] [--doc PATH]

Exit status is 0 when every value verifies, 1 otherwise.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RESULTS = os.path.join(HERE, "result_json")
DEFAULT_DOC = os.path.join(os.path.dirname(HERE), "results_arm_n_normalization.md")

ARMS = [("0'", "arm0prime"), ("N-a", "armNa"), ("N-b", "armNb"), ("N-c", "armNc")]
SUBS = ["N-a", "N-b", "N-c"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=DEFAULT_RESULTS)
    ap.add_argument("--doc", default=DEFAULT_DOC)
    a = ap.parse_args()

    doc = open(a.doc, encoding="utf-8").read()
    F = {k: json.load(open(f"{a.results}/{v}_forms.json", encoding="utf-8")) for k, v in ARMS}
    L = {k: json.load(open(f"{a.results}/latin_{v}.json", encoding="utf-8")) for k, v in ARMS}
    base = F["0'"]["scripts"]

    ok, missing = 0, []

    def check(label, value):
        nonlocal ok
        if value in doc:
            ok += 1
        else:
            missing.append((label, value))

    # 1. arm 0' absolute fertility, as-is and NFC
    for s in base:
        check(f"arm0' {s} as-is", "%.4f" % base[s]["as_is"]["fertility"])
        check(f"arm0' {s} NFC", "%.4f" % base[s]["NFC"]["fertility"])

    # 2. every arm delta against arm 0', as-is and NFC
    for s in base:
        for k in SUBS:
            for form in ("as_is", "NFC"):
                b = base[s][form]["fertility"]
                d = 100.0 * (F[k]["scripts"][s][form]["fertility"] - b) / b
                check(f"{k} {s} {form} delta", "%+.3f%%" % d)

    # 3. penalty, half-penalty bar, gain and share of penalty
    for s in ("gurmukhi", "bengali"):
        asis = base[s]["as_is"]["fertility"]
        pen = 100.0 * (asis - base[s]["NFC"]["fertility"]) / asis
        check(f"{s} penalty", "%.3f%%" % pen)
        check(f"{s} half bar", "%.3f%%" % (pen / 2))
        for k in SUBS:
            gain = 100.0 * (asis - F[k]["scripts"][s]["as_is"]["fertility"]) / asis
            check(f"{k} {s} gain", "%.3f%%" % gain)
            check(f"{k} {s} share of penalty", "%.1f%%" % (100.0 * gain / pen))

    # 4. Latin side, every arm and category
    for c in L["0'"]["categories"]:
        for k, _ in ARMS:
            check(f"{k} {c}", "%.4f" % L[k]["categories"][c]["fertility"])

    # 5. round-trip must be 1012 in all eighteen cells of every arm
    cells = [(k, s, f) for k, _ in ARMS for s in base for f in ("as_is", "NFC", "NFD")]
    bad = [c for c in cells if F[c[0]]["scripts"][c[1]][c[2]]["roundtrip_ok"] != 1012]

    print(f"doc      {a.doc}")
    print(f"results  {a.results}")
    print(f"verified {ok} derived values, {len(missing)} missing")
    for label, v in missing:
        print(f"  MISSING {label}: {v}")
    print(f"round-trip cells checked {len(cells)}, all 1012: {not bad}")
    for c in bad:
        print(f"  BAD CELL {c}")

    return 0 if (not missing and not bad) else 1


if __name__ == "__main__":
    sys.exit(main())
