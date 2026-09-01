# वाक् · Vāk for VS Code

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
  extension will use `python -m vak`.

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

Version 0.11.0. The grammar in this extension is generated from the
language's own keyword tables by `build_extension.py`, so it cannot drift.
