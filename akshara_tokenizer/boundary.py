"""
Akshara boundary detector for Brahmic/Indic scripts.

An Akshara is the orthographic syllable unit of Brahmic scripts — the smallest
meaningful phonological unit.  The tokenizer guarantees it is never split.

Formation rules (applied left-to-right in priority order):

  Rule 1 — Virama conjunct:   C + Virama + C  →  single conjunct unit
  Rule 2 — C + vowel sign     →  one Akshara  ("paa", "gi", …)
  Rule 3 — C + virama alone   →  dead consonant, complete Akshara ("k" in ਕ੍)
  Rule 4 — Independent vowel  →  own Akshara
  Rule 5 — Anusvara/visarga/nukta/addak/tippi/bindi attach to preceding Akshara
  Rule 6 — Latin/digit/punct  →  each character is its own token
"""

from .unicode_tables import (
    SCRIPTS,
    get_script,
    is_consonant,
    is_vowel_independent,
    is_virama,
    is_combining,
)


def segment_aksharas(text: str) -> list[str]:
    """Segment *text* into a list of Akshara units.

    Mixed scripts are supported: Latin/digit/punct are emitted one character
    at a time; Indic text is segmented at true Akshara boundaries.
    """
    aksharas: list[str] = []
    current: str = ""
    current_script: str | None = None
    after_virama: bool = False  # True immediately after a virama — next consonant joins

    for char in text:
        script = get_script(char)

        # ── Non-Indic character ──────────────────────────────────────────────
        if script is None:
            if current:
                aksharas.append(current)
                current = ""
                current_script = None
            after_virama = False
            aksharas.append(char)
            continue

        # ── Indic character ──────────────────────────────────────────────────

        # Rule 1: virama conjunct — absorb consonant into ongoing Akshara.
        # Only scripts that actually use conjuncts (Devanagari, Telugu, Bengali,
        # Kannada) do this; Tamil pulli and Gurmukhi virama produce dead consonants.
        if after_virama and script == current_script and is_consonant(char, script):
            if SCRIPTS[script].get("uses_conjuncts", True):
                current += char
                after_virama = False
                continue
            # else: fall through — dead consonant is flushed as a complete Akshara

        # New consonant starts a fresh Akshara (flushes any in-progress one)
        if is_consonant(char, script):
            if current:
                aksharas.append(current)
            current = char
            current_script = script
            after_virama = False
            continue

        # Independent vowel starts a fresh Akshara
        if is_vowel_independent(char, script):
            if current:
                aksharas.append(current)
            current = char
            current_script = script
            after_virama = False
            continue

        # Virama: attach to current, flag conjunct possibility (Rule 1 / Rule 3)
        if is_virama(char, script):
            if current:
                current += char
            else:
                # Orphaned virama — treat as its own unit
                current = char
                current_script = script
            after_virama = True
            continue

        # All other combining marks (vowel signs, anusvara, nukta, addak…)
        # attach to the preceding Akshara (Rules 2, 5)
        if is_combining(char, script):
            if current:
                current += char
            else:
                # Orphaned diacritic — keep it as a unit
                current = char
                current_script = script
            after_virama = False
            continue

        # Unknown Indic codepoint — treat as a boundary
        if current:
            aksharas.append(current)
            current = ""
            current_script = None
        aksharas.append(char)
        after_virama = False

    if current:
        aksharas.append(current)

    return aksharas


def count_aksharas(text: str) -> int:
    """Return the number of Akshara units in *text*."""
    return len(segment_aksharas(text))
