# -*- coding: utf-8 -*-
"""यन्त्रस्य मूलम् — what the playground's WebAssembly engine was built from.

The playground runs Vāk in the browser from one artifact: the self-hosted
toolchain (स्वयंसिद्धिः/वाक्.vak) compiled to C by vaak/native.py, linked with
the C runtime in native/, and compiled by Emscripten. That artifact is
gitignored and inlined into docs/playground.html, so the page is the only
place it is ever committed — and the only place its provenance can live.

Nothing here does anything at import time, so the test suite, the engine
build and the page generator can all use it without writing a file.

Why a fingerprint of the *generated C*, not of the sources: the engine depends
on the Vāk-written toolchain, on the compiler that turns it into bytecode and
on the emitter that turns that into C, as well as on the runtime. Hashing any
subset of those would miss the others — an earlier version of this check
hashed only native/*.c and would never have noticed कुरु being added to the
parser. The generated C is a deterministic function of all of them, so one
hash covers the lot, and nothing that does not change the engine can trip it.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WASM_DIR = ROOT / "_wasm"
ENGINE_JS = WASM_DIR / "vak.js"
ENGINE_C = WASM_DIR / "vak_wasm.c"
MANIFEST = WASM_DIR / "sources.json"
TOOLCHAIN = ROOT / "स्वयंसिद्धिः" / "वाक्.vak"
RUNTIME_SOURCES = ("mulyani.c", "antarnihitani.c", "yantram.c", "vak.h")

#: The emcc invocation, in one place. The engine was once built with flags that
#: survived only as a comment ending in "…", which made rebuilding it guesswork.
EMCC_FLAGS = (
    "-std=c11", "-O2", "-DVAK_POSIX",
    "-sSINGLE_FILE=1",                        # one .js, so the page can inline it
    "-sMODULARIZE=1", "-sEXPORT_NAME=VakModule",
    "-sEXPORTED_RUNTIME_METHODS=callMain,FS",  # the page calls both
    "-sINVOKE_RUN=0",                         # a fresh module per run, driven by callMain
    "-sALLOW_MEMORY_GROWTH=1",
    "-sFORCE_FILESYSTEM=1",                   # the standard library is written into it
)

_PAGE_MARK = re.compile(r"<!-- वाक्-यन्त्रम् (\{.*?\}) -->")


def generate_engine_c() -> str:
    """The C the engine is compiled from, exactly as build_wasm.py writes it."""
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from vaak.native import generate_c
    return generate_c(TOOLCHAIN.read_text(encoding="utf-8"), TOOLCHAIN)


def fingerprint(generated_c: str | None = None) -> dict[str, str]:
    """What an engine built right now would be built from."""
    if generated_c is None:
        generated_c = generate_engine_c()
    # Line endings are folded before hashing. Git on Windows checks these files
    # out with CRLF and the Linux runner with LF; hashing raw bytes would call a
    # current engine stale on whichever platform did not build it. The
    # generated C needs no such care — the lexer already makes it identical.
    lf = generated_c.replace("\r\n", "\n")
    out = {"generated": hashlib.sha256(lf.encode("utf-8")).hexdigest()}
    for name in RUNTIME_SOURCES:
        data = (ROOT / "native" / name).read_bytes().replace(b"\r\n", b"\n")
        out[f"native/{name}"] = hashlib.sha256(data).hexdigest()
    return out


def page_comment(prints: dict[str, str]) -> str:
    """The provenance line docs/playground.html carries."""
    return f"<!-- वाक्-यन्त्रम् {json.dumps(prints, sort_keys=True)} -->"


def fingerprint_in_page(html: str) -> dict[str, str] | None:
    found = _PAGE_MARK.search(html)
    return json.loads(found.group(1)) if found else None


def recorded() -> dict[str, str] | None:
    """What the local engine in _wasm/ was built from, if build_wasm.py wrote it."""
    if not MANIFEST.is_file():
        return None
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def drift(was: dict[str, str] | None, now: dict[str, str]) -> list[str]:
    """Which inputs have moved since `was` was recorded. Empty means current."""
    if was is None:
        return ["no record of what the engine was built from — run "
                "`python docs/build_wasm.py`"]
    moved = [f"  changed since the engine was built: {key}"
             for key in sorted(now) if was.get(key) != now[key]]
    moved += [f"  was compiled in, no longer exists: {key}"
              for key in sorted(was) if key not in now]
    return moved
