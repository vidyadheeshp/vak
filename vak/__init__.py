"""
वाक् (Vāk) — a Sanskrit-native programming language.

    from vak import run_source
    run_source('लिख("नमस्ते जगत्")')

Pipeline:  source text → Lexer → Tokens → Parser → AST → Interpreter → effects
"""

from __future__ import annotations

from typing import Any

from .analyzer import Analyzer, Report, SemanticError, analyze
from .errors import LexError, ParseError, RuntimeVakError, VakError
from .interpreter import Interpreter
from .lexer import Lexer, tokenize
from .parser import Parser, parse

__version__ = "0.10.0"
__all__ = [
    "Lexer", "tokenize", "Parser", "parse", "Analyzer", "analyze", "Report", "Interpreter",
    "VakError", "LexError", "ParseError", "RuntimeVakError", "SemanticError",
    "run_source", "check_source", "__version__",
]


def check_source(source: str, filename: str = "<वाक्>") -> Report:
    """Lex → parse → analyse, and return the diagnostics without running anything."""
    return analyze(parse(tokenize(source, filename), filename), filename)


def run_source(source: str, filename: str = "<वाक्>", interpreter: Interpreter | None = None,
               check: bool = False) -> Any:
    """Lex → parse → (optionally analyse) → interpret, returning the last value.

    `check=True` raises SemanticError if the analyser finds a fatal problem —
    that is what the command line does before running a file.
    """
    program = parse(tokenize(source, filename), filename)
    if check:
        report = Analyzer(filename).analyze(program)
        if not report.ok:
            raise SemanticError(report, filename, source)
    return (interpreter or Interpreter(filename)).run(program)
