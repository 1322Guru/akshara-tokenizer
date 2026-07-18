#!/usr/bin/env python3
"""
v1.1 fertility benchmark: AksharaTokenizer models vs an optional Qwen3-14B baseline.
FLORES-200 devtest eval files, deterministic single pass.

Akshara SP models use the pipeline sp.encode(' '.join(segment_aksharas(text))) with
the current segmenter. FLORES-200 data and the Qwen tokenizer are supplied locally;
neither ships with the repo. Run with --help for options. The authoritative recorded
numbers are in results_v1_1.md; this script regenerates them on your own eval data.
"""
import os, sys, csv, argparse

HERE = os.path.dirname(os.path.abspath(__file__))            # .../benchmark_2026_07
REPO = os.path.dirname(HERE)                                  # repo root (contains the akshara_tokenizer package)
sys.path.insert(0, REPO)                                      # so `import akshara_tokenizer` resolves from a checkout

import sentencepiece as spm
from importlib.resources import files as _pkg_files
from akshara_tokenizer.boundary import segment_aksharas, count_aksharas

ap = argparse.ArgumentParser(description="AksharaTokenizer fertility benchmark (FLORES-200)")
ap.add_argument("--eval-dir", default=HERE,
                help="directory holding eval_<script>.txt (FLORES-200 devtest, supplied locally)")
ap.add_argument("--qwen-tokenizer", default=os.environ.get("QWEN_TOKENIZER_JSON"),
                help="path to a Qwen3 tokenizer.json for the BPE baseline column; omit to skip it")
ap.add_argument("--out", default=os.path.join(HERE, "results_reproduction.csv"),
                help="output CSV path; does not overwrite the shipped results_v1_1.csv")
args = ap.parse_args()

BENCH = args.eval_dir
QWEN_JSON = args.qwen_tokenizer
def _model_path(fname):
    return str(_pkg_files('akshara_tokenizer').joinpath('model', fname))

SP_MODELS = {
    'akshara_v1_1_16k': _model_path('akshara_tokenizer_v1_1.model'),
    'akshara_v1_7k':    _model_path('akshara_tokenizer_v1.model'),  # optional, skipped if absent
}
SCRIPTS = ['devanagari', 'gurmukhi', 'tamil', 'telugu', 'bengali', 'kannada', 'english']

sps = {}
for name, path in SP_MODELS.items():
    if not os.path.exists(path):
        continue
    try:
        sps[name] = spm.SentencePieceProcessor(model_file=path)
    except Exception as e:
        print(f"WARN could not load {name}: {e!r}")

qwen = None
if QWEN_JSON:
    from tokenizers import Tokenizer
    qwen = Tokenizer.from_file(QWEN_JSON)

def sp_bf_pct(sp, ids):
    if not ids:
        return 0.0
    return 100.0 * sum(1 for i in ids if i == sp.unk_id() or sp.id_to_piece(i).startswith('<0x')) / len(ids)

FIELDS = ['script', 'tokenizer', 'tokens', 'chars', 'words', 'aksharas',
          'tok_per_100char', 'fertility_tok_per_word', 'tok_per_akshara',
          'unk_bytefallback_pct', 'roundtrip_text', 'roundtrip_sp_layer', 'status']
rows = []
for script in SCRIPTS:
    path = os.path.join(BENCH, f'eval_{script}.txt')
    if not os.path.exists(path):
        print(f"WARN missing eval file: {path}")
        continue
    text = open(path, encoding='utf-8').read()
    n_chars = len(text); n_words = len(text.split()); n_aksh = count_aksharas(text)
    ak_text = ' '.join(segment_aksharas(text))
    for name, sp in sps.items():
        try:
            ids = sp.encode(ak_text); tok = len(ids)
            rows.append({'script': script, 'tokenizer': name, 'tokens': tok, 'chars': n_chars,
                         'words': n_words, 'aksharas': n_aksh,
                         'tok_per_100char': round(100.0 * tok / n_chars, 4),
                         'fertility_tok_per_word': round(tok / n_words, 4),
                         'tok_per_akshara': round(tok / n_aksh, 4),
                         'unk_bytefallback_pct': round(sp_bf_pct(sp, ids), 3),
                         'roundtrip_text': 'no',
                         'roundtrip_sp_layer': 'yes' if sp.decode(ids) == ak_text else 'no',
                         'status': 'ok'})
        except Exception as e:
            rows.append({'script': script, 'tokenizer': name, 'status': f'FAIL: {e!r}'})
    if qwen is not None:
        try:
            ids = qwen.encode(text, add_special_tokens=False).ids; tok = len(ids)
            rows.append({'script': script, 'tokenizer': 'qwen3_14b', 'tokens': tok, 'chars': n_chars,
                         'words': n_words, 'aksharas': n_aksh,
                         'tok_per_100char': round(100.0 * tok / n_chars, 4),
                         'fertility_tok_per_word': round(tok / n_words, 4),
                         'tok_per_akshara': round(tok / n_aksh, 4),
                         'unk_bytefallback_pct': 'na',
                         'roundtrip_text': 'yes' if qwen.decode(ids) == text else 'no',
                         'roundtrip_sp_layer': 'na', 'status': 'ok'})
        except Exception as e:
            rows.append({'script': script, 'tokenizer': 'qwen3_14b', 'status': f'FAIL: {e!r}'})

with open(args.out, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=FIELDS, restval='', extrasaction='ignore')
    w.writeheader()
    for r in rows:
        w.writerow(r)
for r in rows:
    print(r.get('script'), r.get('tokenizer'), r.get('status', ''),
          '| fert', r.get('fertility_tok_per_word'), '| tok/aksh', r.get('tok_per_akshara'),
          '| bf%', r.get('unk_bytefallback_pct'))
print(f'WROTE {args.out}')
