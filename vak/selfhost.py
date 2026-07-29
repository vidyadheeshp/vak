"""
स्वयंसिद्धिः — driving the Vāk-written toolchain from Python.

The lexer, parser and compiler in स्वयंसिद्धिः/ are ordinary Vāk modules. This
loads them into an interpreter once and exposes them as Python functions, so a
program can be compiled *by Vāk* and then run on the SanskritVM:

    from vak.selfhost import compile_with_vak
    chunk = compile_with_vak(source, filename)   # lexed, parsed, compiled in Vāk
    VM(filename).run(chunk)                      # executed by the VM

The bytecode it produces is identical to the Python compiler's — that is what
the test suite asserts, file for file.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from .interpreter import Interpreter
from .kosha import kosha_to_chunk

BOOTSTRAP = Path(__file__).resolve().parent.parent / "स्वयंसिद्धिः"

_LOADER = (
    'आनय "शब्दविभाजकः"। '
    'आनय "व्याकरणम्"। '
    'आनय "संकलकः"। '
    'आनय "यन्त्रम्"।'
)


@lru_cache(maxsize=1)
def toolchain() -> dict[str, Any]:
    """Load शब्दविभाजकः, व्याकरणम् and संकलकः once, and hand back their entry points."""
    from . import run_source

    driver = str(BOOTSTRAP / "चालकः.vak")
    interpreter = Interpreter(driver)
    run_source(_LOADER, driver, interpreter)
    modules = {name: interpreter.globals.get(name)
               for name in ("शब्दविभाजकः",
                            "व्याकरणम्",
                            "संकलकः",
                            "यन्त्रम्")}
    return {
        "interpreter": interpreter,
        "lex": modules["शब्दविभाजकः"]["विभज_मूलम्"],
        "parse": modules["व्याकरणम्"]["रचय_वाक्यरचनाम्"],
        "compile": modules["संकलकः"]["संकलय"],
        "run": modules["यन्त्रम्"]["चालय"],
    }


def tokenize_with_vak(source: str) -> list:
    """Run the Vāk-written lexer."""
    tools = toolchain()
    return tools["lex"].call(tools["interpreter"], [source])


def parse_with_vak(source: str) -> dict:
    """Run the Vāk-written lexer and parser; returns the AST as कोशाः."""
    tools = toolchain()
    return tools["parse"].call(tools["interpreter"], [tokenize_with_vak(source)])


def compile_kosha_with_vak(source: str) -> dict:
    """Lex, parse and compile in Vāk; returns the chunk as कोशाः."""
    tools = toolchain()
    return tools["compile"].call(tools["interpreter"], [parse_with_vak(source)])


def run_with_vak(source: str) -> Any:
    """Lex, parse, compile AND run — every stage in Vāk, including the VM."""
    tools = toolchain()
    return tools["run"].call(tools["interpreter"], [compile_kosha_with_vak(source)])


def compile_with_vak(source: str, filename: str = "<वाक्>") -> Any:
    """Lex, parse and compile in Vāk; returns a Chunk the SanskritVM can run."""
    chunk = kosha_to_chunk(compile_kosha_with_vak(source))
    chunk.name = "<मुख्यम्>"
    return chunk
