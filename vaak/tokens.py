"""
शब्दप्रकाराः — Token types and the Sanskrit keyword tables for Vāk (वाक्).

Every keyword and built-in has two spellings:
  * the Devanagari form  (मान, यदि, कार्य ...)
  * an IAST/ASCII form   (mana, yadi, karya ...)
Both are accepted by the lexer so a program can be typed on any keyboard.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class T(Enum):
    """Token kinds."""

    # literals
    NUMBER = auto()
    STRING = auto()
    IDENT = auto()

    # keywords — declarations
    LET = auto()        # मान      māna      "measure/value"      -> let
    CONST = auto()      # ध्रुव     dhruva    "fixed"              -> const
    FUNC = auto()       # कार्यम्   kāryam    "work/task"          -> function
    RETURN = auto()     # प्रत्यागच्छ pratyāgaccha "come back!"     -> return

    # keywords — control flow
    IF = auto()         # यदि      yadi      "if"                 -> if
    ELSE = auto()       # अन्यथा    anyathā   "otherwise"          -> else
    WHILE = auto()      # यावत्     yāvat     "as long as"         -> while
    FOR = auto()        # प्रत्येकम् pratyekam "for each"           -> for
    IN = auto()         # अन्तः     antaḥ     "within"             -> in
    REPEAT = auto()     # आवृत्तिः  āvṛttiḥ   "a turning round"    -> repeat n times
    BREAK = auto()      # विरम     virama    "stop!"              -> break
    CONTINUE = auto()   # अनुवर्त   anuvarta  "carry on!"          -> continue

    # keywords — commands (आज्ञा — the imperative mood)
    PRINT = auto()      # मुद्रय    mudraya   "print!"             -> print statement

    # keywords — modules (आयातः)
    IMPORT = auto()     # आनय      ānaya     "bring!"             -> import
    AS = auto()         # इति      iti       "thus named"         -> as
    FROM = auto()       # तः       taḥ       ablative "from"      -> from

    # keywords — exceptions (दोषनिग्रहः)
    SWITCH = auto()     # विकल्पः   vikalpaḥ  "a choice of options" -> switch
    CASE = auto()       # पक्षे     pakṣe     "in this case"        -> case (locative!)
    TRY = auto()        # प्रयत्नः   prayatnaḥ "an attempt"         -> try
    CATCH = auto()      # दोषे     doṣe      "in case of a fault" -> catch (locative!)
    FINALLY = auto()    # अन्ततः    antataḥ   "in the end"         -> finally
    THROW = auto()      # उत्सृज    utsṛja    "cast forth!"        -> throw

    # keywords — literals
    TRUE = auto()       # सत्य     satya     "truth"              -> true
    FALSE = auto()      # असत्य    asatya    "untruth"            -> false
    NULL = auto()       # शून्य     śūnya     "void"               -> null

    # keywords — logic
    AND = auto()        # च        ca        "and"                -> &&
    OR = auto()         # वा       vā        "or"                 -> ||
    NOT = auto()        # न        na        "not"                -> !

    # single/double character operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    CARET = auto()          # ^  exponent
    ASSIGN = auto()
    OP_ASSIGN = auto()      # += -= *= /= %= ^= — the operator is the lexeme
    EQ = auto()
    NE = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()

    # punctuation
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    DOT = auto()
    COLON = auto()
    SEMI = auto()           # ;  or  ।  (danda)  or  ॥  (double danda)

    EOF = auto()


@dataclass(frozen=True)
class Token:
    type: T
    lexeme: str          # exactly as written in the source
    value: object = None  # cooked value for NUMBER / STRING
    line: int = 0
    col: int = 0

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        v = "" if self.value is None else f" {self.value!r}"
        return f"<{self.type.name} {self.lexeme!r}{v} @{self.line}:{self.col}>"


# --------------------------------------------------------------------------
# keyword table :  lexeme -> token type
# --------------------------------------------------------------------------
KEYWORDS: dict[str, T] = {
    # declarations
    "मान": T.LET, "māna": T.LET, "mana": T.LET,
    "ध्रुव": T.CONST, "dhruva": T.CONST,
    "कार्यम्": T.FUNC, "kāryam": T.FUNC, "karyam": T.FUNC,
    "कार्य": T.FUNC, "kārya": T.FUNC, "karya": T.FUNC,          # पर्यायः / alias
    "प्रत्यागच्छ": T.RETURN, "pratyāgaccha": T.RETURN, "pratyagaccha": T.RETURN,
    "प्रतिदा": T.RETURN, "pratidā": T.RETURN, "pratida": T.RETURN,   # पर्यायः / alias

    # control flow
    "यदि": T.IF, "yadi": T.IF,
    "अन्यथा": T.ELSE, "anyathā": T.ELSE, "anyatha": T.ELSE,
    "यावत्": T.WHILE, "यावत": T.WHILE, "yāvat": T.WHILE, "yavat": T.WHILE,
    "प्रत्येकम्": T.FOR, "प्रत्येकम": T.FOR, "pratyekam": T.FOR,
    "अन्तः": T.IN, "अन्तः": T.IN, "antaḥ": T.IN, "antah": T.IN,
    "आवृत्तिः": T.REPEAT, "आवृत्ति": T.REPEAT, "āvṛttiḥ": T.REPEAT, "avrttih": T.REPEAT,
    "विरम": T.BREAK, "virama": T.BREAK,
    "अनुवर्त": T.CONTINUE, "anuvarta": T.CONTINUE,

    # commands
    "मुद्रय": T.PRINT, "mudraya": T.PRINT,

    # modules
    "आनय": T.IMPORT, "ānaya": T.IMPORT, "anaya": T.IMPORT,
    "इति": T.AS, "iti": T.AS,
    "तः": T.FROM, "taḥ": T.FROM, "tah": T.FROM,

    # exceptions
    "विकल्पः": T.SWITCH, "विकल्प": T.SWITCH, "vikalpaḥ": T.SWITCH,
    "vikalpah": T.SWITCH,
    "पक्षे": T.CASE, "pakṣe": T.CASE, "pakshe": T.CASE,
    "प्रयत्नः": T.TRY, "प्रयत्न": T.TRY, "prayatnaḥ": T.TRY, "prayatnah": T.TRY,
    "दोषे": T.CATCH, "doṣe": T.CATCH, "doshe": T.CATCH,
    "गृहाण": T.CATCH, "gṛhāṇa": T.CATCH, "grihana": T.CATCH,     # पर्यायः / alias
    "अन्ततः": T.FINALLY, "अन्ते": T.FINALLY, "antataḥ": T.FINALLY, "antatah": T.FINALLY,
    "उत्सृज": T.THROW, "utsṛja": T.THROW, "utsrja": T.THROW,
    "क्षिप": T.THROW, "kṣipa": T.THROW, "kshipa": T.THROW,       # पर्यायः / alias

    # literals
    "सत्य": T.TRUE, "satya": T.TRUE,
    "असत्य": T.FALSE, "asatya": T.FALSE,
    "शून्य": T.NULL, "śūnya": T.NULL, "shunya": T.NULL, "sunya": T.NULL,

    # logic
    "च": T.AND, "ca": T.AND,
    "वा": T.OR, "vā": T.OR, "va": T.OR,
    "न": T.NOT, "na": T.NOT,
}


# --------------------------------------------------------------------------
# प्रकारनामानि — type names.
#
# These stay ordinary identifiers in the lexer (so सूची(...) and शब्द(...) keep
# working as function calls); the parser recognises them only in a declaration
# position, i.e. when a type name is immediately followed by a name:
#       पूर्णाङ्कः क = ५।          <- declaration
#       सूची(क)।                  <- still a plain call
# --------------------------------------------------------------------------
TYPE_NAMES: dict[str, str] = {
    "पूर्णाङ्कः": "पूर्णाङ्कः", "पूर्णाङ्क": "पूर्णाङ्कः",
    "purnankah": "पूर्णाङ्कः", "pūrṇāṅkaḥ": "पूर्णाङ्कः",
    "दशांशः": "दशांशः", "दशांश": "दशांशः", "dashamshah": "दशांशः",
    "अङ्कः": "अङ्कः", "अङ्क": "अङ्कः", "ankah": "अङ्कः",
    "शब्दः": "शब्दः", "shabdah": "शब्दः",
    "सत्यता": "सत्यता", "satyata": "सत्यता",
    "सूची": "सूची", "suchi": "सूची",
    "कोशः": "कोशः", "कोश": "कोशः", "koshah": "कोशः",
    "शून्यम्": "शून्यम्", "shunyam": "शून्यम्",
    "किमपि": "किमपि", "kimapi": "किमपि",       # any type
}

ANY_TYPE = "किमपि"


# --------------------------------------------------------------------------
# कारकाणि — the six kāraka roles of Sanskrit grammar, usable as parameter
# markers.  A kāraka says what *part a value plays in the action*, which is
# information a plain type cannot carry:
#
#     कार्यम् छानय(अपादानम् सूची संग्रहः, करणम् कार्यम् परीक्षा) : सूची { ... }
#              ^ the source read from   ^ the instrument used
#
# Like type names these stay ordinary identifiers in the lexer — a kāraka is
# recognised only in a parameter position, so `कर्म` is still a usable name.
# --------------------------------------------------------------------------
KARAKA_NAMES: dict[str, str] = {
    "कर्ता": "कर्ता", "karta": "कर्ता",                        # agent    — प्रथमा
    "कर्म": "कर्म", "कर्मन्": "कर्म", "karma": "कर्म",           # patient  — द्वितीया
    "करणम्": "करणम्", "करण": "करणम्", "karanam": "करणम्",       # means    — तृतीया
    "सम्प्रदानम्": "सम्प्रदानम्", "सम्प्रदान": "सम्प्रदानम्",
    "sampradanam": "सम्प्रदानम्",                              # recipient — चतुर्थी
    "अपादानम्": "अपादानम्", "अपादान": "अपादानम्",
    "apadanam": "अपादानम्",                                    # source   — पञ्चमी
    "अधिकरणम्": "अधिकरणम्", "अधिकरण": "अधिकरणम्",
    "adhikaranam": "अधिकरणम्",                                 # locus    — सप्तमी
}

# the canonical order a Sanskrit sentence names them in
KARAKA_ORDER: list[str] = [
    "कर्ता", "कर्म", "करणम्", "सम्प्रदानम्", "अपादानम्", "अधिकरणम्",
]

KARAKA_VIBHAKTI: dict[str, str] = {
    "कर्ता": "प्रथमा (nominative) — the agent, who acts",
    "कर्म": "द्वितीया (accusative) — the patient, what the action most wants",
    "करणम्": "तृतीया (instrumental) — the means by which it is done",
    "सम्प्रदानम्": "चतुर्थी (dative) — the recipient it is given to",
    "अपादानम्": "पञ्चमी (ablative) — the source it departs from",
    "अधिकरणम्": "सप्तमी (locative) — the locus it happens in",
}


# --------------------------------------------------------------------------
# Devanagari numerals ०-९  <->  ASCII 0-9
# --------------------------------------------------------------------------
DEVANAGARI_DIGITS = "०१२३४५६७८९"
ASCII_DIGITS = "0123456789"
DEV_TO_ASCII = str.maketrans(DEVANAGARI_DIGITS, ASCII_DIGITS)
ASCII_TO_DEV = str.maketrans(ASCII_DIGITS, DEVANAGARI_DIGITS)

DANDA = "।"          # ।
DOUBLE_DANDA = "॥"   # ॥
ZWNJ, ZWJ = "‌", "‍"


VIRAMA = "्"          # U+094D — the vowel-killer that welds a conjunct together


def aksharas(text: str) -> list[str]:
    """अक्षराणि — split a string into syllable clusters, not code points.

    Devanagari writes a syllable as a base letter plus matras, anusvara,
    visarga, and virama-joined consonants: "वाक्" is two akṣaras (वा, क्)
    though it is four code points. Anything that treats a string as a list
    of code points — reversing it especially — produces nonsense text.
    """
    import unicodedata

    clusters: list[str] = []
    for ch in text:
        if clusters and (
            unicodedata.category(ch) in ("Mn", "Mc")      # matras, anusvara, virama
            or ch in (ZWNJ, ZWJ)
            or clusters[-1].endswith(VIRAMA)              # a conjunct continues
            or clusters[-1].endswith(ZWJ)
        ):
            clusters[-1] += ch
        else:
            clusters.append(ch)
    return clusters


def is_devanagari(ch: str) -> bool:
    """True for Devanagari letters, matras and the virama — but not punctuation."""
    o = ord(ch)
    return 0x0900 <= o <= 0x097F and ch not in (DANDA, DOUBLE_DANDA)


def is_digit(ch: str) -> bool:
    return ch in ASCII_DIGITS or ch in DEVANAGARI_DIGITS


def is_ident_start(ch: str) -> bool:
    if is_digit(ch):
        return False
    return ch == "_" or ch.isalpha() or is_devanagari(ch)


def is_ident_part(ch: str) -> bool:
    return is_ident_start(ch) or is_digit(ch) or ch in (ZWNJ, ZWJ)
