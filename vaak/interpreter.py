"""
दुभाषिकः — the tree-walking Interpreter of Vāk.

It walks the AST produced by the parser and evaluates it directly:
  * `evaluate(expr)` returns a value
  * `execute(stmt)`  performs an action
Control flow that jumps (प्रतिदा / विरम / अनुवर्त) is carried by exceptions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import ast_nodes as A
from .builtins import build_builtins
from .environment import Environment
from .errors import RuntimeVakError
from .values import (
    VakCallable,
    VakFunction,
    check_type,
    is_truthy,
    order_by_karaka,
    stringify,
    type_name,
)


# --------------------------------------------------------------------------
# non-local control flow
# --------------------------------------------------------------------------
class ReturnSignal(Exception):
    __slots__ = ("value",)

    def __init__(self, value: Any):
        super().__init__("प्रत्यागच्छ")
        self.value = value


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class VakThrow(Exception):
    """A दोषः travelling up the stack, carrying a Vāk value (usually a कोशः)."""

    __slots__ = ("payload",)

    def __init__(self, payload: Any):
        super().__init__("उत्सृज")
        self.payload = payload


def error_kosha(code: str, message: str, line: int = 0, value: Any = None) -> dict:
    """The कोशः a दोषे block receives."""
    kosha = {"प्रकारः": code, "सन्देशः": message, "पङ्क्तिः": line}
    if value is not None:
        kosha["मूल्यम्"] = value
    return kosha


class Interpreter:
    def __init__(self, filename: str = "<वाक्>"):
        self.filename = filename
        # The built-ins live in their own scope *outside* the global scope, so a
        # program is free to use words like योग or सूची as its own variables.
        self.prelude = Environment()
        for name, fn in build_builtins().items():
            self.prelude.define(name, fn, constant=True)
        self.globals = Environment(self.prelude)
        self.env = self.globals
        # आयातस्मृतिः — every module is executed once, then cached by path
        self.modules: dict[str, dict | None] = {}

    # ======================================================================
    # entry points
    # ======================================================================
    def run(self, program: A.Program) -> Any:
        self._hoist(program.statements, self.env)
        result = None
        try:
            for stmt in program.statements:
                result = self.execute(stmt)
        except VakThrow as thrown:
            raise self._to_error(thrown) from None
        return result

    def execute_block(self, statements: list[A.Stmt], env: Environment) -> None:
        previous = self.env
        self.env = env
        try:
            self._hoist(statements, env)
            for stmt in statements:
                self.execute(stmt)
        finally:
            self.env = previous

    @staticmethod
    def _hoist(statements: list[A.Stmt], env: Environment) -> None:
        """कार्याणि पूर्वम् ज्ञातानि — declare every कार्यम् of a block up front,
        so a function may be called before the line that defines it."""
        for stmt in statements:
            if isinstance(stmt, A.FunctionDecl):
                env.define(
                    stmt.name,
                    VakFunction(stmt.name, stmt.params, stmt.body, env, stmt.return_type),
                    line=stmt.line,
                )

    @staticmethod
    def _to_error(thrown: VakThrow) -> RuntimeVakError:
        """An उत्सृज that nobody caught becomes a normal runtime error."""
        payload = thrown.payload
        if isinstance(payload, dict):
            code = payload.get("प्रकारः", "उपयोक्तृदोषः")
            message = stringify(payload.get("सन्देशः", payload))
            line = payload.get("पङ्क्तिः", 0)
            return RuntimeVakError(message, line if isinstance(line, int) else 0, code=code)
        return RuntimeVakError(stringify(payload), code="उपयोक्तृदोषः")

    # ======================================================================
    # statements
    # ======================================================================
    def execute(self, node: A.Stmt) -> Any:
        method = getattr(self, "_exec_" + type(node).__name__, None)
        if method is None:
            raise RuntimeVakError(
                f"अज्ञातम् वाक्यम् / unknown statement {type(node).__name__}", node.line
            )
        return method(node)

    def _exec_ExpressionStmt(self, node: A.ExpressionStmt) -> Any:
        return self.evaluate(node.expr)

    def _exec_VarDecl(self, node: A.VarDecl) -> Any:
        value = self.evaluate(node.value) if node.value is not None else None
        if node.value is not None:
            check_type(value, node.type, f"चरः {node.name!r}", node.line)
        self.env.define(node.name, value, node.constant, node.line, node.type)
        return value

    def _exec_Print(self, node: A.Print) -> None:
        print(" ".join(stringify(self.evaluate(a)) for a in node.args))

    def _exec_Block(self, node: A.Block) -> None:
        self.execute_block(node.statements, Environment(self.env))

    def _exec_If(self, node: A.If) -> None:
        if is_truthy(self.evaluate(node.condition)):
            self.execute(node.then_branch)
        elif node.else_branch is not None:
            self.execute(node.else_branch)

    def _exec_While(self, node: A.While) -> None:
        while is_truthy(self.evaluate(node.condition)):
            try:
                self.execute(node.body)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def _exec_ForEach(self, node: A.ForEach) -> None:
        iterable = self.evaluate(node.iterable)
        if isinstance(iterable, dict):
            items: Any = list(iterable.keys())
        elif isinstance(iterable, (list, str)):
            items = iterable
        elif isinstance(iterable, (int, float)) and not isinstance(iterable, bool):
            items = list(range(int(iterable)))
        else:
            raise RuntimeVakError(
                f"{type_name(iterable)} इत्यस्य उपरि न भ्रमितुं शक्यते / "
                f"cannot iterate over {type_name(iterable)}",
                node.line, code="प्रकारदोषः",
            )
        for item in items:
            loop_env = Environment(self.env)
            loop_env.define(node.var, item)
            try:
                if isinstance(node.body, A.Block):
                    self.execute_block(node.body.statements, loop_env)
                else:
                    previous, self.env = self.env, loop_env
                    try:
                        self.execute(node.body)
                    finally:
                        self.env = previous
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    # -- modules -----------------------------------------------------------
    def _exec_Import(self, node: A.Import) -> Any:
        module = self._load_module(node.path, node.line)
        if node.names:
            for name in node.names:
                if name not in module:
                    raise RuntimeVakError(
                        f"{node.path!r} इत्यस्मिन् {name!r} इति नास्ति / "
                        f"module {node.path!r} has no {name!r}",
                        node.line, code="आयातदोषः",
                    )
                self.env.define(name, module[name], line=node.line)
            return module
        self.env.define(node.alias or self._module_name(node.path), module, line=node.line)
        return module

    @staticmethod
    def _module_name(path: str) -> str:
        stem = path.replace("\\", "/").rsplit("/", 1)[-1]
        return stem[:-4] if stem.endswith(".vak") else stem

    def _resolve_module(self, path: str) -> Path:
        candidate = Path(path)
        if candidate.suffix != ".vak":
            candidate = candidate.with_suffix(".vak")
        if candidate.is_absolute():
            return candidate
        here = Path(self.filename).parent if self.filename not in ("<वाक्>", "<संवादः>") else Path()
        for base in (here, Path(), Path(__file__).parent / "पुस्तकालयः"):
            resolved = (base / candidate)
            if resolved.exists():
                return resolved.resolve()
        return (here / candidate).resolve()

    def _load_module(self, path: str, line: int) -> dict:
        """Run a .vak file once and hand back its globals as a कोशः."""
        from .lexer import tokenize
        from .parser import parse

        resolved = self._resolve_module(path)
        key = str(resolved)
        if key in self.modules:
            cached = self.modules[key]
            if cached is None:                      # currently loading — a cycle
                raise RuntimeVakError(
                    f"चक्रीयः आयातः {path!r} / circular import of {path!r}",
                    line, code="आयातदोषः",
                )
            return cached
        try:
            source = resolved.read_text(encoding="utf-8")
        except OSError as err:
            raise RuntimeVakError(
                f"सञ्चिका न प्राप्ता {path!r} ({err.strerror}) / cannot read module {path!r}",
                line, code="आयातदोषः",
            ) from None

        self.modules[key] = None                    # mark as in flight
        program = parse(tokenize(source, key), key)
        module_env = Environment(self.prelude)
        previous_env, previous_file = self.env, self.filename
        self.env, self.filename = module_env, key
        try:
            self._hoist(program.statements, module_env)
            for stmt in program.statements:
                self.execute(stmt)
        except VakThrow as thrown:
            self.modules.pop(key, None)
            raise self._to_error(thrown) from None
        except BaseException:
            self.modules.pop(key, None)
            raise
        finally:
            self.env, self.filename = previous_env, previous_file

        exports = dict(module_env.values)
        self.modules[key] = exports
        return exports

    def _exec_Repeat(self, node: A.Repeat) -> None:
        count = self.evaluate(node.count)
        if isinstance(count, bool) or not isinstance(count, (int, float)):
            raise RuntimeVakError(
                f"आवृत्तिः अङ्कम् इच्छति, {type_name(count)} प्राप्तः / "
                f"आवृत्तिः needs a number, got {type_name(count)}",
                node.line, code="प्रकारदोषः",
            )
        for _ in range(max(int(count), 0)):
            try:
                self.execute(node.body)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def _exec_Switch(self, node: A.Switch) -> None:
        """विकल्पः — the first पक्षः that matches wins, and only it runs.

        पक्षाः do not fall through: विकल्पः means a choice among alternatives,
        so choosing one is the whole of it and no विरम is needed to stop it.
        The अन्यथा is kept for last however it was written, so it is still the
        fallback if the author put it first.
        """
        subject = self.evaluate(node.subject)
        default: A.SwitchCase | None = None
        for case in node.cases:
            if case.is_default:
                default = case
                continue
            for expr in case.values:
                if self._equals(subject, self.evaluate(expr)):
                    self.execute_block(case.body, Environment(self.env))
                    return
        if default is not None:
            self.execute_block(default.body, Environment(self.env))

    def _exec_Try(self, node: A.Try) -> None:
        try:
            try:
                self.execute(node.body)
            except VakThrow as thrown:
                self._handle(node, thrown.payload)
            except RuntimeVakError as err:
                self._handle(node, error_kosha(err.code, err.message, err.line))
        finally:
            if node.finally_body is not None:
                self.execute(node.finally_body)

    def _handle(self, node: A.Try, payload: Any) -> None:
        """Run the दोषे block, or let the दोषः keep travelling."""
        if node.catch_body is None:
            raise VakThrow(payload)
        env = Environment(self.env)
        if node.catch_var:
            env.define(node.catch_var, payload)
        self.execute_block(node.catch_body.statements, env)

    def _exec_Throw(self, node: A.Throw) -> None:
        value = self.evaluate(node.value)
        if isinstance(value, dict):
            payload = dict(value)
            payload.setdefault("प्रकारः", "उपयोक्तृदोषः")
            payload.setdefault("सन्देशः", "")
            payload.setdefault("पङ्क्तिः", node.line)
        else:
            payload = error_kosha("उपयोक्तृदोषः", stringify(value), node.line, value)
        raise VakThrow(payload)

    def _exec_FunctionDecl(self, node: A.FunctionDecl) -> Any:
        fn = VakFunction(node.name, node.params, node.body, self.env, node.return_type)
        self.env.define(node.name, fn, line=node.line)
        return fn

    def _exec_Return(self, node: A.Return) -> None:
        raise ReturnSignal(self.evaluate(node.value) if node.value is not None else None)

    def _exec_Break(self, node: A.Break) -> None:
        raise BreakSignal()

    def _exec_Continue(self, node: A.Continue) -> None:
        raise ContinueSignal()

    # ======================================================================
    # expressions
    # ======================================================================
    def evaluate(self, node: A.Expr) -> Any:
        method = getattr(self, "_eval_" + type(node).__name__, None)
        if method is None:
            raise RuntimeVakError(
                f"अज्ञातम् पदम् / unknown expression {type(node).__name__}", node.line
            )
        return method(node)

    def _eval_Literal(self, node: A.Literal) -> Any:
        return node.value

    def _eval_ListLit(self, node: A.ListLit) -> list:
        return [self.evaluate(e) for e in node.elements]

    def _eval_DictLit(self, node: A.DictLit) -> dict:
        result: dict = {}
        for key_node, value_node in node.pairs:
            key = self.evaluate(key_node)
            if isinstance(key, (list, dict)):
                raise RuntimeVakError(
                    f"{type_name(key)} कुञ्जिका न भवति / {type_name(key)} cannot be a key",
                    node.line, code="प्रकारदोषः",
                )
            result[key] = self.evaluate(value_node)
        return result

    def _eval_Identifier(self, node: A.Identifier) -> Any:
        return self.env.get(node.name, node.line)

    def _eval_Assign(self, node: A.Assign) -> Any:
        return self.env.assign(node.name, self.evaluate(node.value), node.line)

    def _eval_Unary(self, node: A.Unary) -> Any:
        value = self.evaluate(node.right)
        if node.op == "-":
            self._need_number(value, "-", node.line)
            return -value
        return not is_truthy(value)          # ! / न

    def _eval_Logical(self, node: A.Logical) -> Any:
        left = self.evaluate(node.left)
        if node.op == "वा":                  # or — short circuit
            return left if is_truthy(left) else self.evaluate(node.right)
        return self.evaluate(node.right) if is_truthy(left) else left   # च — and

    def _eval_Binary(self, node: A.Binary) -> Any:
        left = self.evaluate(node.left)
        right = self.evaluate(node.right)
        op = node.op
        line = node.line

        if op == "==":
            return self._equals(left, right)
        if op == "!=":
            return not self._equals(left, right)

        if op == "+":
            if isinstance(left, str) or isinstance(right, str):
                return stringify(left) + stringify(right)
            if isinstance(left, list) and isinstance(right, list):
                return left + right
            self._need_numbers(left, right, op, line)
            return left + right

        if op in ("<", "<=", ">", ">="):
            if isinstance(left, str) and isinstance(right, str):
                pass
            else:
                self._need_numbers(left, right, op, line)
            return {
                "<": left < right, "<=": left <= right,
                ">": left > right, ">=": left >= right,
            }[op]

        if op == "*" and isinstance(left, str) and isinstance(right, int):
            return left * right

        self._need_numbers(left, right, op, line)
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if right == 0:
                raise RuntimeVakError(
                    "भागहारः शून्येन न शक्यः / division by zero", line, code="गणितदोषः"
                )
            result = left / right
            return int(result) if isinstance(left, int) and isinstance(right, int) and result.is_integer() else result
        if op == "%":
            if right == 0:
                raise RuntimeVakError(
                    "शून्येन शेषः न शक्यः / modulo by zero", line, code="गणितदोषः"
                )
            return left % right
        if op == "^":
            return left ** right

        raise RuntimeVakError(f"अज्ञातः संकारकः {op!r} / unknown operator {op!r}", line, code="प्रकारदोषः")

    def _eval_IndexGet(self, node: A.IndexGet) -> Any:
        target = self.evaluate(node.target)
        index = self.evaluate(node.index)
        return self._index(target, index, node.line)

    def _eval_IndexSet(self, node: A.IndexSet) -> Any:
        target = self.evaluate(node.target)
        index = self.evaluate(node.index)
        value = self.evaluate(node.value)
        if isinstance(target, list):
            i = self._as_index(index, node.line)
            if not -len(target) <= i < len(target):
                raise RuntimeVakError(
                    f"सूचकः परिधेः बहिः {i} / index {i} is out of range", node.line,
                    code="सूचकदोषः",
                )
            target[i] = value
            return value
        if isinstance(target, dict):
            target[index] = value
            return value
        raise RuntimeVakError(
            f"{type_name(target)} इत्यस्मिन् न स्थापयितुं शक्यते / "
            f"cannot assign into a {type_name(target)}",
            node.line,
            code="प्रकारदोषः",
        )

    def _eval_Call(self, node: A.Call) -> Any:
        callee = self.evaluate(node.callee)
        args = [self.evaluate(a) for a in node.args]
        if node.arg_karakas and any(node.arg_karakas):
            args = self._order_by_karaka(callee, args, node.arg_karakas, node.line)
        if not isinstance(callee, VakCallable):
            raise RuntimeVakError(
                f"{type_name(callee)} आह्वातुं न शक्यते / {type_name(callee)} is not callable",
                node.line, code="प्रकारदोषः",
            )
        if callee.arity >= 0 and len(args) != callee.arity:
            raise RuntimeVakError(
                f"{callee.name}: {callee.arity} प्राचलाः अपेक्षिताः, {len(args)} प्राप्ताः / "
                f"expected {callee.arity} argument(s), got {len(args)}",
                node.line, code="प्राचलदोषः",
            )
        try:
            return callee.call(self, args, node.line)
        except RuntimeVakError as err:
            if not err.line:
                err.line = node.line
            raise

    def _eval_FunctionExpr(self, node: A.FunctionExpr) -> VakFunction:
        return VakFunction(node.name, node.params, node.body, self.env, node.return_type)

    # ======================================================================
    # helpers
    # ======================================================================
    @staticmethod
    def _order_by_karaka(callee: Any, args: list[Any], labels: list[str | None],
                         line: int) -> list[Any]:
        return order_by_karaka(callee, args, labels, line)

    def _index(self, target: Any, index: Any, line: int) -> Any:
        if isinstance(target, (list, str)):
            i = self._as_index(index, line)
            if not -len(target) <= i < len(target):
                raise RuntimeVakError(
                    f"सूचकः परिधेः बहिः {i} / index {i} is out of range", line, code="सूचकदोषः"
                )
            return target[i]
        if isinstance(target, dict):
            if index not in target:
                raise RuntimeVakError(
                    f"कुञ्जिका न विद्यते {stringify(index, True)} / no such key "
                    f"{stringify(index, True)}",
                    line,
                    code="कुञ्जिकादोषः",
                )
            return target[index]
        raise RuntimeVakError(
            f"{type_name(target)} इत्यस्मिन् सूचकः न प्रयोज्यः / cannot index a {type_name(target)}",
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

    @staticmethod
    def _need_number(value: Any, op: str, line: int) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RuntimeVakError(
                f"{op!r} इत्यस्य कृते अङ्कः आवश्यकः, प्राप्तम् {type_name(value)} / "
                f"operator {op!r} needs a number, got {type_name(value)}",
                line, code="प्रकारदोषः",
            )

    def _need_numbers(self, left: Any, right: Any, op: str, line: int) -> None:
        self._need_number(left, op, line)
        self._need_number(right, op, line)


def interpret(program: A.Program, filename: str = "<वाक्>") -> Any:
    """Convenience wrapper."""
    return Interpreter(filename).run(program)
