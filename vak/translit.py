# -*- coding: utf-8 -*-
"""
लिप्यन्तरणम् — romanised input to Devanagari.

This is a *typing aid*, not part of the language.  Vāk itself never
transliterates: `नाम` and `naam` are two different identifiers, and that is
deliberate — a language that quietly merged them would make every variable name
ambiguous.  What this does is let you type Devanagari on a plain keyboard, so
that you write one consistent spelling in the first place.

The scheme is ITRANS-flavoured and forgiving:

    ka → क       k  → क्      kaa/kA → का     ki → कि     kii/kI → की
    a  → अ       aa/A → आ     i → इ           ii/I → ई
    kya → क्य    kta → क्त    kaM → कं        kaH → कः

Capitals mark the retroflex and long series, as ITRANS does — `T D N S` are
ट ड ण ष, and `A I U` are the long vowels.  Everything is longest-match, so
`chh` beats `ch` beats `c`.

    >>> devanagari("namaste")
    'नमस्ते'
    >>> devanagari("mudraya")
    'मुद्रय'
"""
from __future__ import annotations

# ---------------------------------------------------------------- व्यञ्जनानि
# longest first at match time; order here is just for reading
CONSONANTS: dict[str, str] = {
    "kh": "ख", "gh": "घ", "ch": "च", "Ch": "छ", "chh": "छ", "jh": "झ",
    "Th": "ठ", "Dh": "ढ", "th": "थ", "dh": "ध", "ph": "फ", "bh": "भ",
    "sh": "श", "Sh": "ष", "GY": "ज्ञ", "jn": "ज्ञ",
    # ITRANS writes the two nasals with a tilde; `ng`/`ny` also work
    "~N": "ङ", "ng": "ङ", "~n": "ञ", "ny": "ञ", "N^": "ङ", "JN": "ज्ञ",
    "k": "क", "g": "ग", "c": "च", "j": "ज",
    "T": "ट", "D": "ड", "N": "ण",
    "t": "त", "d": "द", "n": "न",
    "p": "प", "b": "ब", "m": "म",
    "y": "य", "r": "र", "l": "ल", "L": "ळ",
    "v": "व", "w": "व", "S": "ष", "z": "श", "s": "स", "h": "ह",
    "f": "फ", "q": "क", "x": "क्ष",
}

# ------------------------------------------------------------------- स्वराः
# (independent form, matra) — the matra is empty for अ, which every
# consonant already carries
VOWELS: dict[str, tuple[str, str]] = {
    "aa": ("आ", "ा"), "A": ("आ", "ा"),
    "ii": ("ई", "ी"), "I": ("ई", "ी"), "ee": ("ई", "ी"),
    "uu": ("ऊ", "ू"), "U": ("ऊ", "ू"), "oo": ("ऊ", "ू"),
    "ai": ("ऐ", "ै"), "au": ("औ", "ौ"),
    "RRi": ("ऋ", "ृ"), "R^i": ("ऋ", "ृ"), "Ri": ("ऋ", "ृ"),
    "a": ("अ", ""), "i": ("इ", "ि"), "u": ("उ", "ु"),
    "e": ("ए", "े"), "o": ("ओ", "ो"),
}

# ------------------------------------------------------------------- चिह्नानि
MARKS: dict[str, str] = {
    "M": "ं", ".n": "ं", "~": "ँ", "H": "ः", ".h": "्",
}

DIGITS = dict(zip("0123456789", "०१२३४५६७८९"))
VIRAMA = "्"

# One table, longest key first.  Matching per-table would let the one-character
# `~` win over `~N`, turning अङ्क into अँण्क — so every key competes together.
_ALL: list[tuple[str, str]] = (
    [(k, "C") for k in CONSONANTS]
    + [(k, "V") for k in VOWELS]
    + [(k, "M") for k in MARKS]
)
_ALL.sort(key=lambda kv: len(kv[0]), reverse=True)


def _match(text: str, i: int) -> tuple[str, str] | None:
    for key, kind in _ALL:
        if text.startswith(key, i):
            return key, kind
    return None


def devanagari(text: str, digits: bool = False) -> str:
    """Transliterate romanised text.  Anything unrecognised passes through, so
    punctuation, spaces and already-Devanagari characters survive untouched."""
    out: list[str] = []
    i, n = 0, len(text)
    # True when the last thing emitted was a bare consonant still awaiting its
    # vowel — which decides whether the next vowel is a matra or independent,
    # and whether a following consonant needs a virama between them.
    pending = False

    while i < n:
        hit = _match(text, i)
        if hit is None:
            if pending:
                out.append(VIRAMA)          # a consonant ended the syllable
                pending = False
            ch = text[i]
            out.append(DIGITS.get(ch, ch) if digits else ch)
            i += 1
            continue

        key, kind = hit
        if kind == "C":
            if pending:
                out.append(VIRAMA)          # क + t → क्त
            out.append(CONSONANTS[key])
            pending = True
        elif kind == "V":
            independent, matra = VOWELS[key]
            out.append(matra if pending else independent)
            pending = False
        else:                                # a mark attaches to what precedes
            if not out:                      # nothing to attach to — pass through
                out.append(key)
            else:
                out.append(MARKS[key])
            pending = False
        i += len(key)

    if pending:
        out.append(VIRAMA)                  # a word ending in a consonant
    return "".join(out)


def tables_for_js() -> dict:
    """The same tables, for the editor to use — so the transliteration a
    student types with is the one documented here."""
    return {
        "consonants": CONSONANTS,
        "vowels": {k: list(v) for k, v in VOWELS.items()},
        "marks": MARKS,
        "digits": DIGITS,
        "virama": VIRAMA,
    }


if __name__ == "__main__":                                   # pragma: no cover
    CASES = [
        ("namaste", "नमस्ते"), ("mudraya", "मुद्रय"), ("vaak", "वाक्"),
        ("naama", "नाम"), ("karyam", "कर्यम्"), ("yadi", "यदि"),
        ("sanskrit", "सन्स्क्रित्"), ("a", "अ"), ("k", "क्"),
        ("kaa", "का"), ("ki", "कि"), ("kii", "की"), ("kya", "क्य"),
        ("raamaH", "रामः"), ("ka.nsa", "कंस"),
        ("a~Nka", "अङ्क"), ("anga", "अङ"), ("angga", "अङ्ग"),
        ("pa~ncha", "पञ्च"),
        ("kaaryam", "कार्यम्"), ("puurNaa~NkaH", "पूर्णाङ्कः"),
        ("sa~Nkhyaa", "सङ्ख्या"), ("pratyaagachCha", "प्रत्यागच्छ"),
        ("maana", "मान"),
        # a bare consonant really does take a virama — `pratya` for प्रत्य
        ("praty ekam", "प्रत्य् एकम्"), ("pratya ekam", "प्रत्य एकम्"),
    ]
    bad = 0
    for src, want in CASES:
        got = devanagari(src)
        flag = "ok " if got == want else "!! "
        if got != want:
            bad += 1
        print(f"  {flag}{src:12} → {got}" + ("" if got == want else f"   (want {want})"))
    print(f"\nfailing: {bad}/{len(CASES)}")
