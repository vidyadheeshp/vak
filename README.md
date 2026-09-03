# वाक् · Vāk

**A programming language whose type system is Pāṇini's grammar, and whose own compiler is
written in itself.**

Sanskrit does not decide meaning by word order. It marks the **role** each participant
plays in an action — the agent, the patient, the instrument, the source — and lets the
words fall where they like. Vāk makes those roles part of a function's type:

```sanskrit
कार्यम् छानय(अपादानम् सूची संग्रहः, करणम् कार्यम् परीक्षा) : सूची { ... }
#            ↑ the source drawn from   ↑ the instrument drawn by
```

The analyser enforces Pāṇini's rule that an action takes at most one agent and one
patient. And because each argument carries its own role, **the order stops mattering** —
the same liberty a Sanskrit sentence gets from its case endings, moved into a type system.
[More on kāraka roles →](#कारकाणि--kāraka-roles)

Vāk's own front end — lexer, parser, semantic analyser, compiler and virtual machine — is
**written in Vāk**, 4,178 lines of it. Python builds that toolchain once, the way a C
compiler is used once to build a self-hosting C compiler, and after that Python is not in
the loop. [More on the bootstrap →](#स्वयंसिद्धिः--the-bootstrap)

Underneath, this is a real language rather than a demonstration: optional declared types,
lexical scope, first-class functions with closures, lists and dictionaries, exceptions,
modules and file I/O. Keywords, types, built-in functions, error names and numerals are
Sanskrit — not English with a Devanagari skin. Commands are imperative verbs (`मुद्रय`
"print!", `उत्सृज` "cast forth!"), the catch clause is in the locative case (`दोषे` "in
case of a fault"), and statements end with a danda `।`.

```sanskrit
कार्यम् अभिवादनम्(शब्दः नाम) : शब्दः {
    प्रत्यागच्छ "नमस्ते " + नाम + "!"।
}

सूची जनाः = ["मैत्रेयी", "गार्गी", "आर्यभटः"]।
प्रत्येकम् (जनः अन्तः जनाः) {
    मुद्रय अभिवादनम्(जनः)।
}
```

```
नमस्ते मैत्रेयी!
नमस्ते गार्गी!
नमस्ते आर्यभटः!
```

It runs **five ways** — a tree-walking interpreter, a bytecode VM in Python, that same VM
written in Vāk, a runtime in C, and a **native back end that compiles a program to a
standalone executable** needing no Python and no toolchain to run. All five are held to
byte-identical output by a differential test suite, which is the main reason any of this
can be trusted.

And none of it requires a Devanagari keyboard: every keyword has an ASCII spelling, ASCII
numerals work everywhere, and the [browser playground](https://vidyadheeshp.github.io/vak/playground.html)
turns romanised typing into Devanagari as you write.

---

> **The site** — four self-contained pages in [docs/](docs/), each generated,
> each with no external requests:
>
> | page | what it is | built by |
> |---|---|---|
> | [index.html](docs/index.html) | the landing page — every program on it is run while the page is built | `docs/build_landing.py` |
> | [manual.html](docs/manual.html) | the whole language in 17 sections — syntax, the standard library, every diagnostic, every flag | `docs/build_manual.py` |
> | [playground.html](docs/playground.html) | the toolchain in WebAssembly — runs Vāk in the browser | `docs/build_playground.py` |
> | [story.html](docs/story.html) | कथा — how the language was built, with every figure read from the repository | `docs/build_story.py` |
>
> Serve them with GitHub Pages (Settings → Pages → Deploy from branch → `/docs`).

## विषयसूची · Contents

- [स्थापना · Installing](#स्थापना--installing)
- [चालनम् · Running Vāk](#चालनम्--running-vāk)
- [भाषापरिचयः · A tour of the language](#भाषापरिचयः--a-tour-of-the-language)
- [प्रकाराः · Types](#प्रकाराः--types)
- [कारकाणि · Kāraka roles](#कारकाणि--kāraka-roles)
- [अर्थविश्लेषकः · The semantic analyser](#अर्थविश्लेषकः--the-semantic-analyser)
- [दोषनिग्रहः · Exception handling](#दोषनिग्रहः--exception-handling)
- [आनय · Modules](#आनय--modules)
- [सञ्चिकाः · Files](#सञ्चिकाः--files)
- [अक्षराणि · Syllables](#अक्षराणि--syllables)
- [संस्कृतयन्त्रम् · The SanskritVM](#संस्कृतयन्त्रम्--the-sanskritvm)
- [देशीयसंकलनम् · The native back end](#देशीयसंकलनम्--the-native-back-end)
- [स्वयंसिद्धिः · The bootstrap](#स्वयंसिद्धिः--the-bootstrap)
- [पदकोशः · Keyword reference](#पदकोशः--keyword-reference)
- [अन्तर्निहितानि · Built-in functions](#अन्तर्निहितानि--built-in-functions)
- [व्याकरणम् · Grammar](#व्याकरणम्--grammar)
- [रचना · How the implementation works](#रचना--how-the-implementation-works)
- [उदाहरणानि · Sample programs](#उदाहरणानि--sample-programs)
- [परीक्षाः · Tests](#परीक्षाः--tests)
- [अग्रिमम् · Roadmap](#अग्रिमम्--roadmap)

---

## स्थापना · Installing

Four ways in. They run the same language; pick whichever suits you.

**1 · The standalone binary — nothing else required.** `वाक्.exe` in this
repository is the whole toolchain compiled to one file. It needs no Python.
Copy it anywhere and run it:

```powershell
वाक्.exe प्रोग्राम.vak
```

The binary here is built for **64-bit Windows**. On Linux or macOS, build your
own — see [Building the binary](#building-the-binary). The C sources are
platform-neutral.

**2 · With pip, from GitHub.** Requires **Python 3.10+** and pulls in **no
third-party packages**.

```powershell
pip install git+https://github.com/vidyadheeshp/vak.git
vaak प्रोग्राम.vak
```

> Vāk is not on PyPI yet, so `pip install vak-lang` will not find it. Install
> from the repository as above; the `vak` command works the same either way.

This gives you the interpreter, the bytecode VM, the native back end, the REPL
and the standard library, and the `vak` command works from any directory.

**3 · From a clone,** if you want the parts a wheel does not carry — the C
runtime, the Vāk-written toolchain behind `--self`, the documentation
generators and the editor extension:

```powershell
git clone https://github.com/vidyadheeshp/vak.git
cd vak
python -m vaak examples/01_namaste.vak
```

> **Working from a clone, stay in the repository root.** `python -m vaak`
> finds the package only because you are standing in the directory that
> contains it; from anywhere else you get `No module named vak`. Installing
> with pip avoids this entirely. To run from elsewhere without installing, put
> the root on the module path:
>
> ```bash
> PYTHONPATH=/path/to/vak python -m vaak ~/प्रोग्राम.vak          # bash / zsh
> ```
> ```powershell
> $env:PYTHONPATH = "C:\path\to\vak"; python -m vaak प्रोग्राम.vak  # PowerShell
> ```

On Windows the two launchers do this and set UTF-8 for you:

```powershell
.\vaak.ps1 examples/01_namaste.vak     # PowerShell
vaak.cmd examples/01_namaste.vak       # cmd.exe
```

**4 · In a browser — nothing installed at all.** The
[playground](docs/playground.html) is this toolchain compiled to WebAssembly.
It runs in the page; there is no server and nothing you type leaves your
machine.

### Checking that it works

```powershell
python -m vaak --version          # वाक् (Vāk) 0.11.0
python -m vaak --builtins         # the 39 built-in functions
python -m vaak                    # संवादः — the interactive session
```

Then one line in `परीक्षा.vak`. If you see the greeting, you are set:

```
मुद्रय "नमस्ते जगत्"।
```

### A terminal that can show Devanagari

Two separate things must be right: the console must be in UTF-8, and the font
must contain Devanagari.

- **Windows.** The CLI reconfigures its own output, so Devanagari normally
  works in Windows Terminal. Boxes mean the *font* is wrong, not the encoding —
  choose *Nirmala UI* or *Noto Sans Devanagari*. The older `conhost` console may
  also need `chcp 65001`.
- **Linux and macOS.** A UTF-8 locale is the default almost everywhere;
  `locale` confirms it. Most terminal fonts fall back to a system Devanagari
  face automatically.

You do not have to type Devanagari at all — every keyword has an ASCII spelling
and ASCII numerals work everywhere, so a complete Vāk program fits on a plain
keyboard.

### Building the binary

The native back end turns a program into C and hands it to **gcc**, so a C
compiler is the only extra requirement. On Windows,
[w64devkit](https://github.com/skeeto/w64devkit) is what Vāk looks for by
default; on Linux and macOS the system compiler is already there.

```powershell
python -m vaak --native प्रोग्राम.vak       # produce an executable
python -m vaak --run-native प्रोग्राम.vak   # build it and run it
```

If no compiler is found, Vāk says so rather than failing obscurely.

### The editor extension

Copy `vscode-vak/` into your VS Code extensions directory and reload the
window:

```
%USERPROFILE%\.vscode\extensions\vscode-vak      # Windows
~/.vscode/extensions/vscode-vak                  # macOS and Linux
```

Then point it at whichever toolchain you installed: set `vak.executable` to
your `वाक्.exe`, or leave it empty and set `vak.pythonPath` so it uses
`python -m vaak`. You get highlighting, the `.vak` file icon, romanised typing
that becomes Devanagari, and the analyser's diagnostics on save.

---

## चालनम् · Running Vāk

Once it is installed — see [स्थापना](#स्थापना--installing) — everything below runs from the repository root.

```powershell
# run a program
python -m vaak examples/01_namaste.vak

# or use the launcher (it sets UTF-8 for you)
.\vaak.ps1 examples/01_namaste.vak      # PowerShell
vaak.cmd examples/01_namaste.vak        # cmd.exe

# interactive session (संवादः)
python -m vaak

# see what the front end is doing
python -m vaak --tokens examples/01_namaste.vak    # token stream
python -m vaak --ast    examples/03_yadi.vak       # syntax tree
python -m vaak --builtins                          # standard library listing
```

Embedding it in Python:

```python
from vaak import run_source
run_source('मुद्रय "नमस्ते जगत्"।')
```

> **Windows console note.** Devanagari needs a UTF-8 terminal. The CLI reconfigures
> `stdout` automatically; if your fonts render boxes, use Windows Terminal with a font
> such as *Nirmala UI* or *Noto Sans Devanagari*.

### The REPL

```
वाक् (Vāk) 0.11.0 — संस्कृतभाषायाः संगणकभाषा
सहायता: :सहायता   निर्गमः: :निर्गम  (help / exit)
वाक्> पूर्णाङ्कः क = ७।
वाक्> क * क
49
वाक्> कार्यम् द्विगुणम्(x) {
  ...     प्रत्यागच्छ x * २।
  ... }
वाक्> द्विगुणम्(२१)
42
```

REPL commands: `:सहायता` (`:help`), `:चिह्नानि` (`:tokens`), `:निर्गम` (`:exit`).

---

## भाषापरिचयः · A tour of the language

### Statements and the danda

A statement ends with a **danda `।`**, a double danda `॥`, or an ASCII `;` — and the
terminator is optional at the end of a line. Blocks use `{ }`.

```sanskrit
मुद्रय "अ"।      # danda
मुद्रय "आ"॥      # double danda
मुद्रय "इ";      # semicolon
मुद्रय "ई"       # nothing at all — also fine
```

Comments: `# ...`, `// ...` to end of line, and `/* ... */` for blocks.

### मुद्रय · Printing

`मुद्रय` is an imperative command, so it needs no parentheses — though it accepts them:

```sanskrit
मुद्रय "नाम:", नाम, वयः।       # command form
मुद्रय("नाम:", नाम, वयः)।      # call form — identical
मुद्रय (अ + ब) * २।            # the parenthesis is just an expression here
```

`लिख` is the same thing as an ordinary **function value**, for when you need to pass
printing around: `प्रयोगः(लिख, सूची)`.

### चराः · Variables and constants

```sanskrit
मान नाम = "वाक्"।              # māna  — a variable
ध्रुव पाई = ३.१४१५९।            # dhruva — a constant; reassigning it is an error
पूर्णाङ्कः वयः = ३०।            # a declared type (see below)
```

Names may be written in Devanagari (with matras, virama and conjuncts), in Latin, or
mixed: `छात्रसंख्या`, `total`, `योग_1` are all valid identifiers.

### अङ्काः · Numerals

Devanagari and ASCII digits are the *same numbers* — `१०० + 100` is `200`. Output uses
ASCII digits by default; `देवनागरी(x)` renders a value with Devanagari digits.

### निर्णयाः · Conditionals

```sanskrit
यदि (अङ्कः >= ९०) {
    मुद्रय "उत्तमम्"।
} अन्यथा यदि (अङ्कः >= ५०) {
    मुद्रय "सामान्यम्"।
} अन्यथा {
    मुद्रय "पुनः प्रयत्नः"।
}
```

**Truthiness:** `शून्य`, `असत्य`, `०`, `""`, `[]` and `{}` are false; everything else is true.

### पाशाः · Loops — three of them

```sanskrit
यावत् (क > ०) {                     # while — "as long as"
    क = क - १।
}

आवृत्तिः (५) {                       # repeat exactly five times
    मुद्रय "ॐ"।
}

प्रत्येकम् (ग्रहः अन्तः ग्रहाः) {      # for-each: over a सूची, शब्दः or कोशः
    मुद्रय ग्रहः।
}

प्रत्येकम् (क अन्तः परास(१, ६)) {     # over a numeric range
    यदि (क == ३) { अनुवर्त। }        # continue
    यदि (क == ५) { विरम। }           # break
}
```

Iterating a `कोशः` yields its keys. Parentheses around a loop or condition header are
optional everywhere.

### विकल्पः · Choosing among alternatives

`विकल्पः` is Pāṇini's word for an optional alternative in a rule; `पक्षे` is the
locative, "in this case" — the same case ending `दोषे` uses for catch.

```
कार्यम् वासरनाम(कर्म पूर्णाङ्कः वारः) : शब्दः {
    विकल्पः (वारः) {
        पक्षे १: प्रत्यागच्छ "सोमवासरः"।
        पक्षे २, ३: प्रत्यागच्छ "मङ्गलः बुधः वा"।
        पक्षे ६, ७: प्रत्यागच्छ "सप्ताहान्तः"।
        अन्यथा: प्रत्यागच्छ "अज्ञातः"।
    }
}
```

One `पक्षे` may carry several values. `अन्यथा` is the fallback wherever it is
written, and the subject is evaluated once.

**पक्षाः do not fall through** — the alternative that matches is the only one
that runs. Nothing has to be written to stop it, which leaves `विरम` its
ordinary meaning: inside a विकल्पः it breaks the *enclosing loop*.

The analyser reports a पक्षः that could never match the subject's type, and a
value given twice. A विकल्पः with an `अन्यथा` whose every पक्षः returns counts as
returning on every path.

### कार्याणि · Functions

Functions are values: they can be stored, passed, returned, and they close over the scope
in which they were written. Every `कार्यम्` in a block is **hoisted**, so it may be called
before the line that defines it.

```sanskrit
मुद्रय क्रमगुणितम्(१०)।              # legal — the function below is already known

कार्यम् क्रमगुणितम्(पूर्णाङ्कः न्यूनम्) : पूर्णाङ्कः {
    यदि (न्यूनम् <= १) { प्रत्यागच्छ १। }
    प्रत्यागच्छ न्यूनम् * क्रमगुणितम्(न्यूनम् - १)।
}

मान द्विगुणम् = कार्यम्(क) { प्रत्यागच्छ क * २। }।     # anonymous कार्यम्

कार्यम् गणकनिर्माता(आरम्भः) {                         # closure
    मान संख्या_ = आरम्भः।
    प्रत्यागच्छ कार्यम्() { संख्या_ = संख्या_ + १। प्रत्यागच्छ संख्या_। }।
}
```

A function with no `प्रत्यागच्छ` returns `शून्य`.

### सूचयः कोशाश्च · Lists and dictionaries

```sanskrit
सूची स = [१, २, ३]।
स[०] = ९।                 # index assignment; negative indices count from the end
योजय(स, ४, ५)।            # append
मुद्रय स[-१], दीर्घता(स)।

कोशः क = {"नाम": "वाक्", "वर्षम्": २०२६}।
मुद्रय क.नाम, क["वर्षम्"]।   # dot access and bracket access are the same thing
क.नूतनम् = सत्य।           # new keys are created by assignment
```

### संकारकाः · Operators

| Kind | Operators |
|---|---|
| arithmetic | `+` `-` `*` `/` `%` `^` (power, right-associative) |
| assignment | `=` · `+=` `-=` `*=` `/=` `%=` `^=` |
| comparison | `==` `!=` `<` `<=` `>` `>=` |
| logic | `च` / `&&` · `वा` / `\|\|` · `न` / `!` |
| access | `(...)` call · `[...]` index · `.` key |

`+` also concatenates strings (`"क" + १` → `"क1"`) and joins lists. `च` and `वा`
short-circuit. Equality is type-aware: `१ == सत्य` is `असत्य`.

The compound forms are pure sugar — `क += १` is parsed into exactly the tree `क = क + १`
produces, so declared types, the analyser and all four engines treat them identically. They
work on names, list elements and dictionary keys (`स[०] += १`, `को.अ *= २`); note that a
compound assignment evaluates its target twice, so keep side effects out of the index.

### द्विलिपिता · Two spellings for everything

Every keyword and built-in has a romanized alias, so Vāk can be typed on a plain keyboard:

```sanskrit
mana x = 5;
yadi (x > 3) { mudraya "mahat"; } anyatha { mudraya "alpam"; }
```

---

## प्रकाराः · Types

Types are **optional**. Where you write one, it is enforced — at declaration, at every
later assignment, when an argument is passed, and when a function returns.

| प्रकारः | Holds | Literal |
|---|---|---|
| `पूर्णाङ्कः` | whole number | `४२`, `-७` |
| `दशांशः` | decimal (a `पूर्णाङ्कः` widens into it) | `३.१४` |
| `अङ्कः` | either kind of number | |
| `शब्दः` | string | `"नमस्ते"`, `'क'` |
| `सत्यता` | boolean | `सत्य`, `असत्य` |
| `सूची` | list | `[१, २, ३]` |
| `कोशः` | dictionary | `{"नाम": "वाक्"}` |
| `कार्यम्` | function | `कार्यम्(x) { }` |
| `शून्यम्` | nothing | `शून्य` |
| `किमपि` | anything (the default) | |

Four ways to write a declaration, all equivalent in meaning:

```sanskrit
पूर्णाङ्कः वयः = ३०।            # type first — the classic form
मान पूर्णाङ्कः वयः = ३०।        # with मान
मान वयः : पूर्णाङ्कः = ३०।      # with a colon
ध्रुव दशांशः पाई = ३.१४।        # a typed constant
```

On functions, parameters and the return value both take types:

```sanskrit
कार्यम् क्षेत्रफलम्(दशांशः दैर्घ्यम्, दशांशः विस्तारः) : दशांशः {
    प्रत्यागच्छ दैर्घ्यम् * विस्तारः।
}
```

`प्रकार(मूल्यम्)` reports the precise type of any value at runtime. Type names are **not**
reserved words — `सूची(...)` and `शब्द(...)` still work as function calls, because a type
is only recognised when it is immediately followed by a name.

---

## कारकाणि · Kāraka roles

This is the part of Vāk that exists in no other language.

In Sanskrit, a **kāraka** is the *role a thing plays in an action* — who acts, what is
acted upon, by what means, for whom, from where, in what place — and the case ending
(vibhakti) marks it. Vāk lets a parameter declare that role, before its type:

```sanskrit
कार्यम् छानय(अपादानम् सूची संग्रहः, करणम् कार्यम् परीक्षा) : सूची { ... }
#            ^ the source read from   ^ the instrument used
```

| कारकम् | विभक्तिः | Role | What it usually holds |
|---|---|---|---|
| `कर्ता` | प्रथमा (nominative) | the agent, who acts | anything |
| `कर्म` | द्वितीया (accusative) | the patient, what the action wants | anything |
| `करणम्` | तृतीया (instrumental) | the means | `कार्यम्` or `शब्दः` |
| `सम्प्रदानम्` | चतुर्थी (dative) | the recipient | `सूची` or `कोशः` |
| `अपादानम्` | पञ्चमी (ablative) | the source | a collection |
| `अधिकरणम्` | सप्तमी (locative) | the locus | a collection |

**Case marking frees word order** — that is what it is *for* in Sanskrit — so arguments may
be passed by role, in any sequence:

```sanskrit
छानय(अङ्काः, समः_वा)                        # positional
छानय(अपादानम्: अङ्काः, करणम्: समः_वा)        # labelled
छानय(करणम्: समः_वा, अपादानम्: अङ्काः)        # the same call, reordered
छानय(अङ्काः, करणम्: समः_वा)                  # mixed
```

The analyser enforces the grammar of roles: **one कर्ता and one कर्म at most** (Pāṇini
allows only one of each per action), every label must name a role the function actually
declares, no role may be given twice — and it warns when a role holds a kind of value it
cannot sensibly play, or when a function with a कर्म returns nothing (a transitive verb
yields a result). Order is deliberately *not* checked. `python -m vaak --karakas` lists them.

Kāraka names are contextual, not reserved: `कर्म` alone is still an ordinary variable name.

See [13_karaka.vak](examples/13_karaka.vak).

---

## अर्थविश्लेषकः · The semantic analyser

Between parser and interpreter sits a static pass that answers what the parser cannot.
It runs automatically before a file executes; `--check` runs it alone, `--no-check` skips it.

```powershell
python -m vaak --check प्रोग्राम.vak
```

```
अर्थदोषः (Semantic Analysis) — 2 दोषाः, 1 सूचनाः
  दोषः [प्रकारदोषः] प्रोग्राम.vak:4 — चरः 'वयः': पूर्णाङ्कः अपेक्षितः, शब्दः दीयते
         4 | वयः = "त्रिंशत्"।
  दोषः [नामदोषः] प्रोग्राम.vak:7 — अपरिभाषितम् नाम 'अज्ञातम्'
  सूचना [अगम्यदोषः] प्रोग्राम.vak:9 — इदम् वाक्यम् कदापि न चलति
```

It reports **every** problem in one run, rather than stopping at the first. What it checks:

| Check | Diagnostic |
|---|---|
| every name is declared before use | `नामदोषः` |
| declared types agree with what flows into them (declaration, assignment, argument, return) | `प्रकारदोषः` |
| constants are never reassigned | `ध्रुवदोषः` |
| calls pass the right number of arguments — including built-ins | `प्राचलदोषः` |
| `प्रत्यागच्छ` is inside a `कार्यम्`; `विरम` / `अनुवर्त` inside a loop | `प्रवाहदोषः` |
| kāraka roles obey Sanskrit grammar | `कारकदोषः` |
| unreachable statements, missing returns, redeclarations, doubtful roles | *सूचनाः* (warnings) |

Typing is **gradual**: `किमपि` flows both ways, so only provable mismatches are reported.
A value that passes through an untyped function is unknown to the analyser and is caught
at runtime instead — [11_prakarah.vak](examples/11_prakarah.vak) demonstrates both sides of
that line.

---

## दोषनिग्रहः · Exception handling

```sanskrit
प्रयत्नः {                       # "an attempt"        — try
    मान फलम् = १० / ०।
} दोषे (द) {                     # "in case of a fault" — catch (locative case)
    मुद्रय द.प्रकारः, द.सन्देशः, द.पङ्क्तिः।
} अन्ततः {                       # "in the end"        — finally
    मुद्रय "एतत् सर्वदा चलति"।
}
```

A caught error is an ordinary `कोशः` with three keys — `प्रकारः` (the kind), `सन्देशः`
(the message) and `पङ्क्तिः` (the line) — so you can read it, pass it around, or re-throw
it with `उत्सृज द।`.

Throw anything with `उत्सृज` (`utsṛja`, "cast forth!"). A plain value is wrapped as an
`उपयोक्तृदोषः`; a `कोशः` is used as it stands, so you can name your own error kinds:

```sanskrit
उत्सृज { "प्रकारः": "मूल्यदोषः", "सन्देशः": "वयः ऋणात्मकम् न भवेत्" }।
```

The built-in error kinds, all catchable by name:

| प्रकारः | Raised when |
|---|---|
| `नामदोषः` | an undefined name is used |
| `प्रकारदोषः` | a declared type is violated, or an operator gets the wrong type |
| `गणितदोषः` | division or modulo by zero |
| `सूचकदोषः` | a list or string index is out of range |
| `कुञ्जिकादोषः` | a dictionary key does not exist |
| `प्राचलदोषः` | a function is called with the wrong number of arguments |
| `ध्रुवदोषः` | a constant is reassigned |
| `उपयोक्तृदोषः` | raised by `उत्सृज` or `दोष(...)` |

`अन्ततः` runs on every path — normal exit, caught error, or an error still travelling
outward. `दोषे` may omit its variable, and a `प्रयत्नः` may have `अन्ततः` alone.

---

## आनय · Modules

`आनय` is the imperative "bring!". A module is just a `.vak` file; everything it declares
at the top level becomes an export, and it runs exactly once no matter how often it is
imported.

```sanskrit
आनय "गणितम्"।                      # bind it under its own name
आनय "शब्दाः" इति श।                # इति — "thus named": an alias
आनय "चन्द्रकला" तः तिथिनाम, वर्णनम्।  # तः — ablative "from": selected names

मुद्रय गणितम्.क्रमगुणितम्(१०)।
मुद्रय श.विलोमः_वा("कनक")।
```

A module value is an ordinary `कोशः`, so `कुञ्जिकाः(गणितम्)` lists what it exports.
Search order: the importing file's directory, the current directory, then the bundled
standard library in [vaak/पुस्तकालयः/](vaak/पुस्तकालयः/). Circular imports raise
`आयातदोषः` rather than looping.

**The standard library is written in Vāk itself** — [गणितम्.vak](vaak/पुस्तकालयः/गणितम्.vak)
(squares, gcd/lcm, factorials, primes, mean, median) and
[शब्दाः.vak](vaak/पुस्तकालयः/शब्दाः.vak) (prefix/suffix tests, padding, repetition,
syllable splitting, word counts). They are the first pieces of Vāk standing on their own
feet, and they use kāraka-marked parameters throughout.

---

## सञ्चिकाः · Files

```sanskrit
सञ्चिकालिख("अभिलेखः.txt", "प्रथमा पङ्क्तिः
")।     # write (replaces)
सञ्चिकायोजय("अभिलेखः.txt", "द्वितीया
")।           # append
शब्दः सामग्री = सञ्चिकापठ("अभिलेखः.txt")।           # read the whole file
सूची पङ्क्तयः = सञ्चिकापङ्क्तयः("अभिलेखः.txt")।      # read as lines
यदि (सञ्चिकास्ति("अभिलेखः.txt")) { सञ्चिकानाशय("अभिलेखः.txt")। }
मुद्रय निर्देशिका(".")।                              # list a directory
```

Anything that fails raises a catchable `सञ्चिकादोषः`. Reading and writing files is the
other prerequisite for a compiler written in Vāk. See [14_anaya.vak](examples/14_anaya.vak).

---

## अक्षराणि · Syllables

Devanagari writes a syllable as a base letter plus matras, anusvāra and virāma-joined
consonants, so a string is **not** a list of code points. `अक्षराणि` splits by syllable,
and `विपर्यय` reverses by syllable — reversing code points produces broken text:

```sanskrit
मुद्रय अक्षराणि("संस्कृतम्")।     # ["सं", "स्कृ", "त", "म्"]  — four akṣaras
मुद्रय विपर्यय("कनक")।           # कनक — a palindrome, correctly
```

`दीर्घता` and indexing still work on code points; a full akṣara mode is on the roadmap.

---

## संस्कृतयन्त्रम् · The SanskritVM

Vāk has two engines. The tree-walking interpreter is the reference; the bytecode path
compiles the AST into instructions for a stack machine whose opcodes are Sanskrit words.

```powershell
python -m vaak --vm       प्रोग्राम.vak     # compile, then run on the VM
python -m vaak --bytecode प्रोग्राम.vak     # disassemble instead of running
```

```
॥ <मुख्यम्> ॥  (88 शब्दाः / words)
   0     4 | स्थापय             0  'नमस्ते जगत्'
   2     4 | मुद्रय             1
   4     7 | स्थापय             1  'वाक्'
   6     7 | घोषय               2  'नाम' : किमपि
  26    14 | स्थापय             8  'इयम् '
  28    14 | गृहाण              2  'नाम'
  30    14 | योगः
```

The instruction set: `स्थापय` (push a constant), `गृहाण` / `न्यसय` (read / assign a name),
`योगः` `वियोगः` `गुणनम्` `भागः` `शेषः` `घातः` (arithmetic), `समम्` `न्यूनम्` `अधिकम्`
(comparison), `लङ्घय` / `असत्ये_लङ्घय` / `पुनरागच्छ` (jumps), `आवरणम्` `आह्वय`
`प्रत्यागच्छ` (closures and calls), `प्रयत्नम्_आरभ` `उत्सृज` `अन्ततः_समापय` (exceptions),
`पुनरावर्तय` (iteration), `आनय` (import) — the full list is in
[vaak/opcodes.py](vaak/opcodes.py).

Both engines share the same Environment chain, values, built-ins and error types, so
closures, scoping and exceptions behave identically. That is enforced, not assumed: the
suite runs **every example through both engines and requires byte-identical output**.

Scopes are still dynamic environments rather than frame slots — that optimisation is a
later change and does not affect semantics.

---

## देशीयसंकलनम् · The native back end

A Vāk program can be compiled to a **standalone Windows executable** that needs neither
Python nor the Vāk toolchain to run:

```powershell
python -m vaak --native examples/08_fibonacci.vak    # → examples/08_fibonacci.exe
./examples/08_fibonacci.exe
```

The program is not translated statement by statement into C. Its **bytecode is emitted as C
data** and linked against a C implementation of the SanskritVM in [native/](native/) — the
same instruction set the other three engines run, so there is one semantics and four
executors rather than four dialects.

| File | Sanskrit name | What it is |
|---|---|---|
| [native/vak.h](native/vak.h) | — | The value representation, the instruction set, and the shape a compiled program takes as C data. |
| [native/mulyani.c](native/mulyani.c) | मूल्यानि | Values: tagged unions, reference-counted strings, lists, dictionaries and closures; UTF-8 handling; the scope chain; printing that matches Python's exactly, down to shortest-round-trip floats. |
| [native/antarnihitani.c](native/antarnihitani.c) | अन्तर्निहितानि | All 37 built-ins in C, including akṣara splitting and file I/O, with the same bilingual error text. |
| [native/yantram.c](native/yantram.c) | यन्त्रम् | The VM: value stack, call frames, environments, `प्रयत्नः` handler stack, kāraka-labelled calls, declared-type checks, module loading. |
| [vaak/native.py](vaak/native.py) | देशीयसंकलनम् | The code generator: a Chunk (and every module it imports) becomes one C translation unit, then gcc links it against the runtime. |

Requires a C compiler — [w64devkit](https://github.com/skeeto/w64devkit/releases) is the
easiest on Windows: unzip it, put its `bin` on PATH, and `--native` finds it. Without one
the flag reports that plainly and the other three engines are unaffected.

**Speed**, on recursive Fibonacci (`फ(२४)`, about 150k calls):

| Engine | Time |
|---|---|
| native `.exe` | **0.55 s** |
| tree-walking interpreter | 4.65 s |
| Python bytecode VM | 8.31 s |
| the VM written in Vāk | minutes |

The Python VM being *slower* than the tree-walker is not a mistake: it dispatches in Python
and still resolves every name through the environment chain, so it pays the interpretation
cost twice. Resolving locals to frame slots is the fix, and it would speed up all four.

Two limits worth stating: integers are 64-bit in the native runtime (Python's are
arbitrary-precision), and the reference counting does not collect reference cycles.

---

## स्वयंसिद्धिः · The bootstrap

The goal of the project is a Vāk that does not depend on a host language. **Every stage
of the front end is now written in Vāk** — lexer, parser, analyser, compiler, and the
virtual machine itself — and each is held to the Python implementation exactly:

| Stage | Written in Vāk | Lines | Verified against |
|---|---|---|---|
| Lexer | [शब्दविभाजकः.vak](स्वयंसिद्धिः/शब्दविभाजकः.vak) | 277 | the Python lexer — kind, lexeme, value and line of every token |
| Parser | [व्याकरणम्.vak](स्वयंसिद्धिः/व्याकरणम्.vak) | 791 | the Python parser — the whole syntax tree, node for node |
| **Analyser** | [अर्थविश्लेषकः.vak](स्वयंसिद्धिः/अर्थविश्लेषकः.vak) | 786 | the Python analyser — every diagnostic's code, line and message, in order |
| Compiler | [संकलकः.vak](स्वयंसिद्धिः/संकलकः.vak) | 618 | the Python compiler — every instruction, constant and line |
| VM | [यन्त्रम्.vak](स्वयंसिद्धिः/यन्त्रम्.vak) | 1047 | the Python VM — byte-identical output on every example |
| Driver | [वाक्.vak](स्वयंसिद्धिः/वाक्.vak) | 260 | compiled natively it becomes `वाक्.exe`, which runs every example identically |

Only the [native back end](#देशीयसंकलनम्--the-native-back-end) is written in C, on
purpose: it is the substrate the language stands on, not part of the language.

### अर्थविश्लेषकः वाक्-भाषायाम् — the analyser in Vāk

The analyser was the last stage with no Vāk counterpart, and it is the fussiest to match:
a lexer either agrees on a token or it does not, but an analyser has to produce the *same
complaints*, in the same order, with the same wording. It does:

```powershell
./वाक्.exe --परीक्षा प्रोग्राम.vak     # analyse and stop — no Python anywhere
python -m vaak --check प्रोग्राम.vak    # the same report, from the Python analyser
```

Both are checked against each other on every example, on the standard library, on a
battery of forty deliberately broken programs — one per diagnostic kind — and on the
toolchain's own source, including [अर्थविश्लेषकः.vak](स्वयंसिद्धिः/अर्थविश्लेषकः.vak)
analysing itself. Sixty-five files, every diagnostic identical.

### स्थाननिर्णयः — resolving names to places

A name the compiler can see declared no longer has to be searched for at run time. The
compiler keeps the same picture of the scopes the machine will build, so `अ` inside a
कार्यम् compiles to *the first binding of this scope* rather than to the string `"अ"`:

```
    ०   ५ | स्थानात्_गृहाण     0   0  'नाम'
```

The three operands are how many scopes out, which binding in it, and — carried along so
the machine can check it landed on the binding that was meant — the name. If the scope is
not shaped the way the compiler expected, one comparison notices and the search happens
anyway, so a resolved instruction can never be *wrong*, only occasionally no faster. The
Python VM counts every such miss and the tests insist the count is zero, on the examples,
on the library, and on the toolchain's own source.

Both compilers do this resolution independently, and still emit byte-identical bytecode.

**What it bought, measured.** Compiling a 761-line file with `वाक्.exe`, counting the
string comparisons each name costs:

| | before | after |
|---|---|---|
| lookups in local scopes | 4,529,587 | **1,900,964** |
| comparisons in local scopes | 7,251,008 | **3,116,423** |
| lookups in the global scope | 768,129 | 776,651 |
| comparisons in the global scope | 23,718,087 | 25,837,295 |

Local lookups more than halved — and the wall clock barely moved, because local scopes
were never where the time went. A local scope holds one or two bindings, so searching it
was already cheap; the *global* scope holds every built-in the program can see, and each
lookup that reaches it costs about thirty-three comparisons. That is 89% of the remaining
cost, and slot resolution cannot touch it: the compiler cannot number a scope that was
already full before the program started. Numbering the built-ins is the next step, and now
that names resolve to places at all, it is a small one.

```powershell
python -m vaak स्वयंसिद्धिः/मुख्यम्.vak            # the toolchain over its own source
./वाक्.exe --परीक्षा प्रोग्राम.vak                # analyse it, in Vāk, without Python
python -m vaak --self examples/08_fibonacci.vak   # compiled by Vāk, run on the Python VM
python -m vaak --self-vm examples/13_karaka.vak   # compiled AND run by Vāk
python -m vaak --native examples/08_fibonacci.vak # build a standalone .exe
```

```
॥ स्वयंसिद्धिः — वाक् वाचम् पठति, विश्लेषयति, संकलयति, चालयति च ॥

॥ स्वयंसिद्धिः/व्याकरणम्.vak ॥
  अक्षराणि    : २५८६३
  चिह्नानि    : ५२५९
  पर्वाणि     : २५१९
  आदेशाः     : ६११०

॥ वाक्-यन्त्रेण चालितानि — सर्वम् वाक्-भाषया ॥
  क्रमगुणितम्(१०) = 3628800
  अभाज्याः २० यावत् = [2, 3, 5, 7, 11, 13, 17, 19]
  गृहीतः: मम्दोषः — परीक्षा
```

That run is the **parser parsing itself** and the **compiler compiling itself**, and then
the **VM written in Vāk** executing freshly compiled programs — closures, recursion, kāraka
calls, `प्रयत्नः`/`दोषे`/`अन्ततः`, modules and declared types all included.

The VM in Vāk keeps its own value stack, call frames, environment chain and exception
handler stack, all as ordinary `कोशाः`. It reaches the host only for primitive operations —
arithmetic on numbers, the built-in functions, file access — exactly the boundary a native
runtime would later replace.

The shared contract is [vaak/kosha.py](vaak/kosha.py), which writes the Python AST and Chunk
as plain कोशाः — the same shape the Vāk stages build — so every stage can be compared
against its counterpart. [vaak/selfhost.py](vaak/selfhost.py) drives the Vāk toolchain from
Python (`parse_with_vak`, `compile_with_vak`, `run_with_vak`).

### वाक्.exe — the bootstrap closed

The last hop is done. [स्वयंसिद्धिः/वाक्.vak](स्वयंसिद्धिः/वाक्.vak) is a driver written in
Vāk that reads a `.vak` file and lexes, parses, compiles and runs it using only the
Vāk-written toolchain. Compiled natively, that driver **is** the compiler:

```powershell
python -m vaak --native स्वयंसिद्धिः/वाक्.vak     # once, to build it
./वाक्.exe examples/13_karaka.vak                # thereafter: no Python at all
./वाक्.exe --चिह्नानि प्रोग्राम.vak               # show the tokens
./वाक्.exe --आदेशाः प्रोग्राम.vak                 # count the instructions
```

A 486 KB executable that runs **all fourteen examples with byte-identical output** to the
Python interpreter, in 2.7 s total. Python is used to *build* वाक्.exe once, exactly as a C
compiler is used once to build a self-hosting C compiler — after that the language stands
on its own.

**One machine, not two.** The driver used to hand its bytecode to the Vāk-written VM, which
the C VM then interpreted — a VM inside a VM. The built-in `खण्डम्_चालय(खण्डः, विभागाः)`
removes that layer: it materialises a chunk that arrives as `कोशाः` into the host machine's
own structures and runs it there. The same call works under Python (where it feeds the
Python VM) and in `वाक्.exe` (where it feeds the C VM), so the self-hosted compiler is now
exactly as fast as the native back end:

The figures below were taken when that change was made, with fourteen
examples and a smaller binary than today's; they are kept as measured.

| | two VMs | one VM |
|---|---|---|
| `वाक्.exe examples/08_fibonacci.vak` | 2.02 s | **0.20 s** |
| all fourteen examples | 3.2 s | **2.7 s** |
| the toolchain over its own source | *timed out at 300 s* | **46 s** |
| binary size | 631 KB | 486 KB |

The Vāk-written VM ([यन्त्रम्.vak](स्वयंसिद्धिः/यन्त्रम्.vak)) stays in the repository — it is
the executable specification of the machine's semantics, and the test suite still runs
every example through it — but nothing depends on it any more.

Two things came out of this last step: programs can now read their arguments with
`प्राचलाः()`, and the Windows-specific handling that a Sanskrit-named language needs —
UTF-16 command lines and `_wfopen`, since `main`'s `argv` and `fopen` are both ANSI on
Windows and quietly destroy Devanagari.

**What this does and does not mean.** The language is self-hosting at the front end and in
its runtime semantics: `वाक्.exe` contains no Python and needs none. What it does *not*
mean is that Python is gone from the repository — it built `वाक्.exe`, it is still the
reference implementation the other engines are tested against, and the semantic analyser
has no Vāk counterpart yet. Nor is the double interpretation free: `वाक्.exe` runs a VM
inside a VM, so it is fast for ordinary programs but too slow to run the Vāk parser over
its own 25 KB source in reasonable time.

Three built-ins were added along the way, and are generally useful: `संकेतः` (code point of
a character), `वर्णः` (character for a code point) and `अंशः` (slice a string or list).

---

## पदकोशः · Keyword reference

Both canons are live: the primary spelling is on the left, historical aliases on the right
mean exactly the same thing.

| देवनागरी | Romanized | Literal sense | Role | Alias |
|---|---|---|---|---|
| `मान` | `mana` | measure, value | variable declaration | |
| `ध्रुव` | `dhruva` | fixed, immovable | constant declaration | |
| `कार्यम्` | `karyam` | work, task | function | `कार्य` |
| `प्रत्यागच्छ` | `pratyagaccha` | come back! | return | `प्रतिदा` |
| `मुद्रय` | `mudraya` | print! | print command | `लिख(...)` as a function |
| `यदि` | `yadi` | if | if | |
| `अन्यथा` | `anyatha` | otherwise | else (chain with `अन्यथा यदि`) | |
| `यावत्` | `yavat` | as long as | while | |
| `आवृत्तिः` | `avrttih` | a turning round | repeat *n* times | |
| `विकल्पः` · `विकल्प` | `vikalpaḥ` · `vikalpah` | choose among alternatives |
| `पक्षे` | `pakṣe` · `pakshe` | in this case |
| `प्रत्येकम्` | `pratyekam` | each one | for-each | |
| `अन्तः` | `antah` | within | `in` (inside `प्रत्येकम्`) | |
| `विरम` | `virama` | stop! | break | |
| `अनुवर्त` | `anuvarta` | carry on! | continue | |
| `प्रयत्नः` | `prayatnah` | an attempt | try | |
| `दोषे` | `doshe` | in case of a fault | catch | `गृहाण` |
| `अन्ततः` | `antatah` | in the end | finally | `अन्ते` |
| `उत्सृज` | `utsrja` | cast forth! | throw | `क्षिप` |
| `आनय` | `anaya` | bring! | import | |
| `इति` | `iti` | thus named | `as` (an import alias) | |
| `तः` | `tah` | ablative "from" | `from` (selective import) | |
| `सत्य` / `असत्य` | `satya` / `asatya` | truth / untruth | true / false | |
| `शून्य` | `shunya` | void | null | |
| `च` / `वा` / `न` | `ca` / `va` / `na` | and / or / not | logical operators | |

Punctuation: `।` `॥` `;` end statements · `{}` blocks · `[]` lists · `{k: v}` dictionaries
· `#` `//` `/* */` comments.

---

## अन्तर्निहितानि · Built-in functions

Run `python -m vaak --builtins` to print this table from the interpreter itself.

| देवनागरी | Romanized | What it does |
|---|---|---|
| `लिख(...)` | `likh` | print — the function form of `मुद्रय` |
| `पठ(संकेतः?)` | `patha` | read one line from the user |
| `प्रकार(म)` | `prakara` | the type of a value, as a Sanskrit word |
| `संख्या(म)` | `sankhya` | convert to a number (Devanagari digits accepted) |
| `शब्द(म)` | `shabda` | convert to a string |
| `देवनागरी(म)` | `devanagari` | render digits in Devanagari — `42` → `४२` |
| `दीर्घता(म)` | `dirghata` | length of a string, list or dictionary |
| `सूची(म?)` | `suchi` | build/copy a list (from a string, dict keys, or list) |
| `परास(अ, ब?, पदम्?)` | `parasa` | numeric range as a list |
| `योजय(स, ...)` | `yojaya` | append items to a list |
| `निष्कास(स, सूचकः?)` | `nishkasa` | remove and return an item (list) or key (dict) |
| `अस्ति(संग्रहः, म)` | `asti` | membership test |
| `कुञ्जिकाः(को)` | `kunjika` | the keys of a dictionary |
| `मूल्यानि(को)` | `mulyani` | the values of a dictionary |
| `क्रम(स, विपरीतम्?)` | `krama` | sorted copy of a list |
| `विपर्यय(स)` | `viparyaya` | reversed list or string |
| `विभज(श, विभाजकः?)` | `vibhaja` | split a string into a list |
| `संयोज(स, योजकः?)` | `samyoja` | join a list into a string |
| `योग(स)` | `yoga` | sum of a list of numbers |
| `न्यूनतम(स)` / `अधिकतम(स)` | `nyunatama` / `adhikatama` | min / max |
| `मूल(अ)` | `mula` | square root |
| `पूर्ण(अ)` | `purna` | truncate to an integer |
| `यादृच्छिक(अ?, ब?)` | `yadrcchika` | random float in `[0,1)`, or integer in `[a,b]` |
| `काल()` | `kala` | seconds since the epoch |
| `दोष(सन्देशः?, प्रकारः?)` | `dosha` | raise a catchable error |
| `अक्षराणि(श)` | `aksharani` | split a string into syllables (akṣaras) |
| `संकेतः(अक्षरम्)` | `sanketa` | the Unicode code point of a character |
| `वर्णः(संकेतः)` | `varna` | the character for a code point |
| `अंशः(स, आरम्भः, अन्तः?)` | `amsha` | a slice of a string or list |
| `सञ्चिकापठ(पथः)` | `sanchikapatha` | read a whole file |
| `सञ्चिकापङ्क्तयः(पथः)` | `sanchikapanktayah` | read a file as a सूची of lines |
| `सञ्चिकालिख(पथः, सामग्री)` | `sanchikalikh` | write a file, replacing it |
| `सञ्चिकायोजय(पथः, सामग्री)` | `sanchikayojaya` | append to a file |
| `सञ्चिकास्ति(पथः)` | `sanchikasti` | does the path exist |
| `सञ्चिकानाशय(पथः)` | `sanchikanashaya` | delete a file |
| `निर्देशिका(पथः?)` | `nirdeshika` | list a directory |
| `प्राचलाः()` | `prachalah` | the command-line arguments |
| `खण्डम्_चालय(खण्डः, विभागाः?)` | `khandam_chalaya` | run a compiled chunk on this machine |

Built-ins live in a scope *outside* your globals, so ordinary Sanskrit words like `योग`
or `सूची` remain free for your own variables — declaring `मान योग = ५।` simply shadows
the built-in.

---

## साधनानि · Tooling

**The editor.** [vscode-vak/](vscode-vak/) is a VS Code extension: `.vak` files
carry the वा mark in the explorer, all 38 keywords highlight in every canon with
the kāraka roles given a scope of their own, and the real analyser's diagnostics
appear inline on save. The TextMate grammar is *generated* from `vaak/tokens.py`
and `vaak/builtins.py`, so highlighting cannot drift from the language, and 15
checks run on every build — one of them for `विरम।`, a keyword written hard
against its danda, which stopped matching when the word-boundary class swallowed
U+0964.

**Typing Devanagari.** Vāk never transliterates identifiers — `नाम` and `naam`
are two different names, deliberately, because a language that merged them would
make every variable ambiguous. The help belongs where you type instead:
`Ctrl+Alt+T` converts romanised words as you finish them, `Ctrl+Alt+D` converts a
selection, and the browser playground has the same switch. The scheme is
ITRANS-flavoured — `kaaryam` → `कार्यम्`, `puurNaa~NkaH` → `पूर्णाङ्कः` — and it
exists three times, in Python and in two JavaScript copies, all generated from
one table in [vaak/translit.py](vaak/translit.py) and checked against each other.

**The mark.** [brand/](brand/) holds वा, the first syllable, in real outlines
pulled from a Devanagari font and shaped by HarfBuzz, then converted to SVG
paths so it needs no font installed. वा is chosen because Devanagari hangs its
letters from a शिरोरेखा, and वा gives you that head-line spanning two verticals —
the silhouette that survives being shrunk to the 16 pixels a file tree allows.

---

## व्याकरणम् · Grammar

```ebnf
program     → statement* EOF
statement   → varDecl | funcDecl | ifStmt | whileStmt | forEachStmt
            | repeatStmt | printStmt | tryStmt | throwStmt
            | returnStmt | breakStmt | continueStmt | block | exprStmt

varDecl     → ("मान" | "ध्रुव") type? IDENT (":" type)? ("=" expression)? end
            | type IDENT ("=" expression)? end
funcDecl    → "कार्यम्" IDENT "(" params? ")" (":" type)? block
params      → param ("," param)*
param       → karaka? type? IDENT (":" type)?
karaka      → "कर्ता" | "कर्म" | "करणम्" | "सम्प्रदानम्" | "अपादानम्" | "अधिकरणम्"
type        → "पूर्णाङ्कः" | "दशांशः" | "अङ्कः" | "शब्दः" | "सत्यता"
            | "सूची" | "कोशः" | "कार्यम्" | "शून्यम्" | "किमपि"
ifStmt      → "यदि" expression block ("अन्यथा" (ifStmt | block))?
whileStmt   → "यावत्" expression block
repeatStmt  → "आवृत्तिः" expression block
forEachStmt → "प्रत्येकम्" "("? IDENT "अन्तः" expression ")"? block
printStmt   → "मुद्रय" (expression ("," expression)*)? end
importStmt  → "आनय" STRING ("इति" IDENT | "तः" IDENT ("," IDENT)*)? end
tryStmt     → "प्रयत्नः" block ("दोषे" "("? IDENT? ")"? block)? ("अन्ततः" block)?
throwStmt   → "उत्सृज" expression end
returnStmt  → "प्रत्यागच्छ" expression? end
end         → ";" | "।" | "॥" | ε

expression  → assignment
assignment  → (IDENT | postfix "[" expression "]") "=" assignment | logicOr
logicOr     → logicAnd (("वा" | "||") logicAnd)*
logicAnd    → equality (("च" | "&&") equality)*
equality    → comparison (("==" | "!=") comparison)*
comparison  → term (("<" | "<=" | ">" | ">=") term)*
term        → factor (("+" | "-") factor)*
factor      → power (("*" | "/" | "%") power)*
power       → unary ("^" power)?
unary       → ("-" | "!" | "न") unary | postfix
postfix     → primary ("(" args? ")" | "[" expression "]" | "." IDENT)*
args        → arg ("," arg)*
arg         → (karaka ":")? expression
primary     → NUMBER | STRING | "सत्य" | "असत्य" | "शून्य" | IDENT
            | "(" expression ")" | list | dict
            | "कार्यम्" "(" params? ")" (":" type)? block
```

Precedence runs from lowest (assignment) to highest (call/index); `^` is
right-associative, every other binary operator is left-associative.

---

## रचना · How the implementation works

```
source .vak
    │
    ▼
┌───────────┐  Tokens  ┌───────────┐   AST   ┌────────────┐
│   Lexer   │─────────▶│  Parser   │────────▶│  Analyser  │  नामदोषः, प्रकारदोषः, कारकदोषः …
│ lexer.py  │          │ parser.py │         │analyzer.py │
└───────────┘          └───────────┘         └─────┬──────┘
  tokens.py             ast_nodes.py               │ checked AST
  keyword / type /      node classes               ├──────────────────────┐
  kāraka tables                                    ▼                      ▼
                                        ┌───────────────┐      ┌────────────────┐  Chunk
                                        │  Interpreter  │      │   Compiler     │─────────┐
                                        │interpreter.py │      │ compiler.py    │         │
                                        └───────┬───────┘      └────────────────┘         ▼
                                                │                  opcodes.py     ┌──────────────┐
                                                │                                 │ SanskritVM   │
                                                ▼                                 │   vm.py      │
                                             effects ◀───────────────────────────  └──────────────┘
   shared by both engines: environment.py · values.py · builtins.py · पुस्तकालयः/ (written in Vāk)
```

| File | Sanskrit name | Responsibility |
|---|---|---|
| [vaak/tokens.py](vaak/tokens.py) | शब्दप्रकाराः | Token kinds, the `Token` record, the **keyword table** (both canons + romanized aliases), the **type-name table**, numeral tables, and the character predicates that define a Devanagari identifier. |
| [vaak/lexer.py](vaak/lexer.py) | शब्दविभाजकः | **Lexer.** One left-to-right pass producing tokens: identifiers (letters + matras + virama + ZWJ), numbers in either script, strings with escapes, comments, operators, and `। ॥ ;` as terminators. Tracks line/column for every token. |
| [vaak/ast_nodes.py](vaak/ast_nodes.py) | वाक्यरचना | The **AST**: expressions (`Literal`, `Binary`, `Call`, `IndexGet`, …) and statements (`VarDecl`, `If`, `While`, `Repeat`, `Print`, `Try`, `Throw`, `FunctionDecl`, …), plus `Param` carrying declared types. |
| [vaak/parser.py](vaak/parser.py) | व्याकरणम् | **Parser.** Hand-written recursive descent, one method per grammar rule. Resolves the type-vs-call ambiguity by lookahead, and the `मुद्रय(...)` command-vs-call form by backtracking. |
| [vaak/analyzer.py](vaak/analyzer.py) | अर्थविश्लेषकः | **Semantic analyser.** Scope resolution, gradual type inference and checking, control-flow placement, reachability, and the kāraka rules. Collects every diagnostic instead of stopping at the first. |
| [vaak/पुस्तकालयः/](vaak/पुस्तकालयः/) | पुस्तकालयः | The standard library — `गणितम्` and `शब्दाः` — **written in Vāk itself** and found automatically by `आनय`. |
| [vaak/interpreter.py](vaak/interpreter.py) | दुभाषिकः | **Interpreter.** Walks the AST via `_eval_*` / `_exec_*` dispatch. Hoists functions per block, loads and caches modules, reorders kāraka-labelled arguments. `प्रत्यागच्छ`, `विरम`, `अनुवर्त` and `उत्सृज` travel as `ReturnSignal` / `BreakSignal` / `ContinueSignal` / `VakThrow`. |
| [vaak/environment.py](vaak/environment.py) | परिवेशः | **Scopes.** A chain of `Environment` objects; each block, call and loop iteration gets a child. Enforces `ध्रुव` immutability and the declared type of every variable on assignment. |
| [vaak/values.py](vaak/values.py) | मूल्यानि | Runtime values: `VakFunction` (closure), `NativeFunction`, the **type predicate table** (`matches_type` / `check_type`), plus `type_name`, `is_truthy`, `stringify`. |
| [vaak/builtins.py](vaak/builtins.py) | अन्तर्निहितानि | The standard library and its registry of Devanagari + romanized names. |
| [vaak/errors.py](vaak/errors.py) | दोषाः | `LexError`, `ParseError`, `RuntimeVakError` with its Sanskrit `code`, and the source-snippet renderer. |
| [vaak/opcodes.py](vaak/opcodes.py) | आदेशाः | The instruction set — every opcode with its Sanskrit name and operand count. |
| [vaak/compiler.py](vaak/compiler.py) | संकलकः | **Compiler.** AST → `Chunk` (code, constants, line table). Each कार्यम् compiles to its own chunk; loops patch their own jumps; try/catch/finally compiles to handler ranges. Includes the disassembler. |
| [vaak/vm.py](vaak/vm.py) | संस्कृतयन्त्रम् | **The VM.** A stack machine with call frames, handler stacks and module caching, running the bytecode over the same environments the interpreter uses. |
| [vaak/kosha.py](vaak/kosha.py) | कोशरूपम् | The contract between the two toolchains — the AST and a compiled Chunk written as plain कोशाः, in both directions. |
| [vaak/selfhost.py](vaak/selfhost.py) | स्वयंसिद्धिः | Loads the Vāk-written toolchain and exposes it to Python: `compile_with_vak(source)` returns a Chunk the VM can run. |
| [स्वयंसिद्धिः/](स्वयंसिद्धिः/) | स्वयंसिद्धिः | **Vāk written in Vāk** — the lexer, the parser, the compiler and the VM, plus a driver that runs all four over their own source. |
| [vaak/cli.py](vaak/cli.py) | आदेशपङ्क्तिः | File runner, REPL, `--tokens`, `--ast`, `--bytecode`, `--vm`, `--check`, `--builtins`, `--karakas`. |

Design choices worth knowing:

- **Types are checked where values are bound**, not inferred across a program — that is
  the job of the semantic analyser, which will reuse `TYPE_PREDICATES` unchanged.
- **Built-ins sit in a prelude scope** beneath globals, so Sanskrit words used as library
  names are still available as your own variable names.
- **Type names are contextual, not reserved** — `सूची` is a type in `सूची स = []।` and a
  function in `सूची("अब")।`.
- **Equality is type-aware** — `१ == सत्य` is `असत्य`, unlike Python's `1 == True`.
- **Integer division stays integral when it can:** `१०/५` → `2`, `१०/४` → `2.5`.
- **Errors are bilingual** and carry a Sanskrit `प्रकारः` a program can branch on.

Errors name the stage they came from and point at the source:

```
कार्यकालदोषः (Runtime Error) — examples/demo.vak:2:0
    अपरिभाषितम् नाम 'अज्ञातम्' / undefined name 'अज्ञातम्'
       2 | मुद्रय अज्ञातम्।
```

---

## उदाहरणानि · Sample programs

All of them live in [examples/](examples/) and all of them run:

| Program | Shows |
|---|---|
| [01_namaste.vak](examples/01_namaste.vak) | printing, `मान` / `ध्रुव`, string joining, `प्रकार`, `देवनागरी` |
| [02_ganita.vak](examples/02_ganita.vak) | every operator, `च` / `वा` / `न`, mixed numerals, math built-ins |
| [03_yadi.vak](examples/03_yadi.vak) | `यदि` / `अन्यथा यदि` / `अन्यथा`, truthiness, a predicate function |
| [04_yavat.vak](examples/04_yavat.vak) | `यावत्` loops, `विरम`, `अनुवर्त`, a digit-sum algorithm |
| [05_karya.vak](examples/05_karya.vak) | functions, recursion, mutual recursion, higher-order functions, closures |
| [06_suchi.vak](examples/06_suchi.vak) | lists: indexing, mutation, search, sort, filter, split/join |
| [07_kosha.vak](examples/07_kosha.vak) | dictionaries: dot vs bracket access, iteration, a frequency counter |
| [08_fibonacci.vak](examples/08_fibonacci.vak) | the Piṅgala/Fibonacci sequence three ways — recursive, iterative, memoised |
| [09_pratyekam.vak](examples/09_pratyekam.vak) | `प्रत्येकम्` over lists, ranges and strings; nested loops; a prime sieve |
| [10_granthalaya.vak](examples/10_granthalaya.vak) | capstone: records, sorting, filtering with a callback, grouping, statistics |
| [11_prakarah.vak](examples/11_prakarah.vak) | declared types on variables, parameters and returns — and the errors they raise |
| [12_dosha.vak](examples/12_dosha.vak) | `प्रयत्नः` / `दोषे` / `अन्ततः`, custom errors, re-throwing, retry with `आवृत्तिः` |
| [13_karaka.vak](examples/13_karaka.vak) | kāraka roles on parameters, and calling by role in any order |
| [14_anaya.vak](examples/14_anaya.vak) | `आनय` in all three forms, the Vāk-written stdlib, files, syllables |
| [स्वयंसिद्धिः/मुख्यम्.vak](स्वयंसिद्धिः/मुख्यम्.vak) | the Vāk-written toolchain lexing, parsing, compiling and running its own source |

```powershell
python -m vaak examples/12_dosha.vak
```

---

## कार्यक्षमता · Performance

Every program below prints the same answer in every language, and each figure is
the best of five runs. Startup is measured separately because a language that
takes 150 ms to boot should not be credited for it.

| workload | C ‑O2 | Node/V8 | PHP 8.2 | CPython 3.13 | **वाक्** |
|---|---|---|---|---|---|
| `fib(30)` — recursion | 0.034 s | 0.160 s | 0.387 s | 0.351 s | **2.377 s** |
| 8 M-iteration loop | 0.029 s | 0.177 s | 0.633 s | 2.845 s | **5.926 s** |
| 120 k string appends | 0.032 s | 0.215 s | 1.419 s | 0.950 s | **0.108 s** |
| 1.2 M list operations | 0.025 s | 0.228 s | 0.257 s | 0.551 s | **1.292 s** |
| **startup** | 0.043 s | 0.153 s | 0.135 s | 0.067 s | **0.036 s** |

Relative to CPython, lower being faster: **loops 2.1×, collections 2.3×,
function calls 6.8×, and string building 0.11× — nine times faster.** Vāk also
starts faster than every other language here, from a single 737 KB binary with
nothing to install.

### What made the difference — and what did not

Two optimisations **failed**, and they are worth more than the successes to
anyone building an interpreter:

- Removing **71% of all string comparisons** moved the wall clock **2%**.
- Exploiting the fact that borrowed names are shared pointers moved it **not at
  all** — most of a scope scan is spent on entries that do *not* match, so a
  pointer check only helps the one that does.

The intuition that name lookup dominates was wrong twice. Every real gain came
from allocation and from work that need not have been done at all:

| change | effect |
|---|---|
| bindings borrow their name and type instead of copying | 2 allocations + 2 frees gone per binding |
| a pool of scopes | 364 k scope allocations → 121 k |
| `कोशः` keys carry a cached hash, and the probe is specialised for strings | ~12% on the toolchain's own workload |
| `x = x + y` grows the string in place | **quadratic → linear, 58× on that workload** |
| a call stops formatting an error it will not use, and compares type *codes* | 37% off `fib` |

Growing a string in place is the one with teeth. The machine does not take the
compiler's word for it: after the add pops its operands it looks at the *next*
instruction, and only grows in place if that is an assignment back to a binding
which currently holds this very object **and** would accept it — not a `ध्रुव`,
and not a declared type that would refuse a `शब्दः`. The growth happens before
the assignment, so an assignment that would fail must not be allowed to leave a
mutated string behind.

One caveat worth stating: **measurement noise on the development machine is about
7%**, discovered when a path bug made five supposedly different builds identical
and they still spread that far apart. Anything smaller than that was re-measured
interleaved before being believed.

---

## परीक्षाः · Tests

```powershell
python tests/test_vak.py          # 179 tests
```

The suite covers Devanagari numerals and identifiers, danda terminators, operator
precedence and associativity, compound assignment, type-aware equality, scoping, closures,
hoisting, arity checks, collection semantics, declared types, every error kind, both
keyword canons, every analyser diagnostic, the kāraka rules and labelled calls, modules and
file I/O, akṣara splitting — and it runs all fourteen example programs plus the standard
library through the analyser, the interpreter **and** the bytecode VM, requiring identical
output from both engines.

The bootstrap suites put the same files through both toolchains and require the **tokens**,
the **syntax trees**, the **bytecode** and the **diagnostics** to agree exactly — including
each Vāk-written stage processing its own source. `TestVakAnalyzer` compares the two
analysers on sixty-five files, forty of them deliberately broken, one per diagnostic kind.
`TestSlotResolution` insists that no resolved instruction ever lands on a binding other
than the one it was compiled for. `TestNative` then compiles every example to a native
executable and requires *its* output to match the interpreter too, so all four engines are
pinned to one expected result. The native tests skip themselves when no C compiler is
installed.

---

## अग्रिमम् · Roadmap

The plan is to reach a **self-hosted** Vāk — a compiler for Vāk written in Vāk — so the
language stops depending on a host language. Progress along that road:

- ✅ **Stage 0 — the reference implementation.** Lexer, parser, tree-walking interpreter,
  exceptions, types.
- ✅ **Semantic analyser** with kāraka roles. The static pass, and the language's one
  genuinely Sanskrit contribution to type systems.
- ✅ **Modules (`आनय`) and file I/O (`सञ्चिका…`).** The two hard prerequisites for writing
  a compiler *in* Vāk — a program can now span files and read source text.
- ✅ **A standard library written in Vāk** — `गणितम्`, `शब्दाः`.
- ✅ **Bytecode + SanskritVM.** A compiler to Sanskrit-named opcodes and a stack machine to
  run them, differential-tested against the tree-walker on every example.
- ✅ **The bootstrap — lexer, parser and compiler in Vāk.** Each processes its own source,
  and tokens, trees and bytecode match the Python toolchain exactly on all twenty test
  files. `--self` compiles a program with Vāk and runs the result on the VM.
- ✅ **The runtime in Vāk.** The VM's dispatch loop, environments, call frames, exception
  handling and module loading are written in Vāk too, and produce byte-identical output to
  the Python VM on every example.
- ✅ **A native back end.** Bytecode is emitted as C data and linked against a C
  SanskritVM, producing standalone executables that match the other three engines exactly
  and run about 8× faster than the tree-walker.
- ✅ **The last hop — `वाक्.exe`.** The Vāk-written toolchain, compiled natively. It runs
  every example with byte-identical output and needs no Python.
- ✅ **One VM, not two.** `खण्डम्_चालय` hands a compiled chunk straight to the host
  machine; `वाक्.exe` is 10× faster on function-heavy code and 145 KB smaller.
- ✅ **The analyser in Vāk.** The front end is now Vāk all the way down, and
  `वाक्.exe --परीक्षा` reports exactly what `python -m vaak --check` reports.
- ✅ **Slot-resolved locals.** Names the compiler can see are read by place, in all four
  engines; both compilers resolve them independently and still agree byte for byte.
- ✅ **विकल्पः · switch/case.** Built out of instructions the machine already
  had, so all five engines ran it the day it was written — and both compilers
  emit byte-identical bytecode for it.
- ✅ **Reaching the built-ins directly.** `अन्तर्निहितम्_गृहाण` — the compiler proves a
  name is a built-in the program never declares, and the machine skips the search
  entirely. Comparisons in the global scope fell 25.8 M → 6.4 M on the toolchain
  workload. **It bought 2% of wall clock**, which settled the question below.
- ✅ **Linux and macOS.** `निर्देशिका` has a real `opendir`/`readdir` branch, the platform
  switch is shared by all three C files, and nothing assumes a `.exe` suffix. Building
  with `VAK_POSIX=1` forces that branch, so it can be exercised on Windows too.
- ✅ **A browser playground.** The self-hosted toolchain compiled to WebAssembly.
- ✅ **The instruction pipeline.** Measurement pointed away from name lookup and at
  allocation and wasted work, and five changes followed: bindings borrow their names
  instead of copying them, scopes come from a pool, `कोशः` keys carry a cached hash,
  string building went from quadratic to linear, and a call stopped formatting an
  error message and comparing type *names* for every parameter. See
  [कार्यक्षमता](#कार्यक्षमता--performance).
- ⬜ **Frame slots.** Function calls remain the weak spot, at about 6.8× CPython.
  Closing that means locals in a contiguous stack array with no scope object at
  all — which changes the bytecode, both compilers and all five engines, and needs
  upvalues so a closure can outlive its frame. It is a project, not a patch.
- ⬜ **Computed-goto dispatch.** Mechanical, typically 10–20% — though on this
  machine it must clear a ~7% measurement noise floor to be verifiable.
- ⬜ **Memory.** The native runtime reference-counts and so leaks reference cycles; a small
  mark-and-sweep pass would close that.

Beyond the bootstrap:

1. **Objects** — `वर्गः` (class), `स्वयम्` (self), or a lighter prototype model on `कोशः`.
2. **`सन्धि`-aware identifiers** — accept the sandhi variants of a name as one identifier.
3. **Full akṣara mode** — `दीर्घता` and indexing by syllable, not code point.
4. **Deeper kāraka semantics** — `भाव` and `कर्मणि` voices; roles that flow through calls.
5. **Tooling** — a VS Code grammar for `.vak`, a formatter, a Devanagari output mode.

---

## अनुज्ञा · Licence

Vāk is released under the **MIT Licence** — see [LICENSE](LICENSE). You may use,
modify and redistribute it, including commercially, provided the copyright
notice travels with it.

**The name and the mark are not part of that grant.** "वाक्", "Vāk" and the वा
mark identify this project and its releases; the licence covers the software, not
the identity. This is the ordinary arrangement — Python, Rust, Linux and Firefox
all separate the two — and it exists so that nobody can publish a modified or
broken build under the name and have it taken for yours. Forks are welcome; they
should simply carry their own name.

If you use Vāk in research, [CITATION.cff](CITATION.cff) says how to cite it.

---

## संरचना · Repository layout

```
Sanskrit-Vak/
├── README.md
├── vaak.cmd / vaak.ps1          # launchers that set UTF-8 and call python -m vaak
├── vaak/
│   ├── __init__.py            # public API: run_source(), check_source(), parse(), Interpreter
│   ├── __main__.py            # python -m vaak
│   ├── cli.py                 # file runner, REPL, --tokens / --ast / --builtins
│   ├── tokens.py              # token kinds + keyword, type and numeral tables
│   ├── lexer.py               # text  → tokens
│   ├── translit.py            # romanised typing → Devanagari (a typing aid)
│   ├── ast_nodes.py           # AST node definitions
│   ├── parser.py              # tokens → AST
│   ├── analyzer.py            # AST   → diagnostics (names, types, kārakas)
│   ├── interpreter.py         # AST   → execution (the reference engine)
│   ├── opcodes.py             # the instruction set, named in Sanskrit
│   ├── compiler.py            # AST   → bytecode + disassembler
│   ├── vm.py                  # bytecode → execution (the SanskritVM)
│   ├── kosha.py               # AST and Chunk as कोशाः — the bootstrap contract
│   ├── selfhost.py            # drives the Vāk-written toolchain from Python
│   ├── native.py              # bytecode → C → a standalone executable
│   ├── environment.py         # lexical scopes + declared types
│   ├── values.py              # runtime values, type predicates, printing
│   ├── builtins.py            # standard library
│   ├── errors.py              # error types + source rendering
│   └── पुस्तकालयः/             # the standard library, written in Vāk
│       ├── गणितम्.vak          #   mathematics
│       └── शब्दाः.vak          #   strings
├── native/                    # the native runtime, in C
│   ├── vaak.h                  #   values, opcodes, compiled-program shape
│   ├── mulyani.c              #   values, UTF-8, scopes, printing
│   ├── antarnihitani.c        #   the built-ins
│   └── yantram.c              #   the VM
├── स्वयंसिद्धिः/               # the bootstrap — Vāk written in Vāk
│   ├── शब्दविभाजकः.vak        #   the lexer, in Vāk
│   ├── व्याकरणम्.vak           #   the parser, in Vāk
│   ├── अर्थविश्लेषकः.vak       #   the semantic analyser, in Vāk
│   ├── संकलकः.vak             #   the compiler, in Vāk
│   ├── यन्त्रम्.vak            #   the virtual machine, in Vāk
│   ├── वाक्.vak                #   the driver — compiled natively, this is वाक्.exe
│   └── मुख्यम्.vak             #   the whole toolchain, over its own source
├── brand/                     # the mark — वा, from real font outlines
│   ├── build_brand.py         #   shaped by HarfBuzz, emitted as SVG paths
│   └── vak-icon.svg …         #   icons, wordmark, favicon
├── vscode-vak/                # the VS Code extension
│   ├── build_extension.py     #   grammar generated from vaak/tokens.py
│   └── extension.js           #   diagnostics from the real analyser
├── docs/
│   ├── index.html             # the landing page
│   ├── build_landing.py       #   every sample is run while the page is built
│   ├── manual.html            # the whole language, one page
│   ├── build_manual.py        #   generated from the tables in vak/
│   ├── reference.py           #   library, diagnostics and flags, read from source
│   ├── playground.html        # the toolchain in WebAssembly, runs in a browser
│   ├── build_playground.py    #   emcc + the standard library, inlined
│   ├── story.html             # कथा — how the language came to be
│   └── build_story.py         #   line counts and timings read from the repo
├── examples/                  # 15 runnable .vak programs + 1 importable module
├── वाक्.exe                    # the self-hosted toolchain, built natively
└── tests/
    ├── test_vak.py            # 179 tests
    ├── विश्लेषकपरीक्षा.vak      #   the Vāk analyser, made machine-readable
    ├── दुष्टनमूनाः/            #   40 broken programs — one per diagnostic kind
    └── शुद्धनमूनाः/            #   clean programs that must produce no दोषः
```

---

*वाक् इति भाषा — यत्र संस्कृतम् एव आदेशः।*
