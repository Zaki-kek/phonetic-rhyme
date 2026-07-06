"""Stress placement and vowel reduction for Russian phonetic keys.

Automatic Russian stress prediction requires a pronunciation dictionary, which
is out of scope for a dependency-free engine. Instead this module accepts an
*explicit* stress position and provides:

    * a small built-in exceptions dictionary for common words,
    * a documented default (stress the last vowel) when nothing else is known,
    * vowel reduction (akanye / ikanye) applied to the phoneme string.

Stress is expressed as the **index of the stressed vowel among vowels**
(0-based). For example, in "готова" (phonemes g o t o v a) the stressed vowel
is the second ``o`` -> vowel index ``1``.

Vowel reduction rules implemented (standard literary Russian, a simplified
two-degree model collapsed to one degree for rhyme purposes):

    * Unstressed /o/ -> /a/            (akanye:  "кОрова" -> k a r o v a)
    * Unstressed /e/ -> /i/ after soft, /y/-ish after hard; we use /i/
      (ikanye) which is the dominant literary variant.
    * Unstressed /a/ after a *soft* consonant or glide -> /i/ (e.g. "часы").
    * Other vowels (u, i, y) are treated as reduction-stable.

The stressed vowel itself is never reduced.
"""

from __future__ import annotations

import logging
from typing import Final

from phonetic_rhyme.g2p import ALWAYS_SOFT, GLIDE, VOWELS, grapheme_to_phonemes

logger = logging.getLogger(__name__)

#: Built-in stress exceptions: word -> index of the stressed vowel (0-based).
#: Only a handful of high-frequency words; extend as needed. Keys are lowercase.
STRESS_EXCEPTIONS: Final[dict[str, int]] = {
    "готова": 1,  # go-tO-va
    "какого": 1,  # ka-kO-vo
    "корова": 1,  # ko-rO-va
    "молоко": 2,  # mo-lo-kO
    "хорошо": 2,  # ho-ro-shO
    "здравствуйте": 1,
    "спасибо": 1,  # spa-sI-bo
    "человек": 2,  # che-lo-vEk
    "вода": 1,  # va-dA
    "нога": 1,  # na-gA
}


def count_vowels(phonemes: list[str]) -> int:
    """Count vowel phonemes in a phoneme list.

    Args:
        phonemes: Phoneme symbols.

    Returns:
        The number of symbols that are vowels.
    """
    return sum(1 for p in phonemes if p in VOWELS)


def resolve_stress(word: str, phonemes: list[str], stress: int | None) -> int:
    """Resolve the stressed-vowel index for a word.

    Resolution order:
        1. explicit ``stress`` argument (validated),
        2. built-in :data:`STRESS_EXCEPTIONS`,
        3. default: the last vowel (with a debug-level note).

    Args:
        word: The original (lowercased) word, used for the exceptions lookup.
        phonemes: The word's phoneme list (used to count vowels / clamp).
        stress: Explicit 0-based index of the stressed vowel, or ``None``.

    Returns:
        A valid 0-based stressed-vowel index. If the word has no vowels,
        returns ``-1``.

    Raises:
        ValueError: If ``stress`` is given but out of range.
    """
    n_vowels = count_vowels(phonemes)
    if n_vowels == 0:
        logger.debug("Word %r has no vowels; stress index = -1", word)
        return -1

    if stress is not None:
        if not 0 <= stress < n_vowels:
            raise ValueError(
                f"stress index {stress} out of range for {word!r} "
                f"(has {n_vowels} vowel(s))"
            )
        return stress

    key = word.strip().lower()
    if key in STRESS_EXCEPTIONS:
        idx = STRESS_EXCEPTIONS[key]
        if 0 <= idx < n_vowels:
            return idx
        logger.warning("Exception stress %d invalid for %r; falling back", idx, word)

    logger.debug("No stress info for %r; defaulting to last vowel", word)
    return n_vowels - 1


def _reduce_one(vowel: str, prev: str | None) -> str:
    """Reduce a single unstressed vowel given its left context.

    Args:
        vowel: The unstressed vowel phoneme.
        prev: The immediately preceding phoneme (or ``None`` at word start).

    Returns:
        The reduced vowel phoneme.
    """
    after_soft = prev is not None and (
        prev.endswith("'") or prev == GLIDE or prev in ALWAYS_SOFT
    )

    if vowel == "o":
        return "a"
    if vowel == "e":
        return "i"
    if vowel == "a" and after_soft:
        return "i"
    return vowel


def apply_reduction(phonemes: list[str], stress: int) -> list[str]:
    """Apply vowel reduction to all unstressed vowels.

    Args:
        phonemes: Phoneme symbols (as produced by
            :func:`phonetic_rhyme.g2p.grapheme_to_phonemes`).
        stress: 0-based index of the stressed vowel; ``-1`` for vowel-less
            words means "reduce nothing".

    Returns:
        A new phoneme list with unstressed vowels reduced. Consonants and the
        stressed vowel are unchanged.
    """
    result: list[str] = []
    vowel_idx = -1
    for i, p in enumerate(phonemes):
        if p in VOWELS:
            vowel_idx += 1
            if vowel_idx == stress:
                result.append(p)
            else:
                prev = phonemes[i - 1] if i > 0 else None
                result.append(_reduce_one(p, prev))
        else:
            result.append(p)
    return result


def phonemize(word: str, stress: int | None = None, *, voicing: bool = True) -> tuple[list[str], int]:
    """Full pipeline: grapheme -> phonemes -> resolve stress -> reduce.

    Args:
        word: Input Cyrillic word.
        stress: Explicit stressed-vowel index, or ``None`` to auto-resolve.
        voicing: Whether to apply voicing assimilation in G2P.

    Returns:
        A tuple ``(reduced_phonemes, stress_index)`` where ``stress_index`` is
        the resolved 0-based stressed-vowel index (``-1`` if none).
    """
    raw = grapheme_to_phonemes(word, voicing=voicing)
    resolved = resolve_stress(word, raw, stress)
    reduced = apply_reduction(raw, resolved)
    return reduced, resolved
