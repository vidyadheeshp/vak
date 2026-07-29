"""
अन्तर्निहितानि कार्याणि — the standard library of Vāk.

Every function is registered under its Devanagari name and an IAST alias,
so both `लिख("नमस्ते")` and `likh("namaste")` work.
"""

from __future__ import annotations

import math
import random as _random
from pathlib import Path
import time as _time
from typing import Any

from .errors import RuntimeVakError
from .tokens import DEV_TO_ASCII, aksharas
from .values import NativeFunction, VakCallable, stringify, to_devanagari, type_name


def _fail(msg: str) -> None:
    raise RuntimeVakError(msg)


# --------------------------------------------------------------------------
# input / output
# --------------------------------------------------------------------------
def _likh(*args: Any) -> None:
    """लिख — write the arguments to the screen, separated by spaces."""
    print(" ".join(stringify(a) for a in args))


def _patha(prompt: Any = "") -> str:
    """पठ — read one line from the user."""
    return input(stringify(prompt))


# --------------------------------------------------------------------------
# reflection and conversion
# --------------------------------------------------------------------------
def _prakara(value: Any) -> str:
    """प्रकार — the type of a value, as a Sanskrit word."""
    return type_name(value)


def _sankhya(value: Any) -> int | float:
    """संख्या — convert to a number (Devanagari numerals welcome)."""
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        text = value.strip().translate(DEV_TO_ASCII)
        try:
            return int(text)
        except ValueError:
            try:
                return float(text)
            except ValueError:
                _fail(f"अङ्कः न भवति {value!r} / cannot read {value!r} as a number")
    _fail(f"अङ्कः न भवति {type_name(value)} / cannot convert {type_name(value)} to a number")


def _shabda(value: Any) -> str:
    """शब्द — convert to a string."""
    return stringify(value)


def _sanketa(ch: Any) -> int:
    """संकेतः — the Unicode code point of one character."""
    if not isinstance(ch, str) or len(ch) != 1:
        _fail("संकेतः एकम् अक्षरम् एव इच्छति / संकेतः expects a single character")
    return ord(ch)


def _varna(code: Any) -> str:
    """वर्णः — the character for a Unicode code point."""
    if isinstance(code, bool) or not isinstance(code, (int, float)):
        _fail("वर्णः अङ्कम् एव इच्छति / वर्णः expects a number")
    return chr(int(code))


def _amsha(text: Any, start: Any = 0, stop: Any = None) -> Any:
    """अंशः — a slice of a शब्दः or सूची: अंशः(स, २, ५)"""
    if not isinstance(text, (str, list)):
        _fail("अंशः शब्दम् सूचीम् वा इच्छति / अंशः expects a शब्दः or सूची")
    if isinstance(start, bool) or not isinstance(start, (int, float)):
        _fail("अंशस्य आरम्भः अङ्कः भवेत् / the start of अंशः must be a number")
    if stop is None:
        return text[int(start):]
    if isinstance(stop, bool) or not isinstance(stop, (int, float)):
        _fail("अंशस्य अन्तः अङ्कः भवेत् / the end of अंशः must be a number")
    return text[int(start):int(stop)]


def _devanagari(value: Any) -> str:
    """देवनागरी — render a number with Devanagari digits: 42 -> ४२"""
    return to_devanagari(stringify(value))


# --------------------------------------------------------------------------
# collections
# --------------------------------------------------------------------------
def _dirghata(value: Any) -> int:
    """दीर्घता — length of a string, सूची or कोश."""
    if isinstance(value, (str, list, dict)):
        return len(value)
    _fail(f"{type_name(value)} इत्यस्य दीर्घता नास्ति / {type_name(value)} has no length")


def _suchi(value: Any = None) -> list:
    """सूची — build a list from a string, कोश or another सूची."""
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    if isinstance(value, str):
        return list(value)
    if isinstance(value, dict):
        return list(value.keys())
    _fail(f"सूची न कर्तुं शक्यते {type_name(value)} / cannot make a सूची from {type_name(value)}")


def _parasa(a: Any, b: Any = None, step: Any = 1) -> list:
    """परास — परास(५) -> [०..४];  परास(१, ५) -> [१..४];  परास(०, १०, २)"""
    start, stop = (0, a) if b is None else (a, b)
    for v in (start, stop, step):
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            _fail("परासः अङ्कान् एव इच्छति / परास expects numbers")
    if step == 0:
        _fail("परासस्य पदम् शून्यम् न भवेत् / the step of परास cannot be zero")
    return list(range(int(start), int(stop), int(step)))


def _yojaya(collection: Any, *items: Any) -> Any:
    """योजय — append to a सूची (returns the same सूची)."""
    if not isinstance(collection, list):
        _fail(f"योजयः सूचीम् एव इच्छति / योजय expects a सूची, got {type_name(collection)}")
    collection.extend(items)
    return collection


def _nishkasa(collection: Any, index: Any = -1) -> Any:
    """निष्कास — remove and return an item of a सूची (or a key of a कोश)."""
    if isinstance(collection, list):
        if not collection:
            _fail("रिक्ता सूची / cannot remove from an empty सूची")
        return collection.pop(int(index))
    if isinstance(collection, dict):
        if index not in collection:
            _fail(f"कुञ्जिका न विद्यते {index!r} / no such key {index!r}")
        return collection.pop(index)
    _fail(f"निष्कासः सूचीम् कोशम् वा इच्छति / निष्कास expects a सूची or कोश")


def _asti(collection: Any, item: Any) -> bool:
    """अस्ति — "does it exist in here?" (membership test)."""
    if isinstance(collection, (list, str, dict)):
        return item in collection
    _fail(f"अस्ति इत्यस्य संग्रहः आवश्यकः / अस्ति expects a collection")


def _kunjika(d: Any) -> list:
    """कुञ्जिकाः — the keys of a कोश."""
    if not isinstance(d, dict):
        _fail("कुञ्जिकाः कोशम् एव इच्छन्ति / कुञ्जिकाः expects a कोश")
    return list(d.keys())


def _mulyani(d: Any) -> list:
    """मूल्यानि — the values of a कोश."""
    if not isinstance(d, dict):
        _fail("मूल्यानि कोशम् एव इच्छन्ति / मूल्यानि expects a कोश")
    return list(d.values())


def _krama(seq: Any, descending: Any = False) -> list:
    """क्रम — a sorted copy of a सूची."""
    if not isinstance(seq, list):
        _fail("क्रमः सूचीम् एव इच्छति / क्रम expects a सूची")
    try:
        return sorted(seq, reverse=bool(descending))
    except TypeError:
        _fail("मिश्रितप्रकाराः न तुलनीयाः / cannot sort a सूची of mixed types")


def _aksharani(text: Any) -> list:
    """अक्षराणि — split a शब्दः into syllables (not code points): वाक् -> [वा, क्]"""
    if not isinstance(text, str):
        _fail("अक्षराणि शब्दम् एव इच्छन्ति / अक्षराणि expects a शब्दः")
    return aksharas(text)


def _viparyaya(seq: Any) -> Any:
    """विपर्यय — reverse a सूची, or a शब्दः by अक्षर (never by code point)."""
    if isinstance(seq, list):
        return list(reversed(seq))
    if isinstance(seq, str):
        return "".join(reversed(aksharas(seq)))
    _fail("विपर्ययः सूचीम् शब्दम् वा इच्छति / विपर्यय expects a सूची or शब्द")


def _vibhaja(text: Any, sep: Any = " ") -> list:
    """विभज — split a string into a सूची."""
    if not isinstance(text, str):
        _fail("विभजः शब्दम् एव इच्छति / विभज expects a शब्द")
    return text.split(sep) if sep else list(text)


def _samyoja(seq: Any, sep: Any = "") -> str:
    """संयोज — join a सूची into one शब्द."""
    if not isinstance(seq, list):
        _fail("संयोजः सूचीम् एव इच्छति / संयोज expects a सूची")
    return stringify(sep).join(stringify(v) for v in seq)


# --------------------------------------------------------------------------
# mathematics — गणितम्
# --------------------------------------------------------------------------
def _num_list(seq: Any, who: str) -> list:
    if not isinstance(seq, list) or not seq:
        _fail(f"{who} अरिक्ताम् सूचीम् इच्छति / {who} expects a non-empty सूची")
    for v in seq:
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            _fail(f"{who} अङ्कान् एव इच्छति / {who} expects numbers")
    return seq


def _yoga(seq: Any) -> int | float:
    """योग — the sum of a सूची of numbers."""
    return sum(_num_list(seq, "योगः"))


def _nyunatama(seq: Any) -> Any:
    """न्यूनतम — the smallest number in a सूची."""
    return min(_num_list(seq, "न्यूनतमम्"))


def _adhikatama(seq: Any) -> Any:
    """अधिकतम — the largest number in a सूची."""
    return max(_num_list(seq, "अधिकतमम्"))


def _mula(x: Any) -> float:
    """मूल — the square root."""
    if not isinstance(x, (int, float)) or isinstance(x, bool):
        _fail("मूलम् अङ्कम् एव इच्छति / मूल expects a number")
    if x < 0:
        _fail("ऋणसंख्यायाः मूलम् नास्ति / no real square root of a negative number")
    return math.sqrt(x)


def _purna(x: Any) -> int:
    """पूर्ण — truncate a number to an integer."""
    if not isinstance(x, (int, float)) or isinstance(x, bool):
        _fail("पूर्णम् अङ्कम् एव इच्छति / पूर्ण expects a number")
    return int(x)


def _yadrcchika(a: Any = None, b: Any = None) -> float | int:
    """यादृच्छिक — a random number: () -> [0,1);  (a, b) -> integer in [a, b]."""
    if a is None:
        return _random.random()
    if b is None:
        return _random.randint(0, int(a))
    return _random.randint(int(a), int(b))


ADESHA_PRACHALAH: list[str] = []          # set by the CLI


def _khandam_chalaya(khanda: Any, vibhagah: Any = None) -> Any:
    """खण्डम्_चालय — run a chunk that arrives as कोशाः, on this very machine.

    This is what lets a compiler written in Vāk hand its output straight to the
    VM instead of interpreting it with a second VM written in Vāk.
    """
    from .kosha import kosha_to_chunk
    from .vm import VM

    if not isinstance(khanda, dict):
        _fail("खण्डम्_चालय कोशम् एव इच्छति / खण्डम्_चालय expects a कोशः")
    machine = VM()
    if isinstance(vibhagah, list):
        for pair in vibhagah:
            if isinstance(pair, list) and len(pair) >= 2 and isinstance(pair[0], str):
                machine.precompiled[pair[0]] = kosha_to_chunk(pair[1])
    return machine.run(kosha_to_chunk(khanda))


def _prachalah() -> list:
    """प्राचलाः — the arguments the program was started with."""
    return list(ADESHA_PRACHALAH)


def _kala() -> float:
    """काल — seconds since the epoch."""
    return _time.time()


# --------------------------------------------------------------------------
# सञ्चिकाः — files
# --------------------------------------------------------------------------
def _file_fail(action: str, path: Any, err: OSError) -> None:
    raise RuntimeVakError(
        f"सञ्चिकायाम् {action} न सिद्धम् {path!r} ({err.strerror}) / "
        f"cannot {action} {path!r}",
        code="सञ्चिकादोषः",
    )


def _path_of(path: Any, who: str) -> Path:
    if not isinstance(path, str):
        _fail(f"{who} पथम् (शब्दम्) इच्छति / {who} expects a path string")
    return Path(path)


def _sanchikapatha(path: Any) -> str:
    """सञ्चिकापठ — read a whole file as one शब्दः."""
    target = _path_of(path, "सञ्चिकापठ")
    try:
        return target.read_text(encoding="utf-8")
    except OSError as err:
        _file_fail("पठनम्", path, err)


def _sanchikapanktayah(path: Any) -> list:
    """सञ्चिकापङ्क्तयः — read a file as a सूची of lines."""
    return _sanchikapatha(path).splitlines()


def _sanchikalikh(path: Any, content: Any = "") -> int:
    """सञ्चिकालिख — write a file, replacing whatever was there."""
    target = _path_of(path, "सञ्चिकालिख")
    text = stringify(content)
    try:
        target.write_text(text, encoding="utf-8")
    except OSError as err:
        _file_fail("लेखनम्", path, err)
    return len(text)


def _sanchikayojaya(path: Any, content: Any = "") -> int:
    """सञ्चिकायोजय — append to a file, creating it if needed."""
    target = _path_of(path, "सञ्चिकायोजय")
    text = stringify(content)
    try:
        with target.open("a", encoding="utf-8") as handle:
            handle.write(text)
    except OSError as err:
        _file_fail("योजनम्", path, err)
    return len(text)


def _sanchikasti(path: Any) -> bool:
    """सञ्चिकास्ति — does this path exist?"""
    return _path_of(path, "सञ्चिकास्ति").exists()


def _sanchikanashaya(path: Any) -> bool:
    """सञ्चिकानाशय — delete a file; असत्य if it was not there."""
    target = _path_of(path, "सञ्चिकानाशय")
    try:
        target.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError as err:
        _file_fail("नाशनम्", path, err)


def _nirdeshika(path: Any = ".") -> list:
    """निर्देशिका — the names inside a directory, sorted."""
    target = _path_of(path, "निर्देशिका")
    try:
        return sorted(entry.name for entry in target.iterdir())
    except OSError as err:
        _file_fail("पठनम्", path, err)


def _dosha(message: Any = "दोषः", code: Any = "उपयोक्तृदोषः") -> None:
    """दोष — raise a catchable error deliberately (same as उत्सृज)."""
    from .interpreter import VakThrow, error_kosha

    if isinstance(message, dict):
        raise VakThrow(dict(message))
    raise VakThrow(error_kosha(stringify(code), stringify(message)))


# --------------------------------------------------------------------------
# registry :  (devanagari, iast, python fn, arity, one-line doc)
# --------------------------------------------------------------------------
_REGISTRY: list[tuple[str, str, Any, int, str, str]] = [
    ("लिख", "likh", _likh, -1, "मुद्रयति / print values", "शून्यम्"),
    ("पठ", "patha", _patha, -1, "उपयोक्तुः पङ्क्तिम् पठति / read a line", "शब्दः"),
    ("प्रकार", "prakara", _prakara, 1, "मूल्यस्य प्रकारः / type of a value", "शब्दः"),
    ("संख्या", "sankhya", _sankhya, 1, "अङ्कः करोति / convert to number", "अङ्कः"),
    ("शब्द", "shabda", _shabda, 1, "शब्दः करोति / convert to string", "शब्दः"),
    ("देवनागरी", "devanagari", _devanagari, 1, "देवनागरी-अङ्काः / Devanagari digits", "शब्दः"),
    ("दीर्घता", "dirghata", _dirghata, 1, "दीर्घता / length", "पूर्णाङ्कः"),
    ("सूची", "suchi", _suchi, -1, "सूचीम् रचयति / build a list", "सूची"),
    ("परास", "parasa", _parasa, -1, "अङ्कपरासः / numeric range", "सूची"),
    ("योजय", "yojaya", _yojaya, -1, "सूच्याम् योजयति / append", "सूची"),
    ("निष्कास", "nishkasa", _nishkasa, -1, "अपनयति / remove an item", "किमपि"),
    ("अस्ति", "asti", _asti, 2, "अस्ति वा / membership test", "सत्यता"),
    ("कुञ्जिकाः", "kunjika", _kunjika, 1, "कोशस्य कुञ्जिकाः / keys of a dict", "सूची"),
    ("मूल्यानि", "mulyani", _mulyani, 1, "कोशस्य मूल्यानि / values of a dict", "सूची"),
    ("क्रम", "krama", _krama, -1, "क्रमबद्धा सूची / sorted copy", "सूची"),
    ("विपर्यय", "viparyaya", _viparyaya, 1, "विपरीतक्रमः / reversed", "किमपि"),
    ("अक्षराणि", "aksharani", _aksharani, 1,
     "शब्दस्य अक्षराणि / syllables of a string", "सूची"),
    ("संकेतः", "sanketa", _sanketa, 1, "अक्षरस्य संकेतः / code point of a character",
     "पूर्णाङ्कः"),
    ("वर्णः", "varna", _varna, 1, "संकेतस्य वर्णः / character for a code point", "शब्दः"),
    ("अंशः", "amsha", _amsha, -1, "शब्दस्य सूच्याः वा अंशः / a slice", "किमपि"),
    ("विभज", "vibhaja", _vibhaja, -1, "शब्दम् विभजति / split a string", "सूची"),
    ("संयोज", "samyoja", _samyoja, -1, "सूचीम् संयोजयति / join a list", "शब्दः"),
    ("योग", "yoga", _yoga, 1, "योगफलम् / sum", "अङ्कः"),
    ("न्यूनतम", "nyunatama", _nyunatama, 1, "न्यूनतमम् / minimum", "अङ्कः"),
    ("अधिकतम", "adhikatama", _adhikatama, 1, "अधिकतमम् / maximum", "अङ्कः"),
    ("मूल", "mula", _mula, 1, "वर्गमूलम् / square root", "दशांशः"),
    ("पूर्ण", "purna", _purna, 1, "पूर्णाङ्कः / truncate to integer", "पूर्णाङ्कः"),
    ("यादृच्छिक", "yadrcchika", _yadrcchika, -1, "यादृच्छिकः अङ्कः / random number", "अङ्कः"),
    ("काल", "kala", _kala, 0, "कालः / current time in seconds", "दशांशः"),
    ("प्राचलाः", "prachalah", _prachalah, 0,
     "आदेशपङ्क्त्याः प्राचलाः / command-line arguments", "सूची"),
    ("खण्डम्_चालय", "khandam_chalaya", _khandam_chalaya, -1,
     "संकलितम् खण्डम् चालयति / run a compiled chunk", "किमपि"),
    ("दोष", "dosha", _dosha, -1, "दोषम् उत्पादयति / raise an error", "शून्यम्"),
    ("सञ्चिकापठ", "sanchikapatha", _sanchikapatha, 1,
     "सञ्चिकाम् पठति / read a whole file", "शब्दः"),
    ("सञ्चिकापङ्क्तयः", "sanchikapanktayah", _sanchikapanktayah, 1,
     "सञ्चिकायाः पङ्क्तयः / read a file as lines", "सूची"),
    ("सञ्चिकालिख", "sanchikalikh", _sanchikalikh, -1,
     "सञ्चिकाम् लिखति / write a file", "पूर्णाङ्कः"),
    ("सञ्चिकायोजय", "sanchikayojaya", _sanchikayojaya, -1,
     "सञ्चिकायाम् योजयति / append to a file", "पूर्णाङ्कः"),
    ("सञ्चिकास्ति", "sanchikasti", _sanchikasti, 1,
     "सञ्चिका विद्यते वा / does the path exist", "सत्यता"),
    ("सञ्चिकानाशय", "sanchikanashaya", _sanchikanashaya, 1,
     "सञ्चिकाम् नाशयति / delete a file", "सत्यता"),
    ("निर्देशिका", "nirdeshika", _nirdeshika, -1,
     "निर्देशिकायाः सूची / list a directory", "सूची"),
]


def build_builtins() -> dict[str, VakCallable]:
    """The global table of native functions, keyed by every accepted spelling."""
    table: dict[str, VakCallable] = {}
    for devanagari, iast, fn, arity, doc, _rtype in _REGISTRY:
        native = NativeFunction(devanagari, fn, arity, doc)
        table[devanagari] = native
        table[iast] = native
    return table


BUILTIN_DOCS: list[tuple[str, str, str]] = [
    (dev, iast, doc) for dev, iast, _fn, _arity, doc, _rtype in _REGISTRY
]

# name -> (arity, return type) — what the semantic analyser checks calls against.
BUILTIN_SIGNATURES: dict[str, tuple[int, str]] = {}
for _dev, _iast, _fn, _arity, _doc, _rtype in _REGISTRY:
    BUILTIN_SIGNATURES[_dev] = (_arity, _rtype)
    BUILTIN_SIGNATURES[_iast] = (_arity, _rtype)
