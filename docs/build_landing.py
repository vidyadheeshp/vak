# -*- coding: utf-8 -*-
"""प्रवेशपत्रम् — generate docs/index.html, the landing page.

Every program shown here is run by the real interpreter while the page is
built, and what it printed is what the page displays.  The page cannot claim
output the language does not produce.

    python docs/build_landing.py
"""
import base64
import contextlib
import html
import io
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from vaak import __version__, run_source                        # noqa: E402
from vaak.builtins import BUILTIN_DOCS                          # noqa: E402
from vaak.interpreter import Interpreter                        # noqa: E402
from vaak.tokens import KARAKA_ORDER, KEYWORDS, TYPE_NAMES      # noqa: E402


# The test count is read from the suite, so the page cannot drift from it.
TESTS = sum(
    1
    for line in (ROOT / "tests" / "test_vak.py").read_text(encoding="utf-8").splitlines()
    if line.strip().startswith("def test_")
)

# ------------------------------------------------------------------ shared
TYPES = {t for t in TYPE_NAMES if not t.isascii()}
KEYWORD_SET = {w for w in KEYWORDS if not w.isascii()}
# the words themselves, not the three spellings each of them has
DEV_KEYWORDS = {w for w in KEYWORDS if any("ऀ" <= c <= "ॿ" for c in w)}

import re                                                      # noqa: E402

TOKEN = re.compile(
    r"(#[^\n]*)"
    r'|("(?:[^"\\]|\\.)*")'
    r"|([०-९0-9][०-९0-9._]*)"
    r"|([^\s(){}\[\],;:।॥+\-*/%^<>=!\"#]+)"
)


def highlight(source: str) -> str:
    out, pos = [], 0
    for m in TOKEN.finditer(source):
        out.append(html.escape(source[pos:m.start()]))
        pos = m.end()
        comment, string, number, word = m.groups()
        if comment is not None:
            out.append(f'<i class="c">{html.escape(comment)}</i>')
        elif string is not None:
            out.append(f'<i class="s">{html.escape(string)}</i>')
        elif number is not None:
            out.append(html.escape(number))
        else:
            esc = html.escape(word)
            if word in KEYWORD_SET:
                out.append(f'<b class="k">{esc}</b>')
            elif word in TYPES:
                out.append(f'<b class="t">{esc}</b>')
            elif word in KARAKA_ORDER:
                out.append(f'<b class="ka">{esc}</b>')
            else:
                out.append(esc)
    out.append(html.escape(source[pos:]))
    return "".join(out)


def run(source: str) -> str:
    """What the language actually prints, captured while building the page."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        run_source(source, "<प्रवेशः>", Interpreter("<प्रवेशः>"))
    return buffer.getvalue().rstrip("\n")


def to_playground(source: str) -> str:
    raw = base64.urlsafe_b64encode(source.encode("utf-8")).decode("ascii")
    return f"playground.html#code={raw}"


def demo(source: str, note: str = "") -> str:
    """A program, what it prints, and a way to run it yourself."""
    source = source.strip()
    printed = run(source)
    caption = f'<figcaption>{note}</figcaption>' if note else ""
    return f"""<figure class="demo">
  <div class="src"><pre><code>{highlight(source)}</code></pre></div>
  <div class="res">
    <p class="lbl">फलम् · what it prints</p>
    <pre><code>{html.escape(printed)}</code></pre>
    <a class="try" href="{to_playground(source)}">चालय · run this yourself →</a>
  </div>
  {caption}
</figure>"""


# ------------------------------------------------------------------ content
HERO = '''कार्यम् छानय(अपादानम् सूची संग्रहः, करणम् कार्यम् परीक्षा) : सूची {
    सूची फलम् = []।
    प्रत्येकम् (अङ्गम् अन्तः संग्रहः) {
        यदि (परीक्षा(अङ्गम्)) { योजय(फलम्, अङ्गम्)। }
    }
    प्रत्यागच्छ फलम्।
}

कार्यम् समः(पूर्णाङ्कः सङ्ख्या) : सत्यता { प्रत्यागच्छ सङ्ख्या % २ == ०। }

मुद्रय छानय(अपादानम्: [१, २, ३, ४, ५, ६], करणम्: समः)।'''

KARAKA = '''कार्यम् छानय(अपादानम् सूची संग्रहः, करणम् कार्यम् परीक्षा) : सूची {
    सूची फलम् = []।
    प्रत्येकम् (अङ्गम् अन्तः संग्रहः) {
        यदि (परीक्षा(अङ्गम्)) { योजय(फलम्, अङ्गम्)। }
    }
    प्रत्यागच्छ फलम्।
}
कार्यम् समः(पूर्णाङ्कः सङ्ख्या) : सत्यता { प्रत्यागच्छ सङ्ख्या % २ == ०। }
मान अङ्काः = [१, २, ३, ४, ५, ६]।

# त्रीणि आह्वानानि, एकम् एव अर्थः — विभक्तिः क्रमम् मोचयति।
मुद्रय छानय(अङ्काः, समः)।
मुद्रय छानय(अपादानम्: अङ्काः, करणम्: समः)।
मुद्रय छानय(करणम्: समः, अपादानम्: अङ्काः)।'''

SWITCH = '''कार्यम् वासरनाम(कर्म पूर्णाङ्कः वारः) : शब्दः {
    विकल्पः (वारः) {
        पक्षे १: प्रत्यागच्छ "सोमवासरः"।
        पक्षे ६, ७: प्रत्यागच्छ "सप्ताहान्तः"।
        अन्यथा: प्रत्यागच्छ "अन्यः वासरः"।
    }
}
प्रत्येकम् (वारः अन्तः [१, ६, ३]) { मुद्रय वासरनाम(वारः)। }'''

ASCII = '''karyam varga(purnankah a) : purnankah { pratyagaccha a * a; }
pratyekam (n antah [1, 2, 3, 4]) { mudraya n, "->", varga(n); }'''

PAGE = f"""<title>वाक् · Vāk — a programming language whose compiler is written in Sanskrit</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="favicon.ico" sizes="any">
<meta name="description" content="Vāk is a Sanskrit-native programming language.
Pāṇini's kāraka roles are its type system, and every stage of its front end —
lexer, parser, analyser, compiler and virtual machine — is written in Vāk itself.">
<style>
:root {{
  /* मसी — manuscript ink, paper, and haritāla: the orpiment yellow Indian
     manuscripts used for headings and for painting over mistakes. */
  --ink:#16223f; --ink-soft:#4a5570; --ink-faint:#7c8499; --paper:#f7f6f1;
  --paper-2:#eeece4; --rule:#cfcdc2; --gold:#a8781f; --gold-lit:#f0e4c4;
  --indigo:#37508c; --crimson:#9a3324;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --ink:#e6e3d9; --ink-soft:#a9aec0; --ink-faint:#767d92; --paper:#10141f;
    --paper-2:#171c2b; --rule:#2c3346; --gold:#d8a94a; --gold-lit:#2a2415;
    --indigo:#8aa2df; --crimson:#e0806e;
  }}
}}
:root[data-theme="light"] {{
  --ink:#16223f; --ink-soft:#4a5570; --ink-faint:#7c8499; --paper:#f7f6f1;
  --paper-2:#eeece4; --rule:#cfcdc2; --gold:#a8781f; --gold-lit:#f0e4c4;
  --indigo:#37508c; --crimson:#9a3324;
}}
:root[data-theme="dark"] {{
  --ink:#e6e3d9; --ink-soft:#a9aec0; --ink-faint:#767d92; --paper:#10141f;
  --paper-2:#171c2b; --rule:#2c3346; --gold:#d8a94a; --gold-lit:#2a2415;
  --indigo:#8aa2df; --crimson:#e0806e;
}}
html {{
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,
          "Nirmala UI","Noto Serif Devanagari",serif;
  --sans:"Segoe UI",-apple-system,"Helvetica Neue",Arial,"Nirmala UI",
         "Noto Sans Devanagari",sans-serif;
  --mono:"Cascadia Mono",Consolas,"SF Mono",Menlo,"DejaVu Sans Mono","Nirmala UI",
         "Noto Sans Devanagari",monospace;
  box-sizing:border-box; -webkit-text-size-adjust:100%; scroll-behavior:smooth;
}}
*,*::before,*::after {{ box-sizing:inherit; }}
body {{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:var(--serif); font-size:17px; line-height:1.66;
}}
.wrap {{ max-width:60rem; margin:0 auto; padding:0 clamp(1.1rem,4vw,2.5rem); }}
p {{ max-width:38em; }}

/* ------------------------------------------------------------- top bar */
.top {{
  display:flex; align-items:baseline; gap:1rem; flex-wrap:wrap;
  padding:1.1rem 0 .8rem; border-bottom:1px solid var(--rule);
}}
.top .mark {{ font-size:1.5rem; letter-spacing:-.01em; }}
.top nav {{ margin-left:auto; display:flex; gap:1.1rem; flex-wrap:wrap;
            font-family:var(--sans); font-size:.82rem; }}
.top nav a {{ color:var(--ink-soft); text-decoration:none; }}
.top nav a:hover, .top nav a:focus-visible {{ color:var(--gold); }}
.top button {{
  font:inherit; font-family:var(--sans); font-size:.72rem; cursor:pointer;
  color:var(--ink-faint); background:transparent; border:1px solid var(--rule);
  border-radius:2px; padding:.24rem .5rem;
}}
.top button:hover {{ border-color:var(--gold); color:var(--gold); }}

/* ---------------------------------------------------------------- hero */
.hero {{ padding:clamp(3rem,8vw,6rem) 0 3.5rem; }}
.hero .eyebrow {{
  margin:0 0 1.1rem; font-family:var(--sans); font-size:.75rem;
  letter-spacing:.14em; text-transform:uppercase; color:var(--gold);
}}
.hero h1 {{
  margin:0 0 1.3rem; font-weight:400; line-height:1.12; text-wrap:balance;
  font-size:clamp(2.1rem,1.2rem + 4.2vw,4rem); letter-spacing:-.015em;
  max-width:16em;
}}
.hero h1 em {{ font-style:normal; color:var(--gold); }}
.hero .danda {{ color:var(--gold); }}
.hero .stand {{ font-size:1.13rem; color:var(--ink-soft); max-width:36em; }}
.doors {{ display:flex; gap:.7rem; flex-wrap:wrap; margin:2rem 0 0; }}
.doors a {{
  font-family:var(--sans); font-size:.86rem; text-decoration:none;
  border:1px solid var(--rule); border-radius:2px; padding:.55rem 1.05rem;
  color:var(--ink-soft);
}}
.doors a:hover, .doors a:focus-visible {{ border-color:var(--gold); color:var(--gold); }}
.doors a.first {{ border-color:var(--gold); color:var(--gold); font-weight:600;
                  background:var(--gold-lit); }}

/* ------------------------------------------------------------ sections */
section {{ padding:3.5rem 0 0; scroll-margin-top:1rem; }}
.head {{ border-top:1.5px solid var(--ink); padding-top:.5rem; margin-bottom:1.4rem;
         display:flex; align-items:baseline; gap:.9rem; flex-wrap:wrap; }}
.head h2 {{ margin:0; font-weight:500; font-size:clamp(1.45rem,1.1rem + 1.5vw,2rem);
            line-height:1.2; }}
.head .en {{ font-family:var(--sans); font-size:.78rem; color:var(--ink-soft);
             letter-spacing:.02em; }}
.lede {{ font-size:1.1rem; color:var(--gold); max-width:32em; }}

/* ---------------------------------------------------------------- demo */
figure.demo {{
  margin:1.6rem 0; display:grid; gap:0; border:1px solid var(--rule);
  border-radius:3px; overflow:hidden; grid-template-columns:1.35fr 1fr;
}}
figure.demo .src {{ background:var(--paper-2); min-width:0; }}
figure.demo .res {{ border-left:1px solid var(--rule); min-width:0;
                    display:flex; flex-direction:column; }}
figure.demo pre {{ margin:0; padding:1rem 1.1rem; overflow-x:auto; }}
figure.demo code {{ font-family:var(--mono); font-size:.82rem; line-height:1.7;
                    white-space:pre; }}
figure.demo .lbl {{
  margin:0; padding:.55rem 1.1rem .1rem; font-family:var(--sans);
  font-size:.68rem; letter-spacing:.1em; text-transform:uppercase;
  color:var(--ink-faint);
}}
figure.demo .res pre {{ flex:1; padding-top:.3rem; color:var(--ink-soft); }}
figure.demo .try {{
  font-family:var(--sans); font-size:.76rem; text-decoration:none;
  color:var(--gold); padding:.55rem 1.1rem .8rem; border-top:1px solid var(--rule);
}}
figure.demo .try:hover {{ background:var(--gold-lit); }}
figure.demo figcaption {{
  grid-column:1/-1; border-top:1px solid var(--rule); padding:.55rem 1.1rem;
  font-family:var(--sans); font-size:.76rem; color:var(--ink-faint);
  background:var(--paper-2);
}}
.k {{ color:var(--gold); font-weight:600; font-style:normal; }}
.t {{ color:var(--indigo); font-weight:600; font-style:normal; }}
.ka {{ color:var(--crimson); font-weight:600; font-style:normal;
       border-bottom:1.5px solid currentColor; }}
.s {{ color:var(--indigo); font-style:normal; }}
.c {{ color:var(--ink-faint); font-style:italic; }}
code {{ font-family:var(--mono); font-size:.875em; background:var(--paper-2);
        padding:.06em .32em; border-radius:2px; }}

/* --------------------------------------------------------------- facts */
.facts {{ display:grid; gap:1px; background:var(--rule); border:1px solid var(--rule);
          grid-template-columns:repeat(auto-fit,minmax(9.5rem,1fr)); margin:1.6rem 0;
          border-radius:3px; overflow:hidden; }}
.facts div {{ background:var(--paper); padding:1rem 1.1rem; }}
.facts b {{ display:block; font-size:1.6rem; font-weight:400; color:var(--gold);
            line-height:1.1; font-variant-numeric:tabular-nums; }}
.facts span {{ font-family:var(--sans); font-size:.74rem; color:var(--ink-faint);
               line-height:1.35; display:block; margin-top:.3rem; }}

/* --------------------------------------------------------------- table */
.scroll {{ overflow-x:auto; margin:1.4rem 0; }}
table {{ border-collapse:collapse; width:100%; font-size:.92rem; }}
th,td {{ text-align:left; padding:.45rem .8rem .45rem 0;
         border-bottom:1px solid var(--rule); vertical-align:baseline; }}
th {{ font-family:var(--sans); font-size:.7rem; letter-spacing:.09em;
      text-transform:uppercase; color:var(--ink-faint); font-weight:500;
      border-bottom-color:var(--ink); }}

.note {{ margin:1.5rem 0; padding:.1rem 0 .1rem 1.1rem;
         border-left:2px solid var(--gold); }}
.note p {{ font-size:.94rem; color:var(--ink-soft); }}
a {{ color:var(--gold); text-underline-offset:.18em; }}

footer {{ border-top:1.5px solid var(--ink); margin-top:5rem; padding:1.2rem 0 4rem;
          font-family:var(--sans); font-size:.8rem; color:var(--ink-faint); }}
footer p {{ margin:.35rem 0; max-width:none; }}
footer .verse {{ font-family:var(--serif); font-size:1rem; color:var(--ink-soft);
                 margin-bottom:.9rem; }}
footer a {{ color:var(--ink-soft); }}
footer a:hover {{ color:var(--gold); }}

@media (max-width:44rem) {{
  figure.demo {{ grid-template-columns:1fr; }}
  figure.demo .res {{ border-left:0; border-top:1px solid var(--rule); }}
}}
@media (prefers-reduced-motion:reduce) {{
  html {{ scroll-behavior:auto; }}
  * {{ transition:none !important; animation:none !important; }}
}}
</style>

<div class="wrap">

<div class="top">
  <span class="mark">वाक्</span>
  <nav>
    <a href="#कारकाणि">कारकाणि · kāraka</a>
    <a href="#स्वयंसिद्धिः">स्वयंसिद्धिः · the bootstrap</a>
    <a href="manual.html#sthapana">स्थापना · install</a>
    <a href="story.html">कथा · how it was built</a>
    <a href="manual.html">पुस्तिका · manual</a>
    <a href="playground.html">क्रीडाक्षेत्रम् · try it</a>
  </nav>
  <button id="theme" type="button">theme</button>
</div>

<header class="hero">
  <p class="eyebrow">वाक् · Vāk — version {__version__}</p>
  <h1>A programming language whose type system is Pāṇini's grammar, and whose
  <em>own compiler</em> is written in Sanskrit<span class="danda">।</span></h1>
  <p class="stand">Sanskrit does not decide meaning by word order. It marks the
  <b>role</b> each participant plays in an action — the agent, the instrument,
  the source — and lets the words fall where they like. Vāk makes those roles a
  type system, and then writes its entire front end in itself.</p>
  <div class="doors">
    <a class="first" href="playground.html">क्रीडाक्षेत्रम् · run it in your browser →</a>
    <a href="manual.html">पुस्तिका · read the manual</a>
    <a href="manual.html#sthapana">स्थापना · install it</a>
    <a href="story.html">कथा · how it was built</a>
  </div>
</header>

<section id="कारकाणि">
  <div class="head">
    <h2>कारकाणि</h2><span class="en">the part that exists nowhere else</span>
  </div>
  <p class="lede">A parameter declares the role it plays in the action, and the
  compiler checks the grammar of your function the way Pāṇini checked the
  grammar of a sentence.</p>
  <p>Here <code>संग्रहः</code> is the <b>अपादानम्</b> — the ablative, what we draw
  <i>from</i> — and <code>परीक्षा</code> is the <b>करणम्</b>, the instrumental, the
  means <i>by which</i>. Because the roles are marked, the arguments carry their
  own labels and the order stops mattering. All three of these are one call:</p>
  {demo(KARAKA, "The same insight that frees a Sanskrit sentence from word order, applied to a function call.")}
  <p>The analyser enforces the grammar of roles. Pāṇini's rule that an action has
  one agent and one patient is a real constraint: two <code>कर्ता</code>
  parameters is an error, so is a label naming a role the function never declared.
  Word order is deliberately <em>not</em> constrained — that is the whole point of
  marking the roles.</p>
</section>

<section id="भाषा">
  <div class="head">
    <h2>भाषा</h2><span class="en">the language itself</span>
  </div>
  <p>Statements end with a <b>danda</b> — <code>।</code> — the full stop Sanskrit
  has used since manuscripts. Types are gradual: write none and nothing is
  checked, write one and it binds everywhere. <code>विकल्पः</code> is Pāṇini's word
  for an optional alternative, and <code>पक्षे</code> is the locative, "in this
  case":</p>
  {demo(SWITCH)}
  <p>And none of it requires a Devanagari keyboard. Every keyword has an ASCII
  spelling, and ASCII numerals work everywhere:</p>
  {demo(ASCII, "The same language, typed on a plain keyboard.")}
</section>

<section id="स्वयंसिद्धिः">
  <div class="head">
    <h2>स्वयंसिद्धिः</h2><span class="en">it compiles itself</span>
  </div>
  <p class="lede">A language that depends on another language to exist has not
  quite escaped it.</p>
  <p>Every stage of the front end is written in Vāk — and each is held to its
  Python counterpart at the finest granularity that stage allows: the lexer on
  every token's kind, lexeme, value and line; the parser on the whole syntax tree,
  node for node; the analyser on every diagnostic's code, line and wording; the
  compiler on every instruction, constant and line number.</p>
  <div class="scroll"><table>
    <thead><tr><th>stage</th><th>written in Vāk</th><th>checked against</th></tr></thead>
    <tbody>
      <tr><td>lexer</td><td><code>शब्दविभाजकः.vak</code></td><td>every token</td></tr>
      <tr><td>parser</td><td><code>व्याकरणम्.vak</code></td><td>the whole syntax tree</td></tr>
      <tr><td>analyser</td><td><code>अर्थविश्लेषकः.vak</code></td><td>every diagnostic, word for word</td></tr>
      <tr><td>compiler</td><td><code>संकलकः.vak</code></td><td>every instruction</td></tr>
      <tr><td>machine</td><td><code>यन्त्रम्.vak</code></td><td>byte-identical output</td></tr>
    </tbody>
  </table></div>
  <p>A Vāk program can be run by five engines — a tree-walking interpreter, a
  bytecode VM, that VM written in Vāk, a VM in C, and <code>वाक्.exe</code>, the
  whole self-hosted toolchain compiled natively. All five are held to
  byte-identical output on every example, which is how any of this stays honest.</p>
  <div class="facts">
    <div><b>5</b><span>engines, one output</span></div>
    <div><b>{len(BUILTIN_DOCS)}</b><span>built-in functions</span></div>
    <div><b>{TESTS}</b><span>tests</span></div>
    <div><b>6</b><span>kāraka roles</span></div>
    <div><b>139 KB</b><span>the whole toolchain, in your browser</span></div>
  </div>
  <div class="note">
    <p><b>The page you are reading links to a real compiler.</b> The
    <a href="playground.html">playground</a> is this entire toolchain compiled to
    WebAssembly — it lexes, parses, analyses, compiles and runs Vāk inside the
    browser. There is no server. Nothing you type is sent anywhere.</p>
  </div>
</section>

<footer>
  <p class="verse">वाक् इति भाषा — यत्र संस्कृतम् एव आदेशः<span class="danda">॥</span></p>
  <p><b>Vāk</b> {__version__} · <a href="manual.html">manual</a> ·
     <a href="playground.html">playground</a> ·
     <a href="story.html">the story</a> ·
     <a href="https://github.com/vidyadheeshp/vak">source</a></p>
  <p>Built by Vidyadheesh Pandurangi.</p>
</footer>

</div>

<script>
(function () {{
  "use strict";
  document.getElementById("theme").addEventListener("click", function () {{
    var now = document.documentElement.dataset.theme;
    if (!now) {{
      now = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }}
    document.documentElement.dataset.theme = now === "dark" ? "light" : "dark";
  }});
}})();
</script>
"""

out = ROOT / "docs" / "index.html"
out.write_text(PAGE, encoding="utf-8")
print(f"wrote {out}  ({len(PAGE):,} chars)")
print("hero output, verified by running it:")
print("   ", run(HERO))
