"""
वाक्यरचना — the Abstract Syntax Tree of Vāk.

Two families of nodes:
  * Expr — evaluates to a value
  * Stmt — performs an action
Every node carries the line it came from so runtime errors can point at it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class Node:
    line: int = 0


# ==========================================================================
# expressions
# ==========================================================================
class Expr(Node):
    pass


@dataclass
class Literal(Expr):
    """A number, string, सत्य/असत्य or शून्य."""
    value: Any
    line: int = 0


@dataclass
class ListLit(Expr):
    """सूची — [१, २, ३]"""
    elements: list[Expr] = field(default_factory=list)
    line: int = 0


@dataclass
class DictLit(Expr):
    """कोश — { "कुञ्जी": मूल्य }"""
    pairs: list[tuple[Expr, Expr]] = field(default_factory=list)
    line: int = 0


@dataclass
class Identifier(Expr):
    name: str
    line: int = 0


@dataclass
class Unary(Expr):
    op: str            # '-'  '!'  'न'
    right: Expr = None
    line: int = 0


@dataclass
class Binary(Expr):
    left: Expr
    op: str            # + - * / % ^ == != < <= > >=
    right: Expr
    line: int = 0


@dataclass
class Logical(Expr):
    left: Expr
    op: str            # 'च' (and) | 'वा' (or)
    right: Expr
    line: int = 0


@dataclass
class Assign(Expr):
    """x = मूल्य"""
    name: str
    value: Expr
    line: int = 0


@dataclass
class IndexGet(Expr):
    """सूची[०]  or  कोश["कुञ्जी"]"""
    target: Expr
    index: Expr
    line: int = 0


@dataclass
class IndexSet(Expr):
    target: Expr
    index: Expr
    value: Expr
    line: int = 0


@dataclass
class Call(Expr):
    """फ(अ, ब)  — and the role-labelled form  फ(कर्म: अ, करणम्: ब)

    `arg_karakas` runs parallel to `args`; an entry is None for a plain
    positional argument and a kāraka name for a labelled one.
    """
    callee: Expr
    args: list[Expr] = field(default_factory=list)
    arg_karakas: list[str | None] = field(default_factory=list)
    line: int = 0


@dataclass
class Param:
    """One parameter of a कार्यम्: an optional कारकम् (role), an optional
    प्रकारः (type), and the name — `अपादानम् सूची संग्रहः`."""
    name: str
    type: str = "किमपि"
    karaka: str | None = None

    def __str__(self) -> str:
        parts = [p for p in (self.karaka, None if self.type == "किमपि" else self.type)]
        parts = [p for p in parts if p]
        return " ".join(parts + [self.name])


@dataclass
class FunctionExpr(Expr):
    """An anonymous कार्यम् used as a value."""
    params: list[Param] = field(default_factory=list)
    body: "Block" = None
    name: str = "अनाम"   # anonymous
    return_type: str = "किमपि"
    line: int = 0


# ==========================================================================
# statements
# ==========================================================================
class Stmt(Node):
    pass


@dataclass
class ExpressionStmt(Stmt):
    expr: Expr
    line: int = 0


@dataclass
class VarDecl(Stmt):
    """मान x = मूल्यम्  /  ध्रुव x = मूल्यम्  /  पूर्णाङ्कः x = मूल्यम्"""
    name: str
    value: Expr | None = None
    constant: bool = False
    type: str = "किमपि"
    line: int = 0


@dataclass
class Print(Stmt):
    """मुद्रय अ, ब, स।  — the imperative print command."""
    args: list[Expr] = field(default_factory=list)
    line: int = 0


@dataclass
class Block(Stmt):
    statements: list[Stmt] = field(default_factory=list)
    line: int = 0


@dataclass
class If(Stmt):
    condition: Expr
    then_branch: Stmt
    else_branch: Stmt | None = None
    line: int = 0


@dataclass
class While(Stmt):
    condition: Expr
    body: Stmt
    line: int = 0


@dataclass
class ForEach(Stmt):
    """प्रत्येकम् (x अन्तः संग्रहः) { ... }"""
    var: str
    iterable: Expr
    body: Stmt
    line: int = 0


@dataclass
class Import(Stmt):
    """आनय "गणितम्"।            — bind the module under its own name
       आनय "गणितम्" इति ग।       — bind it under an alias
       आनय "गणितम्" तः योगः, वर्गः। — bind selected names out of it"""
    path: str
    alias: str | None = None
    names: list[str] = field(default_factory=list)
    line: int = 0


@dataclass
class Repeat(Stmt):
    """आवृत्तिः (५) { ... } — do this many times."""
    count: Expr
    body: Stmt
    line: int = 0


@dataclass
class SwitchCase(Node):
    """पक्षे १, २: ... — one alternative, and everything it does."""
    values: list[Expr] = field(default_factory=list)   # empty means अन्यथा
    body: list[Stmt] = field(default_factory=list)
    line: int = 0

    @property
    def is_default(self) -> bool:
        return not self.values


@dataclass
class Switch(Stmt):
    """विकल्पः (क) { पक्षे १: ... अन्यथा: ... }

    पक्षाः do not fall through — each is its own alternative, as विकल्पः means
    in Pāṇini: a choice among options, not a sequence to run into.
    """
    subject: Expr
    cases: list[SwitchCase] = field(default_factory=list)
    line: int = 0


@dataclass
class Try(Stmt):
    """प्रयत्नः { } दोषे (द) { } अन्ततः { }"""
    body: Block
    catch_var: str | None = None
    catch_body: Block | None = None
    finally_body: Block | None = None
    line: int = 0


@dataclass
class Throw(Stmt):
    """उत्सृज मूल्यम्।"""
    value: Expr
    line: int = 0


@dataclass
class FunctionDecl(Stmt):
    name: str
    params: list[Param] = field(default_factory=list)
    body: Block = None
    return_type: str = "किमपि"
    line: int = 0


@dataclass
class Return(Stmt):
    value: Expr | None = None
    line: int = 0


@dataclass
class Break(Stmt):
    line: int = 0


@dataclass
class Continue(Stmt):
    line: int = 0


@dataclass
class Program(Node):
    statements: list[Stmt] = field(default_factory=list)
    line: int = 0
