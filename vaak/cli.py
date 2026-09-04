"""
वाक्-आदेशपङ्क्तिः — the command line front end.

    python -m vaak examples/01_namaste.vak     # run a program
    python -m vaak                             # start the REPL (संवादः)
    python -m vaak --tokens प्रोग्राम.vak       # dump the token stream
    python -m vaak --ast प्रोग्राम.vak          # dump the syntax tree
    python -m vaak --bytecode प्रोग्राम.vak     # disassemble the bytecode
    python -m vaak --vm प्रोग्राम.vak           # run on the SanskritVM
    python -m vaak --self प्रोग्राम.vak         # compile it with Vāk itself, then run
    python -m vaak --self-vm प्रोग्राम.vak      # compile AND run it with Vāk itself
    python -m vaak --native प्रोग्राम.vak       # build a standalone .exe (needs gcc)
    python -m vaak --builtins                  # list the standard library
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

from . import __version__
from .ast_nodes import ExpressionStmt, Program
from .builtins import BUILTIN_DOCS
from .tokens import KARAKA_ORDER, KARAKA_VIBHAKTI
from .errors import VakError
from .analyzer import Analyzer
from .compiler import compile_program
from .interpreter import Interpreter, VakThrow
from .lexer import tokenize
from .parser import parse
from .vm import VM
from .values import stringify

BANNER = f"""वाक् (Vāk) {__version__} — संस्कृतभाषायाः संगणकभाषा
सहायता: :सहायता   निर्गमः: :निर्गम  (help / exit)"""

HELP = """  मान x = ५                  declare a variable            (māna)
  पूर्णाङ्कः x = ५             declare with a type            (pūrṇāṅkaḥ)
  ध्रुव पाई = ३.१४            declare a constant             (dhruva)
  कार्यम् नाम(अ, ब) : शब्दः {} define a function             (kāryam)
  प्रत्यागच्छ मूल्यम्          return from a function         (pratyāgaccha)
  मुद्रय अ, ब                 print                          (mudraya)
  यदि / अन्यथा                if / else                      (yadi / anyathā)
  यावत् (...) {}              while loop                     (yāvat)
  आवृत्तिः (५) {}             repeat five times              (āvṛttiḥ)
  प्रत्येकम् (x अन्तः स) {}     for-each loop                 (pratyekam ... antaḥ)
  प्रयत्नः {} दोषे (द) {}      try / catch                    (prayatnaḥ / doṣe)
  अन्ततः {}                   finally                        (antataḥ)
  उत्सृज "दोषः"               throw                          (utsṛja)
  विरम / अनुवर्त              break / continue               (virama / anuvarta)
  सत्य / असत्य / शून्य          true / false / null           (satya / asatya / śūnya)
  च / वा / न                  and / or / not                 (ca / vā / na)

  प्रकाराः / types: पूर्णाङ्कः दशांशः अङ्कः शब्दः सत्यता सूची कोशः कार्यम् किमपि

  REPL commands:  :सहायता (:help)  :चिह्नानि (:tokens)  :निर्गम (:exit)"""


def _configure_console() -> None:
    """Devanagari needs UTF-8 on stdout/stderr — Windows defaults to cp1252."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass


# --------------------------------------------------------------------------
# debugging views
# --------------------------------------------------------------------------
def dump_tokens(source: str, filename: str) -> None:
    for tok in tokenize(source, filename):
        value = "" if tok.value is None else f"  = {tok.value!r}"
        print(f"{tok.line:>4}:{tok.col:<3} {tok.type.name:<10} {tok.lexeme!r}{value}")


def dump_ast(node, indent: int = 0) -> None:
    pad = "  " * indent
    if is_dataclass(node) or isinstance(node, Program):
        print(f"{pad}{type(node).__name__}")
        for f in fields(node):
            if f.name == "line":
                continue
            value = getattr(node, f.name)
            if isinstance(value, list):
                print(f"{pad}  {f.name}:")
                for item in value:
                    dump_ast(item, indent + 2)
            elif is_dataclass(value):
                print(f"{pad}  {f.name}:")
                dump_ast(value, indent + 2)
            else:
                print(f"{pad}  {f.name}: {value!r}")
    elif isinstance(node, tuple):
        for item in node:
            dump_ast(item, indent)
    else:
        print(f"{pad}{node!r}")


def list_karakas() -> None:
    print("कारकाणि / the kāraka roles a parameter may declare\n")
    for role in KARAKA_ORDER:
        print(f"  {role:<14} {KARAKA_VIBHAKTI[role]}")
    print("\n  कार्यम् छानय(अपादानम् सूची संग्रहः, करणम् कार्यम् परीक्षा) : सूची { ... }")


def list_builtins() -> None:
    print("अन्तर्निहितानि कार्याणि / built-in functions\n")
    for dev, iast, doc in BUILTIN_DOCS:
        print(f"  {dev:<12} {iast:<12} {doc}")


# --------------------------------------------------------------------------
# running
# --------------------------------------------------------------------------
def run_file(path: Path, show_tokens: bool = False, show_ast: bool = False,
             check_only: bool = False, skip_check: bool = False,
             show_bytecode: bool = False, use_vm: bool = False,
             self_hosted: bool = False, self_vm: bool = False,
             native: bool = False, run_native: bool = False) -> int:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as err:
        print(f"सञ्चिका न प्राप्ता / cannot read file: {err}", file=sys.stderr)
        return 66

    try:
        if show_tokens:
            dump_tokens(source, str(path))
            return 0
        program = parse(tokenize(source, str(path)), str(path))
        if show_ast:
            dump_ast(program)
            return 0

        if not skip_check:
            report = Analyzer(str(path)).analyze(program)
            if report.diagnostics:
                print(report.render(source, str(path)), file=sys.stderr)
            if not report.ok:
                return 65                      # अर्थदोषः — do not run a broken program
            if check_only:
                return 0
        if check_only:
            print("परीक्षा त्यक्ता / check skipped")
            return 0

        if native or run_native:
            from .native import build_executable, find_gcc
            if find_gcc() is None:
                print("C-संकलकः न प्राप्तः / no C compiler found — install gcc "
                      "(w64devkit) and put its bin directory on PATH", file=sys.stderr)
                return 69
            exe = build_executable(source, path, keep_c=native and not run_native)
            if not run_native:
                print(f"रचितम् / built: {exe}")
                return 0
            import subprocess
            return subprocess.run([str(exe)]).returncode
        if self_vm:
            # लेखनम्, पठनम्, संकलनम्, चालनम् — सर्वम् वाक्-भाषया
            from .selfhost import run_with_vak
            run_with_vak(source)
            return 0
        if self_hosted:
            # लेखनम् पठनम् संकलनम् च वाक्-भाषया एव / lexed, parsed and compiled in Vāk
            from .selfhost import compile_with_vak
            chunk = compile_with_vak(source, str(path))
            if show_bytecode:
                print(chunk.disassemble())
                return 0
            VM(str(path)).run(chunk)
            return 0
        if show_bytecode:
            print(compile_program(program, str(path)).disassemble())
            return 0
        if use_vm:
            VM(str(path)).run(compile_program(program, str(path)))
        else:
            Interpreter(str(path)).run(program)
        return 0
    except VakError as err:
        print(err.render(source, str(path)), file=sys.stderr)
        return 70
    except RecursionError:
        print("अतिगभीरम् आवर्तनम् / recursion too deep", file=sys.stderr)
        return 70
    except KeyboardInterrupt:
        print("\nविरामः / interrupted", file=sys.stderr)
        return 130


HISTORY_LIMIT = 1000


def history_path() -> Path:
    """Where the संवादः remembers what you typed."""
    return Path.home() / ".vaak_history"


def enable_history() -> object | None:
    """Load the REPL's history and arrange to save it on exit.

    readline is not in the standard library on Windows — which is where Vāk is
    developed — so every part of this is optional. A missing module, an
    unreadable home directory or a read-only disk each mean history does not
    persist, which is a small loss and never a reason to refuse to start.

    Returns the readline module when history is live, and None otherwise, so a
    caller can tell without catching anything.
    """
    try:
        import atexit
        import readline
    except ImportError:                 # Windows, or a build without it
        return None

    path = history_path()
    try:
        readline.read_history_file(str(path))
    except (OSError, ValueError):       # absent, or written by something else
        pass
    readline.set_history_length(HISTORY_LIMIT)

    def save() -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            readline.write_history_file(str(path))
        except OSError:                 # read-only home, full disk
            pass

    atexit.register(save)
    return readline


def repl() -> int:
    print(BANNER)
    enable_history()
    interpreter = Interpreter("<संवादः>")
    buffer: list[str] = []

    while True:
        prompt = "वाक्> " if not buffer else "  ... "
        try:
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print("\nगच्छतु शुभम् / farewell")
            return 0

        stripped = line.strip()
        if not buffer and stripped in (":निर्गम", ":exit", ":quit", ":q"):
            print("गच्छतु शुभम् / farewell")
            return 0
        if not buffer and stripped in (":सहायता", ":help", ":h"):
            print(HELP)
            continue
        if not buffer and stripped in (":चिह्नानि", ":tokens"):
            print("(अग्रिमा पङ्क्तिः चिह्नरूपेण दर्श्यते / next line will be shown as tokens)")
            try:
                dump_tokens(input("चिह्न> "), "<संवादः>")
            except VakError as err:
                print(err, file=sys.stderr)
            continue
        if not buffer and not stripped:
            continue

        buffer.append(line)
        source = "\n".join(buffer)
        if source.count("{") > source.count("}"):      # keep reading a block
            continue
        buffer.clear()

        try:
            program = parse(tokenize(source, "<संवादः>"), "<संवादः>")
            interpreter._hoist(program.statements, interpreter.env)
            for stmt in program.statements:
                value = interpreter.execute(stmt)
                if isinstance(stmt, ExpressionStmt) and value is not None:
                    print(stringify(value, quote_strings=True))
        except VakThrow as thrown:
            print(Interpreter._to_error(thrown).render(source, "<संवादः>"), file=sys.stderr)
        except VakError as err:
            print(err.render(source, "<संवादः>"), file=sys.stderr)
        except RecursionError:
            print("अतिगभीरम् आवर्तनम् / recursion too deep", file=sys.stderr)
        except KeyboardInterrupt:
            print("\nविरामः / interrupted", file=sys.stderr)


def _with_deep_stack(work: "Callable[[], int]") -> int:
    """वाक्-आवर्तनम् गभीरम् भवितुम् अर्हति — a Vāk program may recurse far deeper than
    CPython's default limit allows, because every Vāk call costs several Python frames.
    The self-hosted analyser walking a long अन्यथा-यदि chain is the usual case.
    Run the program on a thread with a large stack so the depth is the language's, not
    the host's.
    """
    import threading

    result: list[int] = [70]

    def runner() -> None:
        sys.setrecursionlimit(60_000)
        result[0] = work()

    try:
        threading.stack_size(64 * 1024 * 1024)
    except (ValueError, RuntimeError):  # pragma: no cover - platform dependent
        return work()
    thread = threading.Thread(target=runner)
    thread.start()
    thread.join()
    return result[0]


def main(argv: list[str] | None = None) -> int:
    _configure_console()
    ap = argparse.ArgumentParser(
        prog="vak",
        description="वाक् — संस्कृतभाषायाः संगणकभाषा / Vāk, a Sanskrit programming language",
    )
    ap.add_argument("file", nargs="?", help="a .vak program to run (omit for the REPL)")
    ap.add_argument("args", nargs="*",
                    help="arguments passed to the program, readable with प्राचलाः()")
    ap.add_argument("--tokens", action="store_true", help="print the token stream and stop")
    ap.add_argument("--ast", action="store_true", help="print the syntax tree and stop")
    ap.add_argument("--check", action="store_true",
                    help="run the semantic analyser and stop, without executing")
    ap.add_argument("--no-check", action="store_true",
                    help="skip the semantic analyser and run the program directly")
    ap.add_argument("--vm", action="store_true",
                    help="compile to bytecode and run on the SanskritVM")
    ap.add_argument("--bytecode", "--vyakhya", action="store_true", dest="bytecode",
                    help="disassemble the compiled bytecode and stop")
    ap.add_argument("--self", "--svayam", action="store_true", dest="self_hosted",
                    help="compile with the Vāk-written toolchain, then run on the VM")
    ap.add_argument("--self-vm", "--svayam-yantram", action="store_true", dest="self_vm",
                    help="lex, parse, compile AND run entirely in Vāk")
    ap.add_argument("--native", "--deshiya", action="store_true", dest="native",
                    help="compile to a standalone native executable (needs gcc)")
    ap.add_argument("--run-native", action="store_true", dest="run_native",
                    help="compile natively and run the result")
    ap.add_argument("--builtins", action="store_true", help="list the built-in functions")
    ap.add_argument("--karakas", action="store_true", help="list the kāraka roles")
    ap.add_argument("--version", action="version", version=f"वाक् (Vāk) {__version__}")
    args = ap.parse_args(argv)

    from .builtins import ADESHA_PRACHALAH
    ADESHA_PRACHALAH[:] = args.args

    if args.builtins:
        list_builtins()
        return 0
    if args.karakas:
        list_karakas()
        return 0
    if args.file:
        return _with_deep_stack(
            lambda: run_file(Path(args.file), args.tokens, args.ast, args.check,
                             args.no_check, args.bytecode, args.vm, args.self_hosted,
                             args.self_vm, args.native, args.run_native))
    return repl()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
