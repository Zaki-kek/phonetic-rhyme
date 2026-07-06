"""Tests for the grapheme-to-phoneme module.

All expected phoneme sequences are hand-computed from the documented rules in
:mod:`phonetic_rhyme.g2p`. Tests are fully offline and deterministic.
"""

from __future__ import annotations

from phonetic_rhyme.g2p import (
    apply_voicing,
    grapheme_to_phonemes,
    is_soft,
    normalize,
    phonemes_to_str,
)


def test_basic_hard_consonants_and_vowels() -> None:
    """A plain word maps letter-by-letter with no softness."""
    assert grapheme_to_phonemes("мама") == ["m", "a", "m", "a"]


def test_iotation_word_initial_glide() -> None:
    """Word-initial е produces a /j/ glide: ель -> j e l'."""
    assert grapheme_to_phonemes("ель") == ["j", "e", "l'"]


def test_no_iotation_after_e_letter() -> None:
    """э does NOT produce a glide: эль -> e l'."""
    assert grapheme_to_phonemes("эль") == ["e", "l'"]


def test_iotation_distinguishes_el_words() -> None:
    """ель and эль differ exactly by the initial glide (iotation handled)."""
    yotated = grapheme_to_phonemes("ель")
    plain = grapheme_to_phonemes("эль")
    assert yotated[0] == "j"
    assert plain[0] != "j"
    # The tail (from the vowel on) is identical; the difference is the glide.
    assert yotated[1:] == plain


def test_iotated_vowel_after_consonant_softens() -> None:
    """е after a consonant softens it without a glide: лес -> l' e s."""
    assert grapheme_to_phonemes("лес") == ["l'", "e", "s"]


def test_soft_sign_is_separating_before_iotated_vowel() -> None:
    """ь before я keeps the glide: семья -> s' e m' j a."""
    assert grapheme_to_phonemes("семья") == ["s'", "e", "m'", "j", "a"]


def test_hard_sign_keeps_glide() -> None:
    """ъ before е keeps the glide: подъезд -> p o d j e s t (with devoicing)."""
    assert grapheme_to_phonemes("подъезд") == ["p", "o", "d", "j", "e", "s", "t"]


def test_i_softens_but_no_glide() -> None:
    """и softens the preceding consonant and adds no glide: мир -> m' i r."""
    assert grapheme_to_phonemes("мир") == ["m'", "i", "r"]


def test_always_hard_consonants_take_no_softness() -> None:
    """ж/ш/ц stay hard even before a softening vowel: жир keeps a hard zh.

    и normally softens the preceding consonant, but ж is always hard, so no
    softness marker is added.
    """
    result = grapheme_to_phonemes("жир", voicing=False)
    assert result[0] == "zh"  # not "zh'"


def test_final_devoicing() -> None:
    """Word-final voiced obstruent devoices: рад -> r a t."""
    assert grapheme_to_phonemes("рад") == ["r", "a", "t"]


def test_regressive_devoicing_in_cluster() -> None:
    """Voiced before voiceless devoices: водка -> v o t k a."""
    assert grapheme_to_phonemes("водка") == ["v", "o", "t", "k", "a"]


def test_regressive_voicing_in_cluster() -> None:
    """Voiceless before voiced voices: сдал -> z d a l."""
    assert grapheme_to_phonemes("сдал") == ["z", "d", "a", "l"]


def test_voicing_preserves_softness() -> None:
    """просьба: с before б voices to з and keeps softness -> z'."""
    assert grapheme_to_phonemes("просьба") == ["p", "r", "o", "z'", "b", "a"]


def test_final_devoicing_propagates_left() -> None:
    """Final devoicing applies before assimilation: подъезд ends in s t."""
    result = grapheme_to_phonemes("подъезд")
    assert result[-2:] == ["s", "t"]


def test_voicing_can_be_disabled() -> None:
    """With voicing off, рад keeps its final д -> r a d."""
    assert grapheme_to_phonemes("рад", voicing=False) == ["r", "a", "d"]


def test_sonorant_does_not_trigger_assimilation() -> None:
    """A sonorant after an obstruent does not change its voicing: смыл."""
    assert grapheme_to_phonemes("смыл", voicing=True) == ["s", "m", "y", "l"]


def test_genitive_ogo_pronounced_as_v() -> None:
    """The -ого ending's г is pronounced /v/: какого -> k a k o v o (raw).

    Reduction (the final о -> a) is applied later by the stress module, not by
    G2P, so the raw phoneme stream still ends in ``o``.
    """
    assert grapheme_to_phonemes("какого") == ["k", "a", "k", "o", "v", "o"]


def test_normalize_lowercases_and_strips() -> None:
    """normalize lowercases and strips whitespace."""
    assert normalize("  РАД  ") == "рад"


def test_unknown_characters_skipped() -> None:
    """Digits and punctuation are dropped from the phoneme stream."""
    assert grapheme_to_phonemes("да!") == ["d", "a"]


def test_empty_word() -> None:
    """An empty word yields an empty phoneme list."""
    assert grapheme_to_phonemes("") == []


def test_apply_voicing_does_not_mutate_input() -> None:
    """apply_voicing returns a new list and leaves the input untouched."""
    original = ["v", "o", "d"]
    snapshot = list(original)
    apply_voicing(original)
    assert original == snapshot


def test_apply_voicing_empty() -> None:
    """apply_voicing on an empty list returns an empty list."""
    assert apply_voicing([]) == []


def test_is_soft_detects_marked_and_always_soft() -> None:
    """is_soft recognises apostrophe-marked and always-soft consonants."""
    assert is_soft("n'")
    assert is_soft("ch")
    assert not is_soft("n")
    assert not is_soft("a")


def test_phonemes_to_str_roundtrip() -> None:
    """phonemes_to_str joins symbols with dots."""
    assert phonemes_to_str(["m", "a", "m", "a"]) == "m.a.m.a"
