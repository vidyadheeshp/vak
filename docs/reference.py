# -*- coding: utf-8 -*-
"""सन्दर्भः — the reference tables the manual could not previously reach.

Three things about Vāk live outside `vaak/tokens.py` and `vaak/builtins.py`, and
so were missing from the manual: the standard library (written in Vāk), the
analyser's diagnostics, and the command line.

Each is read from its real source here — the library through the actual parser,
the diagnostics and the flags out of the modules that define them — and paired
with an English gloss.  `check()` fails the build if the two ever disagree, so a
new library function or a new flag cannot be added without documenting it.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vaak.ast_nodes import FunctionDecl, VarDecl                  # noqa: E402
from vaak.lexer import Lexer                                      # noqa: E402
from vaak.parser import Parser                                    # noqa: E402

LIB_DIR = ROOT / "vaak" / "पुस्तकालयः"


# ------------------------------------------------------------- पुस्तकालयः
# The gloss for each name.  Signatures are never written here — they come from
# parsing the module — so these can only ever be wrong about meaning, not shape.
LIB_DOCS: dict[str, str] = {
    # गणितम्
    "पाई": "π, to fifteen places",
    "ई": "e, the base of the natural logarithm",
    "वर्गः": "क squared",
    "घनः": "क cubed",
    "निरपेक्षम्": "the absolute value of क",
    "चिह्नम्": "the sign of क — १, ०, or -१",
    "क्रमगुणितम्": "न् factorial",
    "मसाभा": "the greatest common divisor of अ and ब",
    "लसागु": "the least common multiple of अ and ब",
    "अभाज्यः_वा": "whether न् is prime",
    "अभाज्याः_यावत्": "every prime up to सीमा, as a list",
    "माध्यम्": "the arithmetic mean of the list",
    "मध्यमा": "the median of the list",
    "घातः": "आधारः raised to the power घाताङ्कः",
    "वर्गमूलम्": "the square root of क, by Newton's method",
    "बहुलकः": "the most frequent value; the smaller one when two tie",
    "विचरणम्": "the population variance — the mean squared deviation",
    "प्रमाणविचलनम्": "the population standard deviation",
    # शब्दाः
    "आदौ_अस्ति": "whether पूर्णः begins with आदिः",
    "अन्ते_अस्ति": "whether पूर्णः ends with अन्तः_",
    "पुनरावृत्तिः": "स repeated वारम् times",
    "पूरय": "स padded with अक्षरम् until it reaches दैर्घ्यम्",
    "अक्षरसूची": "स as a list of its characters",
    "विलोमः_वा": "whether स reads the same in both directions",
    "गणय_अक्षरम्": "how many times अक्षरम् occurs in वाक्यम्",
    "शब्दगणना": "a dictionary of each word in वाक्यम् and its count",
    "रिक्तम्_वा": "whether अ is a space, tab, newline or carriage return",
    "आदौ_छिन्द": "स with leading whitespace removed",
    "अन्ते_छिन्द": "स with trailing whitespace removed",
    "छिन्द": "स with whitespace removed from both ends",
    "प्रतिस्थापय": "वाक्यम् with every पुरातनम् replaced by नूतनम्",
}

MODULE_BLURB: dict[str, str] = {
    "गणितम्": "Mathematics — two constants and sixteen functions.",
    "शब्दाः": "Strings — thirteen functions over शब्दः.",
}


def library() -> list[tuple[str, str, list[tuple[str, str, str]]]]:
    """Every standard-library module as (name, blurb, entries), where each entry
    is (kind, signature, gloss).  The signature comes from the real parser, so
    it is exactly what the module declares."""
    out = []
    for path in sorted(LIB_DIR.glob("*.vak")):
        program = Parser(Lexer(path.read_text(encoding="utf-8")).tokenize()).parse()
        entries: list[tuple[str, str, str]] = []
        for stmt in program.statements:
            if isinstance(stmt, FunctionDecl):
                params = ", ".join(str(p) for p in stmt.params)
                sig = f"{stmt.name}({params}) : {stmt.return_type}"
                entries.append(("कार्यम्", sig, LIB_DOCS.get(stmt.name, "")))
            elif isinstance(stmt, VarDecl) and stmt.constant:
                entries.append(("ध्रुव", f"{stmt.type} {stmt.name}",
                                LIB_DOCS.get(stmt.name, "")))
        out.append((path.stem, MODULE_BLURB.get(path.stem, ""), entries))
    return out


def library_names() -> set[str]:
    names = set()
    for path in sorted(LIB_DIR.glob("*.vak")):
        program = Parser(Lexer(path.read_text(encoding="utf-8")).tokenize()).parse()
        for stmt in program.statements:
            if isinstance(stmt, FunctionDecl):
                names.add(stmt.name)
            elif isinstance(stmt, VarDecl) and stmt.constant:
                names.add(stmt.name)
    return names


# ------------------------------------------------------------------ दोषाः
# What each diagnostic means.  The codes themselves are scraped from the
# analyser, so this dict cannot silently fall behind it.
DIAGNOSTIC_DOCS: dict[str, tuple[str, str]] = {
    "नामदोषः": ("दोषः", "a name is used that was never declared"),
    "प्रकारदोषः": ("दोषः", "a value does not match the declared प्रकारः"),
    "ध्रुवदोषः": ("दोषः", "an assignment to a ध्रुव constant"),
    "प्रवाहदोषः": ("दोषः", "विरम or अनुवर्तस्व outside a loop"),
    "प्राचलदोषः": ("दोषः", "a call passes the wrong number of arguments"),
    "कारकदोषः": ("दोषः", "a kāraka role is repeated — Pāṇini allows one agent "
                          "and one patient"),
    "अगम्यदोषः": ("सूचना", "a statement after प्रत्यागच्छ that can never run"),
    "पुनर्घोषणा": ("सूचना", "a name declared twice in the same scope"),
    "कारकसूचना": ("सूचना", "some parameters carry kāraka roles and some do not"),
    "प्रतिफलसूचना": ("सूचना", "a function promises a return type but has a path "
                              "that returns nothing"),
    "प्रवाहसूचना": ("सूचना", "a विकल्पः with no अन्यथा — an unmatched value does "
                            "nothing"),
}


def diagnostic_codes() -> list[str]:
    """Every code the analyser can emit, read out of the analyser."""
    src = (ROOT / "vaak" / "analyzer.py").read_text(encoding="utf-8")
    return sorted(set(re.findall(r'_(?:error|warn)\(\s*"([^"]+)"', src)))


def diagnostics() -> list[tuple[str, str, str]]:
    """(code, दोषः or सूचना, what it means) — errors first, then warnings."""
    rows = [(c, *DIAGNOSTIC_DOCS.get(c, ("", ""))) for c in diagnostic_codes()]
    return sorted(rows, key=lambda r: (r[1] != "दोषः", r[0]))


def error_kinds() -> list[tuple[str, str]]:
    """The values a दोषे block can find in the error's प्रकारः, taken from the
    error classes themselves."""
    src = (ROOT / "vaak" / "errors.py").read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r'title = "([^"]+)"\s*\n\s*default_code = "([^"]+)"', src):
        title, code = m.group(1), m.group(2)
        english = re.search(r"\(([^)]+)\)", title)
        out.append((code, english.group(1) if english else title))
    return out


# ------------------------------------------------------------- आदेशपङ्क्तिः
FLAG_ORDER = [
    "--tokens", "--ast", "--check", "--no-check", "--vm", "--bytecode",
    "--self", "--self-vm", "--native", "--run-native", "--builtins",
    "--karakas", "--version",
]


def cli_flags() -> list[tuple[str, str, str]]:
    """(flag, Sanskrit alias, help) for every command-line option, read out of
    the argparse calls in vaak/cli.py."""
    src = (ROOT / "vaak" / "cli.py").read_text(encoding="utf-8")
    found: dict[str, tuple[str, str]] = {}
    for call in re.findall(r"ap\.add_argument\((.*?)\)\n", src, re.S):
        flags = [f for f in re.findall(r'"(--[a-z][\w-]*)"', call)]
        if not flags:
            continue
        helps = re.search(r'help="([^"]*)"', call, re.S)
        text = " ".join(helps.group(1).split()) if helps else ""
        if not text and "version" in call:
            text = "print the version and stop"
        found[flags[0]] = (flags[1] if len(flags) > 1 else "", text)
    order = {f: i for i, f in enumerate(FLAG_ORDER)}
    return [(f, *found[f]) for f in sorted(found, key=lambda f: order.get(f, 99))]


# ------------------------------------------------------------------ परीक्षा
def check() -> list[str]:
    """Fail the build rather than ship a reference that has drifted."""
    problems: list[str] = []

    names = library_names()
    for missing in sorted(names - set(LIB_DOCS)):
        problems.append(f"library {missing!r} has no gloss in LIB_DOCS")
    for orphan in sorted(set(LIB_DOCS) - names):
        problems.append(f"LIB_DOCS has {orphan!r}, which the library no longer defines")
    for stem in sorted(p.stem for p in LIB_DIR.glob("*.vak")):
        if stem not in MODULE_BLURB:
            problems.append(f"library module {stem!r} has no blurb")

    codes = set(diagnostic_codes())
    for missing in sorted(codes - set(DIAGNOSTIC_DOCS)):
        problems.append(f"analyser emits {missing!r}, which is undocumented")
    for orphan in sorted(set(DIAGNOSTIC_DOCS) - codes):
        problems.append(f"DIAGNOSTIC_DOCS has {orphan!r}, which the analyser never emits")

    flags = {f for f, _, _ in cli_flags()}
    for missing in sorted(flags - set(FLAG_ORDER)):
        problems.append(f"flag {missing} is not placed in FLAG_ORDER")
    for f, _, text in cli_flags():
        if not text:
            problems.append(f"flag {f} has no help text")

    return problems


if __name__ == "__main__":                                   # pragma: no cover
    bad = check()
    for line in bad:
        print("  !!", line)
    lib = library()
    print(f"library: {len(lib)} modules, {sum(len(e) for _, _, e in lib)} entries")
    print(f"diagnostics: {len(diagnostics())}   error kinds: {len(error_kinds())}")
    print(f"cli flags: {len(cli_flags())}")
    print("drift:", f"{len(bad)} problem(s)" if bad else "none")
