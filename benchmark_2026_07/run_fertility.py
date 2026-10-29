#!/usr/bin/env python3
"""
Deterministic fertility benchmark: AksharaTokenizer v1 vs Qwen3-14B.
Read-only on the tokenizer source. Single pass over each eval file, no sampling.

AksharaTokenizer encode pipeline (as designed, see phase2_evaluate.py):
    ids = sp.encode(' '.join(segment_aksharas(text)))
Qwen3-14B: byte-level BPE loaded from the base tokenizer.json, add_special_tokens=False.

Shared akshara-count denominator: count_aksharas(text) = len(segment_aksharas(text)),
i.e. every segmentation unit including spaces / punctuation / Latin (each non-Indic
character is its own unit). Same value used for both tokenizers.

Round-trip:
  qwen3_14b       roundtrip_text  = (decode(encode(text)) == text)
  akshara_v1_sp   roundtrip_text  = 'no' (v1 ships no detokenizer; the space-join
                                    conflates akshara and word boundaries and the SP
                                    model normalizes whitespace, so the exact original
                                    text is not recoverable from the token stream)
                  roundtrip_sp_layer = (sp.decode(ids) == ' '.join(segment_aksharas(text)))

Byte-fallback %: real value for the SP model (unk id or '<0x..>' pieces); 'na' for
Qwen (byte-level BPE has no UNK / byte-fallback concept).

Output: results.csv
"""
import sys, csv
sys.path.insert(0, '/mnt/d/GuruAI')
import sentencepiece as spm
from tokenizers import Tokenizer
from akshara_tokenizer.boundary import segment_aksharas, count_aksharas

BENCH     = '/mnt/d/GuruAI/akshara_tokenizer/benchmark_2026_07'
AK_MODEL  = '/mnt/d/GuruAI/akshara_tokenizer/model/akshara_tokenizer_v1.model'
QWEN_JSON = '/home/guru/.cache/huggingface/hub/models--unsloth--Qwen3-14B/snapshots/b8755c0b498d7b538068383748d6dc20397b4d1f/tokenizer.json'
SCRIPTS   = ['devanagari', 'gurmukhi', 'tamil', 'telugu', 'bengali', 'kannada', 'english']

sp   = spm.SentencePieceProcessor(model_file=AK_MODEL)
qwen = Tokenizer.from_file(QWEN_JSON)

def ak_encode(text):
    return sp.encode(' '.join(segment_aksharas(text)))

def ak_bytefallback_pct(ids):
    if not ids:
        return 0.0
    n = sum(1 for i in ids if i == sp.unk_id() or sp.id_to_piece(i).startswith('<0x'))
    return 100.0 * n / len(ids)

FIELDS = ['script', 'tokenizer', 'tokens', 'chars', 'words', 'aksharas',
          'tok_per_100char', 'fertility_tok_per_word', 'tok_per_akshara',
          'unk_bytefallback_pct', 'roundtrip_text', 'roundtrip_sp_layer', 'status']
rows = []

for script in SCRIPTS:
    with open(f'{BENCH}/eval_{script}.txt', encoding='utf-8') as f:
        text = f.read()
    n_chars = len(text)
    n_words = len(text.split())
    n_aksh  = count_aksharas(text)

    # AksharaTokenizer v1 (SentencePiece over akshara-segmented text)
    try:
        ak_text = ' '.join(segment_aksharas(text))
        ids = sp.encode(ak_text)
        tok = len(ids)
        rows.append({
            'script': script, 'tokenizer': 'akshara_v1_sp', 'tokens': tok,
            'chars': n_chars, 'words': n_words, 'aksharas': n_aksh,
            'tok_per_100char': round(100.0 * tok / n_chars, 4),
            'fertility_tok_per_word': round(tok / n_words, 4),
            'tok_per_akshara': round(tok / n_aksh, 4),
            'unk_bytefallback_pct': round(ak_bytefallback_pct(ids), 3),
            'roundtrip_text': 'no',
            'roundtrip_sp_layer': 'yes' if sp.decode(ids) == ak_text else 'no',
            'status': 'ok'})
    except Exception as e:
        rows.append({'script': script, 'tokenizer': 'akshara_v1_sp', 'status': f'FAIL: {e!r}'})

    # Qwen3-14B (byte-level BPE)
    try:
        ids = qwen.encode(text, add_special_tokens=False).ids
        tok = len(ids)
        rows.append({
            'script': script, 'tokenizer': 'qwen3_14b', 'tokens': tok,
            'chars': n_chars, 'words': n_words, 'aksharas': n_aksh,
            'tok_per_100char': round(100.0 * tok / n_chars, 4),
            'fertility_tok_per_word': round(tok / n_words, 4),
            'tok_per_akshara': round(tok / n_aksh, 4),
            'unk_bytefallback_pct': 'na',
            'roundtrip_text': 'yes' if qwen.decode(ids) == text else 'no',
            'roundtrip_sp_layer': 'na',
            'status': 'ok'})
    except Exception as e:
        rows.append({'script': script, 'tokenizer': 'qwen3_14b', 'status': f'FAIL: {e!r}'})

with open(f'{BENCH}/results.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=FIELDS, restval='', extrasaction='ignore')
    w.writeheader()
    for r in rows:
        w.writerow(r)

for r in rows:
    print(r.get('script'), r.get('tokenizer'), r.get('status', ''),
          '| fert', r.get('fertility_tok_per_word'),
          '| tok/aksh', r.get('tok_per_akshara'),
          '| bf%', r.get('unk_bytefallback_pct'),
          '| rt_text', r.get('roundtrip_text'))
print('WROTE', f'{BENCH}/results.csv')
