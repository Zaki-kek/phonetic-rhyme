"""Rule-based Cyrillic grapheme-to-phoneme (G2P) conversion for Russian.

This module converts a Russian word (Cyrillic string) into a sequence of
phoneme symbols using a principled, dictionary-free rule set. It intentionally
uses a compact ASCII-ish phoneme alphabet so the output is easy to inspect and
compare in tests.

Phoneme alphabet (rough IPA correspondence):

Vowels
    a   -> /a/          (as in "мАма")
    o   -> /o/          (as in "кОт", stressed)
    u   -> /u/          (as in "лУк")
    i   -> /i/          (as in "мИр")
    y   -> /ɨ/          (as in "мЫ")
    e   -> /e/ ~ /ɛ/    (as in "Это")

Consonants
    Hard: b d g z k l m n p r s t f x c ch sh zh j (see mapping below)
    Palatalisation is written as a trailing apostrophe ' on the consonant,
    e.g. "n'" is a soft /nʲ/. This lets stress/reduction and rhyme keys treat
    softness as part of the phonetic tail without a separate stream.

Design notes:
    * Iotated vowels (е ё ю я and и after softening) are expanded either to a
      /j/ + vowel glide (word-initial, after a vowel, after ь/ъ) or to a
      palatalising vowel that softens the preceding consonant.
    * Voicing assimilation and final devoicing are implemented as an optional
      post-processing pass (see :func:`apply_voicing`), enabled by default.
    * The rules are deliberately shallow: this is a rhyme engine, not a full
      TTS front-end. The goal is that words which *sound* alike map to the same
      phonetic tail.
"""

from __future__ import annotations

import logging
from typing import Final

logger = logging.getLogger(__name__)

# --- Phoneme inventories -------------------------------------------------

#: Phoneme symbols that count as vowels.
VOWELS: Final[frozenset[str]] = frozenset({"a", "o", "u", "i", "y", "e"})

#: The glide /j/ produced by iotation.
GLIDE: Final[str] = "j"

# Plain (non-iotating, non-softening) vowel letters -> phoneme.
_HARD_VOWELS: Final[dict[str, str]] = {
    "а": "a",
    "о": "o",
    "у": "u",
    "ы": "y",
    "э": "e",
}

# Iotated / softening vowel letters. Each maps to (glide_vowel, soft_vowel):
#   * glide_vowel  -> used word-initially / after vowel / after ъ ь  ("j" + V)
#   * soft_vowel   -> used after a consonant (softens it, no glide)
_IOTATED_VOWELS: Final[dict[str, tuple[str, str]]] = {
    "я": ("a", "a"),
    "ё": ("o", "o"),
    "ю": ("u", "u"),
    "е": ("e", "e"),
    "и": ("i", "i"),  # и softens a preceding consonant but never adds a glide
}

# Consonant letters -> phoneme. Palatalisation is added separately.
_CONSONANTS: Final[dict[str, str]] = {
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "ж": "zh",
    "з": "z",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "ф": "f",
    "х": "x",
    "ц": "c",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
}

#: Consonants that are always hard (palatalisation marker never applied).
_ALWAYS_HARD: Final[frozenset[str]] = frozenset({"zh", "sh", "c"})

#: Consonants that are always soft (inherently palatalised).
ALWAYS_SOFT: Final[frozenset[str]] = frozenset({"ch", "sch", "j"})

# Voicing pairs for assimilation / final devoicing (voiced -> voiceless).
_DEVOICE: Final[dict[str, str]] = {
    "b": "p",
    "v": "f",
    "g": "k",
    "d": "t",
    "z": "s",
    "zh": "sh",
}
#: Reverse map (voiceless -> voiced) for regressive voicing assimilation.
_VOICE: Final[dict[str, str]] = {v: k for k, v in _DEVOICE.items()}

#: Voiceless obstruents that trigger regressive devoicing of a preceding pair.
_VOICELESS_TRIGGERS: Final[frozenset[str]] = frozenset(
    {"p", "f", "k", "t", "s", "sh", "ch", "c", "x", "sch"}
)

#: Sonorants and /v/ do NOT trigger voicing assimilation in Russian.
_NO_ASSIM_TRIGGERS: Final[frozenset[str]] = frozenset({"l", "m", "n", "r", "j"})


def _strip_palatal(symbol: str) -> str:
    """Return the base consonant symbol without a palatalisation marker.

    Args:
        symbol: A phoneme symbol, possibly ending in an apostrophe.

    Returns:
        The symbol with any trailing apostrophe removed.
    """
    return symbol[:-1] if symbol.endswith("'") else symbol


def is_soft(symbol: str) -> bool:
    """Return whether a phoneme symbol is a palatalised (soft) consonant.

    Args:
        symbol: A phoneme symbol.

    Returns:
        ``True`` if the symbol is a soft consonant (marked with ``'`` or one of
        the always-soft consonants), ``False`` otherwise.
    """
    return symbol.endswith("'") or symbol in ALWAYS_SOFT


def normalize(word: str) -> str:
    """Normalise a raw Cyrillic word for G2P.

    Lowercases, replaces ``ё`` handling is preserved (it is meaningful), and
    strips surrounding whitespace. Non-Cyrillic characters are kept as-is so
    the caller can decide how to handle them, but a warning is logged.

    Args:
        word: Raw input word.

    Returns:
        The normalised word.
    """
    normalized = word.strip().lower()
    if any(ch.isalpha() and ch not in _ALL_LETTERS for ch in normalized):
        logger.warning("Word %r contains non-Russian letters; results may be off", word)
    return normalized


_ALL_LETTERS: Final[frozenset[str]] = frozenset(
    set(_HARD_VOWELS) | set(_IOTATED_VOWELS) | set(_CONSONANTS) | {"й", "ь", "ъ"}
)


def _apply_orthographic_rules(word: str) -> str:
    """Rewrite spelling for pronunciations that letters do not show directly.

    Currently implements the genitive/adjectival ending rule: the ``г`` in the
    endings ``-ого`` / ``-его`` is pronounced /v/, so ``какого`` sounds like
    "какова" and rhymes with ``готова``. We rewrite that ``г`` to ``в`` before
    G2P. The rule only fires at the end of a word to avoid false positives such
    as "много" (adverb) — but "много" also ends in ``-ого``; the rule is a
    known heuristic approximation and is documented as such.

    Args:
        word: A normalised (lowercased) Cyrillic word.

    Returns:
        The word with orthographic rewrites applied.
    """
    for ending in ("ого", "его"):
        if word.endswith(ending) and len(word) > len(ending):
            return word[: -len(ending)] + ending[0] + "в" + ending[2]
    return word


def grapheme_to_phonemes(word: str, *, voicing: bool = True) -> list[str]:
    """Convert a Cyrillic word to a list of phoneme symbols.

    The conversion is a single left-to-right pass with one look-behind (the
    previously emitted phoneme, to decide iotation vs. softening) followed by an
    optional voicing-assimilation pass.

    Args:
        word: Input Cyrillic word (any case; whitespace is stripped).
        voicing: If ``True`` (default) apply regressive voicing assimilation
            and word-final devoicing.

    Returns:
        A list of phoneme symbols. Soft consonants carry a trailing ``'``.

    Examples:
        >>> grapheme_to_phonemes("ель")
        ['j', 'e', "l'"]
        >>> grapheme_to_phonemes("мама")
        ['m', 'a', 'm', 'a']
    """
    word = _apply_orthographic_rules(normalize(word))
    phonemes: list[str] = []
    prev_is_vowel_or_boundary = True  # start of word acts like a boundary

    for letter in word:
        if letter in _HARD_VOWELS:
            phonemes.append(_HARD_VOWELS[letter])
            prev_is_vowel_or_boundary = True
        elif letter in _IOTATED_VOWELS:
            glide_v, soft_v = _IOTATED_VOWELS[letter]
            if letter == "и":
                # и never adds a glide; it softens a preceding consonant.
                _soften_last_consonant(phonemes)
                phonemes.append(soft_v)
            elif prev_is_vowel_or_boundary:
                phonemes.append(GLIDE)
                phonemes.append(glide_v)
            else:
                _soften_last_consonant(phonemes)
                phonemes.append(soft_v)
            prev_is_vowel_or_boundary = True
        elif letter in _CONSONANTS:
            phonemes.append(_CONSONANTS[letter])
            prev_is_vowel_or_boundary = False
        elif letter == "й":
            phonemes.append(GLIDE)
            prev_is_vowel_or_boundary = False
        elif letter == "ь":
            # Soft sign: softens the preceding consonant AND, as a separating
            # sign, lets a following iotated vowel keep its glide (e.g. "семья"
            # -> s' e m' j a). It therefore acts as a boundary.
            _soften_last_consonant(phonemes)
            prev_is_vowel_or_boundary = True
        elif letter == "ъ":
            # Hard sign: forces a following iotated vowel to keep its glide.
            prev_is_vowel_or_boundary = True
        else:
            # Unknown character (digit, punctuation, foreign letter): skip.
            continue

    if voicing:
        phonemes = apply_voicing(phonemes)
    return phonemes


def _soften_last_consonant(phonemes: list[str]) -> None:
    """Mark the last emitted consonant as palatalised, in place.

    Does nothing if the last phoneme is a vowel, a glide, or a consonant that
    cannot take a softness marker (always-hard or already-soft).

    Args:
        phonemes: The phoneme list being built (mutated in place).
    """
    if not phonemes:
        return
    last = phonemes[-1]
    if last in VOWELS or last == GLIDE:
        return
    base = _strip_palatal(last)
    if base in _ALWAYS_HARD or base in ALWAYS_SOFT:
        return
    if not last.endswith("'"):
        phonemes[-1] = last + "'"


def apply_voicing(phonemes: list[str]) -> list[str]:
    """Apply regressive voicing assimilation and final devoicing.

    Russian obstruent clusters assimilate in voicing to their rightmost member,
    and word-final voiced obstruents devoice. Sonorants (l m n r) and /v/ do
    not trigger assimilation.

    Args:
        phonemes: Phoneme list from the main G2P pass.

    Returns:
        A new phoneme list with voicing rules applied (input not mutated).
    """
    if not phonemes:
        return []

    result = list(phonemes)

    # Word-final devoicing FIRST, so the devoiced final can propagate leftward
    # through the regressive-assimilation pass (e.g. "подъезд" -> ...з.д ->
    # ...з.т -> ...с.т).
    last_base = _strip_palatal(result[-1])
    if last_base in _DEVOICE:
        soft = result[-1].endswith("'")
        new_base = _DEVOICE[last_base]
        result[-1] = new_base + ("'" if soft and new_base not in _ALWAYS_HARD else "")

    # Regressive assimilation: scan right-to-left.
    for i in range(len(result) - 2, -1, -1):
        cur_soft = result[i].endswith("'")
        cur_base = _strip_palatal(result[i])
        nxt_base = _strip_palatal(result[i + 1])
        if cur_base in VOWELS or cur_base == GLIDE:
            continue
        if nxt_base in _NO_ASSIM_TRIGGERS or nxt_base in VOWELS or nxt_base == GLIDE:
            continue
        if nxt_base in _VOICELESS_TRIGGERS and cur_base in _DEVOICE:
            # Voiced obstruent before a voiceless one -> devoice it.
            new_base = _DEVOICE[cur_base]
            result[i] = new_base + ("'" if cur_soft and new_base not in _ALWAYS_HARD else "")
        elif nxt_base in _DEVOICE and cur_base in _VOICE:
            # Voiceless obstruent before a (paired) voiced one -> voice it.
            new_base = _VOICE[cur_base]
            result[i] = new_base + ("'" if cur_soft and new_base not in _ALWAYS_HARD else "")

    return result


def phonemes_to_str(phonemes: list[str]) -> str:
    """Render a phoneme list as a dotted string for logging and tests.

    Args:
        phonemes: Phoneme symbols.

    Returns:
        The symbols joined by ``.`` (e.g. ``"m.a.m.a"``).
    """
    return ".".join(phonemes)
