# -*- coding: utf-8 -*-
"""विस्तारकरचना — generate the VS Code extension for Vāk.

The grammar is not hand-written.  Keywords, type names and kāraka roles are
read out of vaak/tokens.py and vaak/builtins.py, so the highlighting cannot drift
away from the language the way a hand-maintained grammar always does.

    python vscode-vak/build_extension.py
"""
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(REPO))

from vaak import __version__                                    # noqa: E402
from vaak.builtins import BUILTIN_SIGNATURES                    # noqa: E402
from vaak.tokens import KARAKA_ORDER, KEYWORDS, TYPE_NAMES      # noqa: E402


def alt(words) -> str:
    """A regex alternation, longest first so प्रत्यागच्छ wins over प्रति."""
    return "|".join(sorted((w for w in words), key=len, reverse=True))


# Devanagari has no case, and \b does not do what you want, so word boundaries
# are built from "not an identifier character" on either side.
#
# The subtlety that bites: the danda ।(U+0964) and double danda ॥(U+0965) sit
# *inside* the Devanagari block.  Include the whole block here and `विरम।` —
# a keyword written hard against its terminator, which is how Vāk is normally
# written — stops matching.  So the block is taken in two halves, around them.
IDENT = r"\w\u0900-\u0963\u0966-\u097F"
EDGE_L = f"(?<![{IDENT}])"
EDGE_R = f"(?![{IDENT}])"

CONTROL = {"IF", "ELSE", "WHILE", "FOR", "IN", "REPEAT", "BREAK", "CONTINUE",
           "RETURN", "SWITCH", "CASE", "TRY", "CATCH", "FINALLY", "THROW"}
DECL = {"LET", "CONST", "FUNC"}
IMPORT = {"IMPORT", "AS", "FROM"}
CONSTANTS = {"TRUE", "FALSE", "NULL"}
OPERATOR_WORDS = {"AND", "OR", "NOT"}

by_kind: dict[str, list[str]] = {}
for word, kind in KEYWORDS.items():
    by_kind.setdefault(kind.name, []).append(word)


def words_for(kinds) -> list[str]:
    out = []
    for k in kinds:
        out += by_kind.get(k, [])
    return out


PRINT_WORDS = words_for({"PRINT"})
TYPES = sorted(TYPE_NAMES)
BUILTINS = sorted(BUILTIN_SIGNATURES)

grammar = {
    "$schema": "https://raw.githubusercontent.com/martinring/tmlanguage/master/tmlanguage.json",
    "name": "Vāk",
    "scopeName": "source.vak",
    "patterns": [{"include": "#comment"}, {"include": "#string"},
                 {"include": "#karaka"}, {"include": "#declaration"},
                 {"include": "#control"}, {"include": "#import"},
                 {"include": "#constant"}, {"include": "#operator-word"},
                 {"include": "#print"}, {"include": "#type"},
                 {"include": "#builtin"}, {"include": "#number"},
                 {"include": "#danda"}, {"include": "#function-call"},
                 {"include": "#operator"}],
    "repository": {
        "comment": {
            "name": "comment.line.number-sign.vak",
            "match": r"#.*$",
        },
        "string": {
            "name": "string.quoted.double.vak",
            "begin": '"', "end": '"',
            "patterns": [{"name": "constant.character.escape.vak",
                          "match": r"\\."}],
        },
        # कारकाणि — the roles a parameter may declare.  These are what makes
        # Vāk Vāk, so they get their own scope rather than sharing 'keyword'.
        "karaka": {
            "name": "entity.name.tag.karaka.vak",
            "match": EDGE_L + f"({alt(KARAKA_ORDER)})" + EDGE_R,
        },
        "declaration": {
            "name": "storage.type.vak",
            "match": EDGE_L + f"({alt(words_for(DECL))})" + EDGE_R,
        },
        "control": {
            "name": "keyword.control.vak",
            "match": EDGE_L + f"({alt(words_for(CONTROL))})" + EDGE_R,
        },
        "import": {
            "name": "keyword.control.import.vak",
            "match": EDGE_L + f"({alt(words_for(IMPORT))})" + EDGE_R,
        },
        "constant": {
            "name": "constant.language.vak",
            "match": EDGE_L + f"({alt(words_for(CONSTANTS))})" + EDGE_R,
        },
        "operator-word": {
            "name": "keyword.operator.word.vak",
            "match": EDGE_L + f"({alt(words_for(OPERATOR_WORDS))})" + EDGE_R,
        },
        "print": {
            "name": "keyword.other.print.vak",
            "match": EDGE_L + f"({alt(PRINT_WORDS)})" + EDGE_R,
        },
        "type": {
            "name": "support.type.vak",
            "match": EDGE_L + f"({alt(TYPES)})" + EDGE_R,
        },
        "builtin": {
            "name": "support.function.builtin.vak",
            "match": EDGE_L + f"({alt(BUILTINS)})" + EDGE_R + r"(?=\s*\()",
        },
        # both numeral systems are the same numbers
        "number": {
            "name": "constant.numeric.vak",
            "match": EDGE_L + r"[०-९0-9][०-९0-9._]*",
        },
        # दण्डः — the full stop Sanskrit has used since manuscripts
        "danda": {
            "name": "punctuation.terminator.danda.vak",
            "match": r"[।॥;]",
        },
        "function-call": {
            "name": "entity.name.function.vak",
            "match": f"[{IDENT}]+" + r"(?=\s*\()",
        },
        "operator": {
            "name": "keyword.operator.vak",
            "match": r"\+=|-=|\*=|/=|%=|\^=|==|!=|<=|>=|[+\-*/%^<>=]",
        },
    },
}

LANGUAGE_CONFIG = {
    "comments": {"lineComment": "#"},
    "brackets": [["{", "}"], ["[", "]"], ["(", ")"]],
    "autoClosingPairs": [
        {"open": "{", "close": "}"}, {"open": "[", "close": "]"},
        {"open": "(", "close": ")"},
        {"open": '"', "close": '"', "notIn": ["string", "comment"]},
    ],
    "surroundingPairs": [["{", "}"], ["[", "]"], ["(", ")"], ['"', '"']],
    "indentationRules": {
        "increaseIndentPattern": r"\{[^}\"']*$",
        "decreaseIndentPattern": r"^\s*\}",
    },
    "wordPattern": f"[{IDENT}]+",
}

PACKAGE = {
    "name": "vak",
    "displayName": "वाक् · Vāk",
    "description": "Language support for Vāk — a Sanskrit-native programming "
                   "language whose type system is Pāṇini's kāraka grammar.",
    "version": __version__,
    "publisher": "vidyadheeshp",
    "license": "MIT",
    "icon": "images/icon-128.png",
    "engines": {"vscode": "^1.75.0"},
    "categories": ["Programming Languages", "Linters"],
    "keywords": ["vak", "sanskrit", "devanagari", "panini", "संस्कृतम्"],
    "activationEvents": ["onLanguage:vak"],
    "main": "./extension.js",
    "contributes": {
        "languages": [{
            "id": "vak",
            "aliases": ["Vāk", "वाक्", "vak"],
            "extensions": [".vak"],
            "configuration": "./language-configuration.json",
            # this is what puts the वा on a .vak file in the explorer
            "icon": {"light": "./icons/vak-file-light.svg",
                     "dark": "./icons/vak-file-dark.svg"},
        }],
        "grammars": [{
            "language": "vak",
            "scopeName": "source.vak",
            "path": "./syntaxes/vak.tmLanguage.json",
        }],
        "commands": [
            {"command": "vak.run", "title": "Vāk: चालय · Run File",
             "icon": "$(play)"},
            {"command": "vak.check", "title": "Vāk: परीक्षा · Analyse File",
             "icon": "$(checklist)"},
            {"command": "vak.transliterate",
             "title": "Vāk: देवनागरी · Convert typed text to Devanagari"},
            {"command": "vak.toggleTyping",
             "title": "Vāk: देवनागरी-लेखनम् · Toggle Devanagari typing"},
        ],
        "menus": {
            "editor/title/run": [
                {"command": "vak.run", "when": "resourceLangId == vak",
                 "group": "navigation@1"},
            ],
        },
        "keybindings": [
            {"command": "vak.run", "key": "ctrl+alt+r", "mac": "cmd+alt+r",
             "when": "resourceLangId == vak"},
            {"command": "vak.transliterate", "key": "ctrl+alt+d",
             "mac": "cmd+alt+d", "when": "resourceLangId == vak"},
            {"command": "vak.toggleTyping", "key": "ctrl+alt+t",
             "mac": "cmd+alt+t", "when": "resourceLangId == vak"},
        ],
        "configuration": {
            "title": "Vāk",
            "properties": {
                "vak.executable": {
                    "type": "string", "default": "",
                    "markdownDescription":
                        "Path to `वाक्.exe`. Leave empty to use "
                        "`#vak.pythonPath#` with `-m vak` instead.",
                },
                "vak.pythonPath": {
                    "type": "string", "default": "python",
                    "description":
                        "Python used to run the toolchain when no executable "
                        "is configured.",
                },
                "vak.devanagariTyping": {
                    "type": "boolean", "default": False,
                    "markdownDescription":
                        "Convert romanised words to Devanagari as you type. "
                        "`naama` becomes `नाम` when you finish the word. Toggle "
                        "with `Ctrl+Alt+T`.",
                },
                "vak.checkOnSave": {
                    "type": "boolean", "default": True,
                    "description":
                        "Run the semantic analyser on save and show its "
                        "diagnostics in the editor.",
                },
            },
        },
    },
}

EXTENSION_JS = r'''"use strict";
// वाक् — VS Code support.
//
// The analyser already exists and already reports code, line and message, so
// this file does not re-implement any of it: it runs the real toolchain and
// turns what it prints into editor diagnostics.
const vscode = require("vscode");
const cp = require("child_process");
const path = require("path");
const { devanagari } = require("./translit");

let diagnostics;
let statusBar;
let typing = false;      // देवनागरी-लेखनम् — convert romanised words as they finish

/** How to invoke Vāk: the native binary if configured, else `python -m vaak`. */
function toolchain(args) {
  const cfg = vscode.workspace.getConfiguration("vak");
  const exe = (cfg.get("executable") || "").trim();
  if (exe) return { cmd: exe, args };
  return { cmd: cfg.get("pythonPath") || "python", args: ["-m", "vaak", ...args] };
}

/*  अर्थदोषः lines look like:
 *    दोषः [नामदोषः] path/to/file.vak:7 — अपरिभाषितम् नाम 'x' / undefined name 'x'
 *  and a सूचना is advice rather than an error.                                */
const LINE = /^\s*(दोषः|सूचना)\s+\[([^\]]+)\]\s+.*?:(\d+)\s+—\s+(.*)$/;

function parse(output, document) {
  const found = [];
  for (const raw of output.split(/\r?\n/)) {
    const m = LINE.exec(raw);
    if (!m) continue;
    const [, kind, code, lineNo, message] = m;
    const index = Math.max(0, parseInt(lineNo, 10) - 1);
    const textLine = index < document.lineCount ? document.lineAt(index) : null;
    const range = textLine
      ? new vscode.Range(index, textLine.firstNonWhitespaceCharacterIndex,
                         index, textLine.range.end.character)
      : new vscode.Range(index, 0, index, 1);
    const severity = kind === "दोषः"
      ? vscode.DiagnosticSeverity.Error
      : vscode.DiagnosticSeverity.Warning;
    const d = new vscode.Diagnostic(range, message, severity);
    d.source = "वाक्";
    d.code = code;
    found.push(d);
  }
  return found;
}

function check(document) {
  if (document.languageId !== "vak") return;
  if (!vscode.workspace.getConfiguration("vak").get("checkOnSave")) return;

  const { cmd, args } = toolchain(["--check", document.fileName]);
  cp.execFile(cmd, args, { cwd: path.dirname(document.fileName),
                           env: { ...process.env, PYTHONIOENCODING: "utf-8" } },
    (err, stdout, stderr) => {
      const text = `${stdout || ""}\n${stderr || ""}`;
      if (err && !text.trim()) {
        // the toolchain itself could not be started — say so once, quietly
        diagnostics.set(document.uri, []);
        return;
      }
      diagnostics.set(document.uri, parse(text, document));
    });
}

function run(document) {
  const terminal =
    vscode.window.terminals.find((t) => t.name === "वाक्") ||
    vscode.window.createTerminal("वाक्");
  const { cmd, args } = toolchain([document.fileName]);
  terminal.show(true);
  terminal.sendText([cmd, ...args].map(quote).join(" "));
}

function quote(s) {
  return /[\s"]/.test(s) ? `"${s.replace(/"/g, '\\"')}"` : s;
}

/* ------------------------------------------------------- लिप्यन्तरणम्
 * Vāk never transliterates identifiers — `नाम` and `naam` are two different
 * names, deliberately.  This converts what you *type*, so you end up writing
 * one consistent spelling instead of two that look alike.
 */
const ROMAN_WORD = /[A-Za-z~^.]+$/;

/** Convert the selection, or the word the cursor is in. */
function transliterateSelection(editor) {
  editor.edit((edit) => {
    for (const sel of editor.selections) {
      let range = sel;
      if (sel.isEmpty) {
        const found = editor.document.getWordRangeAtPosition(sel.active, /[A-Za-z~^.]+/);
        if (!found) continue;
        range = found;
      }
      const text = editor.document.getText(range);
      const out = devanagari(text, true);
      if (out !== text) edit.replace(range, out);
    }
  });
}

/** Live mode: when a word is finished, convert the word just typed. */
function onType(event) {
  if (!typing) return;
  const editor = vscode.window.activeTextEditor;
  if (!editor || event.document !== editor.document) return;
  if (event.document.languageId !== "vak") return;
  if (event.contentChanges.length !== 1) return;

  const change = event.contentChanges[0];
  // only react to a single character that ends a word
  if (change.text.length !== 1 || /[A-Za-z~^.]/.test(change.text)) return;

  const pos = change.range.start;
  const before = event.document.getText(
    new vscode.Range(new vscode.Position(pos.line, 0), pos));
  const m = ROMAN_WORD.exec(before);
  if (!m) return;

  const word = m[0];
  const out = devanagari(word, true);
  if (out === word) return;
  const range = new vscode.Range(
    new vscode.Position(pos.line, pos.character - word.length), pos);
  editor.edit((edit) => edit.replace(range, out),
              { undoStopBefore: false, undoStopAfter: false });
}

function showStatus() {
  if (!statusBar) return;
  statusBar.text = typing ? "$(check) देवनागरी" : "देवनागरी";
  statusBar.tooltip = typing
    ? "Devanagari typing is on — romanised words convert as you finish them. Ctrl+Alt+T"
    : "Devanagari typing is off. Ctrl+Alt+T to turn it on";
  const editor = vscode.window.activeTextEditor;
  if (editor && editor.document.languageId === "vak") statusBar.show();
  else statusBar.hide();
}

function activate(context) {
  diagnostics = vscode.languages.createDiagnosticCollection("vak");
  context.subscriptions.push(diagnostics);

  typing = vscode.workspace.getConfiguration("vak").get("devanagariTyping") || false;
  statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBar.command = "vak.toggleTyping";
  context.subscriptions.push(statusBar);
  showStatus();

  context.subscriptions.push(
    vscode.commands.registerCommand("vak.transliterate", () => {
      const ed = vscode.window.activeTextEditor;
      if (ed) transliterateSelection(ed);
    }),
    vscode.commands.registerCommand("vak.toggleTyping", () => {
      typing = !typing;
      showStatus();
      vscode.window.setStatusBarMessage(
        typing ? "देवनागरी-लेखनम् आरब्धम् / Devanagari typing on"
               : "देवनागरी-लेखनम् स्थगितम् / Devanagari typing off", 2000);
    }),
    vscode.workspace.onDidChangeTextDocument(onType),
    vscode.window.onDidChangeActiveTextEditor(showStatus)
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("vak.run", () => {
      const ed = vscode.window.activeTextEditor;
      if (ed) ed.document.save().then(() => run(ed.document));
    }),
    vscode.commands.registerCommand("vak.check", () => {
      const ed = vscode.window.activeTextEditor;
      if (ed) ed.document.save().then(() => check(ed.document));
    }),
    vscode.workspace.onDidSaveTextDocument(check),
    vscode.workspace.onDidOpenTextDocument(check),
    vscode.workspace.onDidCloseTextDocument((d) => diagnostics.delete(d.uri))
  );
  vscode.workspace.textDocuments.forEach(check);
}

function deactivate() {
  if (diagnostics) diagnostics.dispose();
  if (statusBar) statusBar.dispose();
}

module.exports = { activate, deactivate };
'''

README = f"""# वाक् · Vāk for VS Code

Language support for [Vāk](https://github.com/vidyadheeshp/vak) — a
Sanskrit-native programming language whose type system is Pāṇini's kāraka
grammar.

## What it does

- **Syntax highlighting** for both spellings of every keyword — Devanagari and
  ASCII — and for both numeral systems. The kāraka roles (`कर्ता`, `कर्म`,
  `करणम्`, `सम्प्रदानम्`, `अपादानम्`, `अधिकरणम्`) get a scope of their own,
  because they are the part of the language that exists nowhere else.
- **A file icon**: `.vak` files show वा in the explorer.
- **Live diagnostics** from the real semantic analyser — undefined names, type
  mismatches, kāraka violations, unreachable code — shown as you save.
- **Run the current file** with `Ctrl+Alt+R`, or the ▷ button.
- **Devanagari typing.** Vāk never transliterates identifiers — `नाम` and
  `naam` are two different names, deliberately — so the help belongs where you
  type. `Ctrl+Alt+T` turns on live conversion: finish a word and `naama`
  becomes `नाम`. `Ctrl+Alt+D` converts a selection on demand.

  The scheme is ITRANS-flavoured: `aa`/`A` for आ, `T D N S` for the retroflex
  series, `~N`/`~n` for ङ/ञ, `H` for ः, `M` for ं. So `kaaryam` → `कार्यम्`
  and `puurNaa~NkaH` → `पूर्णाङ्कः`.

## Setup

The extension needs the Vāk toolchain. Either:

- set **`vak.executable`** to your `वाक्.exe`, or
- leave it empty and set **`vak.pythonPath`** (default `python`), and the
  extension will use `python -m vaak`.

## Settings

| setting | default | |
|---|---|---|
| `vak.executable` | `""` | path to `वाक्.exe` |
| `vak.pythonPath` | `python` | Python used when no executable is set |
| `vak.checkOnSave` | `true` | run the analyser on save |

## Note on fonts

No monospace coding font ships Devanagari, so VS Code falls back to a
proportional face and columns drift. Setting a fallback chain fixes the
rendering:

```json
"editor.fontFamily": "Cascadia Mono, Nirmala UI, monospace"
```

Nothing makes Devanagari truly monospaced, but this makes it render correctly.

---

Version {__version__}. The grammar in this extension is generated from the
language's own keyword tables by `build_extension.py`, so it cannot drift.
"""

VSCODEIGNORE = """build_extension.py
.vscode/**
**/*.map
"""



# ------------------------------------------------------- लिप्यन्तरणम् in JS
# The typing aid runs in the editor, so it has to exist in JavaScript — but the
# tables are the ones in vaak/translit.py, emitted here, so the scheme a student
# types with is the scheme the documentation describes.
from vaak.translit import tables_for_js                        # noqa: E402


def translit_js() -> str:
    t = tables_for_js()
    combined = (
        [[k, "C", v] for k, v in t["consonants"].items()]
        + [[k, "V", v[0], v[1]] for k, v in t["vowels"].items()]
        + [[k, "M", v] for k, v in t["marks"].items()]
    )
    combined.sort(key=lambda e: len(e[0]), reverse=True)
    return (
        '"use strict";\n'
        "// स्वयं जनितम् — generated from vaak/translit.py; do not edit.\n"
        "// Longest key first, across every table at once: matching per-table\n"
        "// would let `~` beat `~N`, turning अङ्क into अँण्क.\n"
        "const TABLE = " + json.dumps(combined, ensure_ascii=False) + ";\n"
        "const DIGITS = " + json.dumps(t["digits"], ensure_ascii=False) + ";\n"
        "const VIRAMA = " + json.dumps(t["virama"], ensure_ascii=False) + ";\n"
        # `mana` transliterates to मन, but the keyword is मान: converting the
        # language's own words phonetically turns valid ASCII Vāk into
        # Devanagari that does not compile, so they are looked up, not guessed.
        "const KEYWORDS = " + json.dumps(t["keywords"], ensure_ascii=False) + ";\n"
        + r"""
function devanagari(text, digits) {
  let out = "", i = 0, pending = false;
  outer:
  while (i < text.length) {
    for (const entry of TABLE) {
      const key = entry[0];
      if (!text.startsWith(key, i)) continue;
      const kind = entry[1];
      if (kind === "C") {
        if (pending) out += VIRAMA;
        out += entry[2];
        pending = true;
      } else if (kind === "V") {
        out += pending ? entry[3] : entry[2];
        pending = false;
      } else {
        out += out.length ? entry[2] : key;
        pending = false;
      }
      i += key.length;
      continue outer;
    }
    if (pending) { out += VIRAMA; pending = false; }
    const ch = text[i];
    out += (digits && DIGITS[ch]) ? DIGITS[ch] : ch;
    i += 1;
  }
  if (pending) out += VIRAMA;
  return out;
}

function convert(word, digits) {
  return KEYWORDS[word] || devanagari(word, digits);
}

module.exports = { devanagari, convert };
"""
    )


# --------------------------------------------------------------------- checks
# A grammar that silently stops matching is worse than none, and Devanagari
# word boundaries are exactly where that happens.  These run on every build.
CHECKS = [
    ("control", "विरम।", "विरम"),
    ("control", "अनुवर्त॥", "अनुवर्त"),
    ("control", "प्रत्यागच्छ फलम्।", "प्रत्यागच्छ"),   # not प्रति inside it
    ("control", "यदि (क > ५)", "यदि"),
    ("print", "मुद्रय क।", "मुद्रय"),
    ("print", "mudraya k;", "mudraya"),
    ("karaka", "कार्यम् छानय(अपादानम् सूची स)", "अपादानम्"),
    ("type", "पूर्णाङ्कः क = ५।", "पूर्णाङ्कः"),
    ("declaration", "मान क = १।", "मान"),
    ("constant", "प्रत्यागच्छ सत्य।", "सत्य"),
    ("number", "मान क = २०२६।", "२०२६"),
    ("number", "mana k = 2026;", "2026"),
    ("danda", "मुद्रय क।", "।"),
    ("builtin", "दीर्घता(अ)", "दीर्घता"),
    ("operator", "क += १।", "+="),
]


def verify() -> int:
    import re
    bad = 0
    for rule, source, expected in CHECKS:
        m = re.search(grammar["repository"][rule]["match"], source)
        got = m.group(0) if m else None
        if got != expected:
            bad += 1
            print(f"  GRAMMAR FAIL [{rule}] {source!r}: "
                  f"expected {expected!r}, got {got!r}")
    return bad

def main() -> None:
    failures = verify()
    if failures:
        raise SystemExit(f"{failures} grammar check(s) failed — nothing written")

    (ROOT / "syntaxes").mkdir(exist_ok=True)
    (ROOT / "icons").mkdir(exist_ok=True)
    (ROOT / "images").mkdir(exist_ok=True)

    (ROOT / "syntaxes" / "vak.tmLanguage.json").write_text(
        json.dumps(grammar, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "language-configuration.json").write_text(
        json.dumps(LANGUAGE_CONFIG, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "package.json").write_text(
        json.dumps(PACKAGE, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "extension.js").write_text(EXTENSION_JS, encoding="utf-8")
    (ROOT / "translit.js").write_text(translit_js(), encoding="utf-8")
    (ROOT / "README.md").write_text(README, encoding="utf-8")
    (ROOT / ".vscodeignore").write_text(VSCODEIGNORE, encoding="utf-8")

    for src, dst in [("vak-file-light.svg", "icons/vak-file-light.svg"),
                     ("vak-file-dark.svg", "icons/vak-file-dark.svg"),
                     ("icon-128.png", "images/icon-128.png")]:
        shutil.copy(REPO / "brand" / src, ROOT / dst)

    print(f"vscode-vak/ built for Vāk {__version__}")
    print(f"  grammar checks       : {len(CHECKS)} passed")
    print(f"  transliteration keys : {len(tables_for_js()['consonants'])} consonants, "
          f"{len(tables_for_js()['vowels'])} vowels")
    print(f"  keywords highlighted : {len(KEYWORDS)}")
    print(f"  built-ins highlighted: {len(BUILTINS)}")
    print(f"  kāraka roles         : {', '.join(KARAKA_ORDER)}")


if __name__ == "__main__":
    main()
