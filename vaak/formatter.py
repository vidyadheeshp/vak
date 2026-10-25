"""
स्वरूपणम् — a canonical printer for the AST, so a Vāk file can be reformatted
to one consistent style instead of every author inventing their own spacing.

This is Python-only, deliberately: unlike a built-in function, formatting is
a development-time tool, not part of the language's own runtime semantics —
nothing a running program can observe needs it, so it does not need to exist
in the native runtime or the self-hosted front end the way दीर्घता or वर्णः do.

    from vaak.formatter import format_source
    print(format_source(source))

Known limitation, stated rather than hidden: **comments are not preserved.**
The parser discards them before the AST exists, so there is nothing here to
echo back. `--स्वरूपण` only ever prints to stdout — it never overwrites a
file — specifically because silently dropping a comment on save would be a
real loss, not a cosmetic one. Reinstating them would mean carrying comment
trivia through the lexer and parser, which is future work, not this.
"""
from __future__ import annotations

from . import ast_nodes as A
from .lexer import tokenize
from .parser import parse

INDENT = "    "

# कार्यक्रमे मुद्रय परिष्कृतः, तथापि कोष्ठकहीनः — the bare form reads better
# and is what most of this project's own examples use.
_BARE_KEYWORDS = {"मुद्रय", "दोषलिख"}


def format_program(program: A.Program) -> str:
    """Print an already-parsed Program back out in one canonical style."""
    out = [_stmt(stmt, 0) for stmt in program.statements]
    return "\n".join(out) + "\n" if out else ""


def format_source(source: str) -> str:
    """Parse source and print it back out in one canonical style."""
    return format_program(parse(tokenize(source)))


def _ind(depth: int) -> str:
    return INDENT * depth


def _block(block: A.Block, depth: int) -> str:
    lines = [_ind(depth) + "{"]
    for s in block.statements:
        lines.append(_stmt(s, depth + 1))
    lines.append(_ind(depth) + "}")
    return "\n".join(lines)


def _stmt(stmt: A.Stmt, depth: int) -> str:
    pad = _ind(depth)

    if isinstance(stmt, A.ExpressionStmt):
        return f"{pad}{_expr(stmt.expr, depth)}।"

    if isinstance(stmt, A.VarDecl):
        kw = "ध्रुव" if stmt.constant else ("मान" if stmt.type == "किमपि" else stmt.type)
        value = f" = {_expr(stmt.value, depth)}" if stmt.value is not None else ""
        return f"{pad}{kw} {stmt.name}{value}।"

    if isinstance(stmt, A.Print):
        return f"{pad}मुद्रय {_args(stmt.args, depth)}।"

    if isinstance(stmt, A.Block):
        return _block(stmt, depth)

    if isinstance(stmt, A.If):
        lines = [f"{pad}यदि ({_expr(stmt.condition, depth)}) " + _block(stmt.then_branch, depth)[len(pad):]]
        if stmt.else_branch is not None:
            if isinstance(stmt.else_branch, A.If):
                lines.append(f"{pad}अन्यथा " + _stmt(stmt.else_branch, depth)[len(pad):])
            else:
                lines.append(f"{pad}अन्यथा " + _block(stmt.else_branch, depth)[len(pad):])
        return "\n".join(lines)

    if isinstance(stmt, A.While):
        if stmt.post_test:
            return (f"{pad}कुरु " + _block(stmt.body, depth)[len(pad):]
                    + f" यावत् ({_expr(stmt.condition, depth)})।")
        return f"{pad}यावत् ({_expr(stmt.condition, depth)}) " + _block(stmt.body, depth)[len(pad):]

    if isinstance(stmt, A.ForEach):
        return (f"{pad}प्रत्येकम् ({stmt.var} अन्तः {_expr(stmt.iterable, depth)}) "
                + _block(stmt.body, depth)[len(pad):])

    if isinstance(stmt, A.Repeat):
        return f"{pad}आवृत्तिः ({_expr(stmt.count, depth)}) " + _block(stmt.body, depth)[len(pad):]

    if isinstance(stmt, A.Switch):
        lines = [f"{pad}विकल्पः ({_expr(stmt.subject, depth)}) {{"]
        for case in stmt.cases:
            head = ("अन्यथा" if case.is_default
                    else "पक्षे " + ", ".join(_expr(v, depth) for v in case.values))
            lines.append(f"{_ind(depth + 1)}{head}:")
            for s in case.body:
                lines.append(_stmt(s, depth + 2))
        lines.append(f"{pad}}}")
        return "\n".join(lines)

    if isinstance(stmt, A.Try):
        lines = [f"{pad}प्रयत्नः " + _block(stmt.body, depth)[len(pad):]]
        if stmt.catch_body is not None:
            var = f" ({stmt.catch_var})" if stmt.catch_var else ""
            lines.append(f"{pad}दोषे{var} " + _block(stmt.catch_body, depth)[len(pad):])
        if stmt.finally_body is not None:
            lines.append(f"{pad}अन्ततः " + _block(stmt.finally_body, depth)[len(pad):])
        return "\n".join(lines)

    if isinstance(stmt, A.Throw):
        return f"{pad}उत्सृज {_expr(stmt.value, depth)}।"

    if isinstance(stmt, A.FunctionDecl):
        rtype = "" if stmt.return_type == "किमपि" else f" : {stmt.return_type}"
        params = ", ".join(str(p) for p in stmt.params)
        return (f"{pad}कार्यम् {stmt.name}({params}){rtype} "
                + _block(stmt.body, depth)[len(pad):])

    if isinstance(stmt, A.Return):
        value = f" {_expr(stmt.value, depth)}" if stmt.value is not None else ""
        return f"{pad}प्रत्यागच्छ{value}।"

    if isinstance(stmt, A.Break):
        return f"{pad}विरम।"

    if isinstance(stmt, A.Continue):
        return f"{pad}अनुवर्त।"

    if isinstance(stmt, A.Import):
        if stmt.names:
            return f'{pad}आनय "{stmt.path}" तः {", ".join(stmt.names)}।'
        if stmt.alias:
            return f'{pad}आनय "{stmt.path}" इति {stmt.alias}।'
        return f'{pad}आनय "{stmt.path}"।'

    raise TypeError(f"formatter has no printer for {type(stmt).__name__}")


def _args(exprs: list[A.Expr], depth: int) -> str:
    return ", ".join(_expr(e, depth) for e in exprs)


#: The lexer's own escape table (vaak/lexer.py), inverted — every value a
#: string literal can contain that `"` alone cannot represent literally
#: inside a double-quoted string.
_ESCAPES = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\t": "\\t", "\r": "\\r", "\0": "\\0"}


def _escape(text: str) -> str:
    return "".join(_ESCAPES.get(ch, ch) for ch in text)


def _number_literal(value: int | float) -> str:
    """सङ्ख्यानि देवनागरीलिप्या एव — the source's own choice of numeral
    orthography is lost by parse time (the AST keeps only the Python
    number), so this canonicalises rather than guesses. Devanagari, not
    ASCII, matches how the rest of this project writes numbers. Written
    without DEVANAGARI_OUTPUT (vaak.values.format_number's global flag) on
    purpose — the formatter is a static source-to-source tool and should
    not depend on whatever a running program last set that flag to.
    """
    from .values import to_devanagari
    text = str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)
    return to_devanagari(text)


def _expr(e: A.Expr, depth: int = 0) -> str:
    """depth is only ever consulted by FunctionExpr, whose body is the one
    place a multi-line construct can appear inside an expression — every
    other branch is printed on one line regardless of where it sits."""
    if isinstance(e, A.Literal):
        if isinstance(e.value, bool):
            return "सत्य" if e.value else "असत्य"
        if isinstance(e.value, (int, float)):
            return _number_literal(e.value)
        if e.value is None:
            return "शून्य"
        if isinstance(e.value, str):
            return f'"{_escape(e.value)}"'
        raise TypeError(f"formatter has no literal printer for {e.value!r}")

    if isinstance(e, A.ListLit):
        return "[" + _args(e.elements, depth) + "]"

    if isinstance(e, A.DictLit):
        inner = ", ".join(f"{_expr(k, depth)}: {_expr(v, depth)}" for k, v in e.pairs)
        return "{" + inner + "}"

    if isinstance(e, A.Identifier):
        return e.name

    if isinstance(e, A.Unary):
        # "न" is a word, not a symbol — न सत्य, with a space, or the lexer
        # reads नसत्य back as one identifier instead of two tokens.
        sep = " " if e.op.isalpha() else ""
        return f"{e.op}{sep}{_expr(e.right, depth)}"

    if isinstance(e, (A.Binary, A.Logical)):
        return f"{_expr(e.left, depth)} {e.op} {_expr(e.right, depth)}"

    if isinstance(e, A.Assign):
        return f"{e.name} = {_expr(e.value, depth)}"

    if isinstance(e, A.IndexGet):
        return f"{_expr(e.target, depth)}[{_expr(e.index, depth)}]"

    if isinstance(e, A.IndexSet):
        return f"{_expr(e.target, depth)}[{_expr(e.index, depth)}] = {_expr(e.value, depth)}"

    if isinstance(e, A.Call):
        parts = []
        for arg, karaka in zip(e.args, e.arg_karakas):
            rendered = _expr(arg, depth)
            parts.append(f"{karaka}: {rendered}" if karaka else rendered)
        return f"{_expr(e.callee, depth)}({', '.join(parts)})"

    if isinstance(e, A.FunctionExpr):
        rtype = "" if e.return_type == "किमपि" else f" : {e.return_type}"
        params = ", ".join(str(p) for p in e.params)
        return f"कार्यम् ({params}){rtype} " + _block(e.body, depth)[len(_ind(depth)):]

    raise TypeError(f"formatter has no printer for {type(e).__name__}")
