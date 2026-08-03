"""Train a sweep arm on a FIXED corpus with no reservoir draw.

Differs from train_arm.py in exactly one respect that matters: input_sentence_size=0, so
SentencePiece consumes every line of the supplied corpus instead of sampling from it.
The corpus is the frozen 6,000,000-line base set (or an arm that substitutes lines within
it, keeping the count at 6,000,000). With no draw, two arms differ only in content.

The seed is still set, but only for hygiene: the reservoir path is the only consumer of
that RNG and it is disabled here. Seed had no observable effect even when sampling was
active, verified at a 0.25 percent draw.

Usage: python3 train_arm_fixed.py <seed> <model_prefix> <corpus_dir>
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
import os
import pickle
import sys
import time

import sentencepiece as spm

LANGS = ["hi", "pa", "ta", "te", "bn", "kn"]
V12_MAPPED = V12_MAPPED_DIR
PUA_RANGES = ((0xE000, 0xF8FF), (0xF0000, 0xFFFFD), (0x100000, 0x10FFFD))

seed = int(sys.argv[1])
model_prefix = sys.argv[2]
corpus = sys.argv[3]

inputs = ",".join(f"{corpus}/{lang}.txt" for lang in LANGS)

# required_chars always from the v1.2 charset pickles: every arm must keep all 14,601
# mapped aksharas, otherwise a dropped akshara degrades to byte fallback and the arm is
# not comparable to the others.
charset = set()
for lang in LANGS:
    with open(f"{V12_MAPPED}/{lang}.txt.charset.pkl", "rb") as handle:
        charset |= pickle.load(handle)
required = sorted(c for c in charset if any(lo <= ord(c) <= hi for lo, hi in PUA_RANGES))
required_chars = "".join(required)

print(f"seed={seed}", flush=True)
print(f"corpus={corpus}", flush=True)
print(f"required_chars_count={len(required)}", flush=True)
print(f"input_sentence_size=0 (no reservoir draw)", flush=True)
print(f"pid={os.getpid()}", flush=True)

spm.set_random_generator_seed(seed)

start = time.time()
spm.SentencePieceTrainer.train(
    input=inputs,
    model_prefix=model_prefix,
    model_type="unigram",
    vocab_size=64000,
    character_coverage=1.0,
    required_chars=required_chars,
    input_sentence_size=0,
    shuffle_input_sentence=True,
    byte_fallback=True,
    normalization_rule_name="identity",
    add_dummy_prefix=False,
    remove_extra_whitespaces=False,
    unk_id=0,
    bos_id=1,
    eos_id=2,
    pad_id=3,
    num_threads=12,
)
print(f"DONE wall_seconds={time.time() - start:.1f}", flush=True)
