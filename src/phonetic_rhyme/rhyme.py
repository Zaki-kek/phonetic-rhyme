"""Rhyme detection from phonetic tails.

A *rhyme key* is the phonetic tail of a word starting at the stressed vowel and
running to the end, computed after grapheme-to-phoneme conversion and vowel
reduction. Two words rhyme when their rhyme keys match; a looser mode compares
only the last few phonemes for near-rhymes.

Example (hand-computed):
    "рад"  -> phonemes r a t  (final devoicing д->т), stress on vowel 0
             -> rhyme key "a.t"
    "брат" -> phonemes b r a t, stress on vowel 0
             -> rhyme key "a.t"           => they rhyme.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from phonetic_rhyme.g2p import VOWELS, phonemes_to_str
from phonetic_rhyme.stress import phonemize

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RhymeMatch:
    """A single rhyme result for :func:`find_rhymes`.

    Attributes:
        word: The candidate word.
        key: The candidate's rhyme key.
        exact: ``True`` if the full rhyme keys matched, ``False`` if it was a
            looser tail match.
    """

    word: str
    key: str
    exact: bool


def _tail_from_stress(phonemes: list[str], stress: int) -> list[str]:
    """Return the phoneme sublist from the stressed vowel to the end.

    Args:
        phonemes: Reduced phoneme symbols.
        stress: 0-based index of the stressed vowel; ``-1`` means no vowel, in
            which case the whole list is returned.

    Returns:
        The phonetic tail as a list of symbols.
    """
    if stress < 0:
        return list(phonemes)
    vowel_idx = -1
    for i, p in enumerate(phonemes):
        if p in VOWELS:
            vowel_idx += 1
            if vowel_idx == stress:
                return phonemes[i:]
    return list(phonemes)


def rhyme_key(word: str, stress: int | None = None, *, voicing: bool = True) -> str:
    """Compute the rhyme key (phonetic tail) of a word.

    Args:
        word: Input Cyrillic word.
        stress: Explicit stressed-vowel index (0-based), or ``None`` to
            auto-resolve via the built-in exceptions / last-vowel default.
        voicing: Whether to apply voicing assimilation during G2P.

    Returns:
        The rhyme key as a dotted phoneme string (e.g. ``"a.t"``).

    Examples:
        >>> rhyme_key("рад", stress=0)
        'a.t'
        >>> rhyme_key("брат", stress=0)
        'a.t'
    """
    reduced, resolved = phonemize(word, stress, voicing=voicing)
    tail = _tail_from_stress(reduced, resolved)
    key = phonemes_to_str(tail)
    logger.debug("rhyme_key(%r, stress=%s) -> %s", word, stress, key)
    return key


def _last_n_symbols(key: str, n: int) -> str:
    """Return the last ``n`` phoneme symbols of a dotted rhyme key."""
    parts = key.split(".") if key else []
    return ".".join(parts[-n:])


def do_rhyme(
    w1: str,
    w2: str,
    s1: int | None = None,
    s2: int | None = None,
    *,
    loose: bool = False,
    tail: int = 3,
    voicing: bool = True,
) -> bool:
    """Return whether two words rhyme.

    In strict mode (default) the full rhyme keys must be equal. In loose mode
    the last ``tail`` phoneme symbols must match, which catches near-rhymes and
    tolerates small differences before the stressed vowel's coda.

    Args:
        w1: First word.
        w2: Second word.
        s1: Explicit stress index for ``w1`` (or ``None``).
        s2: Explicit stress index for ``w2`` (or ``None``).
        loose: If ``True``, compare only the last ``tail`` symbols.
        tail: Number of trailing phoneme symbols to compare in loose mode.
        voicing: Whether to apply voicing assimilation.

    Returns:
        ``True`` if the words rhyme under the selected mode.
    """
    k1 = rhyme_key(w1, s1, voicing=voicing)
    k2 = rhyme_key(w2, s2, voicing=voicing)
    if not k1 or not k2:
        return False
    if k1 == k2:
        return True
    if loose:
        n = max(1, tail)
        return _last_n_symbols(k1, n) == _last_n_symbols(k2, n)
    return False


def find_rhymes(
    word: str,
    candidates: list[str],
    stress: int | None = None,
    *,
    stresses: dict[str, int] | None = None,
    loose: bool = False,
    tail: int = 3,
    voicing: bool = True,
) -> list[RhymeMatch]:
    """Find all candidates that rhyme with ``word``.

    The target word never rhymes with an identical spelling of itself only by
    coincidence; identical candidates are still reported (they trivially match).

    Args:
        word: The target word.
        candidates: Candidate words to test.
        stress: Explicit stress index for the target word.
        stresses: Optional map of ``candidate -> stress index`` for candidates
            whose stress is known; unknown candidates use auto-resolution.
        loose: If ``True``, accept near-rhymes on the last ``tail`` symbols.
        tail: Trailing-symbol count for loose matching.
        voicing: Whether to apply voicing assimilation.

    Returns:
        A list of :class:`RhymeMatch` for every rhyming candidate, in input
        order. Exact matches are marked ``exact=True``.
    """
    stresses = stresses or {}
    target_key = rhyme_key(word, stress, voicing=voicing)
    if not target_key:
        logger.debug("Target %r has empty rhyme key; no matches", word)
        return []

    n = max(1, tail)
    target_tail = _last_n_symbols(target_key, n)
    matches: list[RhymeMatch] = []
    for cand in candidates:
        cand_stress = stresses.get(cand)
        cand_key = rhyme_key(cand, cand_stress, voicing=voicing)
        if not cand_key:
            continue
        if cand_key == target_key:
            matches.append(RhymeMatch(word=cand, key=cand_key, exact=True))
        elif loose and _last_n_symbols(cand_key, n) == target_tail:
            matches.append(RhymeMatch(word=cand, key=cand_key, exact=False))
    logger.debug("find_rhymes(%r) -> %d match(es)", word, len(matches))
    return matches
