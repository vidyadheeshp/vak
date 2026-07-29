# -*- coding: utf-8 -*-
"""क्रीडाक्षेत्रम् — generate docs/playground.html.

The whole Vāk toolchain, compiled to WebAssembly: the page lexes, parses,
analyses, compiles and runs Vāk without a server and without Python.  One
self-contained file, so it works on GitHub Pages and anywhere else.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
WASM = pathlib.Path("C:/Users/Admin/AppData/Local/Temp/claude/"
                    "c--Users-Admin-Documents-Sanskrit-Vak/"
                    "4c4fd862-0883-4daa-adec-bd1c7d0a2de1/scratchpad/wasm/vak.js")

engine = WASM.read_text(encoding="utf-8")

# the standard library travels with the page and is written into the virtual
# filesystem at startup, so आनय works in the browser
library = {}
for f in sorted((ROOT / "vak" / "पुस्तकालयः").glob("*.vak")):
    library["/vak/पुस्तकालयः/" + f.name] = f.read_text(encoding="utf-8")

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
  <button id="theme" type="button">theme</button>
</header>

<main>
  <section class="pane">
    <div class="bar">
      <span class="label">प्रोग्रामः</span>
      <select id="samples" aria-label="Load an example"></select>
      <span class="spacer"></span>
      <button id="check" type="button">परीक्षा · check</button>
      <button id="run" class="go" type="button">चालय · run ⏎</button>
    </div>
    <textarea id="src" spellcheck="false" aria-label="Vāk source"></textarea>
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
  picker.addEventListener("change", function () {
    src.value = SAMPLES[picker.value];
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
  function boot() {
    return VakModule({
      noInitialRun: true,
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
    if (e.key === "Tab") {
      e.preventDefault();
      var a = src.selectionStart, b = src.selectionEnd;
      src.value = src.value.slice(0, a) + "    " + src.value.slice(b);
      src.selectionStart = src.selectionEnd = a + 4;
    }
  });

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
from vak import __version__                                    # noqa: E402

page = (PAGE
        .replace("__ENGINE__", engine)
        .replace("__SAMPLES__", json.dumps(SAMPLES, ensure_ascii=False))
        .replace("__LIBRARY__", json.dumps(library, ensure_ascii=False))
        .replace("__VERSION__", __version__))

out = ROOT / "docs" / "playground.html"
out.write_text(page, encoding="utf-8")
print(f"wrote {out}  ({len(page):,} bytes, {len(SAMPLES)} samples, "
      f"{len(library)} library files)")
