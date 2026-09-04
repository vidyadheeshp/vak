# -*- coding: utf-8 -*-
"""मानदण्डः — the performance figures, measured rather than remembered.

The README and the story page both quote timings. Until this existed, nobody —
including the author — could reproduce them: they were measured once by hand and
retyped. A performance claim that cannot be re-run is a claim on trust, which is
not the standard the rest of this project holds itself to.

    python bench/benchmark.py                  # measure, print a table
    python bench/benchmark.py --json           # and write bench/results.json
    python bench/benchmark.py --only vaak,c    # a subset, while iterating

Method, stated because it changes the numbers:

  * Best of five runs, not the mean. The fastest run is the one least disturbed
    by everything else on the machine.
  * Whole-process wall clock, startup included, and startup measured separately
    so it can be subtracted mentally. A language that takes 150 ms to boot
    should not be credited for it.
  * Workloads sized so startup is a small fraction of the total. Earlier
    attempts at this used workloads short enough that CPython's startup — which
    varied between 0.067 s and 0.134 s across sessions — dominated the result.
  * Noise on the development machine is around 7%. Two figures within that of
    each other are the same figure.

Every language computes the same answer, and the script checks that it does
before believing the timing.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
BENCH = ROOT / "bench"
RUNS = 5

# The Vāk binary is built under an asciified name, because MinGW cannot open a
# Devanagari output path. Prefer a released वाक्.exe if one is sitting there.
def vak_binary() -> pathlib.Path | None:
    for candidate in (ROOT / "वाक्.exe",
                      ROOT / "स्वयंसिद्धिः" / "vak_adc6e74a.exe"):
        if candidate.exists():
            return candidate
    return None


# ---------------------------------------------------------------- workloads
# Each workload is the same computation in every language, with the answer it
# must produce. If a language disagrees, its timing is not reported: a fast
# wrong answer is not a result.
WORKLOADS = {
    "fib(30) — recursion": {
        "answer": "832040",
        "c": """#include <stdio.h>
long long f(int n){return n<2?n:f(n-1)+f(n-2);}
int main(void){printf("%lld\\n", f(30));return 0;}""",
        "python": """import sys
sys.setrecursionlimit(10000)
def f(n): return n if n < 2 else f(n-1)+f(n-2)
print(f(30))""",
        "js": """function f(n){return n<2?n:f(n-1)+f(n-2);}
console.log(f(30));""",
        "php": """<?php function f($n){return $n<2?$n:f($n-1)+f($n-2);} echo f(30), "\\n";""",
        "vak": """कार्यम् फ(पूर्णाङ्कः न्) : पूर्णाङ्कः {
    यदि (न् < २) { प्रत्यागच्छ न्। }
    प्रत्यागच्छ फ(न् - १) + फ(न् - २)।
}
मुद्रय फ(३०)।""",
    },
    "8 M-iteration loop": {
        "answer": "8000000",
        "c": """#include <stdio.h>
int main(void){long long s=0,i=0;while(i<8000000){s++;i++;}printf("%lld\\n",s);return 0;}""",
        "python": """s=0;i=0
while i<8000000:
    s+=1;i+=1
print(s)""",
        "js": """let s=0,i=0;while(i<8000000){s++;i++;}console.log(s);""",
        "php": """<?php $s=0;$i=0;while($i<8000000){$s++;$i++;} echo $s, "\\n";""",
        "vak": """पूर्णाङ्कः स = ०।
पूर्णाङ्कः क = ०।
यावत् (क < ८०००००० ) { स = स + १। क = क + १। }
मुद्रय स।""",
    },
    "120 k string appends": {
        "answer": "120000",
        "c": """#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(void){size_t cap=1024,len=0;char*b=malloc(cap);
 for(int i=0;i<120000;i++){if(len+2>cap){cap*=2;b=realloc(b,cap);}b[len++]='क';}
 printf("%zu\\n",len);free(b);return 0;}""",
        # s = s + "क" in a loop, matching what the Vāk program does. Using
        # "".join(list) would be the idiomatic Python and a different
        # algorithm — the point here is repeated concatenation, so both sides
        # must repeatedly concatenate.
        "python": """s=""
for _ in range(120000): s = s + "क"
print(len(s))""",
        "js": """let s="";for(let i=0;i<120000;i++)s+="क";console.log(s.length);""",
        "php": """<?php $s="";for($i=0;$i<120000;$i++)$s.="x"; echo strlen($s), "\\n";""",
        "vak": """शब्दः अ = ""।
पूर्णाङ्कः क = ०।
यावत् (क < १२०००० ) { अ = अ + "क"। क = क + १। }
मुद्रय दीर्घता(अ)।""",
    },
    "1.2 M list operations": {
        "answer": "1200000",
        "c": """#include <stdio.h>
#include <stdlib.h>
int main(void){size_t cap=16,n=0;long long*a=malloc(cap*sizeof(long long));
 for(int i=0;i<1200000;i++){if(n==cap){cap*=2;a=realloc(a,cap*sizeof(long long));}a[n++]=i;}
 printf("%zu\\n",n);free(a);return 0;}""",
        "python": """a=[]
for i in range(1200000): a.append(i)
print(len(a))""",
        "js": """const a=[];for(let i=0;i<1200000;i++)a.push(i);console.log(a.length);""",
        "php": """<?php $a=[];for($i=0;$i<1200000;$i++)$a[]=$i; echo count($a), "\\n";""",
        "vak": """सूची स = []।
पूर्णाङ्कः क = ०।
यावत् (क < १२००००० ) { योजय(स, क)। क = क + १। }
मुद्रय दीर्घता(स)।""",
    },
    "startup": {
        "answer": "0",
        "c": """#include <stdio.h>\nint main(void){printf("0\\n");return 0;}""",
        "python": """print(0)""",
        "js": """console.log(0);""",
        "php": """<?php echo 0, "\\n";""",
        "vak": """मुद्रय ०।""",
    },
}

LANGUAGES = ["c", "python", "js", "php", "vak"]
LABELS = {"c": "C −O2", "python": "CPython", "js": "Node/V8",
          "php": "PHP", "vak": "वाक्"}
SUFFIX = {"c": ".c", "python": ".py", "js": ".js", "php": ".php", "vak": ".vak"}


def command(lang: str, path: pathlib.Path, work: pathlib.Path) -> list[str] | None:
    """How to run this language's file, compiling first where that is the point."""
    if lang == "c":
        gcc = shutil.which("gcc") or shutil.which("clang")
        if gcc is None:
            return None
        exe = work / (path.stem + ".exe")
        built = subprocess.run([gcc, "-O2", "-o", str(exe), str(path)],
                               capture_output=True)
        return [str(exe)] if built.returncode == 0 else None
    if lang == "python":
        return [sys.executable, str(path)]
    if lang == "js":
        node = shutil.which("node")
        return [node, str(path)] if node else None
    if lang == "php":
        php = shutil.which("php")
        return [php, str(path)] if php else None
    if lang == "vak":
        binary = vak_binary()
        return [str(binary), str(path)] if binary else None
    return None


def measure(cmd: list[str], expected: str) -> float | None:
    """Best of RUNS, or None if the answer is wrong — a fast wrong answer is
    not a result."""
    best = None
    for _ in range(RUNS):
        start = time.perf_counter()
        done = subprocess.run(cmd, capture_output=True)
        elapsed = time.perf_counter() - start
        if done.returncode != 0:
            return None
        got = done.stdout.decode("utf-8", "replace").strip()
        if got != expected:
            print(f"      wrong answer: {got!r}, expected {expected!r}")
            return None
        best = elapsed if best is None else min(best, elapsed)
    return best


def main() -> int:
    ap = argparse.ArgumentParser(description="measure Vāk against other languages")
    ap.add_argument("--json", action="store_true", help="write bench/results.json")
    ap.add_argument("--only", default="", help="comma-separated subset of languages")
    args = ap.parse_args()

    wanted = [l for l in LANGUAGES
              if not args.only or l in args.only.split(",")]
    work = pathlib.Path(tempfile.mkdtemp(prefix="vak-bench-"))
    results: dict[str, dict[str, float | None]] = {}

    for title, spec in WORKLOADS.items():
        print(f"  {title}")
        results[title] = {}
        for lang in wanted:
            source = spec.get(lang)
            if source is None:
                continue
            path = work / (f"{abs(hash(title)) % 99999}_{lang}{SUFFIX[lang]}")
            path.write_text(source, encoding="utf-8")
            cmd = command(lang, path, work)
            if cmd is None:
                print(f"      {LABELS[lang]:10} not available")
                continue
            seconds = measure(cmd, spec["answer"])
            results[title][lang] = seconds
            shown = f"{seconds:.3f} s" if seconds else "failed"
            print(f"      {LABELS[lang]:10} {shown}")

    print("\n" + table(results, wanted))

    if args.json:
        out = BENCH / "results.json"
        out.write_text(json.dumps(
            {"runs": RUNS, "results": results,
             "note": "best of %d whole-process runs; ~7%% noise" % RUNS},
            indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nwrote {out}")
    return 0


NOISE = 0.07          # measured spread on the development machine


def table(results: dict, langs: list[str]) -> str:
    """The README's table, regenerated, with startup taken out."""
    startup = results.get("startup", {})
    head = "| workload | " + " | ".join(LABELS[l] for l in langs) + " |"
    rule = "|---" * (len(langs) + 1) + "|"
    rows = [head, rule]
    for title, row in results.items():
        cells = []
        for lang in langs:
            seconds = row.get(lang)
            if seconds is None:
                cells.append("—")
                continue
            if title == "startup":
                cell = f"{seconds:.3f} s"
            else:
                base = startup.get(lang) or 0.0
                corrected = seconds - base
                # below the noise floor the subtraction has eaten the signal
                cell = (f"{corrected:.3f} s"
                        if corrected > base * NOISE + 0.005 else "< startup")
            cells.append(f"**{cell}**" if lang == "vak" else cell)
        label = f"**{title}**" if title == "startup" else f"`{title}`"
        rows.append(f"| {label} | " + " | ".join(cells) + " |")
    rows.append("")
    rows.append("Work only — each language's own startup has been subtracted. "
                '"< startup" means the workload is too small for that language '
                "to be measured this way, not that it is instant.")
    return "\n".join(rows)


if __name__ == "__main__":
    raise SystemExit(main())
