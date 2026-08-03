"""Build an arm N corpus: substitute dual-form symbols in a fraction f of eligible lines.

METHOD, fixed and deterministic:
  scope        the 11 non-Tamil pairs (5 devanagari, 4 gurmukhi, 2 bengali). Tamil's 4
               pairs are excluded: their dominant form already matches evaluation, so
               there is no penalty to recover and converting would move Tamil away from
               its evaluation distribution.
  eligible     a line containing at least one in-scope symbol in its DOMINANT form
  selection    every k-th eligible line, k = round(1/f). Deterministic stride, no RNG.
  conversion   in a selected line, replace EVERY in-scope dominant-form symbol with its
               paired alternate. Whole-line and all-pairs, mirroring what a user sending
               non-NFC text actually produces, rather than a per-symbol patchwork.
  byte guard   skip any line whose post-substitution UTF-8 length would exceed 4,192,
               SentencePiece's max_sentence_length. 12 of 15 pairs change byte length
               (BMP PUA is 3 bytes, plane-15 PUA is 4), and 16 lines in the base set sit
               close enough to the limit to flip. Skipping them pins every arm to the
               same 5,997,116 training sentences.

Line count is preserved exactly: substitution is in place, never insertion or deletion.

Usage: python3 build_armN.py <f> <out_dir>
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
import json
import os
import sys
import hashlib
from collections import Counter

BASE = f"{SWEEP}/base_6m"
LANGS = ["hi", "pa", "ta", "te", "bn", "kn"]
MAX_BYTES = 4192

f = float(sys.argv[1])
out = sys.argv[2]
os.makedirs(out, exist_ok=True)

PAIRS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "dual_form_pairs.json"), encoding="utf-8"))
INSCOPE = [p for p in PAIRS if p["script"] != "taml"]

# For the 11 in-scope pairs the DOMINANT form in this corpus is the decomposed one, since
# the corpus is NFC and NFC decomposes these canonical-decomposition singletons. So the
# substitution direction is decomposed -> precomposed.
SUB = {chr(p["dec_pua"]): chr(p["pre_pua"]) for p in INSCOPE}
DOMINANT = set(SUB)

k = max(1, round(1.0 / f))
print(f"f={f}  stride k={k}  in-scope pairs={len(INSCOPE)}  out={out}", flush=True)

tot_lines = eligible = selected = skipped_bytes = converted_syms = 0
per_lang = {}

for lang in LANGS:
    src, dst = f"{BASE}/{lang}.txt", f"{out}/{lang}.txt"
    n = e = s = sb = cs = 0
    h = hashlib.sha256()
    with open(src, encoding="utf-8") as fin, open(dst, "w", encoding="utf-8") as fout:
        for line in fin:
            n += 1
            body = line.rstrip("\n")
            if any(c in DOMINANT for c in body):
                e += 1
                if e % k == 0:
                    new = "".join(SUB.get(c, c) for c in body)
                    if len(new.encode("utf-8")) <= MAX_BYTES:
                        cs += sum(1 for c in body if c in DOMINANT)
                        body = new
                        s += 1
                    else:
                        sb += 1
            outline = body + "\n"
            fout.write(outline)
            h.update(outline.encode("utf-8"))
    per_lang[lang] = (n, e, s, sb, cs, h.hexdigest())
    tot_lines += n; eligible += e; selected += s; skipped_bytes += sb; converted_syms += cs
    print(f"  {lang:3} lines={n:>9,} eligible={e:>9,} converted={s:>9,} "
          f"byte_skipped={sb:>3} symbols={cs:>10,}", flush=True)

print(f"\nTOTAL lines={tot_lines:,} eligible={eligible:,} converted_lines={selected:,} "
      f"byte_skipped={skipped_bytes} converted_symbols={converted_syms:,}")
H = hashlib.sha256()
for lang in LANGS:
    with open(f"{out}/{lang}.txt", "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            H.update(chunk)
print(f"ARM sha256 {H.hexdigest()}")
assert tot_lines == 6_000_000, f"line count changed: {tot_lines}"
print("line count preserved at 6,000,000: OK")
