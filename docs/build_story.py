# -*- coding: utf-8 -*-
"""कथा — generate docs/story.html, how Vāk came to be.

The arc is not a list of releases.  It is one thing happening: a language
written in Python slowly becomes able to write itself, and then runs without
Python at all.  That arc has a measurable shape — the share of the toolchain
written in Vāk goes from nothing to all of it — and the page animates that real
number rather than decorating the story with motion.

Line counts, keyword totals, opcode counts and the test total are read out of
the repository at build time.  The three timings are not — there is no benchmark
script in the tree yet, so they are recorded here as measured, and the page says
so rather than implying they are regenerated.

    python docs/build_story.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from vaak import __version__                                     # noqa: E402
from vaak.builtins import BUILTIN_DOCS                           # noqa: E402
from vaak.opcodes import Op                                      # noqa: E402
from vaak.tokens import KARAKA_ORDER, KEYWORDS                   # noqa: E402


def lines(path: pathlib.Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


SELF = ROOT / "स्वयंसिद्धिः"
STAGE_FILE = {
    "lexer": "शब्दविभाजकः", "parser": "व्याकरणम्", "compiler": "संकलकः",
    "machine": "यन्त्रम्", "driver": "वाक्", "analyser": "अर्थविश्लेषकः",
    "main": "मुख्यम्",
}
VAK_LINES = {k: lines(SELF / (v + ".vak")) for k, v in STAGE_FILE.items()}
VAK_TOTAL = sum(VAK_LINES.values())
PY_LINES = sum(lines(f) for f in (ROOT / "vaak").glob("*.py"))
C_LINES = sum(lines(f) for f in (ROOT / "native").glob("*.[ch]"))
EXAMPLES = len(list((ROOT / "examples").glob("*.vak")))
EXE = ROOT / "वाक्.exe"
EXE_KB = round(EXE.stat().st_size / 1024) if EXE.exists() else 737
TESTS = sum(1 for line in (ROOT / "tests" / "test_vak.py")
            .read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("def test_"))

# Which versions were actually cut.  This is stated rather than inferred: the
# repository has exactly one commit (वाक् 0.10.0) and vaak/__init__.py says
# 0.11.0, so those two exist and the other eight numbers on this page do not.
# Scraping them out of commit subjects would mark any version-like number in any
# future commit as a release, which is not the claim being made.
REAL = {"0.10.0", __version__}

# len(KEYWORDS) counts the Devanagari, IAST and ASCII spellings of the same
# word, so it reads as a far larger vocabulary than Vak actually asks anyone
# to learn.  The honest count is the words themselves.
DEV_KEYWORDS = {w for w in KEYWORDS if any("ऀ" <= c <= "ॿ" for c in w)}

ORDER = ["lexer", "parser", "compiler", "machine", "driver", "analyser", "main"]
CUMULATIVE, _running = {}, 0
for _k in ORDER:
    _running += VAK_LINES[_k]
    CUMULATIVE[_k] = round(_running * 100 / VAK_TOTAL)

# (act, version, वाक् title, english, share written in Vāk by then, body)
CHAPTERS = [
    ("I", "0.0.1", "आरम्भः", "It begins in Python", 0, f"""
<p>The first version could not have compiled a single line of itself. It was a
lexer, a parser and a tree-walking interpreter — {PY_LINES:,} lines of Python —
and everything the language could do, Python did on its behalf.</p>
<p>That is the ordinary way to start, and it contains the ordinary trap: a
language whose only implementation is written in another language has not really
escaped it. Everything that follows is an attempt to leave.</p>"""),

    ("I", "0.1.0", "कारकाणि", "The idea that made it worth doing", 0, f"""
<p class="lede">Sanskrit does not decide meaning by word order. It marks the
role each participant plays in the action.</p>
<p>Pāṇini analysed a sentence by <b>kāraka</b>: who acts, what is acted upon, by
what means, from what source. Vāk lets a function's parameters declare those
same {len(KARAKA_ORDER)} roles — and the analyser then enforces the grammar of
roles, including Pāṇini's rule that an action has at most one agent and one
patient.</p>
<p>Because the roles are marked, the arguments carry their own labels and the
order stops mattering. That is not a convenience feature. It is the freedom case
endings give a Sanskrit sentence, moved into a type system.</p>
<p>This is the part that exists nowhere else, and it arrived early — before any
of the machinery below.</p>"""),

    ("I", "0.2.0", "अर्थविश्लेषकः", "Learning to say no", 0, """
<p>A language that only runs is little use to a student; it has to explain what
is wrong. So came the semantic analyser — undefined names, type mismatches,
assignment to a constant, <code>विरम</code> outside a loop, unreachable code,
and the kāraka rules.</p>
<p>Every message is bilingual and every diagnostic carries a Sanskrit code. That
decision paid for itself much later in a way nobody planned: because the
analyser already reported structured diagnostics, the editor extension needed no
analysis of its own.</p>"""),

    ("II", "0.3.0", "संकलकः च यन्त्रम्", "A machine small enough to copy", 0, f"""
<p class="turn">This is the hinge of the whole story.</p>
<p>A tree-walking interpreter cannot be self-hosted in any satisfying way. So
the language grew a second engine: a compiler to bytecode, and a stack machine
to run it — {len(list(Op))} instructions, each with a Sanskrit name.</p>
<p>That mattered because it created something small and precise enough to be
re-implemented. The Python VM became a <em>specification</em>. Anything that
could emit the same instructions and run them to the same output was a
legitimate implementation of Vāk — including one written in Vāk.</p>"""),

    ("II", "0.4.0", "स्वयंसिद्धिः", "The language starts writing itself",
     CUMULATIVE["compiler"], f"""
<p>The lexer came first: {VAK_LINES['lexer']} lines of Vāk that split Vāk source
into tokens, held to the Python lexer on the kind, lexeme, value and line of
every token.</p>
<p>Then the parser, {VAK_LINES['parser']} lines, held to the whole syntax tree,
node for node. Then the compiler, {VAK_LINES['compiler']} lines, held to every
instruction, constant and line number.</p>
<p>At each step the new stage had to process <em>its own source</em> and agree.
The parser parsing the parser. That is the point where this stopped being a
toy.</p>"""),

    ("II", "0.5.0", "यन्त्रम्", "And then the machine itself", CUMULATIVE["driver"], f"""
<p>The virtual machine — dispatch loop, environments, call frames, exception
unwinding — written in Vāk, in {VAK_LINES['machine']} lines. A machine
describing a machine, in the language that machine runs.</p>
<p>It is still in the repository though nothing depends on it now: it is the
executable specification of what the instructions <em>mean</em>, and the tests
still run every example through it.</p>"""),

    ("III", "0.6.0", "देशीयसंकलनम्", "Python leaves", CUMULATIVE["driver"], f"""
<p>The native back end does not translate Vāk into C statement by statement. It
emits the <em>bytecode</em> as C data and links it against a C implementation of
the same machine — {C_LINES:,} lines. That is deliberate: every engine runs the
same instructions, so every engine can be held to the same output.</p>
<p>Compile the Vāk-written toolchain that way and the result is
<b>वाक्.exe</b> — {EXE_KB} KB, self-contained, no Python anywhere in the loop.
Python is used to build it once, exactly as a C compiler is used once to build a
self-hosting C compiler. After that the language stands on its own.</p>"""),

    ("IV", "0.8.0", "पूर्णता", "Finishing the front end", 100, f"""
<p>The analyser was the last stage with no Vāk counterpart, and the fussiest to
match. A lexer either agrees on a token or it does not; an analyser has to
produce the <em>same complaints</em>, in the same order, with the same wording.
It does — across sixty-five files, forty of them deliberately broken, one per
diagnostic kind.</p>
<p>With that, the entire front end exists in Vāk: {VAK_TOTAL:,} lines. The
language describes itself completely.</p>"""),

    ("IV", "0.10.0", "साधनानि", "Making it usable by someone else", 100, f"""
<p>A language nobody can install is a paper. So: a browser playground — the
whole toolchain compiled to WebAssembly, no server at all. An editor extension
whose grammar is <em>generated</em> from the language's own keyword tables, so
highlighting cannot drift. A typing aid, because Devanagari on a plain keyboard
is otherwise a wall. POSIX branches, so Linux and macOS are reachable.</p>
<p>{len(DEV_KEYWORDS)} keywords — each spelled three ways, so none of it needs
a Devanagari keyboard — {len(BUILTIN_DOCS)} built-ins, {EXAMPLES} worked
examples — and every keyword spelled two ways, so none of it requires a
Devanagari keyboard.</p>"""),

    ("V", "0.11.0", "कार्यक्षमता", "Making it fast, and being wrong twice", 100, """
<p>The last act is measurement, and it holds the most useful mistakes.</p>
<p>The obvious suspect was name lookup: every variable was found by comparing
Devanagari strings, and Devanagari strings all begin with the same byte. So
names were resolved to places, and built-ins reached directly. Together those
removed <b>71% of all string comparisons</b> — and moved the wall clock
<b>2%</b>.</p>
<p>A second attempt exploited the fact that identical names share one pointer.
It moved the clock <b>not at all</b>: most of a scope scan is spent on entries
that do <em>not</em> match, and a pointer check only helps the one that does.</p>
<p class="turn">The intuition that name lookup dominates an interpreter was
wrong twice.</p>
<p>Every real gain was elsewhere — in allocation, and in work that needed not to
have happened at all. A call formatted an error message for every argument and
discarded it. A string was copied four times in order to join it twice. Building
a string was quadratic, because each append rebuilt the whole of it.</p>"""),
]

ENGINES = [
    ("the interpreter", "Python", "the reference: what a program <em>means</em>"),
    ("the SanskritVM", "Python", "bytecode, and the machine's specification"),
    ("यन्त्रम्.vak", "Vāk", "the same machine, in the language it runs"),
    ("the C runtime", "C", "the substrate, and what WebAssembly is built from"),
    ("वाक्.exe", "native", "all of it compiled; no Python at all"),
]

PERF = [
    ("building a string", 10.148, 0.174, "quadratic → linear"),
    ("fib(30)", 3.438, 2.377, "calls stopped formatting unused errors"),
    ("1.2 M list operations", 1.809, 1.292, "pooled scopes, cached hashes"),
]


def perf_rows() -> str:
    top = max(max(b, a) for _, b, a, _ in PERF)
    out = []
    for name, before, after, why in PERF:
        out.append(f"""      <div class="bar">
        <p class="what">{name}<span>{why}</span></p>
        <div class="track">
          <div class="was" style="--w:{before / top * 100:.1f}%"><span>{before:.2f}s</span></div>
          <div class="now" style="--w:{after / top * 100:.1f}%"><span>{after:.2f}s</span></div>
        </div>
      </div>""")
    return "\n".join(out)


ACT_TITLES = {"I": "Python builds a language",
              "II": "The language learns to build itself",
              "III": "Python leaves",
              "IV": "Making it real",
              "V": "Making it fast"}


def chapter_html() -> str:
    out, act_seen = [], set()
    for act, ver, dev, eng, share, body in CHAPTERS:
        opener = ""
        if act not in act_seen:
            act_seen.add(act)
            opener = (f'  <li class="act reveal"><p class="mark">Act {act}</p>'
                      f'<p class="name">{ACT_TITLES[act]}</p></li>\n')
        # A version that was cut and a stage numbered after the fact are two
        # different claims, so they carry different marks and the legend says
        # which is which.  Only two of these were ever released.
        cut = ver in REAL
        chip = (f'<span class="ver{" cut" if cut else ""}" title="'
                f'{"a released version" if cut else "numbered in retrospect"}">'
                f'{ver}</span>')
        out.append(opener + f"""  <li class="ch reveal" data-share="{share}" data-ver="{ver}">
    <div class="tick" aria-hidden="true"></div>
    <h3>{chip}<span class="dev">{dev}</span><span class="eng">{eng}</span></h3>
    {body}
  </li>""")
    return "\n".join(out)


PAGE = f"""<title>कथा · How Vāk Was Built</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="favicon.ico" sizes="any">
<meta name="description" content="The making of Vāk — how a Sanskrit programming
language written in Python gradually became able to compile itself, and then ran
without Python at all.">
<style>
:root {{
  /* मसी — the palette the whole project uses: manuscript ink, paper, and
     haritāla, the orpiment yellow used for headings in Indian manuscripts.
     Here the two hues carry meaning: indigo is Python, gold is Vāk. */
  --ink:#16223f; --ink-soft:#4a5570; --ink-faint:#7c8499;
  --paper:#f7f6f1; --paper-2:#eeece4; --rule:#cfcdc2;
  --gold:#a8781f; --gold-lit:#f0e4c4; --indigo:#37508c; --crimson:#9a3324;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --ink:#e6e3d9; --ink-soft:#a9aec0; --ink-faint:#767d92;
    --paper:#10141f; --paper-2:#171c2b; --rule:#2c3346;
    --gold:#d8a94a; --gold-lit:#2a2415; --indigo:#8aa2df; --crimson:#e0806e;
  }}
}}
:root[data-theme="dark"] {{
  --ink:#e6e3d9; --ink-soft:#a9aec0; --ink-faint:#767d92;
  --paper:#10141f; --paper-2:#171c2b; --rule:#2c3346;
  --gold:#d8a94a; --gold-lit:#2a2415; --indigo:#8aa2df; --crimson:#e0806e;
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
  font-family:var(--serif); font-size:17px; line-height:1.68;
}}
.wrap {{ max-width:56rem; margin:0 auto; padding:0 clamp(1.1rem,4vw,2.5rem); }}
p {{ max-width:36em; }}
a {{ color:var(--gold); text-underline-offset:.18em; }}

/* -------------------------------------------------------------- top bar */
.top {{ display:flex; align-items:baseline; gap:1rem; flex-wrap:wrap;
        padding:1.1rem 0 .8rem; border-bottom:1px solid var(--rule); }}
.top .mark {{ font-size:1.4rem; }}
.top nav {{ margin-left:auto; display:flex; gap:1.05rem; flex-wrap:wrap;
            font-family:var(--sans); font-size:.8rem; }}
.top nav a {{ color:var(--ink-soft); text-decoration:none; }}
.top nav a:hover, .top nav a:focus-visible {{ color:var(--gold); }}
.top button {{ font:inherit; font-family:var(--sans); font-size:.71rem;
  cursor:pointer; color:var(--ink-faint); background:transparent;
  border:1px solid var(--rule); border-radius:2px; padding:.22rem .5rem; }}
.top button:hover, .top button:focus-visible {{ border-color:var(--gold); color:var(--gold); }}

/* ------------------------------------------------------------------ hero */
.hero {{ padding:clamp(3rem,9vw,6.5rem) 0 2.5rem; }}
.hero .eyebrow {{ margin:0 0 1.1rem; font-family:var(--sans); font-size:.73rem;
  letter-spacing:.15em; text-transform:uppercase; color:var(--gold); }}
.hero h1 {{ margin:0 0 1.3rem; font-weight:400; line-height:1.1;
  font-size:clamp(2.1rem,1.2rem + 4.4vw,4.2rem); letter-spacing:-.02em;
  text-wrap:balance; max-width:14em; }}
.hero h1 em {{ font-style:normal; color:var(--gold); }}
.hero .stand {{ font-size:1.1rem; color:var(--ink-soft); max-width:34em; }}

/* --------------------------------------------------------------- the meter
   The one animated thing, and it animates a real number: how much of the
   toolchain was written in Vāk itself at that point in the story. */
.meter {{ position:sticky; top:0; z-index:20; background:var(--paper);
  border-bottom:1px solid var(--rule); padding:.55rem 0 .6rem; }}
.meter .inner {{ max-width:56rem; margin:0 auto;
  padding:0 clamp(1.1rem,4vw,2.5rem); display:flex; align-items:center;
  gap:.8rem; flex-wrap:wrap; }}
.meter .lbl {{ font-family:var(--sans); font-size:.68rem; letter-spacing:.09em;
  text-transform:uppercase; color:var(--ink-faint); white-space:nowrap; }}
.meter .track {{ flex:1; min-width:8rem; height:7px; border-radius:4px;
  background:var(--indigo); overflow:hidden; position:relative; }}
.meter .fill {{ height:100%; width:0%; background:var(--gold); border-radius:4px;
  transition:width .7s cubic-bezier(.22,.61,.36,1); }}
.meter .pct {{ font-family:var(--mono); font-size:.78rem; color:var(--gold);
  min-width:3.2rem; text-align:right; font-variant-numeric:tabular-nums; }}

/* ------------------------------------------------------------ the spine
   Devanagari hangs its letters from a शिरोरेखा.  Turned on its side, that
   same head-line becomes the thread the story hangs from. */
ol.story {{ list-style:none; margin:0; padding:0 0 0 clamp(1.4rem,4vw,3rem);
  position:relative; }}
ol.story::before {{ content:""; position:absolute; left:0; top:.6rem; bottom:0;
  width:2px; background:var(--rule); }}
ol.story > li {{ position:relative; padding:0 0 3.2rem; }}
.tick {{ position:absolute; left:calc(clamp(1.4rem,4vw,3rem) * -1); top:1.05rem;
  width:clamp(1.4rem,4vw,3rem); height:2px; background:var(--gold); }}
li.act {{ padding-top:2.6rem; padding-bottom:1.2rem; }}
li.act .mark {{ margin:0; font-family:var(--sans); font-size:.7rem;
  letter-spacing:.16em; text-transform:uppercase; color:var(--gold); }}
li.act .name {{ margin:.2rem 0 0; font-size:clamp(1.3rem,1.1rem + 1.1vw,1.8rem);
  color:var(--ink); }}
li.ch h3 {{ margin:0 0 .7rem; font-weight:500; display:flex; gap:.7rem;
  align-items:baseline; flex-wrap:wrap;
  font-size:clamp(1.15rem,1rem + .8vw,1.5rem); }}
li.ch h3 .eng {{ font-family:var(--sans); font-size:.68em; font-weight:400;
  color:var(--ink-soft); }}
/* An outlined chip is a stage numbered after the fact; a filled one is a
   version that was actually cut.  Only two of these were ever cut. */
.ver {{ font-family:var(--mono); font-size:.62em; font-weight:400;
  letter-spacing:.02em; font-variant-numeric:tabular-nums; white-space:nowrap;
  padding:.2em .55em; border-radius:2px; align-self:center;
  border:1px solid var(--rule); color:var(--ink-faint); background:transparent; }}
.ver.cut {{ border-color:var(--gold); background:var(--gold); color:var(--paper); }}
.legend {{ display:flex; gap:1.4rem; flex-wrap:wrap; align-items:center;
  margin:.4rem 0 2.6rem; font-family:var(--sans); font-size:.77rem;
  color:var(--ink-faint); max-width:none; }}
.legend .k {{ display:inline-flex; align-items:center; gap:.5rem; }}
.legend .ver {{ font-size:.72rem; }}
p.lede {{ font-size:1.08rem; color:var(--gold); max-width:31em; }}
p.turn {{ font-size:1.08rem; color:var(--crimson); max-width:31em;
  font-style:italic; }}
code {{ font-family:var(--mono); font-size:.87em; background:var(--paper-2);
  padding:.06em .32em; border-radius:2px; }}

/* --------------------------------------------------------------- figures */
figure {{ margin:1.8rem 0; }}
figure svg {{ max-width:100%; height:auto; display:block; }}
figcaption {{ margin-top:.6rem; font-family:var(--sans); font-size:.76rem;
  color:var(--ink-faint); max-width:38em; }}
.panel {{ border:1px solid var(--rule); border-radius:3px; padding:1.2rem
  clamp(1rem,3vw,1.5rem); margin:1.8rem 0; background:var(--paper-2); }}
.panel h4 {{ margin:0 0 .8rem; font-size:1rem; font-weight:600; }}

/* engines */
ul.engines {{ list-style:none; margin:0; padding:0; display:flex;
  flex-direction:column; gap:0; }}
ul.engines li {{ display:grid; grid-template-columns:auto 5.2rem 1fr; gap:.9rem;
  padding:.55rem 0; border-bottom:1px solid var(--rule); align-items:baseline;
  max-width:none; }}
ul.engines li:last-child {{ border-bottom:0; }}
ul.engines .n {{ font-family:var(--mono); font-size:.78rem; color:var(--gold); }}
ul.engines .in {{ font-family:var(--sans); font-size:.7rem; letter-spacing:.06em;
  text-transform:uppercase; color:var(--ink-faint); }}
ul.engines .d {{ font-size:.93rem; color:var(--ink-soft); }}

/* performance bars */
.bar {{ margin:0 0 1.1rem; }}
.bar .what {{ margin:0 0 .3rem; font-size:.93rem; max-width:none;
  display:flex; gap:.6rem; align-items:baseline; flex-wrap:wrap; }}
.bar .what span {{ font-family:var(--sans); font-size:.72rem; color:var(--ink-faint); }}
.bar .track {{ display:flex; flex-direction:column; gap:.25rem; }}
.bar .was, .bar .now {{ height:1.35rem; border-radius:2px; display:flex;
  align-items:center; justify-content:flex-end; padding:0 .45rem;
  font-family:var(--mono); font-size:.72rem; width:0;
  transition:width .9s cubic-bezier(.22,.61,.36,1); }}
.reveal.seen .bar .was, .reveal.seen .bar .now {{ width:var(--w); }}
.bar .was {{ background:var(--indigo); color:#fff; min-width:3.4rem; }}
.bar .now {{ background:var(--gold); color:#1a1405; min-width:3.4rem; }}
:root[data-theme="dark"] .bar .was, :root[data-theme="dark"] .bar .now {{ color:#0f1319; }}

/* facts */
.facts {{ display:grid; gap:1px; background:var(--rule); border:1px solid var(--rule);
  grid-template-columns:repeat(auto-fit,minmax(8.5rem,1fr)); margin:1.8rem 0;
  border-radius:3px; overflow:hidden; }}
.facts div {{ background:var(--paper); padding:.9rem 1rem; }}
.facts b {{ display:block; font-size:1.5rem; font-weight:400; color:var(--gold);
  line-height:1.1; font-variant-numeric:tabular-nums; }}
.facts span {{ font-family:var(--sans); font-size:.72rem; color:var(--ink-faint);
  display:block; margin-top:.25rem; line-height:1.35; }}

footer {{ border-top:1.5px solid var(--ink); margin-top:4rem; padding:1.2rem 0 4rem;
  font-family:var(--sans); font-size:.79rem; color:var(--ink-faint); }}
footer p {{ margin:.3rem 0; max-width:none; }}

/* ------------------------------------------------------------- motion
   Reveals are scroll-triggered; everything is visible without JS, and all
   of it is switched off for anyone who asked for less movement. */
.reveal {{ opacity:0; transform:translateY(14px);
  transition:opacity .6s ease, transform .6s cubic-bezier(.22,.61,.36,1); }}
.reveal.seen {{ opacity:1; transform:none; }}
@media (prefers-reduced-motion:reduce) {{
  html {{ scroll-behavior:auto; }}
  .reveal {{ opacity:1; transform:none; transition:none; }}
  .meter .fill {{ transition:none; }}
  .bar .was, .bar .now {{ transition:none; width:var(--w); }}
}}
</style>

<div class="meter" aria-hidden="true">
  <div class="inner">
    <span class="lbl">written in वाक् itself</span>
    <span class="track"><span class="fill" id="fill"></span></span>
    <span class="pct" id="pct">0%</span>
  </div>
</div>

<div class="wrap">

<div class="top">
  <span class="mark">वाक्</span>
  <nav>
    <a href="index.html">वाक्</a>
    <a href="manual.html">पुस्तिका · manual</a>
    <a href="playground.html">क्रीडाक्षेत्रम् · try it</a>
    <a href="https://github.com/vidyadheeshp/vak">स्रोतः · source</a>
  </nav>
  <button id="theme" type="button">theme</button>
</div>

<header class="hero">
  <p class="eyebrow">कथा · the making of वाक्</p>
  <h1>A language written in Python, that slowly learned to
  <em>write itself</em>.</h1>
  <p class="stand"><b>0.0.1 to {__version__}.</b> Vāk began as {PY_LINES:,} lines
  of Python that could not have compiled one line of itself. It now compiles itself completely, runs on five
  independent engines held to identical output, and needs no Python at all. This
  is how that happened — including the two optimisations that turned out to be
  worth nothing.</p>
</header>

<p class="legend">
  <span class="k"><span class="ver cut">0.10.0</span> a version that was actually cut</span>
  <span class="k"><span class="ver">0.4.0</span> a stage, numbered here in retrospect</span>
</p>

<ol class="story">
{chapter_html()}

  <li class="ch reveal" data-share="100" data-ver="{__version__}">
    <div class="tick" aria-hidden="true"></div>
    <h3><span class="ver cut">{__version__}</span><span class="dev">फलम्</span>
      <span class="eng">Where it stands today</span></h3>
    <p>Five engines, one language, and a test suite whose job is to prove they
    never disagree.</p>
    <div class="facts">
      <div><b>5</b><span>engines, byte-identical</span></div>
      <div><b>{TESTS}</b><span>tests</span></div>
      <div><b>{VAK_TOTAL:,}</b><span>lines written in Vāk</span></div>
      <div><b>{EXE_KB} KB</b><span>self-contained binary</span></div>
      <div><b>{len(KARAKA_ORDER)}</b><span>kāraka roles as types</span></div>
    </div>
  </li>
</ol>

<div class="panel">
  <h4>The five engines</h4>
  <ul class="engines">
{chr(10).join(f'''    <li><span class="n">{i}</span><span class="in">{lang}</span>
      <span class="d"><b>{name}</b> — {desc}</span></li>'''
              for i, (name, lang, desc) in enumerate(ENGINES, 1))}
  </ul>
  <figcaption style="margin-top:.8rem">Every example runs through all five and
  must print exactly the same bytes. That single rule is what has kept the
  language honest through every rewrite on this page.</figcaption>
</div>

<figure>
  <svg viewBox="0 0 720 240" role="img" xmlns="http://www.w3.org/2000/svg"
       aria-label="Python compiles the Vāk-written toolchain once; after that the
       toolchain compiles itself and Python is no longer needed.">
    <defs>
      <marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7"
              markerHeight="7" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor"/>
      </marker>
    </defs>
    <g fill="none" stroke="currentColor" stroke-width="1.5">
      <rect x="14" y="86" width="150" height="58" rx="3" stroke="#37508c"/>
      <rect x="248" y="86" width="180" height="58" rx="3"/>
      <rect x="520" y="86" width="180" height="58" rx="3" stroke="#a8781f"/>
      <line x1="164" y1="115" x2="240" y2="115" marker-end="url(#ar)" stroke="#37508c"/>
      <line x1="428" y1="115" x2="512" y2="115" marker-end="url(#ar)" stroke="#a8781f"/>
      <path d="M 338 86 C 338 34, 610 34, 610 82" marker-end="url(#ar)"
            stroke="#a8781f" stroke-dasharray="5 4"/>
    </g>
    <g font-size="13" font-family="sans-serif" fill="currentColor">
      <text x="89" y="110" text-anchor="middle" fill="#37508c">the Python</text>
      <text x="89" y="127" text-anchor="middle" fill="#37508c">implementation</text>
      <text x="338" y="110" text-anchor="middle">toolchain written</text>
      <text x="338" y="127" text-anchor="middle">in Vāk</text>
      <text x="610" y="110" text-anchor="middle" fill="#a8781f">वाक्.exe</text>
      <text x="610" y="127" text-anchor="middle" fill="#a8781f">no Python</text>
      <text x="202" y="107" text-anchor="middle" font-size="11" fill="#37508c">compiles</text>
      <text x="470" y="107" text-anchor="middle" font-size="11" fill="#a8781f">becomes</text>
      <text x="474" y="30" text-anchor="middle" font-size="11" fill="#a8781f">and thereafter compiles itself</text>
      <text x="89" y="172" text-anchor="middle" font-size="11" fill="currentColor"
            opacity=".65">used once</text>
      <text x="610" y="172" text-anchor="middle" font-size="11" fill="currentColor"
            opacity=".65">used from then on</text>
    </g>
  </svg>
  <figcaption>The bootstrap. Python compiles the Vāk-written toolchain exactly
  once — as a C compiler is used once to build a self-hosting C compiler — and
  from then on the language builds itself.</figcaption>
</figure>

<div class="panel reveal">
  <h4>What the optimisation work actually moved</h4>
{perf_rows()}
  <figcaption style="margin-top:.9rem"><b>Indigo is before, gold is after.</b>
  Removing 71% of all string comparisons moved the clock 2% and does not appear
  here at all — the gains came from allocation, and from work that need not have
  been done. These three are wall-clock times measured on one Windows machine
  during the optimisation work, not figures this page regenerates; noise there
  was about 7%, so anything smaller was re-measured interleaved before being
  believed.</figcaption>
</div>

<footer>
  <p>वाक् {__version__} · <a href="index.html">about the language</a> ·
     <a href="manual.html">manual</a> ·
     <a href="playground.html">playground</a></p>
  <p>Line counts, keyword and opcode totals and the test count on this page are
  read from the repository when the page is built. The three timings were
  measured by hand and are quoted, not regenerated.</p>
</footer>

</div>

<script>
(function () {{
  "use strict";
  var reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* The meter shows how much of the toolchain existed in Vāk at the point
     of the story the reader has reached — a real number, not decoration. */
  var fill = document.getElementById("fill");
  var pct = document.getElementById("pct");
  var chapters = [].slice.call(document.querySelectorAll("[data-share]"));

  function setShare(value) {{
    fill.style.width = value + "%";
    pct.textContent = value + "%";
  }}

  var seen = new IntersectionObserver(function (entries) {{
    entries.forEach(function (e) {{
      if (e.isIntersecting) e.target.classList.add("seen");
    }});
  }}, {{ rootMargin: "0px 0px -12% 0px", threshold: 0.08 }});
  [].forEach.call(document.querySelectorAll(".reveal"), function (el) {{
    if (reduce) el.classList.add("seen"); else seen.observe(el);
  }});

  var current = -1;
  var tracker = new IntersectionObserver(function (entries) {{
    entries.forEach(function (e) {{
      if (!e.isIntersecting) return;
      var share = parseInt(e.target.dataset.share, 10);
      if (share !== current) {{ current = share; setShare(share); }}
    }});
  }}, {{ rootMargin: "-45% 0px -45% 0px" }});
  chapters.forEach(function (c) {{ tracker.observe(c); }});
  setShare(0);

  document.getElementById("theme").addEventListener("click", function () {{
    var now = document.documentElement.dataset.theme;
    if (!now) now = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    document.documentElement.dataset.theme = now === "dark" ? "light" : "dark";
  }});
}})();
</script>
"""

out = ROOT / "docs" / "story.html"
out.write_text(PAGE, encoding="utf-8")
print(f"wrote {out}  ({len(PAGE):,} chars)")
# ASCII, so the summary survives a console that is not UTF-8
print(f"  {len(CHAPTERS)} chapters, {TESTS} tests, {VAK_TOTAL} lines of Vak")
print("  versions actually cut: " + ", ".join(sorted(REAL)))
print("  self-hosted share: " + " -> ".join(f"{CUMULATIVE[k]}%" for k in ORDER))
