"""Tests for stress resolution and vowel reduction.

Expected reductions are hand-computed from the akanye/ikanye rules documented
in :mod:`phonetic_rhyme.stress`.
"""

from __future__ import annotations

import pytest

from phonetic_rhyme.g2p import grapheme_to_phonemes, phonemes_to_str
from phonetic_rhyme.stress import (
    STRESS_EXCEPTIONS,
    apply_reduction,
    count_vowels,
    phonemize,
    resolve_stress,
)


def test_count_vowels() -> None:
    """count_vowels counts only vowel phonemes."""
    assert count_vowels(["g", "a", "t", "o", "v", "a"]) == 3
    assert count_vowels(["s", "t"]) == 0


def test_resolve_stress_explicit_valid() -> None:
    """An in-range explicit stress index is returned unchanged."""
    phon = grapheme_to_phonemes("готова", voicing=False)
    assert resolve_stress("готова", phon, 1) == 1


def test_resolve_stress_explicit_out_of_range() -> None:
    """An out-of-range explicit stress raises ValueError."""
    phon = grapheme_to_phonemes("рад", voicing=False)
    with pytest.raises(ValueError):
        resolve_stress("рад", phon, 5)


def test_resolve_stress_from_exceptions_dict() -> None:
    """Known words use the built-in stress exceptions."""
    phon = grapheme_to_phonemes("готова")
    assert resolve_stress("готова", phon, None) == STRESS_EXCEPTIONS["готова"]


def test_resolve_stress_default_last_vowel() -> None:
    """Unknown words default to the last vowel."""
    phon = grapheme_to_phonemes("абвгд", voicing=False)  # one vowel: а
    assert resolve_stress("абвгд", phon, None) == 0


def test_resolve_stress_no_vowels() -> None:
    """A vowel-less token resolves to -1."""
    phon = grapheme_to_phonemes("бр", voicing=False)
    assert resolve_stress("бр", phon, None) == -1


def test_akanye_unstressed_o_becomes_a() -> None:
    """Unstressed о reduces to a: готова (stress on 2nd o) -> g a t o v a."""
    reduced, stress = phonemize("готова", 1, voicing=False)
    assert stress == 1
    assert phonemes_to_str(reduced) == "g.a.t.o.v.a"


def test_ikanye_unstressed_e_becomes_i() -> None:
    """Unstressed е reduces to i: река (stress last) -> r' i k a."""
    reduced, _ = phonemize("река", 1, voicing=False)
    assert phonemes_to_str(reduced) == "r'.i.k.a"


def test_unstressed_a_after_soft_becomes_i() -> None:
    """Unstressed а after a soft consonant reduces to i: часы -> ch i s y."""
    reduced, _ = phonemize("часы", 1, voicing=False)
    assert phonemes_to_str(reduced) == "ch.i.s.y"


def test_stressed_vowel_not_reduced() -> None:
    """The stressed vowel is never reduced: корова stress on 2nd o keeps o."""
    reduced, stress = phonemize("корова", 1, voicing=False)
    assert phonemes_to_str(reduced) == "k.a.r.o.v.a"


def test_apply_reduction_leaves_consonants() -> None:
    """apply_reduction changes only unstressed vowels."""
    phon = ["k", "o", "r", "o", "v", "a"]
    reduced = apply_reduction(phon, stress=1)
    assert reduced == ["k", "a", "r", "o", "v", "a"]


def test_apply_reduction_no_vowels() -> None:
    """Reduction with stress -1 changes nothing."""
    phon = ["b", "r"]
    assert apply_reduction(phon, stress=-1) == ["b", "r"]


def test_u_and_i_are_reduction_stable() -> None:
    """u, i, y are not reduced when unstressed: лужу -> l u zh u (u stable)."""
    reduced, _ = phonemize("уму", 1, voicing=False)  # u-mU
    assert phonemes_to_str(reduced) == "u.m.u"


def test_phonemize_returns_stress_index() -> None:
    """phonemize returns the resolved stress index alongside phonemes."""
    _, stress = phonemize("мама", None, voicing=False)
    assert stress == 1  # last vowel default
