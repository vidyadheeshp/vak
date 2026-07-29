"""
शब्दविभाजकः — the Lexer (tokenizer) of Vāk.

Turns raw Devanagari/IAST source text into a flat list of Tokens.

Handles
  * Devanagari and ASCII identifiers (including matras, virama, ZWJ/ZWNJ)
  * Devanagari numerals  ०१२३४५६७८९  and ASCII numerals, with decimals
  * strings in "double" or 'single' quotes with \\n \\t \\" \\\\ escapes
  * comments:  # ... end of line   and   /* ... */
  * statement terminators:  ;   ।   ॥
"""

from __future__ import annotations

from .errors import LexError
from .tokens import (
    DANDA,
    DEV_TO_ASCII,
    DOUBLE_DANDA,
    KEYWORDS,
    T,
    Token,
    is_digit,
    is_ident_part,
    is_ident_start,
)

_SINGLE = {
    "(": T.LPAREN, ")": T.RPAREN,
    "{": T.LBRACE, "}": T.RBRACE,
    "[": T.LBRACKET, "]": T.RBRACKET,
    ",": T.COMMA, ".": T.DOT, ":": T.COLON,
    "+": T.PLUS, "-": T.MINUS, "*": T.STAR, "%": T.PERCENT, "^": T.CARET,
    ";": T.SEMI, DANDA: T.SEMI, DOUBLE_DANDA: T.SEMI,
}


class Lexer:
    def __init__(self, source: str, filename: str = "<वाक्>"):
        self.src = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: list[Token] = []

    # -- low level cursor helpers -----------------------------------------
    def _at_end(self) -> bool:
        return self.pos >= len(self.src)

    def _peek(self, offset: int = 0) -> str:
        i = self.pos + offset
        return self.src[i] if i < len(self.src) else "\0"

    def _advance(self) -> str:
        ch = self.src[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _match(self, expected: str) -> bool:
        if self._peek() == expected:
            self._advance()
            return True
        return False

    def _add(self, type_: T, lexeme: str, value: object = None, line: int | None = None,
             col: int | None = None) -> None:
        self.tokens.append(
            Token(type_, lexeme, value, self.line if line is None else line,
                  self.col if col is None else col)
        )

    # -- main loop ---------------------------------------------------------
    def tokenize(self) -> list[Token]:
        while not self._at_end():
            self._scan_token()
        self.tokens.append(Token(T.EOF, "", None, self.line, self.col))
        return self.tokens

    def _scan_token(self) -> None:
        line, col = self.line, self.col
        ch = self._advance()

        # whitespace
        if ch in " \t\r\n":
            return

        # comments
        if ch == "#":
            while not self._at_end() and self._peek() != "\n":
                self._advance()
            return
        if ch == "/" and self._peek() == "/":
            while not self._at_end() and self._peek() != "\n":
                self._advance()
            return
        if ch == "/" and self._peek() == "*":
            self._advance()
            while not self._at_end() and not (self._peek() == "*" and self._peek(1) == "/"):
                self._advance()
            if self._at_end():
                raise LexError("अपूर्णा टिप्पणी — unterminated /* comment", line, col)
            self._advance()  # *
            self._advance()  # /
            return
        if ch == "/":
            if self._peek() == "=":
                self._advance()
                self._add(T.OP_ASSIGN, "/=", None, line, col)
                return
            self._add(T.SLASH, ch, None, line, col)
            return

        # two-character operators
        if ch == "=":
            if self._match("="):
                self._add(T.EQ, "==", None, line, col)
            else:
                self._add(T.ASSIGN, "=", None, line, col)
            return
        if ch == "!":
            if self._match("="):
                self._add(T.NE, "!=", None, line, col)
            else:
                self._add(T.NOT, "!", None, line, col)
            return
        if ch == "<":
            if self._match("="):
                self._add(T.LE, "<=", None, line, col)
            else:
                self._add(T.LT, "<", None, line, col)
            return
        if ch == ">":
            if self._match("="):
                self._add(T.GE, ">=", None, line, col)
            else:
                self._add(T.GT, ">", None, line, col)
            return
        if ch == "&":
            if self._match("&"):
                self._add(T.AND, "&&", None, line, col)
                return
            raise LexError("अज्ञातम् अक्षरम् '&' — unknown character '&'", line, col)
        if ch == "|":
            if self._match("|"):
                self._add(T.OR, "||", None, line, col)
                return
            raise LexError("अज्ञातम् अक्षरम् '|' — unknown character '|'", line, col)

        # संयुक्तनियोजनम् — +=  -=  *=  /=  %=  ^=
        if ch in "+-*/%^" and self._peek() == "=":
            self._advance()
            self._add(T.OP_ASSIGN, ch + "=", None, line, col)
            return

        # single character tokens
        if ch in _SINGLE:
            self._add(_SINGLE[ch], ch, None, line, col)
            return

        # strings
        if ch in ('"', "'"):
            self._string(ch, line, col)
            return

        # numbers
        if is_digit(ch):
            self._number(ch, line, col)
            return

        # identifiers and keywords
        if is_ident_start(ch):
            self._identifier(ch, line, col)
            return

        raise LexError(f"अज्ञातम् अक्षरम् {ch!r} — unknown character {ch!r}", line, col)

    # -- token builders ----------------------------------------------------
    def _string(self, quote: str, line: int, col: int) -> None:
        buf: list[str] = []
        while not self._at_end() and self._peek() != quote:
            ch = self._advance()
            if ch == "\\":
                if self._at_end():
                    break
                esc = self._advance()
                buf.append({
                    "n": "\n", "t": "\t", "r": "\r", "0": "\0",
                    "\\": "\\", '"': '"', "'": "'",
                }.get(esc, "\\" + esc))
            else:
                buf.append(ch)
        if self._at_end():
            raise LexError("अपूर्णः शब्दः — unterminated string literal", line, col)
        self._advance()  # closing quote
        text = "".join(buf)
        self._add(T.STRING, quote + text + quote, text, line, col)

    def _number(self, first: str, line: int, col: int) -> None:
        buf = [first]
        while is_digit(self._peek()):
            buf.append(self._advance())
        is_float = False
        if self._peek() == "." and is_digit(self._peek(1)):
            is_float = True
            buf.append(self._advance())
            while is_digit(self._peek()):
                buf.append(self._advance())
        lexeme = "".join(buf)
        normalized = lexeme.translate(DEV_TO_ASCII)
        value: float | int = float(normalized) if is_float else int(normalized)
        self._add(T.NUMBER, lexeme, value, line, col)

    def _identifier(self, first: str, line: int, col: int) -> None:
        buf = [first]
        while is_ident_part(self._peek()):
            buf.append(self._advance())
        lexeme = "".join(buf)
        self._add(KEYWORDS.get(lexeme, T.IDENT), lexeme, None, line, col)


def tokenize(source: str, filename: str = "<वाक्>") -> list[Token]:
    """Convenience wrapper."""
    return Lexer(source, filename).tokenize()
