"""
देशीयसंकलनम् — the native back end: a Chunk becomes C, and gcc makes it an .exe.

The program is not translated into C statement by statement. Instead its
bytecode is emitted as C data and linked against the C implementation of the
SanskritVM in native/ — the same design the Python and Vāk VMs follow, so all
four engines run the same instructions and must print the same thing.

    from vaak.native import build_executable
    exe = build_executable(source, Path("प्रोग्राम.vak"))
    subprocess.run([str(exe)])

Modules are resolved at compile time: every `आनय` a program reaches is compiled
into the same C file and registered in a table the runtime looks up by path.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .compiler import Chunk, CompiledFunction, compile_program
from .lexer import tokenize
from .parser import parse

NATIVE_DIR = Path(__file__).resolve().parent.parent / "native"
# विण्डोज़् एव '.exe' इच्छति; अन्यत्र नाम एव पर्याप्तम्।
EXE_SUFFIX = ".exe" if os.name == "nt" else ""
RUNTIME_SOURCES = ("mulyani.c", "antarnihitani.c", "yantram.c")

GCC_CANDIDATES = (
    "gcc",
    r"C:\w64devkit\bin\gcc.exe",
    r"C:\w64devkit-2.8.0\bin\gcc.exe",
    r"C:\msys64\mingw64\bin\gcc.exe",
)


def find_gcc() -> str | None:
    """संकलकः विद्यते वा — locate a C compiler, PATH first."""
    for candidate in GCC_CANDIDATES:
        found = shutil.which(candidate) if not Path(candidate).is_absolute() else None
        if found:
            return found
        if Path(candidate).exists():
            return str(Path(candidate))
    return None


# --------------------------------------------------------------------------
# C literals
# --------------------------------------------------------------------------
def c_string(text: str) -> str:
    """A C string literal holding the UTF-8 bytes of `text`."""
    out = ['"']
    for byte in text.encode("utf-8"):
        if byte == 0x22:
            out.append('\\"')
        elif byte == 0x5C:
            out.append("\\\\")
        elif byte == 0x0A:
            out.append("\\n")
        elif byte == 0x0D:
            out.append("\\r")
        elif byte == 0x09:
            out.append("\\t")
        elif 0x20 <= byte < 0x7F:
            out.append(chr(byte))
        else:
            out.append(f"\\{byte:03o}")
    out.append('"')
    return "".join(out)


def c_double(value: float) -> str:
    if value != value:
        return "(0.0/0.0)"
    if value in (float("inf"), float("-inf")):
        return "(1.0/0.0)" if value > 0 else "(-1.0/0.0)"
    return repr(value) if "." in repr(value) or "e" in repr(value) else f"{value!r}.0"


class Emitter:
    """खण्डेभ्यः C-सङ्केताः — turns chunks into C declarations."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.counter = 0
        # id(chunk) -> (chunk, C identifier). The Chunk itself is kept in the
        # value on purpose: without a live reference Python may hand the same
        # id() to a later object, and the memo would answer for the wrong chunk.
        self.emitted: dict[int, tuple[Chunk, str]] = {}

    def fresh(self, prefix: str) -> str:
        self.counter += 1
        return f"{prefix}_{self.counter}"

    # -- one chunk ---------------------------------------------------------
    def emit_chunk(self, chunk: Chunk) -> str:
        if id(chunk) in self.emitted:
            return self.emitted[id(chunk)][1]
        name = self.fresh("khanda")
        self.emitted[id(chunk)] = (chunk, name)

        # nested functions first, so their descriptors exist
        fn_names: dict[int, str] = {}
        for index, constant in enumerate(chunk.constants):
            if isinstance(constant, CompiledFunction):
                fn_names[index] = self.emit_function(constant)

        code = ", ".join(str(word) for word in chunk.code) or "0"
        lines = ", ".join(str(line) for line in chunk.lines) or "0"
        self.lines.append(f"static const int {name}_sanketah[] = {{{code}}};")
        self.lines.append(f"static const int {name}_panktayah[] = {{{lines}}};")

        rows: list[str] = []
        for index, constant in enumerate(chunk.constants):
            rows.append("    " + self.constant_row(constant, fn_names.get(index)) + ",")
        body = "\n".join(rows) if rows else "    {0}"
        self.lines.append(f"static const Dhruva {name}_dhruvah[] = {{\n{body}\n}};")
        self.lines.append(
            f"static const Khanda {name} = {{ {c_string(chunk.name)}, "
            f"{name}_sanketah, {len(chunk.code)}, {name}_panktayah, "
            f"{name}_dhruvah, {len(chunk.constants)} }};"
        )
        return name

    def emit_function(self, fn: CompiledFunction) -> str:
        inner = self.emit_chunk(fn.chunk)
        name = self.fresh("karyam")
        params = ", ".join(
            "{ %s, %s, %s }" % (
                c_string(p.name),
                c_string(p.type),
                c_string(p.karaka) if p.karaka else "NULL",
            )
            for p in fn.params
        ) or "{ NULL, NULL, NULL }"
        self.lines.append(f"static const Prachala {name}_prachalah[] = {{{params}}};")
        self.lines.append(
            f"static const SankalitaKaryam {name} = {{ {c_string(fn.name)}, "
            f"{name}_prachalah, {len(fn.params)}, {c_string(fn.return_type)}, &{inner} }};"
        )
        return name

    # -- one constant ------------------------------------------------------
    def constant_row(self, value: Any, fn_name: str | None) -> str:
        """Dhruva: { prakara, purnanka, dashamsha, shabda, satyata, karyam,
                     shabdah, shabda_ganana }"""
        if fn_name is not None:
            return f"{{ K_KARYAM, 0, 0.0, NULL, false, &{fn_name}, NULL, 0 }}"
        if isinstance(value, bool):
            return f"{{ K_SATYATA, 0, 0.0, NULL, {'true' if value else 'false'}, NULL, NULL, 0 }}"
        if isinstance(value, int):
            return f"{{ K_PURNANKA, {value}LL, 0.0, NULL, false, NULL, NULL, 0 }}"
        if isinstance(value, float):
            return f"{{ K_DASHAMSHA, 0, {c_double(value)}, NULL, false, NULL, NULL, 0 }}"
        if isinstance(value, str):
            return f"{{ K_SHABDA, 0, 0.0, {c_string(value)}, false, NULL, NULL, 0 }}"
        if value is None:
            return "{ K_SHUNYAM, 0, 0.0, NULL, false, NULL, NULL, 0 }"
        if isinstance(value, tuple):
            return self.tuple_row(value)
        raise TypeError(f"अज्ञातः ध्रुवः / cannot emit constant {value!r}")

    def tuple_row(self, value: tuple) -> str:
        """Two shapes reach here: kāraka label lists, and import payloads."""
        if len(value) == 3 and isinstance(value[0], str) and isinstance(value[2], tuple):
            path, alias, names = value                     # an आनय payload
            entries = [c_string(alias) if alias else "NULL"]
            entries += [c_string(n) for n in names]
            array = self.fresh("shabdah")
            self.lines.append(
                f"static const char *{array}[] = {{{', '.join(entries)}, NULL}};"
            )
            return (f"{{ K_SUCHI_SHABDANAM, 0, 0.0, {c_string(path)}, false, NULL, "
                    f"{array}, {len(names)} }}")
        entries = [c_string(v) if v is not None else "NULL" for v in value]  # labels
        array = self.fresh("shabdah")
        self.lines.append(
            f"static const char *{array}[] = {{{', '.join(entries) or 'NULL'}, NULL}};"
        )
        return (f"{{ K_SUCHI_SHABDANAM, 0, 0.0, NULL, false, NULL, "
                f"{array}, {len(value)} }}")


# --------------------------------------------------------------------------
# module resolution
# --------------------------------------------------------------------------
def _module_paths(chunk: Chunk) -> list[str]:
    """Every module path an आनय in this chunk (or its functions) names."""
    found: list[str] = []
    for constant in chunk.constants:
        if isinstance(constant, CompiledFunction):
            found += _module_paths(constant.chunk)
        elif (isinstance(constant, tuple) and len(constant) == 3
                and isinstance(constant[0], str) and isinstance(constant[2], tuple)):
            found.append(constant[0])
    return found


def _resolve(path: str, here: Path) -> Path:
    candidate = Path(path)
    if candidate.suffix != ".vak":
        candidate = candidate.with_suffix(".vak")
    if candidate.is_absolute():
        return candidate
    for base in (here, Path(), Path(__file__).resolve().parent / "पुस्तकालयः"):
        resolved = base / candidate
        if resolved.exists():
            return resolved.resolve()
    return (here / candidate).resolve()


def generate_c(source: str, path: Path) -> str:
    """Compile a program and everything it imports into one C translation unit."""
    here = path.resolve().parent
    main_chunk = compile_program(parse(tokenize(source, str(path)), str(path)), str(path))

    emitter = Emitter()
    modules: list[tuple[str, str]] = []          # (path as written, C identifier)
    seen: set[str] = set()
    pending = [(name, main_chunk) for name in _module_paths(main_chunk)]

    while pending:
        module_path, _parent = pending.pop(0)
        if module_path in seen:
            continue
        seen.add(module_path)
        resolved = _resolve(module_path, here)
        if not resolved.exists():
            raise FileNotFoundError(
                f"आयातदोषः: सञ्चिका न प्राप्ता {module_path!r} / cannot find module"
            )
        module_source = resolved.read_text(encoding="utf-8")
        module_chunk = compile_program(
            parse(tokenize(module_source, str(resolved)), str(resolved)), str(resolved)
        )
        modules.append((module_path, emitter.emit_chunk(module_chunk)))
        pending += [(name, module_chunk) for name in _module_paths(module_chunk)]

    main_name = emitter.emit_chunk(main_chunk)

    rows = ",\n".join(f"    {{ {c_string(p)}, &{name} }}" for p, name in modules)
    table = f"const Vibhaga VIBHAGAH[] = {{\n{rows}\n}};" if modules else \
            "const Vibhaga VIBHAGAH[] = { { NULL, NULL } };"
    ganana = len(modules)

    return "\n".join([
        "/* स्वयं रचितम् — generated by vaak/native.py; do not edit. */",
        f'/* मूलम् / source: {path.name} */',
        '#include "vak.h"',
        "",
        *emitter.lines,
        "",
        f"const Khanda MUKHYAM_KHANDA = {main_name};",
        table,
        f"const int VIBHAGA_GANANA = {ganana};",
        "",
        "int main(int argc, char **argv) {",
        "    vak_prachalan_sthapaya(argc, argv);",
        "    return vak_chalaya(&MUKHYAM_KHANDA);",
        "}",
        "",
    ])


# --------------------------------------------------------------------------
# building
# --------------------------------------------------------------------------
def _asciify(stem: str) -> str:
    """A file name gcc can actually open.

    MinGW's linker mangles non-ASCII output paths (`प्रोग्राम.exe` reaches it as
    `????????.exe`), so a Devanagari-named program is built under an ASCII name
    derived from it — deterministic, so rebuilding hits the same file.
    """
    if stem.isascii():
        return stem
    kept = "".join(ch for ch in stem if ch.isascii() and (ch.isalnum() or ch in "._-"))
    digest = hashlib.sha1(stem.encode("utf-8")).hexdigest()[:8]
    return f"{kept}_{digest}" if kept else f"vak_{digest}"


def build_executable(source: str, path: Path, out_dir: Path | None = None,
                     keep_c: bool = False) -> Path:
    """Emit C, compile it with the runtime, and return the executable's path."""
    gcc = find_gcc()
    if gcc is None:
        raise RuntimeError(
            "C-संकलकः न प्राप्तः / no C compiler found — install gcc (w64devkit) "
            "and put its bin directory on PATH"
        )
    out_dir = out_dir or path.resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = _asciify(path.stem)

    # ...and the *directory* must be ASCII too. `स्वयंसिद्धिः/` reaches the linker as
    # `????????????/`, so anything under a Devanagari directory is built in a
    # scratch directory and moved into place afterwards — Python handles the
    # Unicode path that MinGW cannot.
    detour = None if str(out_dir).isascii() else Path(tempfile.mkdtemp(prefix="vak-"))
    work = detour or out_dir
    c_file = work / f"{stem}.c"
    exe = work / (stem + EXE_SUFFIX)

    try:
        c_file.write_text(generate_c(source, path), encoding="utf-8")
        command = [
            gcc, "-std=c11", "-O2", "-o", str(exe),
            str(c_file), *[str(NATIVE_DIR / name) for name in RUNTIME_SOURCES],
            f"-I{NATIVE_DIR}", "-lm",
        ]
        if os.environ.get("VAK_POSIX"):
            # POSIX-मार्गः विण्डोज़्-यन्त्रे अपि परीक्षितुम् शक्यते — तस्य सङ्केतः
            # अन्यथा अत्र कदापि न चलेत्।  Forces the branch Linux and macOS take,
            # so the code they will run can be exercised here as well.
            command.append("-DVAK_POSIX")
        elif Path(gcc).name.lower().startswith("gcc") and NATIVE_DIR.drive:
            command.append("-lshell32")      # CommandLineToArgvW, for UTF-16 argv
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                "C-संकलनम् विफलम् / the C compile failed:\n"
                + (result.stderr or result.stdout)
            )
        if detour is not None:
            exe = Path(shutil.move(str(exe), str(out_dir / (stem + EXE_SUFFIX))))
            if keep_c:
                c_file = Path(shutil.move(str(c_file), str(out_dir / f"{stem}.c")))
        if not keep_c:
            c_file.unlink(missing_ok=True)
    finally:
        if detour is not None:
            shutil.rmtree(detour, ignore_errors=True)
    return exe
