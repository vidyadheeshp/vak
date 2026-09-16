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


class ManyError(VakError):
    """A pass that does not stop at its first error, and so carries them all.

    The lexer and the parser both recover and keep going, so one exception is
    raised at the end: it is the first error, and `errors` lists every one in
    source order.  Rendering is the analyser's diagnostic-line format, which is
    also what the editor extension reads — an error rendered any other way
    never reached the editor at all.
    """

    def __init__(self, message: str, line: int = 0, col: int = 0,
                 code: str | None = None, errors: "list[ManyError] | None" = None):
        super().__init__(message, line, col, code)
        self.errors: list[ManyError] = errors if errors is not None else [self]

    def render(self, source: str | None = None, filename: str = "<वाक्>") -> str:
        lines = source.splitlines() if source else []
        out = [f"{self.title} — {len(self.errors)} दोषाः"]
        for err in self.errors:
            # file:line only.  The editor reads `...:(\d+) —`, so a column
            # written there would be taken for the line.
            out.append(f"  दोषः [{err.code}] {filename}:{err.line} — {err.message}")
            if 0 < err.line <= len(lines):
                out.append(f"      {err.line:>4} | {lines[err.line - 1]}")
                if err.col > 0:
                    out.append(f"      {'':>4} | {' ' * (err.col - 1)}^")
        return "\n".join(out)


class LexError(ManyError):
    """Raised by the lexer for characters it cannot read."""

    title = "अक्षरदोषः (Lexical Error)"
    default_code = "अक्षरदोषः"


class ParseError(ManyError):
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


class VakExit(BaseException):
    """निर्गम — the program asked to end, with a status.

    Deliberately not a VakError. `प्रयत्नः` catches VakThrow, and the VM turns a
    RuntimeVakError into a catchable Vāk error, so an exit built on either would
    be swallowed by a दोषे block that meant to catch ordinary faults. A
    BaseException passes through both, as an exit should, and a plain `except
    Exception` around an embedded interpreter will not eat it either.

    It is also not SystemExit: the CLI runs a program on a thread with a bigger
    stack, and SystemExit raised there would end that thread and leave the
    status behind. run_file catches this on the same thread and returns it.
    """

    def __init__(self, code: int = 0):
        super().__init__(code)
        self.code = int(code)
