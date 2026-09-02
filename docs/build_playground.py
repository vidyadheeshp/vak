# -*- coding: utf-8 -*-
"""क्रीडाक्षेत्रम् — generate docs/playground.html.

The whole Vāk toolchain, compiled to WebAssembly: the page lexes, parses,
analyses, compiles and runs Vāk without a server and without Python.  One
self-contained file, so it works on GitHub Pages and anywhere else.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
# built by:  emcc -O2 -DVAK_POSIX <generated>.c native/*.c -sSINGLE_FILE=1 …
WASM = ROOT / "_wasm" / "vak.js"

engine = WASM.read_text(encoding="utf-8")

# the typing aid, from the same tables as vaak/translit.py
import sys                                                    # noqa: E402
sys.path.insert(0, str(ROOT))
import json as _json                                          # noqa: E402
from vaak.translit import tables_for_js                        # noqa: E402

_t = tables_for_js()
_combined = (
    [[k, "C", v] for k, v in _t["consonants"].items()]
    + [[k, "V", v[0], v[1]] for k, v in _t["vowels"].items()]
    + [[k, "M", v] for k, v in _t["marks"].items()]
)
_combined.sort(key=lambda e: len(e[0]), reverse=True)
TR_KEYWORDS = "const TR_KEYWORDS = " + _json.dumps(_t["keywords"], ensure_ascii=False) + ";"

TRANSLIT = (
    "const TR_TABLE = " + _json.dumps(_combined, ensure_ascii=False) + ";\n"
    "const TR_DIGITS = " + _json.dumps(_t["digits"], ensure_ascii=False) + ";\n"
    "const TR_VIRAMA = " + _json.dumps(_t["virama"], ensure_ascii=False) + ";\n"
)

# the standard library travels with the page and is written into the virtual
# filesystem at startup, so आनय works in the browser
library = {}
for f in sorted((ROOT / "vaak" / "पुस्तकालयः").glob("*.vak")):
    library["/vaak/पुस्तकालयः/" + f.name] = f.read_text(encoding="utf-8")

SAMPLES = {
    "नमस्ते": '''मुद्रय "नमस्ते जगत्"।

शब्दः नाम = "वाक्"।
पूर्णाङ्कः वर्षम् = २०२६।
मुद्रय "भाषायाः नाम:", नाम।
मुद्रय "वर्षम्:", देवनागरी(वर्षम्)।''',

    "कारकाणि": '''# कारकाणि — प्राचलः स्वकीयां भूमिकां घोषयति।
# A parameter declares the role it plays in the action.
कार्यम् छानय(अपादानम् सूची संग्रहः, करणम् कार्यम् परीक्षा) : सूची {
    सूची फलम् = []।
    प्रत्येकम् (अङ्गम् अन्तः संग्रहः) {
        यदि (परीक्षा(अङ्गम्)) { योजय(फलम्, अङ्गम्)। }
    }
    प्रत्यागच्छ फलम्।
}

कार्यम् समः(पूर्णाङ्कः सङ्ख्या) : सत्यता {
    प्रत्यागच्छ सङ्ख्या % २ == ०।
}

मान अङ्काः = [१, २, ३, ४, ५, ६, ७, ८]।

# भूमिकाः अङ्किताः इति क्रमः न बध्नाति — त्रयोऽपि एकम् एव आह्वानम्।
मुद्रय छानय(अङ्काः, समः)।
मुद्रय छानय(अपादानम्: अङ्काः, करणम्: समः)।
मुद्रय छानय(करणम्: समः, अपादानम्: अङ्काः)।''',

    "विकल्पः": '''कार्यम् वासरनाम(कर्म पूर्णाङ्कः वारः) : शब्दः {
    विकल्पः (वारः) {
        पक्षे १: प्रत्यागच्छ "सोमवासरः"।
        पक्षे २, ३: प्रत्यागच्छ "मङ्गलः बुधः वा"।
        पक्षे ६, ७: प्रत्यागच्छ "सप्ताहान्तः"।
        अन्यथा: प्रत्यागच्छ "अज्ञातः वासरः"।
    }
}

प्रत्येकम् (वारः अन्तः परास(१, ९)) {
    मुद्रय देवनागरी(वारः), "—", वासरनाम(वारः)।
}''',

    "दोषनिग्रहः": '''# प्रयत्नः — दोषे — अन्ततः
कार्यम् भज(पूर्णाङ्कः अंशः, पूर्णाङ्कः हरः) : अङ्कः {
    यदि (हरः == ०) {
        उत्सृज { "प्रकारः": "गणितदोषः", "सन्देशः": "शून्येन भागः न सम्भवति" }।
    }
    प्रत्यागच्छ अंशः / हरः।
}

प्रत्येकम् (हरः अन्तः [२, ०, ५]) {
    प्रयत्नः {
        मुद्रय "१००  /", देवनागरी(हरः), "=", भज(१००, हरः)।
    } दोषे (द) {
        मुद्रय "दोषः:", द.प्रकारः, "—", द.सन्देशः।
    } अन्ततः {
        मुद्रय "  (प्रयत्नः समाप्तः)"।
    }
}''',

    "ASCII": '''# purnataya romanized — no Devanagari keyboard needed
karyam varga(purnankah a) : purnankah {
    pratyagaccha a * a;
}

mudraya "vargani / squares:";
pratyekam (n antah [1, 2, 3, 4, 5]) {
    mudraya " ", n, "->", varga(n);
}

purnankah yoga = 0;
yavat (yoga < 10) { yoga += 3; }
mudraya "yoga =", yoga;''',

    "प्रदानम्": '''# पठ() उपयोक्तुः पङ्क्तिम् पठति — प्रदानपेटिकाम् अधः पश्यतु।
# पठ() reads a line from the user; see the input box below the editor.
शब्दः नाम = पठ("नाम किम्? ")।
मुद्रय "नमस्ते,", नाम + "!"।

पूर्णाङ्कः वयः = संख्या(पठ("वयः? "))।
मुद्रय "आगामिवर्षे भवतः वयः", वयः + १, "भविष्यति।"।''',

    "गणितम्": '''आनय "गणितम्" इति ग।

मुद्रय "पाई             =", ग.पाई।
मुद्रय "वर्गः(१२)        =", ग.वर्गः(१२)।
मुद्रय "क्रमगुणितम्(१०)   =", ग.क्रमगुणितम्(१०)।
मुद्रय "मसाभा(४८, १८)   =", ग.मसाभा(४८, १८)।
मुद्रय "अभाज्याः ३० यावत् =", ग.अभाज्याः_यावत्(३०)।
मुद्रय "माध्यम् (कारकेण)  =", ग.माध्यम्(अपादानम्: [१०, २०, ३०])।''',
}

PAGE = """<title>वाक् · क्रीडाक्षेत्रम् — run Sanskrit in your browser</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="favicon.ico" sizes="any">
<style>
:root {
  --ink:#16223f; --ink-soft:#4a5570; --ink-faint:#7c8499; --paper:#f7f6f1;
  --paper-2:#eeece4; --rule:#cfcdc2; --gold:#a8781f; --gold-lit:#f0e4c4;
  --indigo:#37508c; --crimson:#9a3324; --good:#2f6b45;
}
@media (prefers-color-scheme: dark) {
  :root {
    --ink:#e6e3d9; --ink-soft:#a9aec0; --ink-faint:#767d92; --paper:#10141f;
    --paper-2:#171c2b; --rule:#2c3346; --gold:#d8a94a; --gold-lit:#2a2415;
    --indigo:#8aa2df; --crimson:#e0806e; --good:#6fbf8e;
  }
}
:root[data-theme="light"] {
  --ink:#16223f; --ink-soft:#4a5570; --ink-faint:#7c8499; --paper:#f7f6f1;
  --paper-2:#eeece4; --rule:#cfcdc2; --gold:#a8781f; --gold-lit:#f0e4c4;
  --indigo:#37508c; --crimson:#9a3324; --good:#2f6b45;
}
:root[data-theme="dark"] {
  --ink:#e6e3d9; --ink-soft:#a9aec0; --ink-faint:#767d92; --paper:#10141f;
  --paper-2:#171c2b; --rule:#2c3346; --gold:#d8a94a; --gold-lit:#2a2415;
  --indigo:#8aa2df; --crimson:#e0806e; --good:#6fbf8e;
}
html {
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,
          "Nirmala UI","Noto Serif Devanagari",serif;
  --sans:"Segoe UI",-apple-system,"Helvetica Neue",Arial,"Nirmala UI",
         "Noto Sans Devanagari",sans-serif;
  --mono:"Cascadia Mono",Consolas,"SF Mono",Menlo,"DejaVu Sans Mono","Nirmala UI",
         "Noto Sans Devanagari",monospace;
  box-sizing:border-box; -webkit-text-size-adjust:100%;
}
*,*::before,*::after { box-sizing:inherit; }
body {
  margin:0; background:var(--paper); color:var(--ink);
  font-family:var(--serif); font-size:16px; line-height:1.6;
  min-height:100vh; display:flex; flex-direction:column;
}
header {
  border-bottom:1.5px solid var(--ink); padding:1.1rem clamp(1rem,3vw,2rem) .7rem;
  display:flex; align-items:baseline; gap:1rem; flex-wrap:wrap;
}
header h1 { margin:0; font-size:1.6rem; font-weight:500; letter-spacing:-.01em; }
header .sub {
  margin:0; font-family:var(--sans); font-size:.75rem; letter-spacing:.1em;
  text-transform:uppercase; color:var(--ink-faint);
}
header .spacer { flex:1; }
header a { color:var(--gold); font-family:var(--sans); font-size:.8rem; }

main {
  flex:1; display:grid; grid-template-columns:1fr 1fr; gap:0;
  min-height:0; border-bottom:1.5px solid var(--ink);
}
.pane { display:flex; flex-direction:column; min-width:0; min-height:22rem; }
.pane + .pane { border-left:1px solid var(--rule); }
.bar {
  display:flex; align-items:center; gap:.4rem; flex-wrap:wrap;
  padding:.5rem clamp(.7rem,2vw,1.1rem); border-bottom:1px solid var(--rule);
  background:var(--paper-2);
}
.bar .label {
  font-family:var(--sans); font-size:.7rem; letter-spacing:.09em;
  text-transform:uppercase; color:var(--ink-faint); margin-right:.2rem;
}
.bar .spacer { flex:1; }
button, select {
  font:inherit; font-family:var(--sans); font-size:.76rem; letter-spacing:.02em;
  color:var(--ink-soft); background:transparent; border:1px solid var(--rule);
  border-radius:2px; padding:.3rem .62rem; cursor:pointer;
}
button:hover:not(:disabled), button:focus-visible,
select:hover, select:focus-visible { border-color:var(--gold); color:var(--gold); }
button:disabled { opacity:.45; cursor:progress; }
button.go { border-color:var(--gold); color:var(--gold); font-weight:600; }
button.go:hover:not(:disabled) { background:var(--gold-lit); }

textarea, pre.out {
  flex:1; margin:0; padding:.9rem clamp(.7rem,2vw,1.1rem);
  font-family:var(--mono); font-size:.86rem; line-height:1.72;
  background:var(--paper); color:var(--ink); border:0; resize:none;
  overflow:auto; white-space:pre; tab-size:4;
}
textarea:focus-visible { outline:2px solid var(--gold); outline-offset:-2px; }
pre.out { color:var(--ink-soft); }
pre.out .err { color:var(--crimson); }
pre.out .ok { color:var(--good); }
pre.out .dim { color:var(--ink-faint); font-style:italic; }

.feed { border-top:1px solid var(--rule); background:var(--paper-2); }
.feed label {
  display:block; padding:.45rem clamp(.7rem,2vw,1.1rem) 0;
  font-family:var(--sans); font-size:.7rem; letter-spacing:.09em;
  text-transform:uppercase; color:var(--ink-faint);
}
.feed label span { text-transform:none; letter-spacing:0; opacity:.85; }
.feed textarea {
  display:block; width:100%; flex:none; background:var(--paper-2);
  padding:.35rem clamp(.7rem,2vw,1.1rem) .7rem; resize:vertical;
  min-height:2.6rem; font-size:.82rem;
}

footer {
  padding:.6rem clamp(1rem,3vw,2rem); font-family:var(--sans); font-size:.73rem;
  color:var(--ink-faint); display:flex; gap:1rem; flex-wrap:wrap;
  align-items:center;
}
footer .spacer { flex:1; }
footer b { color:var(--ink-soft); font-weight:500; }

@media (max-width:52rem) {
  main { grid-template-columns:1fr; }
  .pane + .pane { border-left:0; border-top:1px solid var(--rule); }
}
@media (prefers-reduced-motion:reduce) { * { transition:none !important; } }
</style>

<header>
  <h1>वाक्</h1>
  <p class="sub">क्रीडाक्षेत्रम् · playground</p>
  <span class="spacer"></span>
  <a href="index.html">← वाक्</a>
  <a href="manual.html">पुस्तिका · the manual</a>
  <a href="story.html">कथा · the story</a>
  <button id="theme" type="button">theme</button>
</header>

<main>
  <section class="pane">
    <div class="bar">
      <span class="label">प्रोग्रामः</span>
      <select id="samples" aria-label="Load an example"></select>
      <span class="spacer"></span>
      <button id="typing" type="button" aria-pressed="true"
              title="Type romanised, get Devanagari in code (ITRANS: aa A T D N S ~N H M)">देवनागरी ✓</button>
      <button id="check" type="button">परीक्षा · check</button>
      <button id="run" class="go" type="button">चालय · run ⏎</button>
    </div>
    <textarea id="src" spellcheck="false" aria-label="Vāk source"></textarea>
    <div class="feed">
      <label for="stdin">प्रदानम् · input <span>— what पठ() reads, one line
        per call</span></label>
      <textarea id="stdin" spellcheck="false" rows="2"
                aria-label="Standard input for the program"></textarea>
    </div>
  </section>

  <section class="pane">
    <div class="bar">
      <span class="label">फलम्</span>
      <span class="spacer"></span>
      <button id="clear" type="button">रिक्तम् · clear</button>
    </div>
    <pre class="out" id="out" aria-live="polite" aria-atomic="false"></pre>
  </section>
</main>

<footer>
  <span>वाक् __VERSION__ — the whole toolchain in WebAssembly: this page lexes,
  parses, analyses, compiles and runs Vāk itself.</span>
  <span class="spacer"></span>
  <span><b>Ctrl/⌘ + Enter</b> runs</span>
</footer>

<script>__ENGINE__</script>
<script>
(function () {
  "use strict";

  var SAMPLES = __SAMPLES__;
  var LIBRARY = __LIBRARY__;

  __TRANSLIT__

  /* लिप्यन्तरणम् — Vāk never transliterates identifiers, so the help belongs
     where you type.  Finish a word and the romanised form becomes Devanagari. */
  function devanagari(text, digits) {
    var out = "", i = 0, pending = false;
    outer:
    while (i < text.length) {
      for (var e = 0; e < TR_TABLE.length; e++) {
        var entry = TR_TABLE[e], key = entry[0];
        if (text.substr(i, key.length) !== key) continue;
        if (entry[1] === "C") {
          if (pending) out += TR_VIRAMA;
          out += entry[2]; pending = true;
        } else if (entry[1] === "V") {
          out += pending ? entry[3] : entry[2]; pending = false;
        } else {
          out += out.length ? entry[2] : key; pending = false;
        }
        i += key.length;
        continue outer;
      }
      if (pending) { out += TR_VIRAMA; pending = false; }
      var ch = text[i];
      out += (digits && TR_DIGITS[ch]) ? TR_DIGITS[ch] : ch;
      i += 1;
    }
    if (pending) out += TR_VIRAMA;
    return out;
  }

  var src = document.getElementById("src");
  var out = document.getElementById("out");
  var runBtn = document.getElementById("run");
  var checkBtn = document.getElementById("check");
  var picker = document.getElementById("samples");
  var names = Object.keys(SAMPLES);

  names.forEach(function (n) {
    var o = document.createElement("option");
    o.value = n; o.textContent = n;
    picker.appendChild(o);
  });
  /* आगतः सङ्केतः — a program handed over in the URL, from the landing page.
     Base64 of the UTF-8 bytes, so Devanagari survives the trip. */
  function fromHash() {
    var m = /[#&]code=([^&]+)/.exec(location.hash || "");
    if (!m) return null;
    try {
      var bin = atob(decodeURIComponent(m[1]).replace(/-/g, "+").replace(/_/g, "/"));
      var bytes = Uint8Array.from(bin, function (c) { return c.charCodeAt(0); });
      return new TextDecoder().decode(bytes);
    } catch (e) { return null; }
  }
  var handed = fromHash();
  src.value = handed || SAMPLES[names[0]];
  /* the reading sample is useless without something to read */
  var SAMPLE_INPUT = { "प्रदानम्": "विद्याधीश\\n38" };
  picker.addEventListener("change", function () {
    src.value = SAMPLES[picker.value];
    document.getElementById("stdin").value = SAMPLE_INPUT[picker.value] || "";
    src.focus();
  });

  function write(text, cls) {
    var span = document.createElement("span");
    if (cls) span.className = cls;
    span.textContent = text + "\\n";
    out.appendChild(span);
    out.scrollTop = out.scrollHeight;
  }
  document.getElementById("clear").addEventListener("click", function () {
    out.textContent = "";
  });

  /* एकम् एव यन्त्रम् — a fresh module per run, so one program's state can never
     leak into the next.  Instantiation is cheap; the wasm is already compiled. */
  var lines = [];

  /* प्रदानम् — Emscripten asks for stdin one byte at a time and takes null as
     end of input, so the input pane is handed over as a byte feeder. */
  function feeder(text) {
    var bytes = new TextEncoder().encode(text);
    var i = 0;
    return function () { return i < bytes.length ? bytes[i++] : null; };
  }

  function boot() {
    var given = document.getElementById("stdin").value;
    if (given && !/\\n$/.test(given)) given += "\\n";   // पठ wants a full line
    return VakModule({
      noInitialRun: true,
      stdin: feeder(given),
      print: function (t) { lines.push(["", t]); },
      printErr: function (t) { lines.push(["err", t]); },
    });
  }

  function go(check) {
    lines = [];
    runBtn.disabled = checkBtn.disabled = true;
    var started = performance.now();
    boot().then(function (mod) {
      Object.keys(LIBRARY).forEach(function (path) {
        var dir = path.slice(0, path.lastIndexOf("/"));
        try { mod.FS.mkdirTree(dir); } catch (e) { /* already there */ }
        mod.FS.writeFile(path, LIBRARY[path]);
      });
      mod.FS.writeFile("/program.vak", src.value);
      var args = check ? ["--परीक्षा", "/program.vak"] : ["/program.vak"];
      try {
        mod.callMain(args);
      } catch (e) {
        lines.push(["err", String(e && e.message ? e.message : e)]);
      }
      var ms = Math.round(performance.now() - started);
      lines.forEach(function (l) { write(l[1], l[0]); });
      if (!lines.length) write(check ? "अर्थविश्लेषणम् निर्दोषम्" : "(फलम् नास्ति)", "dim");
      write("— " + (check ? "परीक्षा" : "चालनम्") + " " + ms + " ms —", "dim");
      runBtn.disabled = checkBtn.disabled = false;
      src.focus();
    }).catch(function (e) {
      write("यन्त्रदोषः / the engine failed to start: " + e, "err");
      runBtn.disabled = checkBtn.disabled = false;
    });
  }

  runBtn.addEventListener("click", function () { go(false); });
  checkBtn.addEventListener("click", function () { go(true); });
  src.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); go(false); }
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === "D" || e.key === "d")) {
      e.preventDefault();
      convertSelection();
      return;
    }
    if (e.key === "Tab") {
      e.preventDefault();
      var a = src.selectionStart, b = src.selectionEnd;
      src.value = src.value.slice(0, a) + "    " + src.value.slice(b);
      src.selectionStart = src.selectionEnd = a + 4;
    }
  });

  /* सन्दर्भः — where the caret sits decides whether romanised input converts.
     Code becomes Devanagari; the inside of a string or a comment does not,
     because मुद्रय "Hello, world" is the author's own text and converting it
     would be wrong.  Vāk's own rules: "..." and '...' with backslash escapes,
     hash and double-slash to end of line, and slash-star block comments. */
  function contextAt(text, index) {
    var i = 0;
    while (i < index) {
      var c = text.charAt(i), d = text.charAt(i + 1);
      if (c === '"' || c === "'") {
        var quote = c, closed = false;
        i++;
        while (i < index) {
          if (text.charAt(i) === "\\\\") { i += 2; continue; }
          if (text.charAt(i) === quote) { i++; closed = true; break; }
          i++;
        }
        if (!closed) return "string";
        continue;
      }
      if (c === "#" || (c === "/" && d === "/")) {
        while (i < index && text.charAt(i) !== "\\n") i++;
        if (i >= index) return "comment";
        continue;
      }
      if (c === "/" && d === "*") {
        i += 2;
        while (i < index && !(text.charAt(i) === "*" && text.charAt(i + 1) === "/")) i++;
        if (i >= index) return "comment";
        i += 2;
        continue;
      }
      i++;
    }
    return "code";
  }

  /* On by default: this page exists to be tried, and most people arriving at it
     have no Devanagari keyboard. */
  var typingOn = true;
  var typingBtn = document.getElementById("typing");
  function setTyping(on) {
    typingOn = on;
    typingBtn.setAttribute("aria-pressed", String(on));
    typingBtn.textContent = on ? "देवनागरी ✓" : "देवनागरी";
    typingBtn.title = on
      ? 'Romanised typing becomes Devanagari in code. Inside strings and comments your text is left alone — select it and press Ctrl+Shift+D to convert it anyway.'
      : 'Romanised typing is off; what you type is left as it is.';
  }
  typingBtn.addEventListener("click", function () {
    setTyping(!typingOn);
    src.focus();
  });
  setTyping(true);

  var ROMAN_TAIL = /[A-Za-z~^.]+$/;
  src.addEventListener("input", function (e) {
    if (!typingOn) return;
    if (e.inputType !== "insertText" || !e.data) return;
    if (/[A-Za-z~^.]/.test(e.data)) return;      // still inside a word
    var at = src.selectionStart - e.data.length;
    var before = src.value.slice(0, at);
    var m = ROMAN_TAIL.exec(before);
    if (!m) return;
    var start = at - m[0].length;
    // the word's own position decides, not the caret's: by now the caret may
    // already have crossed a closing quote
    if (contextAt(src.value, start) !== "code") return;
    // A language word is not a phonetic problem: `mana` transliterates to मन,
    // but the keyword is मान, and converting it phonetically would turn valid
    // ASCII Vāk into Devanagari that does not compile.
    var out = TR_KEYWORDS[m[0]] || devanagari(m[0], true);
    if (out === m[0]) return;
    var after = src.selectionStart;
    src.value = src.value.slice(0, start) + out + src.value.slice(at, after)
              + src.value.slice(after);
    src.selectionStart = src.selectionEnd = start + out.length + e.data.length;
  });

  /* The deliberate escape hatch, both ways: select any text and convert it,
     wherever it sits.  This is how you put Devanagari inside a string. */
  function convertSelection() {
    var a = src.selectionStart, b = src.selectionEnd;
    if (a === b) {
      write("चयनम् नास्ति / select some text first, then Ctrl+Shift+D", "dim");
      return;
    }
    var chosen = src.value.slice(a, b);
    var out = TR_KEYWORDS[chosen] || devanagari(chosen, true);
    if (out === chosen) {
      write("अपरिवर्तितम् / nothing in the selection is romanised Vāk", "dim");
      return;
    }
    src.value = src.value.slice(0, a) + out + src.value.slice(b);
    src.selectionStart = a;
    src.selectionEnd = a + out.length;
    src.focus();
    write("लिप्यन्तरितम् / converted: " + chosen + " → " + out, "ok");
  }

  document.getElementById("theme").addEventListener("click", function () {
    var now = document.documentElement.dataset.theme;
    if (!now) {
      now = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    document.documentElement.dataset.theme = now === "dark" ? "light" : "dark";
  });

  write("वाक् __VERSION__ — सिद्धम्। 'चालय' इति नुदतु।", "ok");
  write("ready — press Run, or Ctrl/⌘+Enter.", "dim");
  if (handed) go(false);          /* it was sent here to be run */
})();
</script>
"""

import sys
sys.path.insert(0, str(ROOT))
from vaak import __version__                                    # noqa: E402

page = (PAGE
        .replace("__ENGINE__", engine)
        .replace("__SAMPLES__", json.dumps(SAMPLES, ensure_ascii=False))
        .replace("__LIBRARY__", json.dumps(library, ensure_ascii=False))
        .replace("__TRANSLIT__", TR_KEYWORDS + "\n  " + TRANSLIT)
        .replace("__VERSION__", __version__))

# ------------------------------------------------------------------ परीक्षा
# This page shipped with a raw newline inside a JS string literal, which is a
# syntax error that kills the whole script — the playground was dead and the
# generator reported success. Nothing here is worth trusting to inspection, so
# the emitted script is parsed before it is written.
def _syntax_check(page_html: str) -> None:
    import re as _re, shutil as _shutil, subprocess as _sp, tempfile as _tf

    script = _re.findall(r"<script>(.*?)</script>", page_html, _re.S)[-1]
    node = _shutil.which("node")
    if node is None:
        print("  note: node not found — the page's JS was NOT syntax-checked")
        return
    tmp = pathlib.Path(_tf.mkdtemp()) / "page.js"
    tmp.write_text(script, encoding="utf-8")
    result = _sp.run([node, "--check", str(tmp)], capture_output=True,
                     encoding="utf-8", errors="replace")
    if result.returncode:
        raise SystemExit("the generated JavaScript does not parse:\n"
                         + (result.stderr or "")[:1200])
    print(f"  javascript: parses ({len(script):,} chars)")


_syntax_check(page)

out = ROOT / "docs" / "playground.html"
out.write_text(page, encoding="utf-8")
print(f"wrote {out}  ({len(page):,} bytes, {len(SAMPLES)} samples, "
      f"{len(library)} library files)")
