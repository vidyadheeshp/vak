"""
अर्थविश्लेषकः — the Semantic Analyser of Vāk.

A static pass that walks the AST *before* the interpreter runs it and answers
questions the parser cannot:

  * नामनिर्णयः    — is every name declared before it is used?
  * प्रकारपरीक्षा  — do the declared प्रकाराः agree with what flows into them?
  * प्रवाहपरीक्षा  — is प्रत्यागच्छ inside a कार्यम्, विरम inside a पाशः?
                     is any statement unreachable?
  * कारकपरीक्षा   — do the kāraka roles obey Sanskrit grammar?

Kāraka checking is the part no other language has. A kāraka is the *role a
value plays in an action* — the agent, the patient, the instrument — and
Sanskrit marks it with a case ending. Vāk lets a parameter carry that role, and
this analyser enforces the grammar of roles: one कर्ता and one कर्म at most, in
the canonical order, with the kind of value each role can sensibly hold.

Diagnostics are collected, never thrown one at a time, so a single run reports
everything wrong with a program.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import ast_nodes as A
from .builtins import BUILTIN_SIGNATURES
from .errors import VakError
from .tokens import ANY_TYPE, KARAKA_ORDER, KARAKA_VIBHAKTI

NUMERIC = {"पूर्णाङ्कः", "दशांशः", "अङ्कः"}
COLLECTIONS = {"सूची", "कोशः", "शब्दः"}
CONTAINERS = {"सूची", "कोशः"}


# ==========================================================================
# diagnostics
# ==========================================================================
@dataclass
class Diagnostic:
    code: str            # नामदोषः, प्रकारदोषः, प्रवाहदोषः, कारकदोषः ...
    message: str
    line: int = 0
    fatal: bool = True   # False -> सूचना (a warning)

    def render(self, source: str | None = None, filename: str = "<वाक्>") -> str:
        kind = "दोषः" if self.fatal else "सूचना"
        head = f"  {kind} [{self.code}] {filename}:{self.line} — {self.message}"
        if source and self.line:
            lines = source.splitlines()
            if 0 < self.line <= len(lines):
                head += f"\n      {self.line:>4} | {lines[self.line - 1].strip()}"
        return head


class SemanticError(VakError):
    """Raised when the analyser found at least one fatal diagnostic."""

    title = "अर्थदोषः (Semantic Error)"
    default_code = "अर्थदोषः"

    def __init__(self, report: "Report", filename: str = "<वाक्>", source: str | None = None):
        self.report = report
        first = report.errors[0]
        super().__init__(first.message, first.line, code=first.code)
        self.filename = filename
        self.source = source

    def render(self, source: str | None = None, filename: str | None = None) -> str:
        return self.report.render(source or self.source, filename or self.filename)


@dataclass
class Report:
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def errors(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.fatal]

    @property
    def warnings(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if not d.fatal]

    @property
    def ok(self) -> bool:
        return not self.errors

    def render(self, source: str | None = None, filename: str = "<वाक्>") -> str:
        if not self.diagnostics:
            return "अर्थविश्लेषणम् निर्दोषम् / semantic analysis found nothing"
        head = (f"अर्थदोषः (Semantic Analysis) — {len(self.errors)} दोषाः, "
                f"{len(self.warnings)} सूचनाः")
        body = [d.render(source, filename) for d in
                sorted(self.diagnostics, key=lambda d: (d.line, not d.fatal))]
        return "\n".join([head, *body])


# ==========================================================================
# symbols and scopes
# ==========================================================================
@dataclass
class Symbol:
    name: str
    type: str = ANY_TYPE
    constant: bool = False
    line: int = 0
    params: list[A.Param] | None = None     # set for functions
    return_type: str = ANY_TYPE
    native_arity: int | None = None         # set for built-ins

    @property
    def is_callable(self) -> bool:
        return self.params is not None or self.native_arity is not None


class Scope:
    __slots__ = ("symbols", "parent", "kind")

    def __init__(self, parent: "Scope | None" = None, kind: str = "खण्डः"):
        self.symbols: dict[str, Symbol] = {}
        self.parent = parent
        self.kind = kind

    def declare(self, symbol: Symbol) -> None:
        self.symbols[symbol.name] = symbol

    def lookup(self, name: str) -> Symbol | None:
        scope: Scope | None = self
        while scope is not None:
            found = scope.symbols.get(name)
            if found is not None:
                return found
            scope = scope.parent
        return None

    def declared_here(self, name: str) -> bool:
        return name in self.symbols


# ==========================================================================
# the analyser
# ==========================================================================
class Analyzer:
    def __init__(self, filename: str = "<वाक्>"):
        self.filename = filename
        self.report = Report()
        self.prelude = Scope(None, "अन्तर्निहितम्")
        for name, (arity, rtype) in BUILTIN_SIGNATURES.items():
            self.prelude.declare(
                Symbol(name, "कार्यम्", constant=True, native_arity=arity, return_type=rtype)
            )
        self.scope = Scope(self.prelude, "वैश्विकः")
        self.function_stack: list[Symbol] = []
        self.loop_depth = 0

    # -- diagnostics -------------------------------------------------------
    def _error(self, code: str, message: str, line: int) -> None:
        self.report.diagnostics.append(Diagnostic(code, message, line, True))

    def _warn(self, code: str, message: str, line: int) -> None:
        self.report.diagnostics.append(Diagnostic(code, message, line, False))

    # -- entry point -------------------------------------------------------
    def analyze(self, program: A.Program) -> Report:
        self._block(program.statements, self.scope)
        return self.report

    # ======================================================================
    # scopes and blocks
    # ======================================================================
    def _block(self, statements: list[A.Stmt], scope: Scope) -> None:
        previous, self.scope = self.scope, scope
        try:
            self._hoist(statements)
            exited: A.Stmt | None = None
            for stmt in statements:
                if exited is not None:
                    self._warn(
                        "अगम्यदोषः",
                        f"इदम् वाक्यम् कदापि न चलति / unreachable code after "
                        f"{type(exited).__name__} on line {exited.line}",
                        stmt.line,
                    )
                    exited = None                  # report once per block
                self._statement(stmt)
                if self._always_exits(stmt):
                    exited = stmt
        finally:
            self.scope = previous

    def _hoist(self, statements: list[A.Stmt]) -> None:
        for stmt in statements:
            if isinstance(stmt, A.FunctionDecl):
                self.scope.declare(Symbol(
                    stmt.name, "कार्यम्", line=stmt.line,
                    params=stmt.params, return_type=stmt.return_type,
                ))

    @staticmethod
    def _always_exits(stmt: A.Stmt) -> bool:
        """Does control certainly leave the block at this statement?"""
        if isinstance(stmt, (A.Return, A.Throw, A.Break, A.Continue)):
            return True
        if isinstance(stmt, A.Block):
            return any(Analyzer._always_exits(s) for s in stmt.statements)
        if isinstance(stmt, A.If):
            return (stmt.else_branch is not None
                    and Analyzer._always_exits(stmt.then_branch)
                    and Analyzer._always_exits(stmt.else_branch))
        if isinstance(stmt, A.Switch):
            # Only with an अन्यथा is every subject accounted for; without one,
            # a value matching no पक्षः falls straight out of the विकल्पः.
            if not any(case.is_default for case in stmt.cases):
                return False
            return all(any(Analyzer._always_exits(s) for s in case.body)
                       for case in stmt.cases)
        if isinstance(stmt, A.Try):
            body_exits = Analyzer._always_exits(stmt.body)
            catch_exits = stmt.catch_body is not None and Analyzer._always_exits(stmt.catch_body)
            finally_exits = (stmt.finally_body is not None
                             and Analyzer._always_exits(stmt.finally_body))
            return finally_exits or (body_exits and catch_exits)
        return False

    # ======================================================================
    # statements
    # ======================================================================
    def _statement(self, node: A.Stmt) -> None:
        getattr(self, "_st_" + type(node).__name__, self._st_unknown)(node)

    def _st_unknown(self, node: A.Stmt) -> None:
        pass

    def _st_ExpressionStmt(self, node: A.ExpressionStmt) -> None:
        self._type_of(node.expr)

    def _st_Print(self, node: A.Print) -> None:
        for arg in node.args:
            self._type_of(arg)

    def _st_VarDecl(self, node: A.VarDecl) -> None:
        value_type = self._type_of(node.value) if node.value is not None else ANY_TYPE
        if node.value is not None and not self._assignable(value_type, node.type):
            self._error(
                "प्रकारदोषः",
                f"चरः {node.name!r}: {node.type} अपेक्षितः, {value_type} दीयते / "
                f"expected {node.type}, got {value_type}",
                node.line,
            )
        if self.scope.declared_here(node.name):
            self._warn(
                "पुनर्घोषणा",
                f"{node.name!r} अस्मिन् एव परिवेशे पुनः घोष्यते / "
                f"{node.name!r} is redeclared in the same scope",
                node.line,
            )
        self.scope.declare(Symbol(node.name, node.type, node.constant, node.line))

    def _st_Import(self, node: A.Import) -> None:
        """The analyser does not load modules — it only records what an
        आनय brings into scope, as किमपि. Module contents are checked when
        that module is itself analysed."""
        if node.names:
            for name in node.names:
                self.scope.declare(Symbol(name, ANY_TYPE, line=node.line))
            return
        bound = node.alias or node.path.replace("\\", "/").rsplit("/", 1)[-1]
        if bound.endswith(".vak"):
            bound = bound[:-4]
        self.scope.declare(Symbol(bound, "कोशः", line=node.line))

    def _st_Block(self, node: A.Block) -> None:
        self._block(node.statements, Scope(self.scope, "खण्डः"))

    def _st_If(self, node: A.If) -> None:
        self._type_of(node.condition)
        self._statement(node.then_branch)
        if node.else_branch is not None:
            self._statement(node.else_branch)

    def _st_While(self, node: A.While) -> None:
        self._type_of(node.condition)
        self.loop_depth += 1
        self._statement(node.body)
        self.loop_depth -= 1

    def _st_Repeat(self, node: A.Repeat) -> None:
        count = self._type_of(node.count)
        if count not in NUMERIC and count != ANY_TYPE:
            self._error(
                "प्रकारदोषः",
                f"आवृत्तिः अङ्कम् इच्छति, {count} दत्तः / आवृत्तिः needs a number, got {count}",
                node.line,
            )
        self.loop_depth += 1
        self._statement(node.body)
        self.loop_depth -= 1

    def _st_ForEach(self, node: A.ForEach) -> None:
        iterable = self._type_of(node.iterable)
        if iterable != ANY_TYPE and iterable not in COLLECTIONS | NUMERIC:
            self._error(
                "प्रकारदोषः",
                f"{iterable} इत्यस्य उपरि न भ्रमितुं शक्यते / cannot iterate over {iterable}",
                node.line,
            )
        item_type = {"शब्दः": "शब्दः", "पूर्णाङ्कः": "पूर्णाङ्कः",
                     "अङ्कः": "पूर्णाङ्कः", "दशांशः": "पूर्णाङ्कः"}.get(iterable, ANY_TYPE)
        loop_scope = Scope(self.scope, "पाशः")
        loop_scope.declare(Symbol(node.var, item_type, line=node.line))
        self.loop_depth += 1
        if isinstance(node.body, A.Block):
            self._block(node.body.statements, loop_scope)
        else:
            previous, self.scope = self.scope, loop_scope
            self._statement(node.body)
            self.scope = previous
        self.loop_depth -= 1

    def _st_Break(self, node: A.Break) -> None:
        if self.loop_depth == 0:
            self._error("प्रवाहदोषः",
                        "'विरम' पाशस्य बहिः / 'विरम' outside a loop", node.line)

    def _st_Continue(self, node: A.Continue) -> None:
        if self.loop_depth == 0:
            self._error("प्रवाहदोषः",
                        "'अनुवर्त' पाशस्य बहिः / 'अनुवर्त' outside a loop", node.line)

    def _st_Return(self, node: A.Return) -> None:
        if not self.function_stack:
            self._error(
                "प्रवाहदोषः",
                "'प्रत्यागच्छ' कार्यस्य बहिः / 'प्रत्यागच्छ' outside a कार्यम्",
                node.line,
            )
            if node.value is not None:
                self._type_of(node.value)
            return
        declared = self.function_stack[-1].return_type
        value_type = self._type_of(node.value) if node.value is not None else "शून्यम्"
        if not self._assignable(value_type, declared):
            self._error(
                "प्रकारदोषः",
                f"{self.function_stack[-1].name} इत्यस्य प्रतिफलम्: {declared} अपेक्षितम्, "
                f"{value_type} दीयते / expected {declared}, got {value_type}",
                node.line,
            )

    def _st_Throw(self, node: A.Throw) -> None:
        self._type_of(node.value)

    def _st_Switch(self, node: A.Switch) -> None:
        """विकल्पः — a पक्षः that could never match, or that was already given,
        is worth saying out loud: neither can ever run."""
        subject = self._type_of(node.subject)
        seen: dict[tuple[str, object], int] = {}
        defaults = 0
        for case in node.cases:
            if case.is_default:
                defaults += 1
                if defaults > 1:
                    self._error(
                        "प्रवाहदोषः",
                        "एकम् एव 'अन्यथा' विकल्पे / a विकल्पः may have only one अन्यथा",
                        case.line,
                    )
            for expr in case.values:
                given = self._type_of(expr)
                if not self._comparable(subject, given):
                    self._error(
                        "प्रकारदोषः",
                        f"पक्षः {given}, विषयः तु {subject} — कदापि न मिलतः / "
                        f"a {given} पक्षः can never match a {subject} subject",
                        case.line,
                    )
                if isinstance(expr, A.Literal):
                    key = (type(expr.value).__name__, expr.value)
                    if key in seen:
                        self._error(
                            "प्रवाहदोषः",
                            f"पक्षः पुनरुक्तः — पङ्क्तौ {seen[key]} एव दत्तः / "
                            f"this पक्षः is already given on line {seen[key]}, so "
                            f"this one can never run",
                            case.line,
                        )
                    else:
                        seen[key] = case.line
            self._block(case.body, Scope(self.scope, "पक्षे"))
        if defaults == 0:
            self._warn(
                "प्रवाहसूचना",
                "विकल्पे 'अन्यथा' नास्ति — अमिलितः विषयः किमपि न करोति / "
                "no अन्यथा, so a subject that matches nothing does nothing",
                node.line,
            )

    @staticmethod
    def _comparable(subject: str, given: str) -> bool:
        """Could these two ever be equal?  Only a provable never is an error."""
        if ANY_TYPE in (subject, given) or subject == given:
            return True
        return subject in NUMERIC and given in NUMERIC

    def _st_Try(self, node: A.Try) -> None:
        self._statement(node.body)
        if node.catch_body is not None:
            catch_scope = Scope(self.scope, "दोषे")
            if node.catch_var:
                catch_scope.declare(Symbol(node.catch_var, "कोशः", line=node.line))
            self._block(node.catch_body.statements, catch_scope)
        if node.finally_body is not None:
            self._statement(node.finally_body)

    def _st_FunctionDecl(self, node: A.FunctionDecl) -> None:
        symbol = self.scope.lookup(node.name)
        if symbol is None or not symbol.is_callable:
            symbol = Symbol(node.name, "कार्यम्", line=node.line,
                            params=node.params, return_type=node.return_type)
            self.scope.declare(symbol)
        self._check_karakas(node.name, node.params, node.return_type, node.line)
        self._function_body(symbol, node.params, node.body, node.return_type, node.line)

    def _function_body(self, symbol: Symbol, params: list[A.Param], body: A.Block,
                       return_type: str, line: int) -> None:
        scope = Scope(self.scope, "कार्यम्")
        for param in params:
            scope.declare(Symbol(param.name, param.type, line=line))
        self.function_stack.append(symbol)
        outer_loops, self.loop_depth = self.loop_depth, 0
        self._block(body.statements, scope)
        self.loop_depth = outer_loops
        self.function_stack.pop()

        if return_type not in (ANY_TYPE, "शून्यम्") and not self._returns_on_every_path(body):
            self._warn(
                "प्रतिफलसूचना",
                f"{symbol.name}: {return_type} इति प्रतिज्ञातम्, किन्तु मार्गः अस्ति यत्र "
                f"किमपि न प्रत्यागच्छति / declared {return_type} but some path returns nothing",
                line,
            )

    @staticmethod
    def _returns_on_every_path(stmt: A.Stmt) -> bool:
        if isinstance(stmt, A.Return):
            return True
        if isinstance(stmt, A.Throw):
            return True
        if isinstance(stmt, A.Block):
            return any(Analyzer._returns_on_every_path(s) for s in stmt.statements)
        if isinstance(stmt, A.If):
            return (stmt.else_branch is not None
                    and Analyzer._returns_on_every_path(stmt.then_branch)
                    and Analyzer._returns_on_every_path(stmt.else_branch))
        if isinstance(stmt, A.Switch):
            # A विकल्पः covers every subject only when it has an अन्यथा.
            if not any(case.is_default for case in stmt.cases):
                return False
            return all(any(Analyzer._returns_on_every_path(s) for s in case.body)
                       for case in stmt.cases)
        if isinstance(stmt, A.Try):
            body_ok = Analyzer._returns_on_every_path(stmt.body)
            catch_ok = (stmt.catch_body is not None
                        and Analyzer._returns_on_every_path(stmt.catch_body))
            finally_ok = (stmt.finally_body is not None
                          and Analyzer._returns_on_every_path(stmt.finally_body))
            return finally_ok or (body_ok and catch_ok)
        return False

    # ======================================================================
    # कारकपरीक्षा — the grammar of roles
    # ======================================================================
    def _check_karakas(self, name: str, params: list[A.Param], return_type: str,
                       line: int) -> None:
        marked = [p for p in params if p.karaka]
        if not marked:
            return
        if len(marked) != len(params):
            self._warn(
                "कारकसूचना",
                f"{name}: केचन प्राचलाः कारकयुक्ताः, केचन न / "
                f"only {len(marked)} of {len(params)} parameters carry a कारकम्",
                line,
            )

        # १. एकम् एव कर्म, एकः एव कर्ता — Pāṇini allows one of each per action
        for role in ("कर्ता", "कर्म"):
            count = sum(1 for p in marked if p.karaka == role)
            if count > 1:
                self._error(
                    "कारकदोषः",
                    f"{name}: {role} इति {count} वारम् — एकम् एव भवितुम् अर्हति / "
                    f"a कार्यम् may declare only one {role}",
                    line,
                )

        # २. कारकाणाम् क्रमः नियतः नास्ति — विभक्तिः एव क्रमम् मोचयति।
        # Order is deliberately NOT enforced: in Sanskrit the case ending is
        # what frees word order, so a caller may pass roles in any sequence
        # (see the labelled-argument form `छानय(करणम्: प, अपादानम्: स)`).

        # ३. प्रत्येकम् कारकम् यत् धारयितुम् अर्हति
        expectations = {
            "करणम्": ({"कार्यम्", "शब्दः"}, "साधनम् — कार्यम् शब्दः वा"),
            "अपादानम्": (COLLECTIONS, "यतः आदीयते — संग्रहः"),
            "सम्प्रदानम्": (CONTAINERS, "यस्मै दीयते — पात्रम्"),
            "अधिकरणम्": (COLLECTIONS, "यत्र क्रिया — आधारः"),
        }
        for param in marked:
            allowed, gloss = expectations.get(param.karaka, (None, ""))
            if allowed and param.type != ANY_TYPE and param.type not in allowed:
                self._warn(
                    "कारकसूचना",
                    f"{name}: {param.karaka} {param.name!r} इत्यस्य प्रकारः {param.type} — "
                    f"{gloss} अपेक्ष्यते ({KARAKA_VIBHAKTI[param.karaka]})",
                    line,
                )

        # ४. सकर्मकम् कार्यम् फलम् ददाति — a verb with a कर्म yields something
        if any(p.karaka == "कर्म" for p in marked) and return_type == "शून्यम्":
            self._warn(
                "कारकसूचना",
                f"{name}: कर्म अस्ति किन्तु प्रतिफलम् शून्यम् — सकर्मकम् कार्यम् फलम् "
                f"ददाति / a कार्यम् with a कर्म normally produces a result",
                line,
            )

    # ======================================================================
    # expressions — every method returns the inferred प्रकारः
    # ======================================================================
    def _type_of(self, node: A.Expr | None) -> str:
        if node is None:
            return "शून्यम्"
        return getattr(self, "_ex_" + type(node).__name__, self._ex_unknown)(node)

    def _ex_unknown(self, node: A.Expr) -> str:
        return ANY_TYPE

    def _ex_Literal(self, node: A.Literal) -> str:
        value = node.value
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
        return ANY_TYPE

    def _ex_ListLit(self, node: A.ListLit) -> str:
        for element in node.elements:
            self._type_of(element)
        return "सूची"

    def _ex_DictLit(self, node: A.DictLit) -> str:
        for key, value in node.pairs:
            self._type_of(key)
            self._type_of(value)
        return "कोशः"

    def _ex_Identifier(self, node: A.Identifier) -> str:
        symbol = self.scope.lookup(node.name)
        if symbol is None:
            self._error(
                "नामदोषः",
                f"अपरिभाषितम् नाम {node.name!r} / undefined name {node.name!r}",
                node.line,
            )
            return ANY_TYPE
        return symbol.type

    def _ex_Assign(self, node: A.Assign) -> str:
        value_type = self._type_of(node.value)
        symbol = self.scope.lookup(node.name)
        if symbol is None:
            self._error(
                "नामदोषः",
                f"अपरिभाषितम् नाम {node.name!r} — प्रथमम् 'मान' इति उपयुज्यताम् / "
                f"undefined name {node.name!r}",
                node.line,
            )
            return value_type
        if symbol.constant:
            self._error(
                "ध्रुवदोषः",
                f"ध्रुवः {node.name!r} न परिवर्तनीयः / cannot reassign the constant "
                f"{node.name!r}",
                node.line,
            )
        elif not self._assignable(value_type, symbol.type):
            self._error(
                "प्रकारदोषः",
                f"चरः {node.name!r}: {symbol.type} अपेक्षितः, {value_type} दीयते / "
                f"expected {symbol.type}, got {value_type}",
                node.line,
            )
        return symbol.type if symbol.type != ANY_TYPE else value_type

    def _ex_IndexGet(self, node: A.IndexGet) -> str:
        target = self._type_of(node.target)
        self._type_of(node.index)
        if target not in (ANY_TYPE, *COLLECTIONS):
            self._error(
                "प्रकारदोषः",
                f"{target} इत्यस्मिन् सूचकः न प्रयोज्यः / cannot index a {target}",
                node.line,
            )
        return "शब्दः" if target == "शब्दः" else ANY_TYPE

    def _ex_IndexSet(self, node: A.IndexSet) -> str:
        target = self._type_of(node.target)
        self._type_of(node.index)
        value = self._type_of(node.value)
        if target not in (ANY_TYPE, *CONTAINERS):
            self._error(
                "प्रकारदोषः",
                f"{target} इत्यस्मिन् न स्थापयितुम् शक्यते / cannot assign into a {target}",
                node.line,
            )
        return value

    def _ex_Unary(self, node: A.Unary) -> str:
        operand = self._type_of(node.right)
        if node.op == "-":
            if operand not in NUMERIC and operand != ANY_TYPE:
                self._error(
                    "प्रकारदोषः",
                    f"'-' अङ्कम् इच्छति, {operand} दत्तः / unary '-' needs a number, "
                    f"got {operand}",
                    node.line,
                )
            return operand if operand in NUMERIC else "अङ्कः"
        return "सत्यता"

    def _ex_Logical(self, node: A.Logical) -> str:
        self._type_of(node.left)
        self._type_of(node.right)
        return ANY_TYPE          # च / वा yield one of their operands

    def _ex_Binary(self, node: A.Binary) -> str:
        left = self._type_of(node.left)
        right = self._type_of(node.right)
        op, line = node.op, node.line

        if op in ("==", "!="):
            return "सत्यता"

        unknown = ANY_TYPE in (left, right)

        if op == "+":
            if unknown or "शब्दः" in (left, right):
                return "शब्दः" if "शब्दः" in (left, right) else ANY_TYPE
            if left == "सूची" and right == "सूची":
                return "सूची"
            if left in NUMERIC and right in NUMERIC:
                return self._numeric_result(left, right)
            self._error(
                "प्रकारदोषः",
                f"'+' {left} तथा {right} इत्येतयोः कृते न प्रयोज्यम् / "
                f"cannot apply '+' to {left} and {right}",
                line,
            )
            return ANY_TYPE

        if op in ("<", "<=", ">", ">="):
            if not unknown and not (
                (left in NUMERIC and right in NUMERIC) or (left == right == "शब्दः")
            ):
                self._error(
                    "प्रकारदोषः",
                    f"{op!r} {left} तथा {right} इत्येतयोः तुलनाम् न करोति / "
                    f"cannot compare {left} with {right}",
                    line,
                )
            return "सत्यता"

        # - * / % ^
        for side, kind in ((node.left, left), (node.right, right)):
            if kind not in NUMERIC and kind != ANY_TYPE:
                self._error(
                    "प्रकारदोषः",
                    f"{op!r} अङ्कम् इच्छति, {kind} दत्तः / operator {op!r} needs a number, "
                    f"got {kind}",
                    line,
                )
        if unknown:
            return ANY_TYPE
        if op == "/":
            return "अङ्कः"
        if op == "^":
            return "अङ्कः"
        return self._numeric_result(left, right)

    @staticmethod
    def _numeric_result(left: str, right: str) -> str:
        if left == right == "पूर्णाङ्कः":
            return "पूर्णाङ्कः"
        if "दशांशः" in (left, right):
            return "दशांशः"
        return "अङ्कः"

    def _ex_FunctionExpr(self, node: A.FunctionExpr) -> str:
        symbol = Symbol(node.name, "कार्यम्", line=node.line,
                        params=node.params, return_type=node.return_type)
        self._check_karakas("अनाम कार्यम्", node.params, node.return_type, node.line)
        self._function_body(symbol, node.params, node.body, node.return_type, node.line)
        return "कार्यम्"

    def _ex_Call(self, node: A.Call) -> str:
        arg_types = [self._type_of(arg) for arg in node.args]   # visited once

        symbol: Symbol | None = None
        if isinstance(node.callee, A.Identifier):
            symbol = self.scope.lookup(node.callee.name)
            if symbol is None:
                self._error(
                    "नामदोषः",
                    f"अपरिभाषितम् कार्यम् {node.callee.name!r} / "
                    f"undefined function {node.callee.name!r}",
                    node.line,
                )
                return ANY_TYPE
            if symbol.type not in ("कार्यम्", ANY_TYPE):
                self._error(
                    "प्रकारदोषः",
                    f"{symbol.type} आह्वातुम् न शक्यते / {symbol.type} is not callable",
                    node.line,
                )
                return ANY_TYPE
        else:
            self._type_of(node.callee)
            return ANY_TYPE

        labels = [k for k in node.arg_karakas if k]
        if labels:
            self._check_labelled_call(symbol, node, labels)
            return symbol.return_type

        if symbol.params is not None:                    # a कार्यम् written in Vāk
            if len(node.args) != len(symbol.params):
                self._error(
                    "प्राचलदोषः",
                    f"{symbol.name}: {len(symbol.params)} प्राचलाः अपेक्षिताः, "
                    f"{len(node.args)} दत्ताः / expected {len(symbol.params)} argument(s), "
                    f"got {len(node.args)}",
                    node.line,
                )
            else:
                for param, given in zip(symbol.params, arg_types):
                    if not self._assignable(given, param.type):
                        self._error(
                            "प्रकारदोषः",
                            f"{symbol.name} इत्यस्य प्राचलः {param.name!r}: {param.type} "
                            f"अपेक्षितः, {given} दीयते / expected {param.type}, got {given}",
                            node.line,
                        )
            return symbol.return_type

        if symbol.native_arity is not None:              # a built-in
            if symbol.native_arity >= 0 and len(node.args) != symbol.native_arity:
                self._error(
                    "प्राचलदोषः",
                    f"{symbol.name}: {symbol.native_arity} प्राचलाः अपेक्षिताः, "
                    f"{len(node.args)} दत्ताः / expected {symbol.native_arity} "
                    f"argument(s), got {len(node.args)}",
                    node.line,
                )
            return symbol.return_type

        return ANY_TYPE

    def _check_labelled_call(self, symbol: Symbol, node: A.Call, labels: list[str]) -> None:
        """`छानय(करणम्: प, अपादानम्: स)` — every label must name a real role."""
        if symbol.params is None:
            self._error(
                "कारकदोषः",
                f"{symbol.name}: कारकनामभिः आह्वानम् केवलम् कारकयुक्तस्य कार्यस्य कृते / "
                f"kāraka labels need a कार्यम् whose parameters declare roles",
                node.line,
            )
            return
        available = {p.karaka for p in symbol.params if p.karaka}
        for label in labels:
            if label not in available:
                self._error(
                    "कारकदोषः",
                    f"{symbol.name}: {label} इति कारकम् नास्ति / declares no {label} parameter",
                    node.line,
                )
        for label in dict.fromkeys(labels):   # first-occurrence order, so it is stable
            if labels.count(label) > 1:
                self._error(
                    "कारकदोषः",
                    f"{symbol.name}: {label} द्विः दत्तम् / the {label} argument is given twice",
                    node.line,
                )
        if len(node.args) != len(symbol.params):
            self._error(
                "प्राचलदोषः",
                f"{symbol.name}: {len(symbol.params)} प्राचलाः अपेक्षिताः, "
                f"{len(node.args)} दत्ताः / expected {len(symbol.params)} argument(s), "
                f"got {len(node.args)}",
                node.line,
            )

    # ======================================================================
    # the type lattice
    # ======================================================================
    @staticmethod
    def _assignable(value: str, declared: str) -> bool:
        """Gradual: anything fits किमपि, and किमपि fits anything. Only
        provable mismatches are reported."""
        if declared in (ANY_TYPE, "") or value in (ANY_TYPE, ""):
            return True
        if value == declared:
            return True
        if value in NUMERIC and declared in NUMERIC:
            return not (declared == "पूर्णाङ्कः" and value == "दशांशः")
        return False


def analyze(program: A.Program, filename: str = "<वाक्>") -> Report:
    """Convenience wrapper — walk a program and return its Report."""
    return Analyzer(filename).analyze(program)
