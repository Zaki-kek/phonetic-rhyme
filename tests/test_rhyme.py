"""Tests for rhyme-key extraction and rhyme detection.

Rhyme keys are hand-computed from the phonetic tail (stressed vowel to end)
after reduction. Tests are offline and deterministic.
"""

from __future__ import annotations

from phonetic_rhyme.rhyme import (
    RhymeMatch,
    do_rhyme,
    find_rhymes,
    rhyme_key,
)


def test_rad_brat_rhyme() -> None:
    """рад and брат share the tail a.t (final devoicing of д)."""
    assert rhyme_key("рад", 0) == "a.t"
    assert rhyme_key("брат", 0) == "a.t"
    assert do_rhyme("рад", "брат", 0, 0)


def test_gotova_kakogo_rhyme_after_reduction() -> None:
    """готова and какого rhyme: both tails are o.v.a (-ого -> /ova/)."""
    assert rhyme_key("готова") == "o.v.a"
    assert rhyme_key("какого") == "o.v.a"
    assert do_rhyme("готова", "какого")


def test_obvious_non_rhyme() -> None:
    """Unrelated words do not rhyme."""
    assert not do_rhyme("дом", "мир", 0, 0)
    assert not do_rhyme("кот", "стул", 0, 0)


def test_rhyme_key_is_stable() -> None:
    """rhyme_key is deterministic across repeated calls."""
    first = rhyme_key("готова")
    for _ in range(5):
        assert rhyme_key("готова") == first


def test_rhyme_key_starts_at_stress() -> None:
    """The key begins at the stressed vowel, dropping the onset."""
    # мама, stress on the last vowel -> tail is just 'a'.
    assert rhyme_key("мама", 1) == "a"
    # мама, stress on the first vowel -> tail is 'a.m.a'.
    assert rhyme_key("мама", 0) == "a.m.a"


def test_iotation_affects_phoneme_but_shared_tail_still_rhymes() -> None:
    """ель and эль rhyme (same stressed /el'/) though onsets differ.

    The glide from iotation sits before the stressed vowel, so it is not part
    of the rhyme tail; the words still rhyme, which is phonetically correct.
    """
    assert rhyme_key("ель") == "e.l'"
    assert rhyme_key("эль") == "e.l'"
    assert do_rhyme("ель", "эль")


def test_iotation_inside_tail_distinguishes_keys() -> None:
    """When the glide falls inside the tail it changes the rhyme key.

    край -> k r a j -> tail a.j ; the glide is part of the tail here, so a word
    without that final glide (шар -> sh a r -> tail a.r) does NOT rhyme.
    """
    assert rhyme_key("край", 0) == "a.j"
    assert rhyme_key("шар", 0) == "a.r"
    assert not do_rhyme("край", "шар", 0, 0)
    assert do_rhyme("край", "сарай", 0, 1)


def test_soft_vs_hard_final_do_not_rhyme() -> None:
    """A soft final consonant does not rhyme with its hard counterpart."""
    # мел -> m' e l  (tail e.l)   vs  ель -> j e l' (tail e.l')
    assert rhyme_key("мел", 0) == "e.l"
    assert rhyme_key("эль", 0) == "e.l'"
    assert not do_rhyme("мел", "эль", 0, 0)


def test_loose_matching_accepts_near_rhyme() -> None:
    """Loose mode matches on the trailing phonemes only (assonance).

    дом -> o.m and сам -> a.m have different full keys but share the final /m/.
    Strict mode rejects them; loose mode with tail=1 accepts them.
    """
    assert rhyme_key("дом", 0) == "o.m"
    assert rhyme_key("сам", 0) == "a.m"
    assert not do_rhyme("дом", "сам", 0, 0)
    assert do_rhyme("дом", "сам", 0, 0, loose=True, tail=1)
    assert not do_rhyme("дом", "сам", 0, 0, loose=True, tail=2)


def test_find_rhymes_returns_matches_in_order() -> None:
    """find_rhymes returns rhyming candidates in input order, marked exact."""
    matches = find_rhymes("кот", ["год", "рот", "мир", "дом", "пот"], 0)
    words = [m.word for m in matches]
    assert words == ["год", "рот", "пот"]
    assert all(isinstance(m, RhymeMatch) for m in matches)
    assert all(m.exact for m in matches)


def test_find_rhymes_with_candidate_stresses() -> None:
    """Per-candidate stress overrides are honoured.

    весна/луна/окна/стена all end in a stressed -а, so all three candidates
    rhyme; кино (tail o) does not.
    """
    matches = find_rhymes(
        "весна",
        ["луна", "окна", "стена", "кино"],
        stress=1,
        stresses={"луна": 1, "окна": 1, "стена": 1, "кино": 1},
    )
    assert {m.word for m in matches} == {"луна", "окна", "стена"}


def test_find_rhymes_loose_marks_non_exact() -> None:
    """Loose matches that are not exact are flagged exact=False.

    дом (o.m) vs сам (a.m): shared final /m/ only -> a loose, non-exact match.
    """
    matches = find_rhymes(
        "дом",
        ["сам"],
        stress=0,
        stresses={"сам": 0},
        loose=True,
        tail=1,
    )
    assert len(matches) == 1
    assert matches[0].word == "сам"
    assert matches[0].exact is False


def test_find_rhymes_empty_candidates() -> None:
    """No candidates yields no matches."""
    assert find_rhymes("кот", [], 0) == []


def test_do_rhyme_empty_word_is_false() -> None:
    """A word with no phonetic content cannot rhyme."""
    assert not do_rhyme("", "кот", None, 0)
