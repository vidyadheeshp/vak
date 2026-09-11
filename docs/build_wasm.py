# -*- coding: utf-8 -*-
"""यन्त्रनिर्माणम् — build the playground's WebAssembly engine.

    python docs/build_wasm.py            generate the C, compile it, record it
    python docs/build_wasm.py --check    say whether _wasm/ is current; build nothing

Needs Emscripten. It is found, in order, from $EMCC, from `emcc` on PATH, or
from an emsdk at C:\\emsdk or ~/emsdk — so an installed emsdk works without
activating it first. Afterwards run docs/build_playground.py, which inlines the
engine into docs/playground.html together with the record of what it was built
from.

The engine is the self-hosted toolchain, not the Python one: स्वयंसिद्धिः/वाक्.vak
compiled to C by vaak/native.py and linked with native/. So any change to the
Vāk-written lexer, parser, analyser, compiler or VM — not only to the C runtime
— leaves the playground behind until this is run again.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine  # noqa: E402

ROOT = engine.ROOT


def find_emcc() -> tuple[str, dict[str, str]] | None:
    """emcc, and the environment it needs to find its own configuration."""
    env = dict(os.environ)
    candidates = []
    if env.get("EMCC"):
        candidates.append(Path(env["EMCC"]))
    on_path = shutil.which("emcc")
    if on_path:
        candidates.append(Path(on_path))
    for root in (Path("C:/emsdk"), Path.home() / "emsdk"):
        for name in ("emcc.exe", "emcc.bat", "emcc"):
            candidates.append(root / "upstream" / "emscripten" / name)
    for emcc in candidates:
        if not emcc.is_file():
            continue
        emsdk_root = emcc.parents[2] if emcc.parent.name == "emscripten" else None
        config = emsdk_root / ".emscripten" if emsdk_root else None
        if config and config.is_file() and "EM_CONFIG" not in env:
            env["EM_CONFIG"] = str(config)
        return str(emcc), env
    return None


def check() -> int:
    now = engine.fingerprint()
    moved = engine.drift(engine.recorded(), now)
    if moved:
        print("_wasm/ is behind the sources:")
        print("\n".join(moved))
        return 1
    print("_wasm/ is current")
    return 0


def build() -> int:
    found = find_emcc()
    if found is None:
        raise SystemExit(
            "Emscripten not found. Install emsdk (https://emscripten.org/docs/"
            "getting_started/downloads.html), or set EMCC to the emcc executable.")
    emcc, env = found

    started = time.perf_counter()
    engine.WASM_DIR.mkdir(exist_ok=True)
    generated = engine.generate_engine_c()
    engine.ENGINE_C.write_text(generated, encoding="utf-8")
    print(f"generated {engine.ENGINE_C.relative_to(ROOT)}  ({len(generated):,} chars)")

    command = [emcc, *engine.EMCC_FLAGS,
               str(engine.ENGINE_C),
               *[str(ROOT / "native" / name) for name in engine.RUNTIME_SOURCES
                 if name.endswith(".c")],
               f"-I{ROOT / 'native'}",
               "-o", str(engine.ENGINE_JS)]
    result = subprocess.run(command, env=env, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    noise = [line for line in (result.stderr + result.stdout).splitlines()
             if "INFO" not in line]
    if result.returncode != 0:
        raise SystemExit("emcc failed:\n" + "\n".join(noise[-40:]))

    # Recorded only after emcc succeeds, so a failed build can never be
    # mistaken for a current one.
    engine.MANIFEST.write_text(
        __import__("json").dumps(engine.fingerprint(generated), indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    size = engine.ENGINE_JS.stat().st_size
    print(f"compiled {engine.ENGINE_JS.relative_to(ROOT)}  ({size:,} bytes, "
          f"{time.perf_counter() - started:.0f} s)")
    print(f"recorded {engine.MANIFEST.relative_to(ROOT)}")
    print("next: python docs/build_playground.py")
    return 0


if __name__ == "__main__":
    sys.exit(check() if "--check" in sys.argv else build())
