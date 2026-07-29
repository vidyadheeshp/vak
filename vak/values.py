"""
मूल्यानि — the runtime values of Vāk and how they are named and printed.

Vāk value        Sanskrit name   Python representation
---------------  --------------  ---------------------
number           अङ्कः            int | float
string           शब्दः            str
boolean          सत्यता           bool
list             सूची             list
dictionary       कोशः             dict
nothing          शून्यम्           None
function         कार्यम्           VakFunction | NativeFunction
"""

from __future__ import annotations

from typing import Any, Callable

from .tokens import ASCII_TO_DEV


class VakCallable:
    """Anything that can appear before '(' in a call."""

    name: str = "कार्यम्"
    arity: int = 0

    def call(self, interpreter, args: list[Any], line: int = 0) -> Any:  # pragma: no cover
        raise NotImplementedError


class VakFunction(VakCallable):
    """A कार्यम् written in Vāk, closed over the scope it was defined in."""

    __slots__ = ("name", "params", "body", "closure", "return_type")

    def __init__(self, name: str, params: list, body, closure, return_type: str = "किमपि"):
        self.name = name
        self.params = params            # list[ast_nodes.Param]
        self.body = body
        self.closure = closure
        self.return_type = return_type

    @property
    def arity(self) -> int:  # type: ignore[override]
        return len(self.params)

    def call(self, interpreter, args: list[Any], line: int = 0) -> Any:
        from .environment import Environment
        from .interpreter import ReturnSignal

        env = Environment(self.closure)
        for param, arg in zip(self.params, args):
            check_type(arg, param.type, f"{self.name} इत्यस्य प्राचलः {param.name!r}", line)
            env.define(param.name, arg)
        result = None
        try:
            interpreter.execute_block(self.body.statements, env)
        except ReturnSignal as ret:
            result = ret.value
        check_type(result, self.return_type, f"{self.name} इत्यस्य प्रतिफलम्", line)
        return result

    def __repr__(self) -> str:
        return f"<कार्यम् {self.name}/{len(self.params)}>"


class NativeFunction(VakCallable):
    """A built-in implemented in Python (लिख, दीर्घता, ...)."""

    __slots__ = ("name", "fn", "_arity", "doc")

    def __init__(self, name: str, fn: Callable[..., Any], arity: int = -1, doc: str = ""):
        self.name = name
        self.fn = fn
        self._arity = arity          # -1 = variadic
        self.doc = doc

    @property
    def arity(self) -> int:  # type: ignore[override]
        return self._arity

    def call(self, interpreter, args: list[Any], line: int = 0) -> Any:
        return self.fn(*args)

    def __repr__(self) -> str:
        return f"<अन्तर्निहितम् {self.name}>"


def order_by_karaka(callee: Any, args: list, labels: list, line: int = 0) -> list:
    """Place role-labelled arguments in the slots their kāraka names.

    विभक्तिः क्रमम् मोचयति — the case ending frees the word order, so
    `छानय(करणम्: प, अपादानम्: स)` and `छानय(स, प)` are the same call.
    Shared by the tree-walking interpreter and the SanskritVM.
    """
    from .errors import RuntimeVakError

    params = getattr(callee, "params", None)
    if not params:
        raise RuntimeVakError(
            "कारकनामभिः आह्वानम् केवलम् कारकयुक्तस्य कार्यस्य कृते / "
            "kāraka-labelled arguments need a कार्यम् whose parameters declare roles",
            line, code="कारकदोषः",
        )
    slots: list[Any] = [None] * len(params)
    filled = [False] * len(params)
    positions = {p.karaka: i for i, p in enumerate(params) if p.karaka}

    for value, label in zip(args, labels):
        if label is None:
            continue
        index = positions.get(label)
        if index is None:
            raise RuntimeVakError(
                f"अस्मिन् कार्ये {label} इति कारकम् नास्ति / this कार्यम् declares no "
                f"{label} parameter",
                line, code="कारकदोषः",
            )
        if filled[index]:
            raise RuntimeVakError(
                f"{label} इति कारकम् द्विः दत्तम् / the {label} argument was given twice",
                line, code="कारकदोषः",
            )
        slots[index] = value
        filled[index] = True

    free = (i for i, done in enumerate(filled) if not done)
    for value, label in zip(args, labels):
        if label is not None:
            continue
        try:
            index = next(free)
        except StopIteration:
            raise RuntimeVakError(
                "अतिरिक्ताः प्राचलाः / too many arguments", line, code="प्राचलदोषः"
            ) from None
        slots[index] = value
        filled[index] = True

    if not all(filled):
        missing = ", ".join(p.karaka or p.name for p, done in zip(params, filled) if not done)
        raise RuntimeVakError(
            f"न्यूनाः प्राचलाः: {missing} / missing argument(s): {missing}",
            line, code="प्राचलदोषः",
        )
    return slots


# --------------------------------------------------------------------------
# प्रकारपरीक्षा — types
#
# Declared types are checked when a value is bound: at a declaration, when an
# argument is passed, and when a कार्यम् returns. This is deliberately a
# *dynamic* check — the static semantic analyser will reuse the same table.
# --------------------------------------------------------------------------
def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


TYPE_PREDICATES: dict[str, Any] = {
    "किमपि": lambda v: True,
    "पूर्णाङ्कः": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "दशांशः": _is_number,                     # an int widens to a decimal
    "अङ्कः": _is_number,
    "शब्दः": lambda v: isinstance(v, str),
    "सत्यता": lambda v: isinstance(v, bool),
    "सूची": lambda v: isinstance(v, list),
    "कोशः": lambda v: isinstance(v, dict),
    "कार्यम्": lambda v: isinstance(v, VakCallable),
    "शून्यम्": lambda v: v is None,
}


def matches_type(value: Any, declared: str) -> bool:
    predicate = TYPE_PREDICATES.get(declared)
    return True if predicate is None else predicate(value)


def check_type(value: Any, declared: str, what: str, line: int = 0) -> Any:
    """Raise a प्रकारदोषः unless `value` fits the declared type."""
    if declared == "किमपि" or matches_type(value, declared):
        return value
    from .errors import RuntimeVakError

    raise RuntimeVakError(
        f"{what}: {declared} अपेक्षितः, {type_name(value)} प्राप्तः / "
        f"expected {declared}, got {type_name(value)}",
        line,
        code="प्रकारदोषः",
    )


# --------------------------------------------------------------------------
# naming and printing
# --------------------------------------------------------------------------
def type_name(value: Any) -> str:
    """The Sanskrit name of a value's type — what प्रकार() returns.

    Numbers report the precise type (पूर्णाङ्कः / दशांशः); `अङ्कः` remains
    usable as the umbrella type when you declare a variable.
    """
    if value is None:
        return "शून्यम्"
    if isinstance(value, bool):
        return "सत्यता"
    if isinstance(value, int):
        return "पूर्णाङ्कः"
    if isinstance(value, float):
        return "दशांशः"
    if isinstance(value, str):
        return "शब्दः"
    if isinstance(value, list):
        return "सूची"
    if isinstance(value, dict):
        return "कोशः"
    if isinstance(value, VakCallable):
        return "कार्यम्"
    return "अज्ञातम्"


def is_truthy(value: Any) -> bool:
    """शून्यम् and असत्य are false; 0, "" and empty collections are false too."""
    if value is None or value is False:
        return False
    if value is True:
        return True
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, (str, list, dict)):
        return len(value) > 0
    return True


def format_number(value: int | float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def to_devanagari(text: str) -> str:
    """'42' -> '४२'"""
    return text.translate(ASCII_TO_DEV)


def stringify(value: Any, quote_strings: bool = False) -> str:
    """Render a value the way लिख() shows it."""
    if value is None:
        return "शून्यम्"
    if value is True:
        return "सत्य"
    if value is False:
        return "असत्य"
    if isinstance(value, (int, float)):
        return format_number(value)
    if isinstance(value, str):
        return f'"{value}"' if quote_strings else value
    if isinstance(value, list):
        return "[" + ", ".join(stringify(v, True) for v in value) + "]"
    if isinstance(value, dict):
        inner = ", ".join(
            f"{stringify(k, True)}: {stringify(v, True)}" for k, v in value.items()
        )
        return "{" + inner + "}"
    if isinstance(value, VakCallable):
        return repr(value)
    return str(value)
