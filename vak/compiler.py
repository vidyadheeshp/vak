"""
संकलकः — the Compiler of Vāk: AST → bytecode.

Walks the same tree the interpreter walks, but instead of performing actions it
emits instructions into a Chunk. Each कार्यम् compiles into its own Chunk, kept
in the enclosing chunk's constant table.

    संकलय(program) -> Chunk

Scopes stay dynamic (SCOPE_PUSH / SCOPE_POP over the same Environment chain the
tree-walker uses), so closures behave identically in both engines. Resolving
locals to frame slots is a later optimisation, not a semantic change.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any

from . import ast_nodes as A
from .builtins import BUILTIN_SIGNATURES
from .errors import VakError
from .opcodes import OPERANDS, SANSKRIT, Op
from .tokens import ANY_TYPE


class CompileError(VakError):
    title = "संकलनदोषः (Compile Error)"
    default_code = "संकलनदोषः"


@dataclass
class Chunk:
    """One unit of compiled code — a program, or the body of one कार्यम्."""
    name: str = "<मुख्यम्>"
    code: list[int] = field(default_factory=list)
    constants: list[Any] = field(default_factory=list)
    lines: list[int] = field(default_factory=list)

    def emit(self, op: Op, *operands: int, line: int = 0) -> int:
        """Write one instruction; returns the address it was written at."""
        at = len(self.code)
        self.code.append(int(op))
        self.lines.append(line)
        for operand in operands:
            self.code.append(int(operand))
            self.lines.append(line)
        return at

    def constant(self, value: Any) -> int:
        """Intern a constant and return its index."""
        for index, existing in enumerate(self.constants):
            if type(existing) is type(value) and existing == value:
                return index
        self.constants.append(value)
        return len(self.constants) - 1

    # -- jump patching -----------------------------------------------------
    def emit_jump(self, op: Op, line: int = 0) -> int:
        return self.emit(op, 0, line=line)

    def patch(self, at: int) -> None:
        """Point the jump written at `at` to the current end of the code."""
        self.code[at + 1] = len(self.code) - (at + 2)

    def patch_to(self, at: int, target: int) -> None:
        self.code[at + 1] = target - (at + 2)

    def emit_loop(self, start: int, line: int = 0) -> None:
        at = self.emit(Op.JUMP_BACK, 0, line=line)
        self.code[at + 1] = (at + 2) - start

    # -- disassembly -------------------------------------------------------
    def disassemble(self, indent: str = "") -> str:
        out = [f"{indent}॥ {self.name} ॥  ({len(self.code)} शब्दाः / words)"]
        ip = 0
        nested: list[Chunk] = []
        while ip < len(self.code):
            op = Op(self.code[ip])
            count = OPERANDS[op]
            operands = self.code[ip + 1: ip + 1 + count]
            line = self.lines[ip] if ip < len(self.lines) else 0
            text = f"{indent}{ip:>4}  {line:>4} | {SANSKRIT[op]:<16}"
            if op in (Op.CONST, Op.GET_VAR, Op.SET_VAR, Op.CLOSURE, Op.IMPORT,
                      Op.GET_BUILTIN):
                text += f"{operands[0]:>4}  {self.constants[operands[0]]!r}"
            elif op in (Op.DEF_VAR, Op.DEF_CONST):
                text += (f"{operands[0]:>4}  {self.constants[operands[0]]!r}"
                         f" : {self.constants[operands[1]]}")
            elif op in (Op.GET_LOCAL, Op.SET_LOCAL):
                text += (f"{operands[0]:>4} {operands[1]:>3}  "
                         f"{self.constants[operands[2]]!r}")
            elif op in (Op.JUMP, Op.JUMP_IF_FALSE, Op.JUMP_IF_TRUE, Op.ITER_NEXT):
                text += f"{operands[0]:>4}  → {ip + 2 + operands[0]}"
            elif op is Op.JUMP_BACK:
                text += f"{operands[0]:>4}  → {ip + 2 - operands[0]}"
            elif count:
                text += "  ".join(f"{o:>4}" for o in operands)
            out.append(text.rstrip())
            if op is Op.CLOSURE:
                nested.append(self.constants[operands[0]].chunk)
            ip += 1 + count
        for chunk in nested:
            out.append("")
            out.append(chunk.disassemble(indent + "    "))
        return "\n".join(out)


@dataclass
class CompiledFunction:
    """A कार्यम् after compilation — its signature plus its Chunk."""
    name: str
    params: list[A.Param]
    return_type: str
    chunk: Chunk

    @property
    def arity(self) -> int:
        return len(self.params)

    def __repr__(self) -> str:
        return f"<संकलितम् {self.name}/{len(self.params)}>"


@dataclass
class _Loop:
    """Where विरम and अनुवर्त should jump, and what to clean up first."""
    start: int
    scope_depth: int
    stack_extra: int                       # an iterator left on the stack
    breaks: list[int] = field(default_factory=list)
    continues: list[int] = field(default_factory=list)


class Compiler:
    """स्थाननिर्णयः — the compiler keeps the same picture of the scopes that the
    machine will build at run time, so a name it can see declared resolves to a
    place rather than to a search.

    `self.scopes` is that picture, innermost last.  A scope is the ordered list
    of names bound in it — the order the machine binds them in, since a binding
    is found by its position.  `None` stands for a scope whose contents the
    compiler cannot know: the global environment, which already holds every
    built-in before the program starts.  Nothing resolves through it.
    """

    def __init__(self, name: str = "<मुख्यम्>", filename: str = "<वाक्>",
                 scopes: list[list[str] | None] | None = None):
        self.chunk = Chunk(name)
        self.filename = filename
        self.loops: list[_Loop] = []
        self.scope_depth = 0
        self.scopes: list[list[str] | None] = scopes if scopes is not None else [None]
        # नामानि यानि क्वचिदपि घोष्यन्ते — तेभ्यः अन्तर्निहितम् न निर्णीयते।
        # Every name the program declares anywhere.  A built-in whose name
        # appears here might be shadowed at run time, so it is left to the
        # ordinary search; one that appears nowhere cannot be.
        self.shadowed: frozenset[str] = frozenset()

    # -- the scope model ---------------------------------------------------
    def _push_scope(self, names: list[str] | None = None) -> None:
        self.scopes.append(list(names) if names else [])

    def _pop_scope(self) -> None:
        self.scopes.pop()

    def _declare(self, name: str) -> None:
        """The machine overwrites a binding of the same name in place, keeping
        its position — so a redeclaration must not take a second slot here."""
        scope = self.scopes[-1]
        if scope is not None and name not in scope:
            scope.append(name)

    def _resolve(self, name: str) -> tuple[int, int] | None:
        """(how many scopes out, which binding) — or None, meaning search."""
        for hops, scope in enumerate(reversed(self.scopes)):
            if scope is None:
                return None                  # the global scope: never resolved
            if name in scope:
                return hops, scope.index(name)
        return None

    # ======================================================================
    def compile(self, program: A.Program) -> Chunk:
        for stmt in program.statements:
            self._hoist(stmt)
        for stmt in program.statements:
            self.statement(stmt)
        self.chunk.emit(Op.HALT, line=0)
        return self.chunk

    def compile_body(self, statements: list[A.Stmt]) -> None:
        for stmt in statements:
            self._hoist(stmt)
        for stmt in statements:
            self.statement(stmt)

    def _hoist(self, stmt: A.Stmt) -> None:
        """कार्याणि पूर्वम् — define functions before the rest of the block runs."""
        if isinstance(stmt, A.FunctionDecl):
            self._function(stmt.name, stmt.params, stmt.body, stmt.return_type, stmt.line)
            self._declare(stmt.name)
            self.chunk.emit(Op.DEF_VAR, self.chunk.constant(stmt.name),
                            self.chunk.constant(ANY_TYPE), line=stmt.line)

    # ======================================================================
    # statements
    # ======================================================================
    def statement(self, node: A.Stmt) -> None:
        method = getattr(self, "_st_" + type(node).__name__, None)
        if method is None:
            raise CompileError(
                f"अज्ञातम् वाक्यम् / cannot compile {type(node).__name__}", node.line
            )
        method(node)

    def _st_FunctionDecl(self, node: A.FunctionDecl) -> None:
        pass                                    # already emitted by _hoist

    def _st_ExpressionStmt(self, node: A.ExpressionStmt) -> None:
        self.expression(node.expr)
        self.chunk.emit(Op.POP, line=node.line)

    def _st_Print(self, node: A.Print) -> None:
        for arg in node.args:
            self.expression(arg)
        self.chunk.emit(Op.PRINT, len(node.args), line=node.line)

    def _st_VarDecl(self, node: A.VarDecl) -> None:
        if node.value is not None:
            self.expression(node.value)
        else:
            self.chunk.emit(Op.NIL, line=node.line)
        op = Op.DEF_CONST if node.constant else Op.DEF_VAR
        self._declare(node.name)
        self.chunk.emit(op, self.chunk.constant(node.name),
                        self.chunk.constant(node.type), line=node.line)

    def _st_Block(self, node: A.Block) -> None:
        self.chunk.emit(Op.SCOPE_PUSH, line=node.line)
        self.scope_depth += 1
        self._push_scope()
        self.compile_body(node.statements)
        self._pop_scope()
        self.scope_depth -= 1
        self.chunk.emit(Op.SCOPE_POP, line=node.line)

    def _st_If(self, node: A.If) -> None:
        self.expression(node.condition)
        else_jump = self.chunk.emit_jump(Op.JUMP_IF_FALSE, node.line)
        self.chunk.emit(Op.POP, line=node.line)
        self.statement(node.then_branch)
        end_jump = self.chunk.emit_jump(Op.JUMP, node.line)
        self.chunk.patch(else_jump)
        self.chunk.emit(Op.POP, line=node.line)
        if node.else_branch is not None:
            self.statement(node.else_branch)
        self.chunk.patch(end_jump)

    def _st_While(self, node: A.While) -> None:
        start = len(self.chunk.code)
        loop = _Loop(start, self.scope_depth, 0)
        self.loops.append(loop)
        self.expression(node.condition)
        exit_jump = self.chunk.emit_jump(Op.JUMP_IF_FALSE, node.line)
        self.chunk.emit(Op.POP, line=node.line)
        self.statement(node.body)
        for at in loop.continues:
            self.chunk.patch_to(at, start)
        self.chunk.emit_loop(start, node.line)
        self.chunk.patch(exit_jump)
        self.chunk.emit(Op.POP, line=node.line)
        self.loops.pop()
        for at in loop.breaks:
            self.chunk.patch(at)

    def _st_Repeat(self, node: A.Repeat) -> None:
        # आवृत्तिः (न्) — the VM iterates a number as परास(०, न्)
        self._iterate(node.count, "_आवृत्तिः_", node.body, node.line)

    def _st_ForEach(self, node: A.ForEach) -> None:
        self._iterate(node.iterable, node.var, node.body, node.line)

    def _iterate(self, iterable: A.Expr, var: str, body: A.Stmt, line: int) -> None:
        self.expression(iterable)
        self.chunk.emit(Op.ITER_NEW, line=line)
        start = len(self.chunk.code)
        loop = _Loop(start, self.scope_depth, stack_extra=1)
        self.loops.append(loop)
        exit_jump = self.chunk.emit_jump(Op.ITER_NEXT, line)
        self.chunk.emit(Op.SCOPE_PUSH, line=line)
        self.scope_depth += 1
        self._push_scope([var])
        self.chunk.emit(Op.DEF_VAR, self.chunk.constant(var),
                        self.chunk.constant(ANY_TYPE), line=line)
        if isinstance(body, A.Block):
            self.compile_body(body.statements)
        else:
            self.statement(body)
        self._pop_scope()
        self.scope_depth -= 1
        self.chunk.emit(Op.SCOPE_POP, line=line)
        for at in loop.continues:
            self.chunk.patch_to(at, start)
        self.chunk.emit_loop(start, line)
        self.chunk.patch(exit_jump)             # ITER_NEXT pops the iterator itself
        self.loops.pop()
        for at in loop.breaks:
            self.chunk.patch(at)

    def _st_Break(self, node: A.Break) -> None:
        if not self.loops:
            raise CompileError("'विरम' पाशस्य बहिः / 'विरम' outside a loop", node.line)
        loop = self.loops[-1]
        for _ in range(self.scope_depth - loop.scope_depth):
            self.chunk.emit(Op.SCOPE_POP, line=node.line)
        for _ in range(loop.stack_extra):
            self.chunk.emit(Op.POP, line=node.line)
        loop.breaks.append(self.chunk.emit_jump(Op.JUMP, node.line))

    def _st_Continue(self, node: A.Continue) -> None:
        if not self.loops:
            raise CompileError("'अनुवर्त' पाशस्य बहिः / 'अनुवर्त' outside a loop", node.line)
        loop = self.loops[-1]
        for _ in range(self.scope_depth - loop.scope_depth):
            self.chunk.emit(Op.SCOPE_POP, line=node.line)
        loop.continues.append(self.chunk.emit_jump(Op.JUMP, node.line))

    def _st_Return(self, node: A.Return) -> None:
        if node.value is not None:
            self.expression(node.value)
        else:
            self.chunk.emit(Op.NIL, line=node.line)
        self.chunk.emit(Op.RETURN, line=node.line)

    def _st_Throw(self, node: A.Throw) -> None:
        self.expression(node.value)
        self.chunk.emit(Op.THROW, line=node.line)

    def _st_Import(self, node: A.Import) -> None:
        payload = (node.path, node.alias, tuple(node.names))
        # आनय binds exactly these, in this order — the machine and the model
        # must agree, or the slots after them would all be off by one.
        if node.names:
            for name in node.names:
                self._declare(name)
        else:
            stem = node.path.replace("\\", "/").rsplit("/", 1)[-1]
            stem = stem[:-4] if stem.endswith(".vak") else stem
            self._declare(node.alias or stem)
        self.chunk.emit(Op.IMPORT, self.chunk.constant(payload), line=node.line)

    def _st_Switch(self, node: A.Switch) -> None:
        """विकल्पः needs no instruction of its own.

        The subject stays on the stack; each पक्षः value is compared against a
        copy of it, and the first match jumps to its own body.  Because this is
        built out of instructions the machine already had, every engine — the
        Python VM, the Vāk VM and the C VM — runs it the day it is written.
        """
        self.expression(node.subject)                       # [विषयः]

        hits: list[tuple[A.SwitchCase, list[int]]] = []
        default: A.SwitchCase | None = None
        for case in node.cases:
            if case.is_default:
                default = case
                continue
            jumps: list[int] = []
            for expr in case.values:
                self.chunk.emit(Op.DUP, line=case.line)     # [विषयः, विषयः]
                self.expression(expr)                       # [विषयः, विषयः, मूल्यम्]
                self.chunk.emit(Op.EQ, line=case.line)      # [विषयः, सत्यता]
                jumps.append(self.chunk.emit_jump(Op.JUMP_IF_TRUE, case.line))
                self.chunk.emit(Op.POP, line=case.line)     # not this one — drop it
            hits.append((case, jumps))

        to_default = self.chunk.emit_jump(Op.JUMP, node.line)

        ends: list[int] = []
        for case, jumps in hits:
            for at in jumps:
                self.chunk.patch(at)
            self.chunk.emit(Op.POP, line=case.line)         # the सत्यता that matched
            self.chunk.emit(Op.POP, line=case.line)         # the विषयः itself
            self._case_body(case)
            ends.append(self.chunk.emit_jump(Op.JUMP, case.line))

        self.chunk.patch(to_default)
        self.chunk.emit(Op.POP, line=node.line)             # the विषयः, unmatched
        if default is not None:
            self._case_body(default)
        for at in ends:
            self.chunk.patch(at)

    def _case_body(self, case: A.SwitchCase) -> None:
        """A पक्षः is a scope of its own, like any other block."""
        self.chunk.emit(Op.SCOPE_PUSH, line=case.line)
        self.scope_depth += 1
        self._push_scope()
        self.compile_body(case.body)
        self._pop_scope()
        self.scope_depth -= 1
        self.chunk.emit(Op.SCOPE_POP, line=case.line)

    def _st_Try(self, node: A.Try) -> None:
        setup = self.chunk.emit(Op.SETUP_TRY, 0, 0, line=node.line)
        self.statement(node.body)
        self.chunk.emit(Op.POP_TRY, line=node.line)
        to_finally = self.chunk.emit_jump(Op.JUMP, node.line)

        # दोषे — the VM pushes the error कोशः before jumping here
        catch_at = len(self.chunk.code)
        if node.catch_body is not None:
            self.chunk.emit(Op.SCOPE_PUSH, line=node.line)
            self.scope_depth += 1
            self._push_scope([node.catch_var] if node.catch_var else [])
            if node.catch_var:
                self.chunk.emit(Op.DEF_VAR, self.chunk.constant(node.catch_var),
                                self.chunk.constant(ANY_TYPE), line=node.line)
            else:
                self.chunk.emit(Op.POP, line=node.line)
            self.compile_body(node.catch_body.statements)
            self._pop_scope()
            self.scope_depth -= 1
            self.chunk.emit(Op.SCOPE_POP, line=node.line)
        self.chunk.patch(to_finally)

        # अन्ततः — runs on every path, including while unwinding
        finally_at = len(self.chunk.code)
        if node.finally_body is not None:
            self.statement(node.finally_body)
        self.chunk.emit(Op.END_FINALLY, line=node.line)

        self.chunk.code[setup + 1] = (catch_at if node.catch_body is not None else -1)
        self.chunk.code[setup + 2] = finally_at

    # ======================================================================
    # expressions
    # ======================================================================
    def expression(self, node: A.Expr) -> None:
        method = getattr(self, "_ex_" + type(node).__name__, None)
        if method is None:
            raise CompileError(
                f"अज्ञातम् पदम् / cannot compile {type(node).__name__}", node.line
            )
        method(node)

    def _ex_Literal(self, node: A.Literal) -> None:
        value = node.value
        if value is None:
            self.chunk.emit(Op.NIL, line=node.line)
        elif value is True:
            self.chunk.emit(Op.TRUE, line=node.line)
        elif value is False:
            self.chunk.emit(Op.FALSE, line=node.line)
        else:
            self.chunk.emit(Op.CONST, self.chunk.constant(value), line=node.line)

    def _ex_Identifier(self, node: A.Identifier) -> None:
        place = self._resolve(node.name)
        if place is None:
            if node.name in BUILTIN_SIGNATURES and node.name not in self.shadowed:
                self.chunk.emit(Op.GET_BUILTIN, self.chunk.constant(node.name),
                                line=node.line)
                return
            self.chunk.emit(Op.GET_VAR, self.chunk.constant(node.name), line=node.line)
        else:
            self.chunk.emit(Op.GET_LOCAL, place[0], place[1],
                            self.chunk.constant(node.name), line=node.line)

    def _ex_Assign(self, node: A.Assign) -> None:
        self.expression(node.value)
        place = self._resolve(node.name)
        if place is None:
            self.chunk.emit(Op.SET_VAR, self.chunk.constant(node.name), line=node.line)
        else:
            self.chunk.emit(Op.SET_LOCAL, place[0], place[1],
                            self.chunk.constant(node.name), line=node.line)

    def _ex_ListLit(self, node: A.ListLit) -> None:
        for element in node.elements:
            self.expression(element)
        self.chunk.emit(Op.BUILD_LIST, len(node.elements), line=node.line)

    def _ex_DictLit(self, node: A.DictLit) -> None:
        for key, value in node.pairs:
            self.expression(key)
            self.expression(value)
        self.chunk.emit(Op.BUILD_DICT, len(node.pairs), line=node.line)

    def _ex_IndexGet(self, node: A.IndexGet) -> None:
        self.expression(node.target)
        self.expression(node.index)
        self.chunk.emit(Op.INDEX_GET, line=node.line)

    def _ex_IndexSet(self, node: A.IndexSet) -> None:
        self.expression(node.target)
        self.expression(node.index)
        self.expression(node.value)
        self.chunk.emit(Op.INDEX_SET, line=node.line)

    def _ex_Unary(self, node: A.Unary) -> None:
        self.expression(node.right)
        self.chunk.emit(Op.NEG if node.op == "-" else Op.NOT, line=node.line)

    _BINARY = {
        "+": Op.ADD, "-": Op.SUB, "*": Op.MUL, "/": Op.DIV, "%": Op.MOD, "^": Op.POW,
        "==": Op.EQ, "!=": Op.NE, "<": Op.LT, "<=": Op.LE, ">": Op.GT, ">=": Op.GE,
    }

    def _ex_Binary(self, node: A.Binary) -> None:
        self.expression(node.left)
        self.expression(node.right)
        self.chunk.emit(self._BINARY[node.op], line=node.line)

    def _ex_Logical(self, node: A.Logical) -> None:
        self.expression(node.left)
        jump = self.chunk.emit_jump(
            Op.JUMP_IF_FALSE if node.op == "च" else Op.JUMP_IF_TRUE, node.line
        )
        self.chunk.emit(Op.POP, line=node.line)
        self.expression(node.right)
        self.chunk.patch(jump)

    def _ex_Call(self, node: A.Call) -> None:
        self.expression(node.callee)
        for arg in node.args:
            self.expression(arg)
        if any(node.arg_karakas):
            labels = self.chunk.constant(tuple(node.arg_karakas))
            self.chunk.emit(Op.CALL_LABELLED, len(node.args), labels, line=node.line)
        else:
            self.chunk.emit(Op.CALL, len(node.args), line=node.line)

    def _ex_FunctionExpr(self, node: A.FunctionExpr) -> None:
        self._function(node.name, node.params, node.body, node.return_type, node.line)

    # -- functions ---------------------------------------------------------
    def _function(self, name: str, params: list[A.Param], body: A.Block,
                  return_type: str, line: int) -> None:
        # The frame the machine makes for a call hangs off the environment the
        # closure was made in — this one — so the compiler's picture of the
        # scopes carries straight through, and a nested कार्यम् can still reach
        # the locals of the one that encloses it by position.
        inner = Compiler(name, self.filename,
                         scopes=[*self.scopes, [p.name for p in params]])
        inner.shadowed = self.shadowed
        inner.scope_depth = 1        # the call frame's own environment is scope १
        # Parameters are bound by the VM when the frame is made: it reorders
        # kāraka-labelled arguments and checks declared types there.
        inner.compile_body(body.statements)
        inner.chunk.emit(Op.NIL, line=line)
        inner.chunk.emit(Op.RETURN, line=line)
        compiled = CompiledFunction(name, params, return_type, inner.chunk)
        self.chunk.emit(Op.CLOSURE, self.chunk.constant(compiled), line=line)


def declared_names(node: Any) -> set[str]:
    """Every name this program binds, anywhere, at any depth.

    Used to decide whether a built-in can be reached directly: if the program
    never declares that name, nothing can be standing in front of it.
    """
    found: set[str] = set()

    def walk(n: Any) -> None:
        if isinstance(n, (A.VarDecl, A.FunctionDecl)):
            found.add(n.name)
        elif isinstance(n, A.ForEach):
            found.add(n.var)
        elif isinstance(n, A.Try) and n.catch_var:
            found.add(n.catch_var)
        elif isinstance(n, A.Param):
            found.add(n.name)
        elif isinstance(n, A.Import):
            if n.names:
                found.update(n.names)
            else:
                stem = n.path.replace("\\", "/").rsplit("/", 1)[-1]
                found.add(n.alias or (stem[:-4] if stem.endswith(".vak") else stem))
        if is_dataclass(n) and not isinstance(n, type):
            for f in fields(n):
                walk(getattr(n, f.name))
        elif isinstance(n, (list, tuple)):
            for item in n:
                walk(item)

    walk(node)
    if isinstance(node, A.Program):
        for stmt in node.statements:
            walk(stmt)
    return found


def compile_program(program: A.Program, filename: str = "<वाक्>") -> Chunk:
    """Convenience wrapper — संकलय।"""
    compiler = Compiler("<मुख्यम्>", filename)
    compiler.shadowed = frozenset(declared_names(program))
    return compiler.compile(program)
