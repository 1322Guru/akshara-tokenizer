#!/usr/bin/env python3
"""Rebuild the code-switched Hinglish eval set used by run_fertility_competitors.py.

The set itself is third-party corpus text and is deliberately NOT vendored into this
repository. What lives here is the recipe (this script) and a manifest of per-line sha256
hashes (hinglish_findnitai_manifest.json). Run this once to materialise the set locally,
then the harness verifies it against the manifest before measuring.

Source: findnitai/english-to-hinglish, field translation.hi_ng, filtered to source == 1
(human annotated). Note: every row in the sampled prefix already carries source == 1, so
that filter excluded nothing rather than removing synthetic data.

Selection rule, deterministic and order-preserving:
  - walk the train split in offset order, 100 rows at a time
  - keep rows where 40 <= len(text) <= 200 and len(text.split()) >= 6
  - drop case-insensitive duplicates, keeping the first occurrence
  - stop at 600 rows, no shuffle, no sampling

Usage:
  python3 build_hinglish_set.py --out /path/outside/the/repo/hinglish_findnitai_600.json
"""
import argparse
import hashlib
import json
import os
import urllib.parse
import urllib.request

DATASET = "findnitai/english-to-hinglish"
CONFIG = "default"
SPLIT = "train"
VIEWER = "https://datasets-server.huggingface.co/rows"
WANT = 600
MIN_CHARS, MAX_CHARS, MIN_WORDS = 40, 200, 6

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = "/mnt/c/GuruAI-Data/hinglish/hinglish_findnitai_600.json"
MANIFEST = os.path.join(HERE, "hinglish_findnitai_manifest.json")


def fetch(offset, length=100):
    q = urllib.parse.urlencode({"dataset": DATASET, "config": CONFIG, "split": SPLIT,
                                "offset": offset, "length": length})
    with urllib.request.urlopen(f"{VIEWER}?{q}", timeout=120) as r:
        return json.load(r)


def build(want=WANT):
    got, seen, offset = [], set(), 0
    while len(got) < want and offset < 40000:
        d = fetch(offset)
        rows = d.get("rows", [])
        if not rows:
            break
        for r in rows:
            tr = r["row"].get("translation") or {}
            if tr.get("source") != 1:
                continue
            t = " ".join(str(tr.get("hi_ng", "")).split())
            if not (MIN_CHARS <= len(t) <= MAX_CHARS):
                continue
            if len(t.split()) < MIN_WORDS:
                continue
            k = t.lower()
            if k in seen:
                continue
            seen.add(k)
            got.append(t)
            if len(got) >= want:
                break
        offset += 100
    return got


def line_hashes(lines):
    return [hashlib.sha256(l.encode("utf-8")).hexdigest() for l in lines]


def set_hash(lines):
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def verify(lines, manifest_path=MANIFEST):
    """Return (ok, message). Compares a materialised set against the repo manifest."""
    if not os.path.isfile(manifest_path):
        return False, f"manifest not found at {manifest_path}"
    m = json.load(open(manifest_path, encoding="utf-8"))
    if len(lines) != m["row_count"]:
        return False, f"row count {len(lines)} != manifest {m['row_count']}"
    got = set_hash(lines)
    if got != m["set_sha256"]:
        per = line_hashes(lines)
        bad = [i for i, (a, b) in enumerate(zip(per, m["line_sha256"])) if a != b]
        return False, (f"set sha256 {got[:16]} != manifest {m['set_sha256'][:16]}; "
                       f"{len(bad)} line(s) differ, first at index {bad[0] if bad else 'n/a'}")
    return True, "matches manifest"


def main():
    ap = argparse.ArgumentParser(description="Materialise the Hinglish eval set (not vendored)")
    ap.add_argument("--out", default=DEFAULT_OUT,
                    help="where to write the set; must be OUTSIDE the repo")
    ap.add_argument("--write-manifest", action="store_true",
                    help="regenerate the repo manifest from this pull (normally not wanted)")
    ap.add_argument("--from-frozen", default=None,
                    help="build the manifest from an existing frozen selection json "
                         "(key hinglish_findnitai_human) instead of pulling")
    args = ap.parse_args()

    if args.from_frozen:
        lines = json.load(open(args.from_frozen, encoding="utf-8"))["hinglish_findnitai_human"]
        print(f"loaded {len(lines)} lines from frozen selection {args.from_frozen}")
    else:
        lines = build()
        print(f"pulled {len(lines)} lines from {DATASET}")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    json.dump(lines, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"wrote set to {args.out}")

    if args.write_manifest:
        import datetime
        m = {
            "dataset": DATASET, "config": CONFIG, "split": SPLIT,
            "field": "translation.hi_ng",
            "filter": {"source": 1, "min_chars": MIN_CHARS, "max_chars": MAX_CHARS,
                       "min_words": MIN_WORDS,
                       "dedup": "case-insensitive, first occurrence kept",
                       "order": "offset order, no shuffle"},
            "row_count": len(lines),
            "set_sha256": set_hash(lines),
            "line_sha256": line_hashes(lines),
            "generated": datetime.date.today().isoformat(),
            "note": ("Hashes describe the exact selection that produced the published "
                     "numbers in results_competitor_comparison.md. The corpus text itself "
                     "is third-party and is not vendored in this repository."),
        }
        json.dump(m, open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"wrote manifest to {MANIFEST}")
        print(f"  row_count  {m['row_count']}")
        print(f"  set_sha256 {m['set_sha256']}")
    else:
        ok, msg = verify(lines)
        print(f"verify against repo manifest: {'OK' if ok else 'MISMATCH'} ({msg})")


if __name__ == "__main__":
    main()
