# phonetic-rhyme

**A pure-Python Russian phonetic rhyme engine — detect words that _sound_ alike, not just spelled alike.**

`рад` and `брат` do not share a single letter of their endings on paper, yet they rhyme perfectly
in speech (`/rat/` vs `/brat/`). This library models the Russian sound system with a compact,
documented rule set — grapheme-to-phoneme conversion, stress, and vowel reduction — and compares
the resulting **phonetic tails** to decide whether two words rhyme. No dictionaries, no ML, no
network: everything is deterministic and offline.

## Features

- **Rule-based Cyrillic G2P** — maps letters to a readable phoneme alphabet with iotation
  (`е ё ю я` → glide or softening), palatalisation, regressive voicing assimilation, and word-final
  devoicing.
- **Stress + reduction** — accepts an explicit stress position, falls back to a small built-in
  exceptions dictionary, then to a documented last-vowel default. Applies akanye (`о→a`) and ikanye
  (`е→i`, soft-`а→i`) to unstressed vowels.
- **Phonetic rhyme keys** — the tail from the stressed vowel to the end, computed *after* reduction,
  so `готова` and `какого` match once the silent-letter genitive rule (`-ого → /ova/`) is applied.
- **Strict and loose matching** — exact key equality, or last-`N`-phoneme assonance for near-rhymes.
- **Zero dependencies** — pure standard-library Python, fully typed, `ruff`- and `mypy`-clean.

## Quickstart

```bash
# clone, then (using uv — or plain pip)
uv venv && uv pip install -e ".[dev]"
# or: python -m venv .venv && .venv/bin/pip install -e ".[dev]"
```

```python
from phonetic_rhyme import do_rhyme, rhyme_key, find_rhymes

do_rhyme("рад", "брат", 0, 0)        # True  — same /at/ tail
do_rhyme("готова", "какого")          # True  — same /ova/ tail after reduction
do_rhyme("дом", "мир", 0, 0)          # False

rhyme_key("рад", stress=0)            # 'a.t'
```

## Usage examples

### Rhyme keys

The rhyme key is the phonetic tail starting at the stressed vowel:

```python
from phonetic_rhyme import rhyme_key

rhyme_key("рад", stress=0)      # 'a.t'   (final д devoices to т)
rhyme_key("готова")             # 'o.v.a' (stress auto-resolved from exceptions)
rhyme_key("какого")             # 'o.v.a' (-ого pronounced /ova/)
rhyme_key("мама", stress=1)     # 'a'     (tail is just the stressed vowel)
```

### Finding rhymes in a list

```python
from phonetic_rhyme import find_rhymes

matches = find_rhymes("кот", ["год", "рот", "мир", "дом", "пот"], stress=0)
[m.word for m in matches]       # ['год', 'рот', 'пот']
matches[0]                      # RhymeMatch(word='год', key='o.t', exact=True)
```

### Loose (assonance) matching

```python
from phonetic_rhyme import do_rhyme

do_rhyme("дом", "сам", 0, 0)                          # False (o.m vs a.m)
do_rhyme("дом", "сам", 0, 0, loose=True, tail=1)      # True  (shared final /m/)
```

### Inspecting the pipeline

```python
from phonetic_rhyme import grapheme_to_phonemes, phonemize

grapheme_to_phonemes("семья")   # ['s', 'e', "m'", 'j', 'a']  (ь keeps the glide)
phonemize("готова", stress=1)   # (['g', 'a', 't', 'o', 'v', 'a'], 1)  after reduction
```

## How it works

The engine is a three-stage pipeline, one module per stage:

1. **`g2p.py` — grapheme → phoneme.** A single left-to-right pass over the Cyrillic string.
   Iotated vowels either emit a `/j/` glide (word-initial, after a vowel, after `ъ`/`ь`) or softens
   the preceding consonant. A post-pass applies word-final devoicing first, then regressive voicing
   assimilation, so a devoiced final consonant can propagate leftward
   (`подъезд → …з.д → …з.т → …с.т`). A small orthographic rule rewrites the genitive `-ого/-его`
   ending's `г` to `в`.

2. **`stress.py` — stress & reduction.** Stress is the index of the stressed vowel (automatic Russian
   stress needs a dictionary, which this library deliberately avoids). It is taken from the explicit
   argument, then a built-in exceptions table, then a last-vowel default. Unstressed vowels are then
   reduced: `о→a`, `е→i`, and `а→i` after a soft consonant. The stressed vowel is never touched.

3. **`rhyme.py` — rhyme keys.** The rhyme key is the reduced phoneme tail from the stressed vowel to
   the end. Two words rhyme when their keys are equal (strict) or when their last `N` phonemes match
   (loose). `find_rhymes` scans a candidate list and reports each match with its key and whether it
   was exact.

The phoneme alphabet is intentionally readable (`a o u i y e` for vowels; base Latin letters for
consonants; a trailing `'` marks palatalisation), so every intermediate result can be eyeballed and
asserted in tests.

## Tech

- Python ≥ 3.11, standard library only (no runtime dependencies).
- Build: `hatchling`. Lint: `ruff` (line length 120). Types: `mypy --strict`. Tests: `pytest`.

## Run the tests

```bash
pytest                 # run the suite
ruff check .           # lint
mypy src               # type-check
```

## License

MIT — see [LICENSE](LICENSE).
