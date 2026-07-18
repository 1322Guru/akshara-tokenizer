"""
Unicode character classification tables for Brahmic/Indic scripts.
Each script entry defines codepoint ranges for consonants, vowels, and diacritics.
"""

SCRIPTS = {
    "devanagari": {
        "range": (0x0900, 0x097F),
        "language": ["Hindi", "Sanskrit", "Marathi"],
        "consonants": list(range(0x0915, 0x0940)),
        "vowels_independent": list(range(0x0904, 0x0915)),
        "vowel_signs": list(range(0x093E, 0x094F)),
        "virama": 0x094D,   # halant, kills inherent vowel
        "anusvara": 0x0902,
        "visarga": 0x0903,
        "candrabindu": 0x0901,
        "nukta": 0x093C,
        "uses_conjuncts": True,   # ज्ञ, क्ष, etc.
    },
    "gurmukhi": {
        "range": (0x0A00, 0x0A7F),
        "language": ["Punjabi"],
        "consonants": list(range(0x0A15, 0x0A40)),
        "vowels_independent": list(range(0x0A04, 0x0A15)),
        "vowel_signs": list(range(0x0A3E, 0x0A4F)),
        "virama": 0x0A4D,
        "anusvara": 0x0A02,
        "candrabindu": 0x0A01,   # adak bindi
        "nukta": 0x0A3C,    # produces sha (ਸ਼), llla, etc.
        "bindi": 0x0A70,    # tippi in Unicode, light nasalization
        "tippi": 0x0A71,    # addak in Unicode, doubles following consonant
        "addak": 0x0A71,
        "uses_conjuncts": False,  # virama creates dead consonants in modern Punjabi
    },
    "tamil": {
        "range": (0x0B80, 0x0BFF),
        "language": ["Tamil"],
        # Extended to 0x0BBA to cover ழ (0x0BB4), ள (0x0BB3), வ (0x0BB5), etc.
        "consonants": list(range(0x0B95, 0x0BBA)),
        "vowels_independent": list(range(0x0B85, 0x0B95)),
        "vowel_signs": list(range(0x0BBE, 0x0BD0)),
        "virama": 0x0BCD,   # pulli, always a dead-consonant marker, never conjunct
        "anusvara": 0x0B82,
        "uses_conjuncts": False,  # Tamil phonology uses open syllables; pulli ≠ conjunct
    },
    "telugu": {
        "range": (0x0C00, 0x0C7F),
        "language": ["Telugu"],
        "consonants": list(range(0x0C15, 0x0C45)),
        "vowels_independent": list(range(0x0C04, 0x0C15)),
        "vowel_signs": list(range(0x0C3E, 0x0C4F)),
        "virama": 0x0C4D,
        "anusvara": 0x0C02,
        "visarga": 0x0C03,
        "candrabindu": 0x0C01,
        "uses_conjuncts": True,
    },
    "bengali": {
        "range": (0x0980, 0x09FF),
        "language": ["Bengali"],
        "consonants": list(range(0x0995, 0x09C0)),
        "vowels_independent": list(range(0x0985, 0x0995)),
        "vowel_signs": list(range(0x09BE, 0x09CF)),
        "virama": 0x09CD,
        "anusvara": 0x0982,
        "visarga": 0x0983,
        "candrabindu": 0x0981,
        "nukta": 0x09BC,
        "uses_conjuncts": True,   # হসন্ত conjuncts (ক্ষ, জ্ঞ, etc.)
    },
    "kannada": {
        "range": (0x0C80, 0x0CFF),
        "language": ["Kannada"],
        "consonants": list(range(0x0C95, 0x0CC5)),
        "vowels_independent": list(range(0x0C85, 0x0C95)),
        "vowel_signs": list(range(0x0CBE, 0x0CCF)),
        "virama": 0x0CCD,
        "anusvara": 0x0C82,
        "visarga": 0x0C83,
        "candrabindu": 0x0C81,
        "uses_conjuncts": True,
    },
}

# Precomputed fast-lookup sets per script.
_SCRIPT_SETS: dict = {}

for _name, _s in SCRIPTS.items():
    _lo, _hi = _s["range"]
    # All special single-codepoint combining marks for this script.
    _extras: set = set()
    for _key in ("virama", "anusvara", "visarga", "candrabindu", "nukta", "bindi", "tippi", "addak"):
        _v = _s.get(_key)
        if _v is not None:
            _extras.add(_v)

    _SCRIPT_SETS[_name] = {
        "consonants": frozenset(_s["consonants"]),
        "vowels_independent": frozenset(_s["vowels_independent"]),
        "vowel_signs": frozenset(_s["vowel_signs"]),
        "combining_extras": frozenset(_extras),
        "range": (_lo, _hi),
    }


# ---------------------------------------------------------------------------
# Public helper functions
# ---------------------------------------------------------------------------

def get_script(char: str) -> str | None:
    """Return the script name for *char*, or None if not a supported Indic char."""
    cp = ord(char)
    for name, sets in _SCRIPT_SETS.items():
        lo, hi = sets["range"]
        if lo <= cp <= hi:
            return name
    return None


def is_consonant(char: str, script: str) -> bool:
    """True if *char* is a consonant in *script*."""
    cp = ord(char)
    sets = _SCRIPT_SETS[script]
    return (
        cp in sets["consonants"]
        and cp not in sets["vowel_signs"]
        and cp not in sets["combining_extras"]
    )


def is_vowel_independent(char: str, script: str) -> bool:
    """True if *char* is a standalone (independent) vowel in *script*."""
    cp = ord(char)
    return cp in _SCRIPT_SETS[script]["vowels_independent"]


def is_vowel_sign(char: str, script: str) -> bool:
    """True if *char* is a dependent vowel sign (matra) in *script*."""
    cp = ord(char)
    return cp in _SCRIPT_SETS[script]["vowel_signs"]


def is_virama(char: str, script: str) -> bool:
    """True if *char* is the virama (halant / pulli) of *script*."""
    cp = ord(char)
    return cp == SCRIPTS[script].get("virama")


def is_combining(char: str, script: str) -> bool:
    """True if *char* is any combining diacritic that attaches to the preceding Akshara.

    Covers: vowel signs, virama, anusvara, visarga, nukta, addak, tippi/bindi.
    """
    cp = ord(char)
    sets = _SCRIPT_SETS[script]
    return cp in sets["vowel_signs"] or cp in sets["combining_extras"]
