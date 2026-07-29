"""दोषाः — the error hierarchy of Vāk. Every message is bilingual."""

from __future__ import annotations


class VakError(Exception):
    """Base class for every Vāk error."""

    title = "दोषः (Error)"
    default_code = "दोषः"

    def __init__(self, message: str, line: int = 0, col: int = 0, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col
        # `code` is the Sanskrit name a दोषे (catch) block sees in error.प्रकारः
        self.code = code or self.default_code

    def render(self, source: str | None = None, filename: str = "<वाक्>") -> str:
        where = f"{filename}:{self.line}:{self.col}" if self.line else filename
        out = [f"{self.title} — {where}", f"    {self.message}"]
        if source and self.line:
            lines = source.splitlines()
            if 0 < self.line <= len(lines):
                out.append(f"    {self.line:>4} | {lines[self.line - 1]}")
                if self.col > 0:
                    out.append(f"    {'':>4} | {' ' * (self.col - 1)}^")
        return "\n".join(out)

    def __str__(self) -> str:
        return f"{self.title}: {self.message} (पङ्क्ति/line {self.line})"


class LexError(VakError):
    """Raised by the lexer for characters it cannot read."""

    title = "अक्षरदोषः (Lexical Error)"
    default_code = "अक्षरदोषः"


class ParseError(VakError):
    """Raised by the parser for malformed grammar."""

    title = "व्याकरणदोषः (Syntax Error)"
    default_code = "व्याकरणदोषः"


class RuntimeVakError(VakError):
    """Raised by the interpreter while a program is running.

    `code` names the kind of fault in Sanskrit, and is what a दोषे (catch)
    block reads from the error कोश as `प्रकारः`:

        नामदोषः      undefined name          कुञ्जिकादोषः  missing dictionary key
        प्रकारदोषः    wrong type              सूचकदोषः     index out of range
        गणितदोषः     arithmetic (÷ by zero)  प्राचलदोषः    wrong number of arguments
        मूल्यदोषः     bad value               उपयोक्तृदोषः  raised by उत्सृज / दोष()
    """

    title = "कार्यकालदोषः (Runtime Error)"
    default_code = "कार्यकालदोषः"
