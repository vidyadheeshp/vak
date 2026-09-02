"""
संस्कृतयन्त्रम् — the SanskritVM.

A stack machine that executes the bytecode produced by compiler.py. It shares
the Environment chain, values, built-ins and error types with the tree-walking
interpreter, so both engines are semantically identical — which is what makes
them differential-testable against each other.

    यन्त्रम् = VM(filename)
    यन्त्रम्.run(chunk)

Frames hold their own instruction pointer, environment and exception handlers;
the value stack is shared across frames, each frame remembering its base.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .builtins import build_builtins
from .compiler import CompiledFunction, compile_program
from .environment import Environment
from .errors import RuntimeVakError
from .interpreter import VakThrow, error_kosha
from .opcodes import Op
from .values import (
    VakCallable,
    check_type,
    is_truthy,
    order_by_karaka,
    stringify,
    type_name,
)


class VakClosure(VakCallable):
    """A compiled कार्यम् together with the environment it was made in."""

    __slots__ = ("fn", "env")

    def __init__(self, fn: CompiledFunction, env: Environment):
        self.fn = fn
        self.env = env

    @property
    def name(self) -> str:                        # type: ignore[override]
        return self.fn.name

    @property
    def params(self) -> list:
        return self.fn.params

    @property
    def arity(self) -> int:                       # type: ignore[override]
        return len(self.fn.params)

    def call(self, interpreter, args: list[Any], line: int = 0) -> Any:
        """Let a VakClosure be callable from the tree-walker too."""
        return VM(getattr(interpreter, "filename", "<वाक्>")).call_closure(self, args, line)

    def __repr__(self) -> str:
        return f"<कार्यम् {self.fn.name}/{len(self.fn.params)}>"


@dataclass
class _Handler:
    catch_ip: int
    finally_ip: int
    env: Environment
    stack_height: int


@dataclass
class _Frame:
    closure: VakClosure | None
    chunk: Any
    env: Environment
    ip: int = 0
    base: int = 0
    handlers: list[_Handler] = field(default_factory=list)
    pending: Any = None          # an error travelling through an अन्ततः block


class VM:
    def __init__(self, filename: str = "<वाक्>"):
        self.filename = filename
        self.prelude = Environment()
        for name, fn in build_builtins().items():
            self.prelude.define(name, fn, constant=True)
        self.globals = Environment(self.prelude)
        self.stack: list[Any] = []
        self.frames: list[_Frame] = []
        self.modules: dict[str, dict | None] = {}
        # पूर्वसंकलिताः विभागाः — modules supplied as chunks rather than found on
        # disk, which is how a self-hosted compiler passes what it just compiled.
        self.precompiled: dict[str, Any] = {}
        self.slot_misses = 0      # स्थानभ्रंशः — see Op.GET_LOCAL

    # ======================================================================
    # entry points
    # ======================================================================
    def run(self, chunk) -> Any:
        self.frames.append(_Frame(None, chunk, self.globals))
        try:
            return self._loop()
        except VakThrow as thrown:
            raise self._to_error(thrown) from None

    def call_closure(self, closure: VakClosure, args: list[Any], line: int = 0) -> Any:
        """Run one closure to completion — used when the tree-walker calls VM code."""
        self._push_frame(closure, args, [None] * len(args), line)
        return self._loop(stop_at=len(self.frames) - 1)

    @staticmethod
    def _to_error(thrown: VakThrow) -> RuntimeVakError:
        payload = thrown.payload
        if isinstance(payload, dict):
            line = payload.get("पङ्क्तिः", 0)
            return RuntimeVakError(
                stringify(payload.get("सन्देशः", payload)),
                line if isinstance(line, int) else 0,
                code=payload.get("प्रकारः", "उपयोक्तृदोषः"),
            )
        return RuntimeVakError(stringify(payload), code="उपयोक्तृदोषः")

    # ======================================================================
    # helpers
    # ======================================================================
    @property
    def frame(self) -> _Frame:
        return self.frames[-1]

    def _line(self) -> int:
        frame = self.frame
        lines = frame.chunk.lines
        index = min(max(frame.ip - 1, 0), len(lines) - 1) if lines else 0
        return lines[index] if lines else 0

    def _push_frame(self, closure: VakClosure, args: list[Any],
                    labels: list[str | None], line: int) -> None:
        params = closure.fn.params
        if any(labels):
            args = order_by_karaka(closure, args, labels, line)
        if len(args) != len(params):
            raise RuntimeVakError(
                f"{closure.fn.name}: {len(params)} प्राचलाः अपेक्षिताः, {len(args)} प्राप्ताः / "
                f"expected {len(params)} argument(s), got {len(args)}",
                line, code="प्राचलदोषः",
            )
        env = Environment(closure.env)
        for param, arg in zip(params, args):
            check_type(arg, param.type, f"{closure.fn.name} इत्यस्य प्राचलः {param.name!r}", line)
            env.define(param.name, arg, line=line, declared=param.type)
        self.frames.append(_Frame(closure, closure.fn.chunk, env, base=len(self.stack)))

    # ======================================================================
    # the dispatch loop
    # ======================================================================
    def _loop(self, stop_at: int = 0) -> Any:
        while True:
            try:
                result = self._step(stop_at)
            except VakThrow as thrown:
                if not self._unwind(thrown.payload, stop_at):
                    raise
                continue
            except RuntimeVakError as err:
                payload = error_kosha(err.code, err.message, err.line or self._line())
                if not self._unwind(payload, stop_at):
                    raise
                continue
            if result is not _KEEP_GOING:
                return result

    def _step(self, stop_at: int) -> Any:
        """Run instructions until the frame returns or the program halts."""
        while True:
            frame = self.frame
            code = frame.chunk.code
            op = Op(code[frame.ip])
            frame.ip += 1

            # ---------------------------------------------------- values
            if op is Op.CONST:
                self.stack.append(frame.chunk.constants[code[frame.ip]])
                frame.ip += 1
            elif op is Op.NIL:
                self.stack.append(None)
            elif op is Op.TRUE:
                self.stack.append(True)
            elif op is Op.FALSE:
                self.stack.append(False)
            elif op is Op.POP:
                self.stack.pop()
            elif op is Op.DUP:
                self.stack.append(self.stack[-1])

            # ------------------------------------------------- variables
            elif op is Op.DEF_VAR or op is Op.DEF_CONST:
                name = frame.chunk.constants[code[frame.ip]]
                declared = frame.chunk.constants[code[frame.ip + 1]]
                frame.ip += 2
                value = self.stack.pop()
                check_type(value, declared, f"चरः {name!r}", self._line())
                frame.env.define(name, value, op is Op.DEF_CONST, self._line(), declared)
            elif op is Op.GET_VAR:
                name = frame.chunk.constants[code[frame.ip]]
                frame.ip += 1
                self.stack.append(frame.env.get(name, self._line()))
            elif op is Op.SET_VAR:
                name = frame.chunk.constants[code[frame.ip]]
                frame.ip += 1
                frame.env.assign(name, self.stack[-1], self._line())

            elif op is Op.GET_BUILTIN:
                # The compiler proved this name is a built-in that the program
                # never declares, so the environment chain cannot hold it and
                # there is nothing to search.
                name = frame.chunk.constants[code[frame.ip]]
                frame.ip += 1
                self.stack.append(self.prelude.values[name])

            # स्थाननिर्णीतौ — the compiler already worked out where these live.
            # The binding is checked against the name it was compiled for: if
            # the scope is not shaped the way the compiler expected, the search
            # still happens and the answer is still right, but self.slot_misses
            # counts it so the tests can insist that it never happens.
            elif op is Op.GET_LOCAL:
                hops, slot = code[frame.ip], code[frame.ip + 1]
                name = frame.chunk.constants[code[frame.ip + 2]]
                frame.ip += 3
                env = frame.env.binding(hops, slot, name)
                if env is None:
                    self.slot_misses += 1
                    self.stack.append(frame.env.get(name, self._line()))
                else:
                    self.stack.append(env.values[name])
            elif op is Op.SET_LOCAL:
                hops, slot = code[frame.ip], code[frame.ip + 1]
                name = frame.chunk.constants[code[frame.ip + 2]]
                frame.ip += 3
                env = frame.env.binding(hops, slot, name)
                if env is None:
                    self.slot_misses += 1
                    env = frame.env
                env.assign(name, self.stack[-1], self._line())

            # ------------------------------------------------ arithmetic
            elif op is Op.ADD:
                right, left = self.stack.pop(), self.stack.pop()
                self.stack.append(self._add(left, right))
            elif op in _ARITH:
                right, left = self.stack.pop(), self.stack.pop()
                self.stack.append(self._arith(op, left, right))
            elif op is Op.NEG:
                value = self.stack.pop()
                self._need_number(value, "-")
                self.stack.append(-value)
            elif op is Op.NOT:
                self.stack.append(not is_truthy(self.stack.pop()))

            # ------------------------------------------------ comparison
            elif op is Op.EQ:
                right, left = self.stack.pop(), self.stack.pop()
                self.stack.append(self._equals(left, right))
            elif op is Op.NE:
                right, left = self.stack.pop(), self.stack.pop()
                self.stack.append(not self._equals(left, right))
            elif op in _COMPARE:
                right, left = self.stack.pop(), self.stack.pop()
                self.stack.append(self._compare(op, left, right))

            # ---------------------------------------------------- control
            elif op is Op.JUMP:
                frame.ip += code[frame.ip] + 1
            elif op is Op.JUMP_IF_FALSE:
                offset = code[frame.ip]
                frame.ip += 1
                if not is_truthy(self.stack[-1]):
                    frame.ip += offset
            elif op is Op.JUMP_IF_TRUE:
                offset = code[frame.ip]
                frame.ip += 1
                if is_truthy(self.stack[-1]):
                    frame.ip += offset
            elif op is Op.JUMP_BACK:
                frame.ip += 1
                frame.ip -= code[frame.ip - 1]

            # ----------------------------------------------------- scopes
            elif op is Op.SCOPE_PUSH:
                frame.env = Environment(frame.env)
            elif op is Op.SCOPE_POP:
                frame.env = frame.env.parent

            # ------------------------------------------------ collections
            elif op is Op.BUILD_LIST:
                count = code[frame.ip]
                frame.ip += 1
                items = self.stack[len(self.stack) - count:]
                del self.stack[len(self.stack) - count:]
                self.stack.append(items)
            elif op is Op.BUILD_DICT:
                count = code[frame.ip]
                frame.ip += 1
                flat = self.stack[len(self.stack) - 2 * count:]
                del self.stack[len(self.stack) - 2 * count:]
                result: dict = {}
                for index in range(0, len(flat), 2):
                    key = flat[index]
                    if isinstance(key, (list, dict)):
                        raise RuntimeVakError(
                            f"{type_name(key)} कुञ्जिका न भवति / "
                            f"{type_name(key)} cannot be a key",
                            self._line(), code="प्रकारदोषः",
                        )
                    result[key] = flat[index + 1]
                self.stack.append(result)
            elif op is Op.INDEX_GET:
                index, target = self.stack.pop(), self.stack.pop()
                self.stack.append(self._index(target, index))
            elif op is Op.INDEX_SET:
                value, index, target = self.stack.pop(), self.stack.pop(), self.stack.pop()
                self._index_set(target, index, value)
                self.stack.append(value)

            # -------------------------------------------------- functions
            elif op is Op.CLOSURE:
                compiled = frame.chunk.constants[code[frame.ip]]
                frame.ip += 1
                self.stack.append(VakClosure(compiled, frame.env))
            elif op is Op.CALL or op is Op.CALL_LABELLED:
                argc = code[frame.ip]
                if op is Op.CALL:
                    labels: list[str | None] = [None] * argc
                    frame.ip += 1
                else:
                    labels = list(frame.chunk.constants[code[frame.ip + 1]])
                    frame.ip += 2
                args = self.stack[len(self.stack) - argc:]
                del self.stack[len(self.stack) - argc:]
                callee = self.stack.pop()
                value = self._call(callee, args, labels)
                if value is not _PUSHED_FRAME:
                    self.stack.append(value)
            elif op is Op.RETURN:
                value = self.stack.pop()
                closure = frame.closure
                if closure is not None:
                    check_type(value, closure.fn.return_type,
                               f"{closure.fn.name} इत्यस्य प्रतिफलम्", self._line())
                del self.stack[frame.base:]
                self.frames.pop()
                if len(self.frames) <= stop_at:
                    return value
                self.stack.append(value)

            # --------------------------------------------------- commands
            elif op is Op.PRINT:
                count = code[frame.ip]
                frame.ip += 1
                args = self.stack[len(self.stack) - count:]
                del self.stack[len(self.stack) - count:]
                print(" ".join(stringify(a) for a in args))

            # -------------------------------------------------- iteration
            elif op is Op.ITER_NEW:
                self.stack.append(_Iterator(self._items(self.stack.pop())))
            elif op is Op.ITER_NEXT:
                offset = code[frame.ip]
                frame.ip += 1
                iterator: _Iterator = self.stack[-1]
                if iterator.index < len(iterator.items):
                    self.stack.append(iterator.items[iterator.index])
                    iterator.index += 1
                else:
                    self.stack.pop()
                    frame.ip += offset

            # ------------------------------------------------- exceptions
            elif op is Op.SETUP_TRY:
                catch_ip, finally_ip = code[frame.ip], code[frame.ip + 1]
                frame.ip += 2
                frame.handlers.append(
                    _Handler(catch_ip, finally_ip, frame.env, len(self.stack))
                )
            elif op is Op.POP_TRY:
                frame.handlers.pop()
            elif op is Op.THROW:
                value = self.stack.pop()
                raise VakThrow(self._as_payload(value))
            elif op is Op.END_FINALLY:
                pending, frame.pending = frame.pending, None
                if pending is not None:
                    raise VakThrow(pending)

            # ---------------------------------------------------- modules
            elif op is Op.IMPORT:
                path, alias, names = frame.chunk.constants[code[frame.ip]]
                frame.ip += 1
                self._import(path, alias, list(names))

            elif op is Op.HALT:
                return None

            else:                                            # pragma: no cover
                raise RuntimeVakError(f"अज्ञातः आदेशः / unknown opcode {op}", self._line())

    # ======================================================================
    # calling
    # ======================================================================
    def _call(self, callee: Any, args: list[Any], labels: list[str | None]) -> Any:
        line = self._line()
        if isinstance(callee, VakClosure):
            self._push_frame(callee, args, labels, line)
            return _PUSHED_FRAME
        if isinstance(callee, VakCallable):
            if any(labels):
                raise RuntimeVakError(
                    "कारकनामभिः आह्वानम् केवलम् कारकयुक्तस्य कार्यस्य कृते / "
                    "kāraka labels need a कार्यम् whose parameters declare roles",
                    line, code="कारकदोषः",
                )
            if callee.arity >= 0 and len(args) != callee.arity:
                raise RuntimeVakError(
                    f"{callee.name}: {callee.arity} प्राचलाः अपेक्षिताः, {len(args)} प्राप्ताः / "
                    f"expected {callee.arity} argument(s), got {len(args)}",
                    line, code="प्राचलदोषः",
                )
            return callee.call(self, args, line)
        raise RuntimeVakError(
            f"{type_name(callee)} आह्वातुं न शक्यते / {type_name(callee)} is not callable",
            line, code="प्रकारदोषः",
        )

    # ======================================================================
    # unwinding
    # ======================================================================
    def _unwind(self, payload: Any, stop_at: int) -> bool:
        """Find a प्रयत्नः that wants this दोषः. False means nobody does."""
        while len(self.frames) > stop_at:
            frame = self.frame
            while frame.handlers:
                handler = frame.handlers.pop()
                del self.stack[handler.stack_height:]
                frame.env = handler.env
                if handler.catch_ip >= 0:
                    self.stack.append(payload)
                    frame.ip = handler.catch_ip
                    return True
                if handler.finally_ip >= 0:      # अन्ततः only — run it, then rethrow
                    frame.pending = payload
                    frame.ip = handler.finally_ip
                    return True
            if len(self.frames) - 1 <= stop_at:
                return False
            del self.stack[frame.base:]
            self.frames.pop()
        return False

    @staticmethod
    def _as_payload(value: Any) -> Any:
        if isinstance(value, dict):
            payload = dict(value)
            payload.setdefault("प्रकारः", "उपयोक्तृदोषः")
            payload.setdefault("सन्देशः", "")
            payload.setdefault("पङ्क्तिः", 0)
            return payload
        return error_kosha("उपयोक्तृदोषः", stringify(value), 0, value)

    # ======================================================================
    # modules
    # ======================================================================
    def _import(self, path: str, alias: str | None, names: list[str]) -> None:
        from .lexer import tokenize
        from .parser import parse

        line = self._line()
        resolved = self._resolve(path)
        key = str(resolved)
        module = self.modules.get(key, _MISSING)
        if module is None:
            raise RuntimeVakError(
                f"चक्रीयः आयातः {path!r} / circular import of {path!r}",
                line, code="आयातदोषः",
            )
        if module is _MISSING and (path in self.precompiled
                                   or str(resolved) in self.precompiled):
            chunk = self.precompiled.get(path) or self.precompiled[str(resolved)]
            self.modules[key] = None
            module_env = Environment(self.prelude)
            saved_frames, saved_stack = self.frames, self.stack
            self.frames, self.stack = [], []
            try:
                self.frames.append(_Frame(None, chunk, module_env))
                self._loop()
            finally:
                self.frames, self.stack = saved_frames, saved_stack
            module = dict(module_env.values)
            self.modules[key] = module
        if module is _MISSING:
            try:
                source = resolved.read_text(encoding="utf-8")
            except OSError as err:
                raise RuntimeVakError(
                    f"सञ्चिका न प्राप्ता {path!r} ({err.strerror}) / "
                    f"cannot read module {path!r}",
                    line, code="आयातदोषः",
                ) from None
            self.modules[key] = None
            chunk = compile_program(parse(tokenize(source, key), key), key)
            module_env = Environment(self.prelude)
            saved_frames, saved_stack = self.frames, self.stack
            self.frames, self.stack = [], []
            try:
                self.frames.append(_Frame(None, chunk, module_env))
                self._loop()
            finally:
                self.frames, self.stack = saved_frames, saved_stack
            module = dict(module_env.values)
            self.modules[key] = module

        frame = self.frame
        if names:
            for name in names:
                if name not in module:
                    raise RuntimeVakError(
                        f"{path!r} इत्यस्मिन् {name!r} इति नास्ति / "
                        f"module {path!r} has no {name!r}",
                        line, code="आयातदोषः",
                    )
                frame.env.define(name, module[name], line=line)
        else:
            stem = path.replace("\\", "/").rsplit("/", 1)[-1]
            stem = stem[:-4] if stem.endswith(".vak") else stem
            frame.env.define(alias or stem, module, line=line)

    def _resolve(self, path: str) -> Path:
        candidate = Path(path)
        if candidate.suffix != ".vak":
            candidate = candidate.with_suffix(".vak")
        if candidate.is_absolute():
            return candidate
        here = Path(self.filename).parent if self.filename not in ("<वाक्>", "<संवादः>") \
            else Path()
        for base in (here, Path(), Path(__file__).parent / "पुस्तकालयः"):
            resolved = base / candidate
            if resolved.exists():
                return resolved.resolve()
        return (here / candidate).resolve()

    # ======================================================================
    # operators — the same rules the tree-walker uses
    # ======================================================================
    def _add(self, left: Any, right: Any) -> Any:
        if isinstance(left, str) or isinstance(right, str):
            return stringify(left) + stringify(right)
        if isinstance(left, list) and isinstance(right, list):
            return left + right
        self._need_number(left, "+")
        self._need_number(right, "+")
        return left + right

    def _arith(self, op: Op, left: Any, right: Any) -> Any:
        if op is Op.MUL and isinstance(left, str) and isinstance(right, int):
            return left * right
        self._need_number(left, _SYMBOL[op])
        self._need_number(right, _SYMBOL[op])
        if op is Op.SUB:
            return left - right
        if op is Op.MUL:
            return left * right
        if op is Op.DIV:
            if right == 0:
                raise RuntimeVakError("भागहारः शून्येन न शक्यः / division by zero",
                                      self._line(), code="गणितदोषः")
            result = left / right
            return (int(result) if isinstance(left, int) and isinstance(right, int)
                    and result.is_integer() else result)
        if op is Op.MOD:
            if right == 0:
                raise RuntimeVakError("शून्येन शेषः न शक्यः / modulo by zero",
                                      self._line(), code="गणितदोषः")
            return left % right
        return left ** right

    def _compare(self, op: Op, left: Any, right: Any) -> bool:
        if not (isinstance(left, str) and isinstance(right, str)):
            self._need_number(left, _SYMBOL[op])
            self._need_number(right, _SYMBOL[op])
        if op is Op.LT:
            return left < right
        if op is Op.LE:
            return left <= right
        if op is Op.GT:
            return left > right
        return left >= right

    @staticmethod
    def _equals(a: Any, b: Any) -> bool:
        if isinstance(a, bool) != isinstance(b, bool):
            return False
        if a is None or b is None:
            return a is None and b is None
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return a == b
        if type(a) is not type(b):
            return False
        return a == b

    def _need_number(self, value: Any, symbol: str) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RuntimeVakError(
                f"{symbol!r} इत्यस्य कृते अङ्कः आवश्यकः, प्राप्तम् {type_name(value)} / "
                f"operator {symbol!r} needs a number, got {type_name(value)}",
                self._line(), code="प्रकारदोषः",
            )

    # -- indexing ----------------------------------------------------------
    def _index(self, target: Any, index: Any) -> Any:
        line = self._line()
        if isinstance(target, (list, str)):
            position = self._as_index(index, line)
            if not -len(target) <= position < len(target):
                raise RuntimeVakError(
                    f"सूचकः परिधेः बहिः {position} / index {position} is out of range",
                    line, code="सूचकदोषः",
                )
            return target[position]
        if isinstance(target, dict):
            if index not in target:
                raise RuntimeVakError(
                    f"कुञ्जिका न विद्यते {stringify(index, True)} / "
                    f"no such key {stringify(index, True)}",
                    line, code="कुञ्जिकादोषः",
                )
            return target[index]
        raise RuntimeVakError(
            f"{type_name(target)} इत्यस्मिन् सूचकः न प्रयोज्यः / cannot index a "
            f"{type_name(target)}",
            line, code="प्रकारदोषः",
        )

    def _index_set(self, target: Any, index: Any, value: Any) -> None:
        line = self._line()
        if isinstance(target, list):
            position = self._as_index(index, line)
            if not -len(target) <= position < len(target):
                raise RuntimeVakError(
                    f"सूचकः परिधेः बहिः {position} / index {position} is out of range",
                    line, code="सूचकदोषः",
                )
            target[position] = value
            return
        if isinstance(target, dict):
            target[index] = value
            return
        raise RuntimeVakError(
            f"{type_name(target)} इत्यस्मिन् न स्थापयितुं शक्यते / "
            f"cannot assign into a {type_name(target)}",
            line, code="प्रकारदोषः",
        )

    @staticmethod
    def _as_index(index: Any, line: int) -> int:
        if isinstance(index, bool) or not isinstance(index, (int, float)):
            raise RuntimeVakError(
                f"सूचकः अङ्कः भवेत् / the index must be a number, got {type_name(index)}",
                line, code="प्रकारदोषः",
            )
        return int(index)

    def _items(self, iterable: Any) -> list:
        if isinstance(iterable, dict):
            return list(iterable.keys())
        if isinstance(iterable, (list, str)):
            return list(iterable)
        if isinstance(iterable, (int, float)) and not isinstance(iterable, bool):
            return list(range(int(iterable)))
        raise RuntimeVakError(
            f"{type_name(iterable)} इत्यस्य उपरि न भ्रमितुं शक्यते / "
            f"cannot iterate over {type_name(iterable)}",
            self._line(), code="प्रकारदोषः",
        )


@dataclass
class _Iterator:
    items: list
    index: int = 0


class _Sentinel:
    def __repr__(self) -> str:                    # pragma: no cover
        return "<सङ्केतः>"


_KEEP_GOING = _Sentinel()
_PUSHED_FRAME = _Sentinel()
_MISSING = _Sentinel()

_ARITH = frozenset({Op.SUB, Op.MUL, Op.DIV, Op.MOD, Op.POW})
_COMPARE = frozenset({Op.LT, Op.LE, Op.GT, Op.GE})
_SYMBOL = {
    Op.ADD: "+", Op.SUB: "-", Op.MUL: "*", Op.DIV: "/", Op.MOD: "%", Op.POW: "^",
    Op.LT: "<", Op.LE: "<=", Op.GT: ">", Op.GE: ">=",
}


def execute(chunk, filename: str = "<वाक्>") -> Any:
    """Convenience wrapper — चालय।"""
    return VM(filename).run(chunk)
