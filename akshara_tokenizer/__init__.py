from .boundary import segment_aksharas, count_aksharas
from .unicode_tables import SCRIPTS, get_script

__all__ = ["segment_aksharas", "count_aksharas", "SCRIPTS", "get_script", "AksharaTokenizer"]


def __getattr__(name):
    # Lazy so importing the pure-stdlib segmenter never pulls in sentencepiece.
    if name == "AksharaTokenizer":
        from .tokenizer import AksharaTokenizer

        return AksharaTokenizer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
