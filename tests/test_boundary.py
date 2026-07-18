"""
Akshara boundary segmentation tests.

Each test verifies a specific Brahmic rule or script behaviour.
Run with: python -m pytest akshara_tokenizer/tests/ -v
"""

import pytest
from akshara_tokenizer.boundary import segment_aksharas, count_aksharas


# ---------------------------------------------------------------------------
# Gurmukhi (Punjabi)
# ---------------------------------------------------------------------------

class TestGurmukhi:
    def test_tippi_attaches_to_preceding(self):
        # ੰ (tippi/U+0A70) is a nasalisation mark, glues to pa, not ja
        assert segment_aksharas("ਪੰਜਾਬ") == ["ਪੰ", "ਜਾ", "ਬ"]

    def test_addak_attaches_to_preceding_vowel(self):
        # ੱ (addak/U+0A71) doubles following consonant; attaches to ਅ
        assert segment_aksharas("ਅੱਜ") == ["ਅੱ", "ਜ"]

    def test_independent_vowel_then_vowel_sign(self):
        # ਆ is independent; ਿ is a vowel sign attaching to ਗ
        assert segment_aksharas("ਗਿਆਨ") == ["ਗਿ", "ਆ", "ਨ"]

    def test_simple_consonants_no_matras(self):
        assert segment_aksharas("ਨਿਆਯ") == ["ਨਿ", "ਆ", "ਯ"]

    def test_nukta_combines_into_sha(self):
        # ਸ + ਼ (nukta/U+0A3C) → ਸ਼ (sha), must not split
        assert segment_aksharas("ਦਰਸ਼ਨ") == ["ਦ", "ਰ", "ਸ਼", "ਨ"]

    def test_aa_matra(self):
        assert segment_aksharas("ਪੰਜਾਬ")[1] == "ਜਾ"   # ਜ + ਾ

    def test_word_punjab(self):
        result = segment_aksharas("ਪੰਜਾਬ")
        assert result == ["ਪੰ", "ਜਾ", "ਬ"]

    def test_count_aksharas(self):
        assert count_aksharas("ਪੰਜਾਬ") == 3


# ---------------------------------------------------------------------------
# Devanagari (Hindi)
# ---------------------------------------------------------------------------

class TestDevanagari:
    def test_consonant_with_aa_matra(self):
        # भा = bhaa, र = ra (inherent a), त = ta
        assert segment_aksharas("भारत") == ["भा", "र", "त"]

    def test_virama_conjunct_with_matra(self):
        # ज् + ञ → conjunct ज्ञ, then ा matra → ज्ञा, then न
        assert segment_aksharas("ज्ञान") == ["ज्ञा", "न"]

    def test_double_conjunct(self):
        # क् + य → conjunct क्य, then ा → क्या (one unit)
        assert segment_aksharas("क्या") == ["क्या"]

    def test_simple_word(self):
        assert segment_aksharas("भारत") == ["भा", "र", "त"]

    def test_nyaya(self):
        # न्या = न् + या, य = ya
        result = segment_aksharas("न्याय")
        assert result == ["न्या", "य"]


# ---------------------------------------------------------------------------
# Tamil
# ---------------------------------------------------------------------------

class TestTamil:
    def test_pulli_creates_dead_consonant(self):
        # ழ் = zha + pulli (virama) → dead consonant, complete Akshara
        assert segment_aksharas("தமிழ்") == ["த", "மி", "ழ்"]

    def test_vowel_sign_i(self):
        # ம + ி = mi
        result = segment_aksharas("தமிழ்")
        assert result[1] == "மி"

    def test_consonant_cluster_word(self):
        # இன்று = இ + ன் + று  (today)
        # Tamil pulli always creates a dead consonant, never a conjunct.
        # ன் = dead na (complete Akshara), று = ற + ு
        result = segment_aksharas("இன்று")
        assert result == ["இ", "ன்", "று"]


# ---------------------------------------------------------------------------
# Mixed script (Indic + Latin)
# ---------------------------------------------------------------------------

class TestMixedScript:
    def test_latin_then_gurmukhi(self):
        # Latin chars each become their own unit; Indic follows Akshara rules
        result = segment_aksharas("IYRA ਦਰਸ਼ਨ")
        assert result == ["I", "Y", "R", "A", " ", "ਦ", "ਰ", "ਸ਼", "ਨ"]

    def test_space_is_individual_token(self):
        tokens = segment_aksharas("ਪੰਜਾਬ ਦੀ")
        assert " " in tokens

    def test_digits_are_individual(self):
        tokens = segment_aksharas("ਕ੍ਰਮ 123")
        assert "1" in tokens and "2" in tokens and "3" in tokens

    def test_purely_latin(self):
        # No Indic chars → each character is its own unit
        assert segment_aksharas("abc") == ["a", "b", "c"]

    def test_empty_string(self):
        assert segment_aksharas("") == []


# ---------------------------------------------------------------------------
# Fertility sanity checks
# ---------------------------------------------------------------------------

class TestFertility:
    def _fertility(self, sentence: str) -> float:
        words = sentence.split()
        from akshara_tokenizer.unicode_tables import get_script
        aksharas = sum(
            1 for tok in segment_aksharas(sentence)
            if get_script(tok[0]) is not None
        )
        return aksharas / len(words)

    def test_punjabi_fertility_within_target(self):
        sentences = [
            "ਅੱਜ ਅਸਮਾਨ ਬਹੁਤ ਨੀਲਾ ਹੈ",
            "ਪੰਜਾਬ ਦੀ ਧਰਤੀ ਬਹੁਤ ਉਪਜਾਊ ਹੈ",
        ]
        avg = sum(self._fertility(s) for s in sentences) / len(sentences)
        assert avg <= 2.8, f"Punjabi fertility {avg:.2f} too high"

    def test_hindi_fertility_within_target(self):
        sentences = [
            "आज आसमान बहुत नीला है",
            "भारत एक महान देश है",
        ]
        avg = sum(self._fertility(s) for s in sentences) / len(sentences)
        assert avg <= 2.8, f"Hindi fertility {avg:.2f} too high"


# ---------------------------------------------------------------------------
# v1.1: anusvara / visarga / candrabindu attach to the preceding akshara
# (telugu and kannada previously had no anusvara/visarga/candrabindu defined,
#  so those marks segmented standalone; bengali/devanagari lacked candrabindu)
# ---------------------------------------------------------------------------

class TestCombiningMarksV11:
    def test_telugu_anusvara_attaches(self):
        # anusvara U+0C02 must glue to స, giving సం
        assert segment_aksharas("సంఖ్య")[0] == "సం"
        assert "ం" not in segment_aksharas("సంఖ్య")

    def test_telugu_visarga_attaches(self):
        # visarga U+0C03 must glue to దు, giving దుః
        assert segment_aksharas("దుఃఖ")[0] == "దుః"
        assert "ః" not in segment_aksharas("దుఃఖ")

    def test_telugu_candrabindu_attaches(self):
        # candrabindu U+0C01 glues to the preceding consonant
        assert segment_aksharas("కఁ") == ["కఁ"]

    def test_kannada_anusvara_attaches(self):
        # anusvara U+0C82 must glue to ಸ, giving ಸಂ
        assert segment_aksharas("ಸಂಖ್ಯೆ")[0] == "ಸಂ"
        assert "ಂ" not in segment_aksharas("ಸಂಖ್ಯೆ")

    def test_kannada_visarga_attaches(self):
        assert segment_aksharas("ದುಃಖ")[0] == "ದುಃ"
        assert "ಃ" not in segment_aksharas("ದುಃಖ")

    def test_kannada_candrabindu_attaches(self):
        assert segment_aksharas("ಕಁ") == ["ಕಁ"]

    def test_bengali_visarga_attaches(self):
        # visarga U+0983 glues to দু, giving দুঃ
        assert segment_aksharas("দুঃখ")[0] == "দুঃ"
        assert "ঃ" not in segment_aksharas("দুঃখ")

    def test_bengali_candrabindu_attaches(self):
        # candrabindu U+0981 glues to চা, giving চাঁ
        assert segment_aksharas("চাঁদ")[0] == "চাঁ"
        assert "ঁ" not in segment_aksharas("চাঁদ")

    def test_devanagari_candrabindu_attaches(self):
        # candrabindu U+0901 glues to चा, giving चाँ
        assert segment_aksharas("चाँद")[0] == "चाँ"
        assert "ँ" not in segment_aksharas("चाँद")

    def test_gurmukhi_candrabindu_attaches(self):
        # adak bindi U+0A01 glues to the preceding consonant
        assert segment_aksharas("ਕਁ") == ["ਕਁ"]

    def test_bengali_anusvara_still_attaches(self):
        # regression: bengali anusvara U+0982 was already correct
        assert "ং" not in segment_aksharas("বাংলা")
