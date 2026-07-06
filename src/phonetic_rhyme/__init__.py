"""Russian phonetic rhyme engine.

Detect words that *sound* alike, not just spelled alike, using a pure-Python
pipeline: rule-based grapheme-to-phoneme conversion, explicit/heuristic stress,
vowel reduction (akanye / ikanye), and phonetic-tail rhyme keys.

Public API:
    * :func:`grapheme_to_phonemes` - Cyrillic word -> phoneme symbols.
    * :func:`phonemize` - full G2P + stress + reduction pipeline.
    * :func:`rhyme_key` - phonetic tail from the stressed vowel.
    * :func:`do_rhyme` - whether two words rhyme.
    * :func:`find_rhymes` - all rhyming candidates for a word.
    * :class:`RhymeMatch` - a single rhyme result.

Example:
    >>> from phonetic_rhyme import do_rhyme
    >>> do_rhyme("рад", "брат", 0, 0)
    True
"""

from __future__ import annotations

from phonetic_rhyme.g2p import (
    apply_voicing,
    grapheme_to_phonemes,
    phonemes_to_str,
)
from phonetic_rhyme.rhyme import (
    RhymeMatch,
    do_rhyme,
    find_rhymes,
    rhyme_key,
)
from phonetic_rhyme.stress import (
    STRESS_EXCEPTIONS,
    apply_reduction,
    phonemize,
    resolve_stress,
)

__version__ = "0.1.0"

__all__ = [
    "STRESS_EXCEPTIONS",
    "RhymeMatch",
    "apply_reduction",
    "apply_voicing",
    "do_rhyme",
    "find_rhymes",
    "grapheme_to_phonemes",
    "phonemes_to_str",
    "phonemize",
    "resolve_stress",
    "rhyme_key",
]
