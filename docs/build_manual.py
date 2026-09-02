# -*- coding: utf-8 -*-
"""पुस्तिकारचना — generate docs/index.html, the Vāk manual.

The keyword table, the kāraka roles and the built-in list are read out of vak/
itself rather than retyped, so the reference cannot drift from the language.
Every code sample on the page is parsed by the real parser before it is written.

    python docs/build_manual.py
"""
import html
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import reference                                                # noqa: E402

from vak import __version__                                    # noqa: E402
from vak.builtins import BUILTIN_DOCS                          # noqa: E402
from vak.tokens import KARAKA_ORDER, KARAKA_VIBHAKTI, KEYWORDS, TYPE_NAMES  # noqa: E402

# ---------------------------------------------------------------- canon map
# Every Devanagari keyword paired with the ASCII spelling of the same word, so
# the page can show either canon.  Both come out of the lexer's own table.
ROMAN_OF: dict[str, str] = {}
_by_kind: dict[str, list[str]] = {}
for word, kind in KEYWORDS.items():
    _by_kind.setdefault(kind.name, []).append(word)
for kind, words in _by_kind.items():
    dev = [w for w in words if not w.isascii()]
    rom = [w for w in words if w.isascii()]
    if dev and rom:
        for d in dev:
            ROMAN_OF[d] = rom[0]

TYPE_ROMAN = {
    "पूर्णाङ्कः": "purnankah", "दशांशः": "dashamshah", "अङ्कः": "ankah",
    "शब्दः": "shabdah", "सत्यता": "satyata", "सूची": "suchi", "कोशः": "koshah",
    "कार्यम्": "karyam", "किमपि": "kimapi", "शून्यम्": "shunyam",
}
DIGITS = dict(zip("०१२३४५६७८९", "0123456789"))

TYPES = {t for t in TYPE_NAMES if not t.isascii()}
KEYWORD_SET = {w for w in KEYWORDS if not w.isascii()}

TOKEN = re.compile(
    r"(#[^\n]*)"                       # comment
    r'|("(?:[^"\\]|\\.)*")'            # string
    r"|([०-९0-9][०-९0-9._]*)"          # number
    r"|([^\s(){}\[\],;:।॥+\-*/%^<>=!\"#]+)"   # word
)


def highlight(source: str) -> str:
    """Vāk source as HTML: keywords carry their romanized spelling, so the
    canon switch is the same markup that does the colouring."""
    out: list[str] = []
    pos = 0
    for m in TOKEN.finditer(source):
        out.append(html.escape(source[pos:m.start()]))
        pos = m.end()
        comment, string, number, word = m.groups()
        if comment is not None:
            out.append(f'<i class="c">{html.escape(comment)}</i>')
        elif string is not None:
            out.append(f'<i class="s">{html.escape(string)}</i>')
        elif number is not None:
            roman = "".join(DIGITS.get(ch, ch) for ch in number)
            out.append(f'<i class="n" data-r="{html.escape(roman)}">'
                       f'{html.escape(number)}</i>')
        elif word is not None:
            esc = html.escape(word)
            if word in KEYWORD_SET:
                out.append(f'<b class="k" data-r="{html.escape(ROMAN_OF.get(word, word))}">'
                           f'{esc}</b>')
            elif word in TYPES:
                out.append(f'<b class="t" data-r="{html.escape(TYPE_ROMAN.get(word, word))}">'
                           f'{esc}</b>')
            elif word in KARAKA_ORDER:
                out.append(f'<b class="ka">{esc}</b>')
            else:
                out.append(esc)
    out.append(html.escape(source[pos:]))
    return "".join(out)


SAMPLES: list[str] = []


def code(source: str, caption: str = "") -> str:
    SAMPLES.append(source.strip())
    body = f'<pre><code>{highlight(source.strip())}</code></pre>'
    if caption:
        return f'<figure class="code">{body}<figcaption>{caption}</figcaption></figure>'
    return f'<figure class="code">{body}</figure>'


def shell(text: str) -> str:
    return f'<figure class="code sh"><pre><code>{html.escape(text.strip())}</code></pre></figure>'


# ------------------------------------------------------------------ sections
SECTIONS: list[tuple[str, str, str, str]] = []   # id, number, दे, English


def devanagari_number(n: int) -> str:
    return "".join("०१२३४५६७८९"[int(d)]
                   for d in str(n))


def section(sid: str, dev: str, eng: str, body: str) -> str:
    """Sections number themselves in order of appearance, so inserting one in
    the middle cannot leave the rest of the manual mislabelled."""
    num = devanagari_number(len(SECTIONS) + 1)
    SECTIONS.append((sid, num, dev, eng))
    return f"""<section id="{sid}">
  <div class="head">
    <p class="num">{num}</p>
    <h2><span class="dev">{dev}</span><span class="eng">{eng}</span></h2>
  </div>
  {body}
</section>"""


parts: list[str] = []

flag_rows = chr(10).join(
    f'    <tr><td><code>{html.escape(flag)}</code></td>'
    f'<td><code>{html.escape(alias)}</code></td>'
    f"<td>{html.escape(text)}</td></tr>"
    for flag, alias, text in reference.cli_flags())

# ------------------------------------------------------------- १ · स्थापना
parts.append(section("sthapana", "स्थापना", "Installing Vāk", f"""
<p class="lede">There is no package to install and nothing to configure. Pick
whichever of these four suits you — they run the same language.</p>

<h3 class="lib"><span class="way">१</span> The standalone binary
  <span>nothing else required</span></h3>
<p><code>वाक्.exe</code> ships in the repository. It is the whole toolchain —
lexer, parser, analyser, compiler and machine — compiled to one file, and it
needs neither Python nor anything else. Copy it where you like and run it:</p>
{shell('''वाक्.exe प्रोग्राम.vak''')}
<p>The binary in the repository is built for <b>64-bit Windows</b>. On Linux or
macOS, build your own — see <i>Building the binary</i> below; the C sources are
platform-neutral.</p>

<h3 class="lib"><span class="way">२</span> With pip, from GitHub
  <span>Python 3.10 or newer</span></h3>
<p>Vāk pulls in <b>no third-party packages</b>. A standard Python is all it
needs; it was developed on 3.13.</p>
{shell('''pip install git+https://github.com/vidyadheeshp/vak.git
vak प्रोग्राम.vak''')}
<div class="note">
  <p><b>Not on PyPI yet.</b> <code>pip install vak-lang</code> will not find
  anything — install from the repository as above. The <code>vak</code> command
  is the same either way.</p>
</div>
<p>This gives you the interpreter, the bytecode virtual machine, the native back
end, the REPL and the standard library, and the <code>vak</code> command works
from any directory.</p>

<h3 class="lib"><span class="way">३</span> From a clone
  <span>everything a wheel does not carry</span></h3>
<p>Clone it for the C runtime, the Vāk-written toolchain behind
<code>--self</code>, the documentation generators and the editor extension:</p>
{shell('''git clone https://github.com/vidyadheeshp/vak.git
cd vak
python -m vak examples/01_namaste.vak''')}
<div class="note">
  <p><b>Working from a clone, stay in the repository root.</b>
  <code>python -m vak</code> finds the package only because you are standing in
  the directory that contains it; from anywhere else you will get
  <code>No module named vak</code>. Installing with pip avoids this entirely.
  To run from elsewhere without installing, put the root on the module
  path:</p>
</div>
{shell('''# bash / zsh
PYTHONPATH=/path/to/vak python -m vak ~/प्रोग्राम.vak

# PowerShell
$env:PYTHONPATH = "C:\\path\\to\\vak"; python -m vak प्रोग्राम.vak''')}
<p>On Windows the two launchers in the repository do this and set UTF-8 for
you:</p>
{shell('''.\\vak.ps1 examples/01_namaste.vak     # PowerShell
vak.cmd examples/01_namaste.vak       # cmd.exe''')}

<h3 class="lib"><span class="way">४</span> In a browser
  <span>nothing installed at all</span></h3>
<p>The <a href="playground.html">playground</a> is this same toolchain compiled
to WebAssembly. It runs entirely in the page — there is no server, and nothing
you type leaves your machine. Use it to try the language before deciding
whether to install anything.</p>

<h3 class="lib">Checking that it works</h3>
{shell('''python -m vak --version          # वाक् (Vāk) ''' + __version__ + '''
python -m vak --builtins         # the 39 built-in functions
python -m vak                    # संवादः — the interactive session''')}
<p>Then a program of one line. Put this in <code>परीक्षा.vak</code> and run
it — if you see the greeting, everything works:</p>
{code('''मुद्रय "नमस्ते जगत्"।''')}

<h3 class="lib">A terminal that can show Devanagari</h3>
<p>Two separate things have to be right: the console must be in UTF-8, and the
font must contain Devanagari.</p>
<ul>
  <li><b>Windows.</b> The CLI reconfigures its own output, so Devanagari
  normally works in Windows Terminal. If you see boxes, the font is the
  problem, not the encoding — choose <i>Nirmala UI</i> or
  <i>Noto Sans Devanagari</i>. The older <code>conhost</code> console may also
  need <code>chcp 65001</code>.</li>
  <li><b>Linux and macOS.</b> A UTF-8 locale is the default almost everywhere;
  <code>locale</code> will confirm it. Most terminal fonts fall back to a system
  Devanagari face automatically.</li>
</ul>
<div class="note">
  <p><b>You do not have to type Devanagari at all.</b> Every keyword has an
  ASCII spelling and ASCII numerals work everywhere, so a complete Vāk program
  can be written on a plain keyboard. The switch at the top of this page shows
  any example either way.</p>
</div>

<h3 class="lib">Building the binary</h3>
<p>The native back end turns a program into C and hands it to <b>gcc</b>, so a C
compiler is the only extra requirement. On Windows,
<a href="https://github.com/skeeto/w64devkit">w64devkit</a> is the one Vāk looks
for by default; on Linux and macOS the system compiler is already there.</p>
{shell('''python -m vak --native प्रोग्राम.vak       # produce an executable
python -m vak --run-native प्रोग्राम.vak   # build it and run it''')}
<p>If no compiler is found, Vāk says so rather than failing obscurely.</p>

<h3 class="lib">The editor extension</h3>
<p>Copy the <code>vscode-vak</code> folder from the repository into your VS Code
extensions directory and reload the window:</p>
{shell('''# Windows
%USERPROFILE%\\.vscode\\extensions\\vscode-vak

# macOS and Linux
~/.vscode/extensions/vscode-vak''')}
<p>Then point it at whichever toolchain you installed — set
<code>vak.executable</code> to your <code>वाक्.exe</code>, or leave that empty
and set <code>vak.pythonPath</code> so it uses <code>python -m vak</code>. You
get highlighting, the <code>.vak</code> file icon, romanised typing that becomes
Devanagari, and the analyser's diagnostics as you save — the same ones listed in
<a href="#doshasuchi">दोषसूची</a>.</p>"""))

# ---------------------------------------------------------------- १ · running
parts.append(section("chalanam", "चालनम्", "Running Vāk", f"""
<p>Three ways to run a program, all producing identical output. The first needs
Python; the last needs nothing at all.</p>
{shell('''python -m vak प्रोग्राम.vak          # the tree-walking interpreter
python -m vak --vm प्रोग्राम.vak     # compile to bytecode, run on the SanskritVM
./वाक्.exe प्रोग्राम.vak              # the self-hosted toolchain, no Python''')}
<p>Two more you will want early — the first analyses without running, the second
starts a REPL:</p>
{shell('''./वाक्.exe --परीक्षा प्रोग्राम.vak    # report problems, run nothing
python -m vak                        # संवादः — the REPL''')}
<p>The full set of options, read from the argument parser itself. Four carry a
Sanskrit alias:</p>
<div class="scroll"><table class="kw">
  <thead><tr><th>विकल्पः</th><th>संस्कृतम्</th><th>what it does</th></tr></thead>
  <tbody>
{flag_rows}
  </tbody>
</table></div>
<div class="note">
  <p><b>An editor.</b> The <code>vscode-vak</code> extension in the repository
  gives Vāk syntax highlighting, the <code>.vak</code> file icon, romanised
  typing that becomes Devanagari as you write, and live diagnostics from the
  real analyser — the same messages listed in
  <a href="#doshasuchi">दोषसूची</a>.</p>
</div>
<div class="note">
  <p><b>Fonts.</b> No monospace coding font contains Devanagari, so an editor
  falls back to a proportional face and columns drift. Setting
  <code>editor.fontFamily</code> to a chain ending in <code>Nirmala UI</code> or
  <code>Noto Sans Devanagari</code> fixes the rendering, though nothing makes
  Devanagari truly monospaced. Installation is covered in
  <a href="#sthapana">स्थापना</a>.</p>
</div>"""))

# ---------------------------------------------------------------- २ · danda
parts.append(section("vakyani", "वाक्यानि", "Statements and the danda", f"""
<p>A statement ends with a <b>danda</b> — <code>।</code> — the full stop
Sanskrit has used since manuscripts. <code>॥</code>, the double danda, ends a
section. A semicolon means the same thing and is easier to type.</p>
{code('''मुद्रय "नमस्ते जगत्"।
मान क = ५;
मुद्रय क॥''')}
<p><code>मुद्रय</code> prints its arguments separated by a space. Comments run
from <code>#</code> to the end of the line.</p>"""))

# ---------------------------------------------------------------- ३ · चराः
parts.append(section("charah", "चराः", "Variables and numerals", f"""
<p><code>मान</code> declares a variable, <code>ध्रुव</code> a constant. A type
may be written in place of <code>मान</code>, and then it binds — the analyser
and every engine hold you to it.</p>
{code('''मान नाम = "वाक्"।
ध्रुव पाई = ३.१४१५९।
पूर्णाङ्कः वर्षम् = २०२६।
शब्दः अभिवादनम् = "नमस्ते"।

वर्षम् += १।
मुद्रय नाम, वर्षम्, पाई।''')}
<p>Devanagari and ASCII numerals are the same numbers — <code>२०२६</code> and
<code>2026</code> are one value, and you may mix them freely. Output uses
whichever form the value was written in where that is knowable, and
<code>देवनागरी()</code> converts on demand.</p>"""))

# ---------------------------------------------------------------- ४ · प्रवाहः
parts.append(section("pravahah", "प्रवाहः", "Control flow", f"""
<p><code>यदि</code> and <code>अन्यथा</code> branch. Parentheses around the
condition are optional; the braces are not.</p>
{code('''यदि (अङ्कः > १००) {
    मुद्रय "महान्"।
} अन्यथा यदि (अङ्कः > १०) {
    मुद्रय "मध्यमः"।
} अन्यथा {
    मुद्रय "अल्पः"।
}''')}
<p>Three loops, because three different things are worth saying. <code>यावत्</code>
repeats while a condition holds, <code>आवृत्तिः</code> repeats a fixed number of
times, and <code>प्रत्येकम् … अन्तः</code> walks a collection.</p>
{code('''यावत् (क < १०) { क += १। }

आवृत्तिः (३) { मुद्रय "ॐ"। }

प्रत्येकम् (अङ्कः अन्तः [१, २, ३, ४]) {
    यदि (अङ्कः == ३) { अनुवर्त। }
    मुद्रय अङ्कः।
}''')}
<p><code>विरम</code> leaves a loop, <code>अनुवर्त</code> starts its next turn.</p>

<h3>विकल्पः · Choosing among alternatives</h3>
<p>Where a chain of <code>अन्यथा यदि</code> only compares one value over and over,
<code>विकल्पः</code> says it once. The word is Pāṇini's own: a <i>vikalpa</i> is
an optional alternative in a rule. Each alternative is introduced by
<code>पक्षे</code> — the locative, “in this case” — matching
<code>दोषे</code>, the locative Vāk already uses for catch.</p>
{code('''कार्यम् वासरनाम(कर्म पूर्णाङ्कः वारः) : शब्दः {
    विकल्पः (वारः) {
        पक्षे १: प्रत्यागच्छ "सोमवासरः"।
        पक्षे २, ३: प्रत्यागच्छ "मङ्गलः बुधः वा"।
        पक्षे ६, ७: प्रत्यागच्छ "सप्ताहान्तः"।
        अन्यथा: प्रत्यागच्छ "अज्ञातः"।
    }
}''')}
<p>One <code>पक्षे</code> may carry several values, separated by commas.
<code>अन्यथा</code> is the fallback, and it is the fallback wherever it is
written. The subject is evaluated once.</p>
<div class="note">
  <p><b>पक्षाः do not fall through.</b> The alternative that matches is the only
  one that runs, so nothing has to be written to stop it. That frees
  <code>विरम</code> to keep its ordinary meaning: inside a विकल्पः it leaves the
  <em>enclosing loop</em>, not the विकल्पः — and outside a loop it is an error,
  exactly as it always was.</p>
  <p>The analyser reports a पक्षः whose type could never match the subject, and
  a value given twice — neither could ever run. A विकल्पः without an
  <code>अन्यथा</code> is only advice, not an error, but it does mean an
  unmatched subject does nothing at all.</p>
</div>
<p>A विकल्पः also counts as returning on every path, so long as it has an
<code>अन्यथा</code> and every पक्षः returns — which is why the function above
needs no closing <code>प्रत्यागच्छ</code>.</p>"""))

# ---------------------------------------------------------------- ५ · कार्याणि
parts.append(section("karyani", "कार्याणि", "Functions", f"""
<p><code>कार्यम्</code> defines a function. A return type after the colon is
optional and binding. Functions are values: pass them, return them, close over
their surroundings.</p>
{code('''कार्यम् क्षेत्रफलम्(पूर्णाङ्कः दैर्घ्यम्, पूर्णाङ्कः विस्तारः) : पूर्णाङ्कः {
    प्रत्यागच्छ दैर्घ्यम् * विस्तारः।
}

कार्यम् योजकः(आधारः) : कार्यम् {
    प्रत्यागच्छ कार्यम्(क) : पूर्णाङ्कः { प्रत्यागच्छ आधारः + क। }।
}

मान दश = योजकः(१०)।
मुद्रय क्षेत्रफलम्(६, ७), दश(५)।''')}
<p>Functions are hoisted: a function may call one defined later in the same
block.</p>"""))

# ---------------------------------------------------------------- ६ · संग्रहाः
parts.append(section("sangrahah", "संग्रहाः", "Lists and dictionaries", f"""
<p><code>सूची</code> is an ordered list, <code>कोशः</code> a dictionary —
literally a <i>treasury</i>, the word Sanskrit uses for a lexicon. Negative
indices count from the end.</p>
{code('''मान अङ्काः = [१, २, ३, ४, ५]।
मुद्रय अङ्काः[०], अङ्काः[-१], दीर्घता(अङ्काः)।
योजय(अङ्काः, ६)।

मान छात्रः = { "नाम": "रामः", "वयः": २० }।
मुद्रय छात्रः.नाम, छात्रः["वयः"]।
छात्रः.नगरम् = "काशी"।''')}
<p>A dictionary key may be reached with a dot or with brackets; the dot form is
the same lookup written more quietly.</p>"""))

# ---------------------------------------------------------------- ७ · प्रकाराः
type_rows = "\n".join(
    f'    <tr><td><code class="ty" data-r="{html.escape(TYPE_ROMAN.get(t, t))}">{t}</code></td>'
    f"<td>{d}</td></tr>"
    for t, d in [
        ("पूर्णाङ्कः", "whole number — <i>pūrṇāṅkaḥ</i>, “complete-numbered”"),
        ("दशांशः", "a number with a fractional part — <i>daśāṃśaḥ</i>, “tenth-part”"),
        ("अङ्कः", "either kind of number"),
        ("शब्दः", "text — <i>śabdaḥ</i>, the word for <i>word</i>"),
        ("सत्यता", "truth — <code>सत्य</code> or <code>असत्य</code>"),
        ("सूची", "a list"),
        ("कोशः", "a dictionary"),
        ("कार्यम्", "a function"),
        ("किमपि", "anything at all — <i>kimapi</i>, “whatever”"),
        ("शून्यम्", "nothing — <i>śūnyam</i>, the zero India gave the world"),
    ])
parts.append(section("prakarah", "प्रकाराः", "Types", f"""
<p>Typing is gradual. Write no type and nothing is checked; write one and it is
enforced everywhere — at declaration, at assignment, at every call, and on the
way out of a function. <code>किमपि</code> flows both ways, so only a provable
mismatch is an error.</p>
<div class="scroll"><table>
  <thead><tr><th>प्रकारः</th><th>what it holds</th></tr></thead>
  <tbody>
{type_rows}
  </tbody>
</table></div>
{code('''पूर्णाङ्कः आयुः = २५।
आयुः = "पञ्चविंशतिः"।   # प्रकारदोषः — शब्दः दीयते, पूर्णाङ्कः अपेक्षितः''',
      "The analyser reports this before the program runs.")}"""))

# ---------------------------------------------------------------- ८ · कारकाणि
karaka_rows = "\n".join(
    f'    <tr><td><code class="ka">{role}</code></td><td>{html.escape(desc)}</td></tr>'
    for role, desc in [(r, KARAKA_VIBHAKTI[r]) for r in KARAKA_ORDER])
parts.append(section("karakani", "कारकाणि", "Kāraka roles", f"""
<p class="lede">This is the part of Vāk that exists nowhere else.</p>
<p>Pāṇini analysed a sentence not by word order but by <b>kāraka</b> — the role
each participant plays in the action. Vāk lets a parameter declare its role, and
then checks the grammar of your function the way Pāṇini checked the grammar of a
sentence.</p>
<div class="scroll"><table>
  <thead><tr><th>कारकम्</th><th>विभक्तिः · what the role means</th></tr></thead>
  <tbody>
{karaka_rows}
  </tbody>
</table></div>
{code('''कार्यम् छानय(अपादानम् सूची संग्रहः, करणम् कार्यम् परीक्षा) : सूची {
    सूची फलम् = []।
    प्रत्येकम् (अङ्गम् अन्तः संग्रहः) {
        यदि (परीक्षा(अङ्गम्)) { योजय(फलम्, अङ्गम्)। }
    }
    प्रत्यागच्छ फलम्।
}''', "The collection is what we draw <i>from</i>; the test is the means <i>by which</i>.")}
<p>Because the roles are marked, the arguments carry their own labels and the
order stops mattering — exactly the freedom case marking gives a Sanskrit
sentence. All three of these calls are the same call:</p>
{code('''छानय(अङ्काः, समः)।
छानय(अपादानम्: अङ्काः, करणम्: समः)।
छानय(करणम्: समः, अपादानम्: अङ्काः)।''')}
<div class="note">
  <p><b>What gets checked.</b> Pāṇini's rule that an action has one agent and one
  patient is enforced: two <code>कर्ता</code> parameters, or two
  <code>कर्म</code>, is an error. A label that names no declared role is an
  error, and so is giving the same role twice. Word order is deliberately
  <em>not</em> enforced — that is the whole point of marking the roles.</p>
  <p>Softer observations come back as सूचनाः rather than errors: a
  <code>करणम्</code> that is not a means, an <code>अपादानम्</code> that is not a
  collection, a function with a <code>कर्म</code> that returns nothing.</p>
</div>"""))

# ---------------------------------------------------------------- ९ · analyser
parts.append(section("vishleshakah", "अर्थविश्लेषकः", "The semantic analyser", f"""
<p>Before anything runs, the analyser walks the syntax tree and reports what it
can prove wrong: undefined names, type mismatches, assignments to constants,
wrong argument counts, <code>विरम</code> outside a loop, kāraka violations,
unreachable code, a declared return type some path does not satisfy.</p>
{shell('''$ ./वाक्.exe --परीक्षा प्रोग्राम.vak
अर्थदोषः (Semantic Analysis) — 2 दोषाः, 0 सूचनाः
  दोषः [ध्रुवदोषः] प्रोग्राम.vak:6 — ध्रुवः 'सीमा' न परिवर्तनीयः / cannot reassign the constant 'सीमा'
         6 | सीमा = ११।
  दोषः [नामदोषः] प्रोग्राम.vak:7 — अपरिभाषितम् नाम 'अज्ञातम्' / undefined name 'अज्ञातम्'
         7 | मुद्रय बाह्यम्(), अज्ञातम्।''')}
<p>Every message is bilingual, and every diagnostic carries a Sanskrit code —
<code>नामदोषः</code>, <code>प्रकारदोषः</code>, <code>कारकदोषः</code>,
<code>ध्रुवदोषः</code>, <code>प्राचलदोषः</code>, <code>प्रवाहदोषः</code>. Errors
stop the program; सूचनाः are advice and do not.</p>
<p>The analyser exists twice: once in Python and once
<a href="#yantram">written in Vāk itself</a>. The two are compared on sixty-five
files — every example, the standard library, forty deliberately broken programs,
and the toolchain's own source — and must produce identical diagnostics, in the
same order, with the same wording.</p>"""))

# ---------------------------------------------------------------- १० · दोषाः
parts.append(section("doshah", "दोषनिग्रहः", "Exceptions", f"""
<p><code>प्रयत्नः</code> is the attempt, <code>दोषे</code> the locative — “in
the event of an error” — and <code>अन्ततः</code> what happens at the end
regardless. <code>उत्सृज</code> throws.</p>
{code('''प्रयत्नः {
    यदि (हरः == ०) {
        उत्सृज { "प्रकारः": "गणितदोषः", "सन्देशः": "शून्येन भागः" }।
    }
    मुद्रय अंशः / हरः।
} दोषे (द) {
    मुद्रय "दोषः प्राप्तः:", द.प्रकारः, "—", द.सन्देशः।
} अन्ततः {
    मुद्रय "समाप्तम्"।
}''')}
<p>The caught value is an ordinary <code>कोशः</code> carrying at least
<code>प्रकारः</code> and <code>सन्देशः</code>. Runtime failures from the
language itself arrive in the same shape, so one handler catches both.</p>"""))

# ------------------------------------------------------------ प्रदानम्
parts.append(section("pradanam", "प्रदानम्", "Reading from the user", f"""
<p><code>पठ</code> reads one line from the user and hands it back as a
<code>शब्दः</code>. Give it an argument and that is printed first, as a
prompt.</p>
{code('''शब्दः नाम = पठ("नाम किम्? ")।
मुद्रय "नमस्ते,", नाम + "!"।

पूर्णाङ्कः वयः = संख्या(पठ("वयः? "))।
मुद्रय "आगामिवर्षे भवतः वयः", वयः + १, "भविष्यति।"।''',
      "संख्या turns the line into a number — and it reads Devanagari numerals, "
      "so the user may type ३८ or 38.")}
<p>What comes back is always text, even when it looks like a number, so wrap it
in <code>संख्या</code> when you want arithmetic. A line that cannot be read as a
number raises a catchable <code>कार्यकालदोषः</code>:</p>
{code('''प्रयत्नः {
    पूर्णाङ्कः क = संख्या(पठ("अङ्कम् लिखतु: "))।
    मुद्रय "वर्गः:", क * क।
} दोषे (द) {
    मुद्रय "सः अङ्कः न आसीत् —", द.सन्देशः।
}''')}
<div class="note">
  <p><b>At the end of input</b> <code>पठ</code> returns the empty string rather
  than failing, in every engine. So a program that reads until there is nothing
  left tests for it:</p>
  <p><code>यावत् (सत्य) {{ शब्दः पं = पठ()। यदि (दीर्घता(पं) == ०) {{ विरम। }} … }}</code></p>
  <p>That does mean an empty line and the end of input look alike. If you need
  to tell them apart, read the whole of standard input another way.</p>
</div>
<p>In the <a href="playground.html">playground</a> there is no terminal to type
into, so the box under the editor is what <code>पठ</code> reads — one line per
call.</p>"""))

# ---------------------------------------------------------------- १२ · आनय
parts.append(section("anaya", "आनय", "Modules and files", f"""
<p><code>आनय</code> — <i>bring</i> — imports. A module is any
<code>.vak</code> file; whatever it declares at the top level is what it
exports.</p>
{code('''आनय "गणितम्"।                       # गणितम्.वर्गः(...)
आनय "गणितम्" इति ग।                  # ग.वर्गः(...)
आनय "गणितम्" तः वर्गः, क्रमगुणितम्।   # वर्गः(...)''')}
<p>Modules run once and are cached; a circular import is reported rather than
hung on. Files are read and written with the built-ins:</p>
{code('''शब्दः विषयम् = सञ्चिकापठ("काव्यम्.txt")।
सञ्चिकालिख("फलम्.txt", विषयम्)।
यदि (सञ्चिकास्ति("फलम्.txt")) { मुद्रय निर्देशिका(".")। }''')}"""))


# ------------------------------------------------------------ १३ · पुस्तकालयः
# Signatures come from parsing the modules with the real parser; the glosses
# live in docs/reference.py, which fails the build if the two fall out of step.
lib_parts = []
for _mod, _blurb, _entries in reference.library():
    _rows = chr(10).join(
        f'    <tr><td><code>{html.escape(sig)}</code></td>'
        f'<td>{html.escape(gloss)}</td></tr>'
        for _kind, sig, gloss in _entries)
    lib_parts.append(f"""
<h3 class="lib"><code>आनय "{_mod}"।</code> <span>{html.escape(_blurb)}</span></h3>
<div class="scroll"><table class="kw">
  <thead><tr><th>{_mod}</th><th>what it does</th></tr></thead>
  <tbody>
{_rows}
  </tbody>
</table></div>""")

parts.append(section("pustakalayah", "पुस्तकालयः", "The standard library", f"""
<p>Two modules ship with Vāk, and both are <b>written in Vāk</b> — they are
ordinary <code>.vak</code> files you can read, and a fair sample of what the
language looks like in use. Bring one in with <code>आनय</code>:</p>
{code('''आनय "गणितम्"।
मुद्रय गणितम्.क्रमगुणितम्(५)।        # १२०

आनय "शब्दाः" तः विलोमः_वा।
मुद्रय विलोमः_वा("नयन")।            # सत्य''')}
<p>Every signature below is printed from the module's own source, so it is
exactly what the file declares — including the kāraka role each parameter
takes.</p>
{"".join(lib_parts)}"""))

# ---------------------------------------------------------------- १४ · यन्त्रम्
parts.append(section("yantram", "यन्त्रम्", "How Vāk runs", f"""
<p class="lede">The point of the project is a language that does not depend on a
host language.</p>
<p>A Vāk program can be executed by any of five engines, and all five are held to
byte-identical output on every example:</p>
<ol class="engines">
  <li><b>The tree-walking interpreter</b>, in Python — the reference, the
  definition of what a program means.</li>
  <li><b>The SanskritVM</b>, in Python — a stack machine over bytecode whose
  every instruction has a Sanskrit name.</li>
  <li><b>The SanskritVM written in Vāk</b> — the machine's semantics, expressed
  in the language it runs.</li>
  <li><b>The SanskritVM in C</b> — the native runtime, ~2,600 lines.</li>
  <li><b>वाक्.exe</b> — the whole Vāk-written toolchain compiled natively. No
  Python anywhere.</li>
</ol>
<p>The front end is <b>entirely self-hosted</b>. Lexer, parser, analyser,
compiler and virtual machine all exist written in Vāk, and each is checked
against its Python counterpart at the finest granularity that stage allows —
the lexer on every token's kind, lexeme, value and line; the parser on the whole
syntax tree node for node; the analyser on every diagnostic's code, line and
wording; the compiler on every instruction, constant and line number.</p>
{shell('''python -m vak --self प्रोग्राम.vak      # compiled by Vāk, run on the Python VM
python -m vak --self-vm प्रोग्राम.vak   # lexed, parsed, compiled AND run by Vāk
python -m vak --native प्रोग्राम.vak    # a standalone executable (needs gcc)
python -m vak --bytecode प्रोग्राम.vak  # disassemble''')}
<p>Python is used to build <code>वाक्.exe</code> once, exactly as a C compiler is
used once to build a self-hosting C compiler. After that the language stands on
its own.</p>
<div class="note">
  <p><b>Where it runs.</b> The Python implementation is portable as it stands.
  The native runtime is C11; the few places that need the operating system —
  the command line, opening a file by a Devanagari path, listing a directory —
  have both a Windows branch and a POSIX one, chosen by a single switch that
  every file shares. Building with <code>VAK_POSIX=1</code> forces the POSIX
  branch, so the code Linux and macOS will run can be exercised anywhere.</p>
  <p>And it runs in a browser: the same C machine, compiled to WebAssembly, is
  what the <a href="playground.html">playground</a> executes. Nothing is sent
  anywhere — the lexer, parser, analyser, compiler and VM are all in the page.</p>
</div>"""))

# ---------------------------------------------------------------- १३ · keywords
ORDER = [
    ("LET", "declare a variable"), ("CONST", "declare a constant"),
    ("FUNC", "define a function"), ("RETURN", "return from a function"),
    ("PRINT", "print"), ("IF", "if"), ("ELSE", "else"), ("WHILE", "while"),
    ("REPEAT", "repeat a fixed number of times"), ("FOR", "for each"),
    ("SWITCH", "choose among alternatives"), ("CASE", "in this case"),
    ("IN", "of the collection"), ("BREAK", "leave the loop"),
    ("CONTINUE", "next turn of the loop"), ("TRY", "attempt"),
    ("CATCH", "in the event of an error"), ("FINALLY", "at the end, regardless"),
    ("THROW", "throw"), ("IMPORT", "import"), ("AS", "under the name"),
    ("FROM", "taking from"), ("TRUE", "true"), ("FALSE", "false"),
    ("NULL", "nothing"), ("AND", "and"), ("OR", "or"), ("NOT", "not"),
]
# Some constructs accept two Devanagari words — दोषे and गृहाण are one and the
# same token.  Worth counting, because the table shows them side by side and a
# reader has no other way to tell a synonym from a different keyword.
SYNONYMS = sum(
    1 for _kind, _words in _by_kind.items()
    if len([w for w in _words
            if not w.isascii()
            and not any(c in w for c in "āīūṛṇṣśḥṭḍñṅ")]) > 1)

kw_rows = []
for kind, gloss in ORDER:
    words = _by_kind.get(kind, [])
    dev = [w for w in words if not w.isascii() and not any(c in w for c in "āīūṛṇṣśḥṭḍñṅ")]
    iast = [w for w in words if not w.isascii() and any(c in w for c in "āīūṛṇṣśḥṭḍñṅ")]
    rom = [w for w in words if w.isascii()]
    kw_rows.append(
        f'    <tr><td><code>{" · ".join(dev) or "—"}</code></td>'
        f'<td class="iast">{" · ".join(iast + rom) or "—"}</td>'
        f"<td>{gloss}</td></tr>")
# ------------------------------------------------------------- १५ · दोषसूची
_diag_rows = chr(10).join(
    f'    <tr><td><code>{html.escape(codeword)}</code></td>'
    f'<td class="iast">{kind}</td><td>{html.escape(what)}</td></tr>'
    for codeword, kind, what in reference.diagnostics())
_kind_rows = chr(10).join(
    f'    <tr><td><code>{html.escape(codeword)}</code></td>'
    f'<td>{html.escape(english)}</td></tr>'
    for codeword, english in reference.error_kinds())
_errors = sum(1 for _, k, _ in reference.diagnostics() if k == "दोषः")
_warns = len(reference.diagnostics()) - _errors

parts.append(section("doshasuchi", "दोषसूची", "Every diagnostic", f"""
<p>The analyser reports {_errors} kinds of error and {_warns} kinds of warning.
A <b>दोषः</b> stops the program from running; a <b>सूचना</b> is printed and the
program runs anyway. Every one carries its Sanskrit name, so a message can be
looked up here.</p>
<div class="scroll"><table class="kw">
  <thead><tr><th>सङ्केतः</th><th>kind</th><th>what it means</th></tr></thead>
  <tbody>
{_diag_rows}
  </tbody>
</table></div>
<p>Separately, an error caught by <code>दोषे</code> carries its kind in
<code>प्रकारः</code>. These are the {len(reference.error_kinds())} values it can
hold:</p>
<div class="scroll"><table class="kw">
  <thead><tr><th>प्रकारः</th><th>raised by</th></tr></thead>
  <tbody>
{_kind_rows}
  </tbody>
</table></div>
{code('''प्रयत्नः {
    मुद्रय संख्या("न अङ्कः")।
} दोषे (त्रुटिः) {
    यदि (त्रुटिः.प्रकारः == "कार्यकालदोषः") {
        मुद्रय "गणने दोषः / a runtime error"।
    }
}''')}"""))

parts.append(section("padakoshah", "पदकोशः", "Every keyword", f"""
<p>Each keyword may be written in Devanagari, in IAST transliteration, or in
plain ASCII. They are the same word — the lexer holds all three spellings, so
{len(ORDER)} keywords are what there is to learn.</p>
<p>Where a cell lists two Devanagari words joined by <code>·</code>, they are
<b>synonyms for the identical token</b>, not different keywords:
<code>दोषे</code> and <code>गृहाण</code> both begin a catch block. {SYNONYMS}
constructs have such a pair.</p>
<div class="scroll"><table class="kw">
  <thead><tr><th>देवनागरी</th><th>IAST · ASCII</th><th>meaning</th></tr></thead>
  <tbody>
{chr(10).join(kw_rows)}
  </tbody>
</table></div>"""))

# ---------------------------------------------------------------- १४ · builtins
bi_rows = "\n".join(
    f'    <tr><td><code>{html.escape(dev)}</code></td>'
    f'<td class="iast">{html.escape(iast)}</td>'
    f"<td>{html.escape(doc)}</td></tr>"
    for dev, iast, doc in BUILTIN_DOCS)
parts.append(section("antarnihitani", "अन्तर्निहितानि",
                     f"The {len(BUILTIN_DOCS)} built-ins", f"""
<p>Available everywhere without an import. Two more —
<code>गणितम्</code> and <code>शब्दाः</code> — are libraries written in Vāk and
brought in with <code>आनय</code>.</p>
<div class="scroll"><table class="kw">
  <thead><tr><th>नाम</th><th>roman</th><th>what it does</th></tr></thead>
  <tbody>
{bi_rows}
  </tbody>
</table></div>"""))

# The reference tables are only worth having if they cannot fall behind the
# language, so a mismatch stops the build instead of shipping quietly.
_drift = reference.check()
if _drift:
    for _line in _drift:
        print(f"  !! {_line}")
    raise SystemExit("reference has drifted from the source; manual not written")

# ------------------------------------------------------------------- assemble
nav = "\n".join(
    f'      <li><a href="#{sid}"><span class="n">{num}</span>'
    f'<span class="d">{dev}</span><span class="e">{eng}</span></a></li>'
    for sid, num, dev, eng in SECTIONS)

HERO_CODE = code('''# कारकाणि — a parameter declares the role it plays in the action
कार्यम् छानय(अपादानम् सूची संग्रहः, करणम् कार्यम् परीक्षा) : सूची {
    सूची फलम् = []।
    प्रत्येकम् (अङ्गम् अन्तः संग्रहः) {
        यदि (परीक्षा(अङ्गम्)) { योजय(फलम्, अङ्गम्)। }
    }
    प्रत्यागच्छ फलम्।
}

मुद्रय छानय(करणम्: समः, अपादानम्: [१, २, ३, ४, ५, ६])।''')

DOC = f"""<title>वाक् · Vāk — a Sanskrit-native programming language</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="favicon.ico" sizes="any">
<style>
:root {{
  /* मसी — manuscript ink, paper, and haritāla: the orpiment yellow Indian
     manuscripts used for headings and for painting over mistakes. */
  --ink:      #16223f;
  --ink-soft: #4a5570;
  --ink-faint:#7c8499;
  --paper:    #f7f6f1;
  --paper-2:  #eeece4;
  --rule:     #cfcdc2;
  --gold:     #a8781f;
  --gold-lit: #f0e4c4;
  --indigo:   #37508c;
  --crimson:  #9a3324;
  --shadow:   rgba(22,34,63,.07);
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --ink:      #e6e3d9;
    --ink-soft: #a9aec0;
    --ink-faint:#767d92;
    --paper:    #10141f;
    --paper-2:  #171c2b;
    --rule:     #2c3346;
    --gold:     #d8a94a;
    --gold-lit: #2a2415;
    --indigo:   #8aa2df;
    --crimson:  #e0806e;
    --shadow:   rgba(0,0,0,.4);
  }}
}}
:root[data-theme="light"] {{
  --ink:#16223f; --ink-soft:#4a5570; --ink-faint:#7c8499; --paper:#f7f6f1;
  --paper-2:#eeece4; --rule:#cfcdc2; --gold:#a8781f; --gold-lit:#f0e4c4;
  --indigo:#37508c; --crimson:#9a3324; --shadow:rgba(22,34,63,.07);
}}
:root[data-theme="dark"] {{
  --ink:#e6e3d9; --ink-soft:#a9aec0; --ink-faint:#767d92; --paper:#10141f;
  --paper-2:#171c2b; --rule:#2c3346; --gold:#d8a94a; --gold-lit:#2a2415;
  --indigo:#8aa2df; --crimson:#e0806e; --shadow:rgba(0,0,0,.4);
}}

/* देवनागरी must be named in every stack: no Latin face contains it, and a
   silent fallback is what breaks pages like this one. */
html {{
  --serif: "Iowan Old Style", "Palatino Linotype", Palatino, "Book Antiqua",
           Georgia, "Nirmala UI", "Noto Serif Devanagari", serif;
  --sans:  "Segoe UI", -apple-system, "Helvetica Neue", Arial,
           "Nirmala UI", "Noto Sans Devanagari", sans-serif;
  --mono:  "Cascadia Mono", Consolas, "SF Mono", Menlo, "DejaVu Sans Mono",
           "Nirmala UI", "Noto Sans Devanagari", monospace;
  box-sizing: border-box;
  -webkit-text-size-adjust: 100%;
}}
*, *::before, *::after {{ box-sizing: inherit; }}

body {{
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: var(--serif);
  font-size: 17px;
  line-height: 1.66;
}}

/* ------------------------------------------------------------ shirorekha
   Devanagari hangs its letters from a head-line. So does every heading here. */
.head {{
  border-top: 1.5px solid var(--ink);
  padding-top: .5rem;
  margin: 4.5rem 0 1.5rem;
  display: flex;
  align-items: baseline;
  gap: 1rem;
  flex-wrap: wrap;
}}
.head .num {{
  margin: 0;
  font-family: var(--serif);
  font-size: .95rem;
  color: var(--gold);
  min-width: 1.6rem;
}}
.head h2 {{
  margin: 0;
  font-weight: 500;
  font-size: clamp(1.5rem, 1.1rem + 1.6vw, 2.1rem);
  line-height: 1.2;
  text-wrap: balance;
  display: flex;
  align-items: baseline;
  gap: .75rem;
  flex-wrap: wrap;
}}
.head h2 .eng {{
  font-family: var(--sans);
  font-size: .72em;
  font-weight: 400;
  color: var(--ink-soft);
  letter-spacing: .01em;
}}

/* ------------------------------------------------------------------ shell */
.wrap {{ display: grid; grid-template-columns: 16.5rem minmax(0,1fr); gap: 3.5rem;
        max-width: 74rem; margin: 0 auto; padding: 0 clamp(1.1rem,3vw,2.5rem); }}
main {{ min-width: 0; padding-bottom: 8rem; }}
section {{ scroll-margin-top: 1.5rem; }}
p, li {{ max-width: 40em; }}

/* ------------------------------------------------------------------- nav */
.rail {{ position: sticky; top: 0; align-self: start; height: 100vh;
         overflow-y: auto; padding: 2.5rem 0 3rem;
         border-right: 1px solid var(--rule); }}
.rail .mark {{ margin: 0 0 .15rem; font-size: 2.6rem; line-height: 1;
               letter-spacing: -.01em; }}
.rail .sub {{ margin: 0 0 .35rem; font-family: var(--sans); font-size: .78rem;
              letter-spacing: .11em; text-transform: uppercase;
              color: var(--ink-faint); }}
.rail .ver {{ margin: 0 0 .5rem; font-family: var(--mono); font-size: .74rem;
              color: var(--gold); }}
.rail .play {{ margin: 0 0 1.5rem; font-family: var(--sans); font-size: .78rem;
               line-height: 1.35; }}
.rail ol {{ list-style: none; margin: 0; padding: 0;
            display: flex; flex-direction: column; gap: .1rem; }}
.rail a {{ display: grid; grid-template-columns: 1.5rem 1fr; align-items: baseline;
           gap: .1rem .5rem; padding: .3rem .5rem .3rem .1rem;
           text-decoration: none; color: var(--ink-soft); border-radius: 2px; }}
.rail a .n {{ font-size: .8rem; color: var(--ink-faint); }}
.rail a .d {{ font-size: .95rem; color: var(--ink); }}
.rail a .e {{ grid-column: 2; font-family: var(--sans); font-size: .72rem;
              color: var(--ink-faint); line-height: 1.3; }}
.rail a:hover, .rail a:focus-visible {{ background: var(--paper-2); }}
.rail a:hover .d, .rail a:focus-visible .d {{ color: var(--gold); }}
.rail a.on {{ background: var(--gold-lit); }}
.rail a.on .d {{ color: var(--gold); }}

/* -------------------------------------------------------------- controls */
.controls {{ display: flex; gap: .4rem; flex-wrap: wrap; margin: 1.7rem 0 0; }}
button {{ font: inherit; font-family: var(--sans); font-size: .74rem;
          letter-spacing: .04em; color: var(--ink-soft); cursor: pointer;
          background: transparent; border: 1px solid var(--rule);
          border-radius: 2px; padding: .32rem .6rem; }}
button:hover, button:focus-visible {{ border-color: var(--gold); color: var(--gold); }}
button[aria-pressed="true"] {{ background: var(--gold-lit); border-color: var(--gold);
                               color: var(--gold); }}

/* ------------------------------------------------------------------ hero */
.hero {{ padding: 4.5rem 0 0; }}
.hero .lead {{ font-size: clamp(1.35rem, 1.05rem + 1.2vw, 1.85rem); line-height: 1.42;
               margin: 0 0 1.1rem; max-width: 22em; text-wrap: balance;
               font-weight: 400; }}
.hero .lead em {{ font-style: normal; color: var(--gold); }}
.hero p.sub {{ color: var(--ink-soft); max-width: 38em; }}
.danda {{ color: var(--gold); }}

/* ------------------------------------------------------------------ code */
figure.code {{ margin: 1.5rem 0; }}
figure.code pre {{ margin: 0; overflow-x: auto; background: var(--paper-2);
                   border: 1px solid var(--rule); border-radius: 3px;
                   padding: .95rem 1.1rem; }}
figure.code code {{ font-family: var(--mono); font-size: .855rem; line-height: 1.75;
                    white-space: pre; }}
figure.code figcaption {{ margin-top: .5rem; font-family: var(--sans);
                          font-size: .76rem; color: var(--ink-faint);
                          max-width: 40em; }}
figure.sh pre {{ background: transparent; border-style: dashed; }}
code {{ font-family: var(--mono); font-size: .875em;
        background: var(--paper-2); padding: .06em .32em; border-radius: 2px; }}
figure.code code {{ background: none; padding: 0; }}
.k {{ color: var(--gold); font-weight: 600; font-style: normal; }}
.t {{ color: var(--indigo); font-weight: 600; font-style: normal; }}
.ka {{ color: var(--crimson); font-weight: 600; font-style: normal;
       border-bottom: 1.5px solid currentColor; }}
.s {{ color: var(--indigo); font-style: normal; }}
.n {{ font-style: normal; }}
.c {{ color: var(--ink-faint); font-style: italic; }}

/* ----------------------------------------------------------------- tables */
.scroll {{ overflow-x: auto; margin: 1.4rem 0; }}
table {{ border-collapse: collapse; width: 100%; font-size: .93rem; }}
th, td {{ text-align: left; padding: .45rem .8rem .45rem 0;
          border-bottom: 1px solid var(--rule); vertical-align: baseline; }}
th {{ font-family: var(--sans); font-size: .72rem; letter-spacing: .09em;
      text-transform: uppercase; color: var(--ink-faint); font-weight: 500;
      border-bottom-color: var(--ink); }}
td .iast, td.iast {{ font-family: var(--mono); font-size: .82rem;
                     color: var(--ink-soft); }}
table.kw td:first-child {{ white-space: nowrap; }}
/* the library tables carry full signatures, which are long — let them wrap */
#pustakalayah table.kw td:first-child {{ white-space: normal; }}
#pustakalayah table.kw td:first-child code {{ white-space: normal;
  word-break: break-word; }}

/* one sub-heading per library module, reading as the आनय line that loads it */
h3.lib {{ margin: 2.2rem 0 .2rem; font-size: 1.02rem; font-weight: 500;
  display: flex; gap: .8rem; align-items: baseline; flex-wrap: wrap;
  padding-bottom: .5rem; border-bottom: 1px solid var(--rule); }}
h3.lib span {{ font-family: var(--sans); font-size: .78rem; font-weight: 400;
  color: var(--ink-faint); }}
/* the three installation routes are numbered because they are alternatives,
   not steps — the badge says "pick one", the ordering says nothing else */
h3.lib span.way {{ display: inline-flex; align-items: center;
  justify-content: center; width: 1.55rem; height: 1.55rem; flex: none;
  border-radius: 50%; background: var(--gold); color: var(--paper);
  font-family: var(--serif); font-size: .82rem; }}

/* ------------------------------------------------------------------ notes */
.note {{ margin: 1.6rem 0; padding: .1rem 0 .1rem 1.1rem;
         border-left: 2px solid var(--gold); }}
.note p {{ font-size: .93rem; color: var(--ink-soft); }}
.note p:first-child {{ margin-top: .6rem; }}
.note p:last-child {{ margin-bottom: .6rem; }}
.note b {{ color: var(--ink); }}
p.lede {{ font-size: 1.12rem; color: var(--gold); max-width: 32em; }}
ol.engines {{ padding-left: 1.2rem; }}
ol.engines li {{ margin-bottom: .5rem; }}
ol.engines b {{ font-weight: 600; }}
a {{ color: var(--gold); text-underline-offset: .18em; }}

footer {{ border-top: 1.5px solid var(--ink); margin-top: 5rem; padding-top: 1rem;
          font-family: var(--sans); font-size: .78rem; color: var(--ink-faint);
          display: flex; justify-content: space-between; gap: 1rem;
          flex-wrap: wrap; }}
footer .verse {{ font-family: var(--serif); font-size: .95rem; color: var(--ink-soft); }}

/* ----------------------------------------------------------------- narrow */
.railtop {{ display: none; }}
@media (max-width: 62rem) {{
  .wrap {{ grid-template-columns: 1fr; gap: 0; }}
  .rail {{ position: static; height: auto; border-right: 0;
           border-bottom: 1px solid var(--rule); padding: 2rem 0 1.5rem; }}
  .rail ol {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(11rem,1fr));
              gap: 0 .5rem; }}
  .rail a .e {{ display: none; }}
  .hero {{ padding-top: 2.5rem; }}
  .head {{ margin-top: 3.25rem; }}
}}
@media (prefers-reduced-motion: reduce) {{
  * {{ animation: none !important; transition: none !important; scroll-behavior: auto !important; }}
}}
</style>

<div class="wrap">
<nav class="rail" aria-label="Contents">
  <p class="mark">वाक्</p>
  <p class="sub">Vāk · a manual</p>
  <p class="ver">{__version__}</p>
  <p class="play"><a href="playground.html">क्रीडाक्षेत्रम् · try it in the browser →</a></p>
  <p class="play"><a href="story.html">कथा · how it was built →</a></p>
  <ol>
{nav}
  </ol>
  <div class="controls">
    <button id="canon" aria-pressed="false">देवनागरी → roman</button>
    <button id="theme">theme</button>
  </div>
</nav>

<main>
  <header class="hero">
    <p class="lead">A programming language whose keywords, whose type system,
    and whose <em>own compiler</em> are written in Sanskrit<span class="danda">।</span></p>
    <p class="sub">Vāk takes Pāṇini's analysis of a sentence — that meaning comes
    from the <b>role</b> each participant plays, not from where it sits — and
    makes it a type system. Every stage of the language is written in the
    language itself.</p>
    {HERO_CODE}
  </header>

{chr(10).join(parts)}

  <footer>
    <p class="verse">वाक् इति भाषा — यत्र संस्कृतम् एव आदेशः<span class="danda">॥</span></p>
    <p>{__version__} · {len(BUILTIN_DOCS)} built-ins · five engines, one output</p>
  </footer>
</main>
</div>

<script>
(function () {{
  "use strict";

  /* द्विलिपिता — every keyword carries its ASCII spelling, so the page can be
     read in either canon.  Identifiers stay as their author wrote them. */
  var canon = document.getElementById("canon");
  var swappable = [].slice.call(document.querySelectorAll("[data-r]"));
  swappable.forEach(function (el) {{ el.dataset.d = el.textContent; }});
  var roman = false;
  canon.addEventListener("click", function () {{
    roman = !roman;
    swappable.forEach(function (el) {{
      el.textContent = roman ? el.dataset.r : el.dataset.d;
    }});
    canon.setAttribute("aria-pressed", String(roman));
    canon.textContent = roman ? "roman → देवनागरी" : "देवनागरी → roman";
  }});

  /* theme: follow the viewer, until they say otherwise */
  var theme = document.getElementById("theme");
  theme.addEventListener("click", function () {{
    var now = document.documentElement.dataset.theme;
    if (!now) {{
      now = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }}
    document.documentElement.dataset.theme = now === "dark" ? "light" : "dark";
  }});

  /* mark the section being read */
  var links = {{}};
  [].forEach.call(document.querySelectorAll(".rail a"), function (a) {{
    links[a.getAttribute("href").slice(1)] = a;
  }});
  var seen = new Set();
  var obs = new IntersectionObserver(function (entries) {{
    entries.forEach(function (e) {{
      if (e.isIntersecting) seen.add(e.target.id); else seen.delete(e.target.id);
    }});
    Object.keys(links).forEach(function (id) {{
      links[id].classList.toggle("on", seen.has(id));
    }});
  }}, {{ rootMargin: "-10% 0px -70% 0px" }});
  [].forEach.call(document.querySelectorAll("section"), function (s) {{ obs.observe(s); }});
}})();
</script>
"""

# एकम् अपि उदाहरणम् न भग्नम् — every sample on the page must really parse.
from vak import parse, tokenize                                # noqa: E402
from vak.errors import VakError                                # noqa: E402

broken = 0
for sample in SAMPLES:
    try:
        parse(tokenize(sample, "<manual>"), "<manual>")
    except VakError as err:
        broken += 1
        print(f"BROKEN SAMPLE: {err}")
        print("    " + sample.splitlines()[0])
print(f"samples: {len(SAMPLES)} checked, {broken} broken")

out = ROOT / "docs" / "manual.html"
out.parent.mkdir(exist_ok=True)
out.write_text(DOC, encoding="utf-8")
print(f"wrote {out}  ({len(DOC):,} bytes, {len(SECTIONS)} sections)")
