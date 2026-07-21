"""High-level v1.2 tokenizer: lossless encode/decode over atomic Akshara symbols.

The v1.2 model is trained on a stream where each Akshara is mapped to a single
private-use codepoint, so learned pieces span whole aksharas and never split one.
This module hides that mapping: `encode` takes text and returns ids, `decode`
takes ids and returns text. The private-use codepoints never surface to callers.

`segment_aksharas` and `count_aksharas` are unchanged; this class uses the former
internally. `sentencepiece` is imported lazily, so importing the package for the
pure-stdlib segmenter never requires it.

The v1.1 model is a documented legacy path, not routed through this class: its
encode pipeline space-joins aksharas and the model normalizes whitespace, so it
cannot round-trip. Use the two-line legacy pattern for v1.1:

    sp.encode(" ".join(segment_aksharas(text)))

The v1.1 model file is present in the repository and on HuggingFace, but is NOT
bundled in the 1.2.0 package. To get it installed, pin akshara-tokenizer==1.1.0.
Note that v1.1 and v1.2 produce different id streams: decoding v1.1 ids with the
v1.2 model returns silent garbage, since nothing in the API can detect which model
produced a stream. Keep a v1.1-tokenized corpus on 1.1.0 rather than upgrading in
place.
"""
from __future__ import annotations

import hashlib
import json
import re
from importlib.resources import files
from typing import overload

from .boundary import segment_aksharas

# Private-use ranges the mapping draws from: BMP PUA and supplementary planes 15/16.
# Real Brahmic/Latin text never contains these, so their presence in input is an error.
# Built from integer bounds so no literal private-use codepoint lives in this source.
_PUA_RANGES = ((0xE000, 0xF8FF), (0xF0000, 0xFFFFD), (0x100000, 0x10FFFD))
_PUA_RE = re.compile("[" + "".join(f"{chr(lo)}-{chr(hi)}" for lo, hi in _PUA_RANGES) + "]")


class AksharaTokenizer:
    """Lossless Akshara-atomic tokenizer.

    Construct with :meth:`load` (packaged v1.2 artifacts) or :meth:`from_files`
    (explicit paths). The mapping table is bound to the model by sha256; a
    mismatch refuses construction.
    """

    def __init__(self, sp, a2p: dict[str, str], *, model_sha256: str, version: str | None):
        self._sp = sp
        self._a2p = a2p                               # akshara -> single PUA char
        self._p2a = {v: k for k, v in a2p.items()}    # PUA char -> akshara
        self.model_sha256 = model_sha256
        self.version = version

    # ---- construction -----------------------------------------------------

    @classmethod
    def _build(cls, model_bytes: bytes, mapping_obj: dict, source: str) -> "AksharaTokenizer":
        actual = hashlib.sha256(model_bytes).hexdigest()
        expected = mapping_obj.get("model_sha256")
        if expected and actual != expected:
            raise ValueError(
                f"model/mapping mismatch for {source}: mapping was built for model "
                f"sha256 {expected}, but the model file hashes to {actual}. Refusing "
                f"to construct; the mapping and model must be a matched pair."
            )
        import sentencepiece as spm  # lazy: keeps segmenter import stdlib-only

        sp = spm.SentencePieceProcessor(model_proto=model_bytes)
        a2p = {k: chr(int(v)) for k, v in mapping_obj["aksharas"].items()}
        return cls(sp, a2p, model_sha256=actual, version=mapping_obj.get("version"))

    @classmethod
    def load(cls) -> "AksharaTokenizer":
        """Load the packaged v1.2 model and mapping together from package data."""
        model_dir = files("akshara_tokenizer").joinpath("model")
        model_bytes = model_dir.joinpath("akshara_tokenizer_v1_2.model").read_bytes()
        mapping_obj = json.loads(
            model_dir.joinpath("akshara_tokenizer_v1_2.map.json").read_text("utf-8")
        )
        return cls._build(model_bytes, mapping_obj, source="packaged v1.2")

    @classmethod
    def from_files(cls, model_path: str, mapping_path: str) -> "AksharaTokenizer":
        """Load a model and its mapping from explicit paths (dev and custom models)."""
        with open(model_path, "rb") as f:
            model_bytes = f.read()
        with open(mapping_path, encoding="utf-8") as f:
            mapping_obj = json.load(f)
        return cls._build(model_bytes, mapping_obj, source=model_path)

    # ---- guard ------------------------------------------------------------

    @staticmethod
    def _guard(text: str, batch_index: int | None = None) -> None:
        m = _PUA_RE.search(text)
        if m is not None:
            cp = ord(m.group())
            where = "" if batch_index is None else f", batch item {batch_index}"
            raise ValueError(
                f"input contains private-use codepoint U+{cp:04X} at index "
                f"{m.start()}{where}; such codepoints do not occur in Brahmic or "
                f"Latin text and collide with internal symbols, so they are not "
                f"supported input."
            )

    # ---- core (single) ----------------------------------------------------

    def _map_text(self, text: str) -> str:
        return "".join(self._a2p.get(seg, seg) for seg in segment_aksharas(text))

    def _encode_one(self, text: str, batch_index: int | None = None) -> list[int]:
        self._guard(text, batch_index)
        return self._sp.encode(self._map_text(text))

    def _decode_one(self, ids: list[int]) -> str:
        decoded = self._sp.decode(ids)
        return "".join(self._p2a.get(ch, ch) for ch in decoded)

    def _pieces_one(self, text: str, batch_index: int | None = None) -> list[str]:
        self._guard(text, batch_index)
        raw = self._sp.encode(self._map_text(text), out_type=str)
        # map PUA back to aksharas so callers never see private-use codepoints
        return ["".join(self._p2a.get(ch, ch) for ch in piece) for piece in raw]

    # ---- public overloads -------------------------------------------------

    @overload
    def encode(self, text: str) -> list[int]: ...
    @overload
    def encode(self, text: list[str]) -> list[list[int]]: ...

    def encode(self, text):
        """Encode text to ids.

        - ``encode(str) -> list[int]``
        - ``encode(list[str]) -> list[list[int]]`` (batch, sentencepiece convention)
        """
        if isinstance(text, str):
            return self._encode_one(text)
        return [self._encode_one(t, i) for i, t in enumerate(text)]

    @overload
    def decode(self, ids: list[int]) -> str: ...
    @overload
    def decode(self, ids: list[list[int]]) -> list[str]: ...

    def decode(self, ids):
        """Decode ids to text.

        - ``decode(list[int]) -> str``
        - ``decode(list[list[int]]) -> list[str]`` (batch)

        An empty list is treated as a single empty id sequence and returns ``""``.
        """
        if len(ids) == 0 or isinstance(ids[0], int):
            return self._decode_one(ids)
        return [self._decode_one(seq) for seq in ids]

    @overload
    def pieces(self, text: str) -> list[str]: ...
    @overload
    def pieces(self, text: list[str]) -> list[list[str]]: ...

    def pieces(self, text):
        """Return the Akshara-level pieces (never private-use codepoints).

        - ``pieces(str) -> list[str]``
        - ``pieces(list[str]) -> list[list[str]]`` (batch)
        """
        if isinstance(text, str):
            return self._pieces_one(text)
        return [self._pieces_one(t, i) for i, t in enumerate(text)]
