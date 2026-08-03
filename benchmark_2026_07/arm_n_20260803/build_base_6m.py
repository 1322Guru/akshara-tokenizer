"""Build the fixed 6,000,000-line base set for the v1.3 arm sweep.

WHY: the v1.2 run passed all 22.5M lines to SentencePiece with input_sentence_size=6M,
so an internal reservoir picked the 6M. If later arms add or alter lines in that 22.5M
pool, the draw changes too, and an arm difference could come from the draw rather than
the content. Freezing one 6M base set and training every arm with input_sentence_size=0
removes that confound entirely.

SELECTION RULE, deterministic, no RNG:
  - per-script quota proportional to the current corpus balance, so the base set keeps
    the same script mix the reservoir would have produced in expectation:
        hi 533,333   pa 533,333   ta 533,333
        te 1,466,667 bn 1,466,667 kn 1,466,667      total 6,000,000
  - a line is ACCEPTABLE if it is non-empty after rstrip and at most 4,192 characters,
    which is SentencePiece's max_sentence_length; longer lines are silently dropped by
    the trainer and would otherwise leave the arm short of 6M
  - within each file, let A be the number of acceptable lines and Q the quota. Select the
    j-th acceptable line for j = floor(i * A / Q), i = 0 .. Q-1. This is even stride over
    the whole file, not a head slice, so ordering effects in the corpus do not bias it.

Reproducible from the v1.2 mapped corpus alone. Writes only under the sweep directory.
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
import hashlib
import os
import sys

SRC = V12_MAPPED_DIR
DST = f"{SWEEP}/base_6m"
MAX_LEN = 4192
QUOTA = {"hi": 533_333, "pa": 533_333, "ta": 533_333,
         "te": 1_466_667, "bn": 1_466_667, "kn": 1_466_667}


def acceptable(line):
    s = line.rstrip("\n")
    return bool(s.strip()) and len(s) <= MAX_LEN


def count_acceptable(path):
    n = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if acceptable(line):
                n += 1
    return n


def main():
    os.makedirs(DST, exist_ok=True)
    total = 0
    print(f"{'lang':6}{'raw':>12}{'acceptable':>12}{'quota':>10}{'written':>10}  sha256")
    for lang, q in QUOTA.items():
        src = f"{SRC}/{lang}.txt"
        dst = f"{DST}/{lang}.txt"
        A = count_acceptable(src)
        if A < q:
            sys.exit(f"FATAL {lang}: only {A} acceptable lines, quota {q}")
        # even stride: the j-th acceptable line for j = floor(i*A/Q)
        wanted = set((i * A) // q for i in range(q))
        h = hashlib.sha256()
        written = raw = j = 0
        with open(src, encoding="utf-8") as fin, open(dst, "w", encoding="utf-8") as fout:
            for line in fin:
                raw += 1
                if not acceptable(line):
                    continue
                if j in wanted:
                    s = line.rstrip("\n") + "\n"
                    fout.write(s)
                    h.update(s.encode("utf-8"))
                    written += 1
                j += 1
        total += written
        print(f"{lang:6}{raw:>12,}{A:>12,}{q:>10,}{written:>10,}  {h.hexdigest()}")
    print(f"\nTOTAL WRITTEN {total:,}")
    # whole-set hash, files concatenated in fixed lang order
    H = hashlib.sha256()
    for lang in QUOTA:
        with open(f"{DST}/{lang}.txt", "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                H.update(chunk)
    print(f"BASE SET sha256 {H.hexdigest()}")


if __name__ == "__main__":
    main()
