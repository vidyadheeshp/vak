# योगदानम् · Contributing to वाक्

Thank you for looking. Vāk is a Sanskrit-native programming language: its
keywords are Sanskrit, its type system is built from Pāṇini's kāraka roles, and
its own front end is written in Vāk. Contributions are welcome from people who
know compilers, people who know Sanskrit, and people who know neither but want
to learn — the three groups need each other here.

**You do not need to read Devanagari to contribute.** Every keyword has an ASCII
spelling, every diagnostic is bilingual, and most of the implementation is
ordinary Python and C.

## Getting set up

```bash
git clone https://github.com/vidyadheeshp/vak.git
cd vak
python -m pytest tests/ -q          # 208 tests, ~7 minutes
python -m vaak examples/01_namaste.vak
```

Requirements: **Python 3.10+** and nothing else. There are no third-party
dependencies, and adding one is a decision worth discussing in an issue first.

A clone gives you more than the published wheel does: the C runtime under
`native/`, the Vāk-written toolchain under `स्वयंसिद्धिः/`, the documentation
generators under `docs/`, and the editor extension under `vscode-vak/`. The
`--self` and `--self-vm` engines read `स्वयंसिद्धिः/*.vak` and therefore only
work from a clone.

Building the native binary additionally needs a C compiler —
[w64devkit](https://github.com/skeeto/w64devkit) on Windows, the system `gcc` or
`clang` elsewhere.

## The one rule that shapes everything

**Five engines must produce byte-identical output.**

A Vāk program can be run by the Python tree-walking interpreter, the Python
bytecode VM, the virtual machine written in Vāk, the C runtime, or the compiled
`वाक्.exe`. The test suite runs examples through all of them and compares the
bytes.

This is the project's main correctness guarantee, and it is why a language
change is more work here than in a single-implementation language. If you add an
opcode or change a semantic, you are changing it in more than one place. The
tests will tell you which places, and reviewers will help.

If that sounds like a lot: it is, and it is also why bugs in this language tend
to get caught. Start with a change that does not cross the engine boundary —
there are plenty, and they are labelled.

## Good first contributions

Look for issues labelled **`good first issue`**. Categories that reliably do not
touch all five engines:

- **Standard library functions.** `vaak/पुस्तकालयः/` holds `गणितम्` (maths) and
  `शब्दाः` (strings), written in Vāk. The library is small — 22 entries — and
  growing it is genuinely useful. Add the function, add a gloss in
  `docs/reference.py`, add a test.
- **Example programs.** `examples/` has 16. Programs that teach a concept
  clearly are worth as much as code.
- **Diagnostics.** Making an analyser message clearer, or adding a check the
  analyser does not yet make.
- **The POSIX build.** The C sources carry `VAK_POSIX` branches that are less
  exercised than the Windows ones. Building on Linux or macOS and reporting what
  breaks is a real contribution.
- **Documentation.** The manual is generated from the language's own tables by
  `docs/build_manual.py` — edit the generator, not `manual.html`.

## An open design question

If you want to think about language design rather than code, this one is
genuinely unresolved and discussion is open:

> **What kāraka role does the receiver of a method take?**
>
> Vāk has no object system yet. If it gains one, `स्वयम्` (self) has to fit into
> a system where an action already admits at most one कर्ता (agent) and one कर्म
> (patient). Is the receiver the agent? Does it consume the agent slot? Is a
> method a different kind of action from a function? Sanskrit grammar has
> opinions here, and so does type-system design, and they may not agree.

Answering this well matters more than answering it quickly.

## Making a change

1. **Open an issue first** for anything that changes the language — syntax,
   semantics, keywords, kāraka rules. For a bug fix or a library function, go
   straight to a pull request.
2. **Branch** from `main`.
3. **Add a test.** Every behaviour change needs one. The suite is a single file,
   `tests/test_vak.py`, organised by topic.
4. **Run the whole suite** before opening the PR. It takes about seven minutes.
   A change that passes in Python but diverges in the C runtime will be caught
   here rather than by a user.
5. **Regenerate the documentation** if you touched anything the manual reads
   from — keywords, built-ins, diagnostics, the standard library, CLI flags:
   ```bash
   python docs/build_manual.py     # will refuse if the reference has drifted
   ```
6. **Open the pull request**, describing what changed and why. If it is a
   language change, say what a Sanskrit reader would expect and what a
   programmer would expect, since those sometimes differ.

## House style

- **Comments explain why, not what.** The existing code is commented at the
  level of decisions and their reasons. Match that; it is the house style and it
  is deliberate.
- **Sanskrit naming.** Identifiers in the Vāk-written parts are Sanskrit.
  In the Python and C, Sanskrit names appear where they name a concept of the
  language (`कारक`, `Shabda`, `Parivesha`) and English elsewhere. When in doubt,
  match the file you are editing.
- **No new dependencies** without discussion.
- **Bilingual messages.** Every user-facing diagnostic carries both a Sanskrit
  and an English form, and a Sanskrit code.

## Reporting bugs

Open an issue with the Vāk program that misbehaves, what you expected, what
happened, your OS and Python version, and — if you can — whether the engines
disagree:

```bash
python -m vaak प्रोग्राम.vak            # tree-walking interpreter
python -m vaak --vm प्रोग्राम.vak       # bytecode VM
python -m vaak --self प्रोग्राम.vak     # the Vāk-written toolchain
```

An engine disagreement is the most valuable bug report this project can
receive. Please say so in the title.

## Security

For anything you would rather not post publicly, open a private security
advisory through GitHub rather than a public issue.

## Licence and conduct

Contributions are accepted under the [MIT Licence](LICENSE), the same terms the
project is released under. Participation is governed by the
[Code of Conduct](CODE_OF_CONDUCT.md).

## A note on claims

Vāk is not the first Sanskrit programming language —
[Vedic](https://github.com/vedic-lang/vedic) has been working since 2022, and
there are others. What is distinctive here is narrower: kāraka roles as a static
type system, and a front end written in the language itself. Please keep claims
in issues, pull requests and documentation to what can be demonstrated. Sanskrit
and computing attract a good deal of overstatement, and this project would
rather not add to it.
