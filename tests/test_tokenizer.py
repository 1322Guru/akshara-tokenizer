"""Tests for the v1.2 AksharaTokenizer API (lossless atomic encode/decode).

Runs against the packaged dev v1.2 placeholder artifacts. sentencepiece is
required (the [model] extra); tests skip cleanly if it is absent.
"""
import copy
import hashlib
import json

import pytest

from akshara_tokenizer import segment_aksharas

pytest.importorskip("sentencepiece")
from akshara_tokenizer import AksharaTokenizer  # noqa: E402
from importlib.resources import files  # noqa: E402

MODEL = files("akshara_tokenizer").joinpath("model", "akshara_tokenizer_v1_2.model")
MAPPING = files("akshara_tokenizer").joinpath("model", "akshara_tokenizer_v1_2.map.json")


@pytest.fixture(scope="module")
def tok():
    return AksharaTokenizer.load()


ROUND_TRIP_CASES = [
    # six scripts, plain
    ("devanagari", "न्याय दर्शन"),
    ("gurmukhi", "ਨਿਆਯ ਦਰਸ਼ਨ"),
    ("tamil", "நியாயம் தர்ஷனம்"),
    ("telugu", "తెలుగు భాష"),
    ("bengali", "বাংলা ভাষা"),
    ("kannada", "ಕನ್ನಡ ಭಾಷೆ"),
    # whitespace shapes
    ("double_space", "ਪੰਜਾਬ  ਦੇਸ"),
    ("triple_space", "राम   सीता"),
    ("leading_space", " ਅੱਗੇ ਸਪੇਸ"),
    ("trailing_space", "ਪਿੱਛੇ ਸਪੇਸ "),
    ("newline", "ਲਾਈਨ੧\nਲਾਈਨ੨"),
    ("tab", "टैब\tके बाद"),
    ("crlf", "पंक्ति\r\nदो"),
    ("mixed_ws", " \tਪੰਜਾਬ \n ਦੇਸ\t"),
    # punctuation, latin, digits
    ("punctuation", "ਸਤਿ, ਸ੍ਰੀ; ਅਕਾਲ!"),
    ("question", "प्रश्न? उत्तर."),
    ("mixed_latin", "IYRA ਮਾਡਲ v1.1"),
    ("digits", "੧੨੩ ਅਤੇ 123"),
    ("conjunct_ta", "க்ஷேத்திரம்"),
    ("conjunct_te", "ద్విత్వాక్షరం"),
    ("empty", ""),
    ("only_space", "   "),
]


@pytest.mark.parametrize("label,text", ROUND_TRIP_CASES, ids=[c[0] for c in ROUND_TRIP_CASES])
def test_round_trip_byte_identical(tok, label, text):
    got = tok.decode(tok.encode(text))
    assert got == text, f"{label}: {text!r} -> {got!r}"


def test_encode_returns_ints(tok):
    ids = tok.encode("न्याय")
    assert isinstance(ids, list) and all(isinstance(i, int) for i in ids)


def test_no_pua_leaks_in_pieces(tok):
    # pieces must be human-readable aksharas, never private-use codepoints
    for piece in tok.pieces("ద్విత్వాక్షరం దర్శన"):
        for ch in piece:
            assert not (0xE000 <= ord(ch) <= 0xF8FF), f"PUA leaked in piece {piece!r}"


# ---- batch overloads ------------------------------------------------------

def test_encode_batch(tok):
    batch = ["न्याय दर्शन", "தமிழ்", ""]
    out = tok.encode(batch)
    assert isinstance(out, list) and len(out) == 3
    assert all(isinstance(seq, list) for seq in out)
    for i, t in enumerate(batch):
        assert out[i] == tok.encode(t)


def test_decode_batch(tok):
    batch = ["न्याय दर्शन", "தமிழ் மொழி", "ਪੰਜਾਬ  ਦੇਸ"]
    ids = tok.encode(batch)
    texts = tok.decode(ids)
    assert texts == batch


def test_pieces_batch(tok):
    batch = ["न्याय", "தமிழ்"]
    out = tok.pieces(batch)
    assert len(out) == 2 and all(isinstance(p, list) for p in out)
    assert out[0] == tok.pieces("न्याय")


def test_decode_empty_is_single_empty_string(tok):
    assert tok.decode([]) == ""


# ---- PUA guard ------------------------------------------------------------

def test_guard_rejects_pua_single(tok):
    prefix = "न्याय "
    bad = prefix + chr(0xE123) + "दर्शन"   # PUA codepoint mid-string
    with pytest.raises(ValueError) as exc:
        tok.encode(bad)
    msg = str(exc.value)
    assert "U+E123" in msg                 # names the offending codepoint
    assert f"index {len(prefix)}" in msg   # names its exact index


def test_guard_rejects_pua_batch_names_item(tok):
    batch = ["fine text", "न्याय", "oops " + chr(0xF000) + " here"]
    with pytest.raises(ValueError) as exc:
        tok.encode(batch)
    msg = str(exc.value)
    assert "U+F000" in msg
    assert "batch item 2" in msg           # names which batch item failed


def test_guard_rejects_supplementary_pua(tok):
    with pytest.raises(ValueError, match=r"U\+F0000"):
        tok.encode("text " + chr(0xF0000))


def test_guard_on_pieces_too(tok):
    with pytest.raises(ValueError, match="private-use"):
        tok.pieces("bad " + chr(0xE500))


def test_empty_and_clean_input_not_guarded(tok):
    # empty and ordinary text must NOT trip the guard
    assert tok.pieces("") == []
    assert tok.encode("") == []
    assert isinstance(tok.pieces("न्याय"), list)


# ---- model/mapping binding ------------------------------------------------

def test_mapping_bound_to_model_by_sha(tok):
    model_bytes = MODEL.read_bytes()
    expected = json.loads(MAPPING.read_text("utf-8"))["model_sha256"]
    assert hashlib.sha256(model_bytes).hexdigest() == expected
    assert tok.model_sha256 == expected


def test_mismatched_mapping_refused(tmp_path):
    obj = json.loads(MAPPING.read_text("utf-8"))
    obj["model_sha256"] = "0" * 64
    bad_map = tmp_path / "bad.map.json"
    bad_map.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    model_copy = tmp_path / "m.model"
    model_copy.write_bytes(MODEL.read_bytes())
    with pytest.raises(ValueError, match="model/mapping mismatch"):
        AksharaTokenizer.from_files(str(model_copy), str(bad_map))


# ---- unmapped-akshara handling -------------------------------------------

def test_unmapped_akshara_round_trips(tok):
    # forcibly drop a mapping entry so its akshara takes the raw-codepoint
    # fallback path on encode; decode must still reconstruct it byte-identically
    text = "ਪੰਜਾਬ"
    seg = [s for s in segment_aksharas(text) if s.strip()][0]
    stripped = copy.copy(tok)
    stripped._a2p = dict(tok._a2p)
    stripped._a2p.pop(seg, None)
    stripped._p2a = {v: k for k, v in stripped._a2p.items()}
    assert seg not in stripped._a2p
    assert stripped.decode(stripped.encode(text)) == text


# ---- segment_aksharas unchanged ------------------------------------------

def test_segment_aksharas_signature_and_behavior_unchanged():
    assert segment_aksharas("ਨਿਆਯ ਦਰਸ਼ਨ") == ["ਨਿ", "ਆ", "ਯ", " ", "ਦ", "ਰ", "ਸ਼", "ਨ"]
    assert segment_aksharas("ज्ञान") == ["ज्ञा", "न"]
    from akshara_tokenizer import count_aksharas
    assert count_aksharas("ਪੰਜਾਬ") == 3
    # the segmenter is a clean partition: concatenation reproduces the input
    for _, text in ROUND_TRIP_CASES:
        assert "".join(segment_aksharas(text)) == text
