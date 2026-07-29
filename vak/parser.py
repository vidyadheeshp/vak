"""
व्याकरणम् — the Parser of Vāk.

A hand-written recursive-descent parser producing the AST in ast_nodes.py.

    program     → statement* EOF
    statement   → varDecl | funcDecl | ifStmt | whileStmt | forEachStmt
                | repeatStmt | printStmt | importStmt | tryStmt | throwStmt
                | returnStmt | breakStmt | continueStmt | block | exprStmt

    varDecl     → ("मान" | "ध्रुव") type? IDENT (":" type)? ("=" expression)? end
                | type IDENT ("=" expression)? end
    funcDecl    → "कार्यम्" IDENT "(" params? ")" (":" type)? block
    params      → param ("," param)*
    param       → type? IDENT (":" type)?
    type        → "पूर्णाङ्कः" | "दशांशः" | "अङ्कः" | "शब्दः" | "सत्यता"
                | "सूची" | "कोशः" | "कार्यम्" | "शून्यम्" | "किमपि"
    ifStmt      → "यदि" expression block ("अन्यथा" (ifStmt | block))?
    whileStmt   → "यावत्" expression block
    forEachStmt → "प्रत्येकम्" "("? IDENT "अन्तः" expression ")"? block
    repeatStmt  → "आवृत्तिः" expression block
    printStmt   → "मुद्रय" (expression ("," expression)*)? end
    importStmt  → "आनय" STRING ("इति" IDENT | "तः" IDENT ("," IDENT)*)? end
    tryStmt     → "प्रयत्नः" block ("दोषे" "("? IDENT? ")"? block)? ("अन्ततः" block)?
    throwStmt   → "उत्सृज" expression end
    returnStmt  → "प्रत्यागच्छ" expression? end
    end         → ";" | "।" | "॥" | ε

    expression  → assignment
    assignment  → (call ".")? IDENT "=" assignment | logicOr
    logicOr     → logicAnd (("वा" | "||") logicAnd)*
    logicAnd    → equality (("च" | "&&") equality)*
    equality    → comparison (("==" | "!=") comparison)*
    comparison  → term (("<" | "<=" | ">" | ">=") term)*
    term        → factor (("+" | "-") factor)*
    factor      → power (("*" | "/" | "%") power)*
    power       → unary ("^" power)?            # right associative
    unary       → ("-" | "!" | "न") unary | postfix
    postfix     → primary ( "(" args? ")" | "[" expression "]" | "." IDENT )*
    primary     → NUMBER | STRING | "सत्य" | "असत्य" | "शून्य" | IDENT
                | "(" expression ")" | list | dict | anonymous-function
"""

from __future__ import annotations

from .ast_nodes import (
    Assign,
    Binary,
    Block,
    Break,
    Call,
    Continue,
    DictLit,
    ExpressionStmt,
    Expr,
    ForEach,
    FunctionDecl,
    Import,
    FunctionExpr,
    Identifier,
    If,
    IndexGet,
    IndexSet,
    ListLit,
    Literal,
    Logical,
    Param,
    Print,
    Program,
    Repeat,
    Return,
    Stmt,
    Switch,
    SwitchCase,
    Throw,
    Try,
    Unary,
    VarDecl,
    While,
)
from .errors import ParseError
from .tokens import ANY_TYPE, KARAKA_NAMES, TYPE_NAMES, T, Token

# tokens that could continue an expression — used to tell the command form
# `मुद्रय (अ + ब) * २।` apart from the call form `मुद्रय(अ, ब)।`
_CONTINUES_EXPR = frozenset({
    T.PLUS, T.MINUS, T.STAR, T.SLASH, T.PERCENT, T.CARET,
    T.EQ, T.NE, T.LT, T.LE, T.GT, T.GE, T.AND, T.OR,
    T.DOT, T.LBRACKET, T.LPAREN, T.ASSIGN, T.OP_ASSIGN, T.COMMA,
})


class Parser:
    def __init__(self, tokens: list[Token], filename: str = "<वाक्>"):
        self.tokens = tokens
        self.filename = filename
        self.pos = 0

    # -- cursor helpers ----------------------------------------------------
    @property
    def current(self) -> Token:
        return self.tokens[self.pos]

    def _previous(self) -> Token:
        return self.tokens[self.pos - 1]

    def _check(self, *types: T) -> bool:
        return self.current.type in types

    def _match(self, *types: T) -> bool:
        if self._check(*types):
            self.pos += 1
            return True
        return False

    def _advance(self) -> Token:
        tok = self.current
        if tok.type is not T.EOF:
            self.pos += 1
        return tok

    def _expect(self, type_: T, message: str) -> Token:
        if self._check(type_):
            return self._advance()
        raise ParseError(
            f"{message} — किन्तु प्राप्तम् / but found {self.current.lexeme!r}",
            self.current.line,
            self.current.col,
        )

    def _end_of_statement(self) -> None:
        """Statement terminators (; । ॥) are welcome but optional."""
        while self._match(T.SEMI):
            pass

    # -- entry point -------------------------------------------------------
    def parse(self) -> Program:
        prog = Program(line=1)
        while not self._check(T.EOF):
            prog.statements.append(self.statement())
        return prog

    # ======================================================================
    # statements
    # ======================================================================
    def statement(self) -> Stmt:
        if self._check(T.LET, T.CONST):
            return self.var_decl()
        if self._is_typed_decl():
            return self.var_decl()
        if self._check(T.FUNC) and self.tokens[self.pos + 1].type is T.IDENT \
                and self.tokens[self.pos + 2].type is T.LPAREN:
            return self.func_decl()
        if self._match(T.IF):
            return self.if_stmt()
        if self._match(T.WHILE):
            return self.while_stmt()
        if self._match(T.FOR):
            return self.for_each_stmt()
        if self._match(T.REPEAT):
            return self.repeat_stmt()
        if self._match(T.PRINT):
            return self.print_stmt()
        if self._match(T.IMPORT):
            return self.import_stmt()
        if self._check(T.SWITCH):
            return self.switch_stmt()
        if self._match(T.TRY):
            return self.try_stmt()
        if self._match(T.THROW):
            return self.throw_stmt()
        if self._match(T.RETURN):
            return self.return_stmt()
        if self._match(T.BREAK):
            line = self._previous().line
            self._end_of_statement()
            return Break(line=line)
        if self._match(T.CONTINUE):
            line = self._previous().line
            self._end_of_statement()
            return Continue(line=line)
        if self._check(T.LBRACE):
            return self.block()
        return self.expression_stmt()

    # -- types -------------------------------------------------------------
    def _is_type_token(self) -> bool:
        """Is the current token usable as a प्रकारनाम (type name)?"""
        tok = self.current
        if tok.type in (T.FUNC, T.NULL):
            return True
        return tok.type is T.IDENT and tok.lexeme in TYPE_NAMES

    def _is_typed_decl(self) -> bool:
        """`पूर्णाङ्कः क = ५` — a type name followed by a name starts a declaration."""
        if not self._is_type_token():
            return False
        if self.tokens[self.pos + 1].type is not T.IDENT:
            return False
        if self.current.type is T.FUNC:              # कार्यम् क = ... vs कार्यम् क(...)
            return self.tokens[self.pos + 2].type is not T.LPAREN
        return True

    def _read_type(self) -> str:
        tok = self.current
        if tok.type is T.FUNC:
            self._advance()
            return "कार्यम्"
        if tok.type is T.NULL:
            self._advance()
            return "शून्यम्"
        if tok.type is T.IDENT and tok.lexeme in TYPE_NAMES:
            self._advance()
            return TYPE_NAMES[tok.lexeme]
        raise ParseError(
            f"प्रकारनाम अपेक्षितम् / expected a type name, found {tok.lexeme!r}",
            tok.line, tok.col,
        )

    # -- declarations ------------------------------------------------------
    def var_decl(self) -> VarDecl:
        """मान क = ५।   ध्रुव पाई = ३.१४।   पूर्णाङ्कः क = ५।   मान क : शब्दः = "अ"।"""
        constant = False
        declared = ANY_TYPE
        if self._check(T.LET, T.CONST):
            kw = self._advance()                   # मान / ध्रुव
            constant = kw.type is T.CONST
            line, col = kw.line, kw.col
            if self._is_typed_decl():              # मान पूर्णाङ्कः क = ५
                declared = self._read_type()
        else:                                      # पूर्णाङ्कः क = ५
            line, col = self.current.line, self.current.col
            declared = self._read_type()

        name = self._expect(T.IDENT, "नाम अपेक्षितम् / expected a variable name")
        if self._match(T.COLON):                   # मान क : पूर्णाङ्कः = ५
            declared = self._read_type()

        value: Expr | None = None
        if self._match(T.ASSIGN):
            value = self.expression()
        elif constant:
            raise ParseError(
                "ध्रुवस्य मूल्यम् आवश्यकम् / a ध्रुव (constant) must be initialised",
                line, col,
            )
        self._end_of_statement()
        return VarDecl(name.lexeme, value, constant, declared, line)

    def func_decl(self) -> FunctionDecl:
        kw = self._advance()                       # कार्यम्
        name = self._expect(T.IDENT, "कार्यस्य नाम अपेक्षितम् / expected a function name")
        params = self.params()
        return_type = self._return_type()
        body = self.block()
        return FunctionDecl(name.lexeme, params, body, return_type, kw.line)

    def params(self) -> list[Param]:
        self._expect(T.LPAREN, "'(' अपेक्षितम् / expected '(' after the function name")
        params: list[Param] = []
        if not self._check(T.RPAREN):
            while True:
                karaka = self._read_karaka()       # अपादानम् ...
                declared = ANY_TYPE
                if self._is_type_token() and self.tokens[self.pos + 1].type is T.IDENT:
                    declared = self._read_type()   # पूर्णाङ्कः अ
                tok = self._expect(T.IDENT, "प्राचलनाम अपेक्षितम् / expected a parameter name")
                if self._match(T.COLON):           # अ : पूर्णाङ्कः
                    declared = self._read_type()
                params.append(Param(tok.lexeme, declared, karaka))
                if not self._match(T.COMMA):
                    break
        self._expect(T.RPAREN, "')' अपेक्षितम् / expected ')' after the parameters")
        return params

    def _read_karaka(self) -> str | None:
        """A kāraka marker, if one opens this parameter.

        `कर्म` alone is a parameter *name*; `कर्म सूची स` marks the role of `स`.
        So a marker counts only when something else follows it.
        """
        tok = self.current
        if tok.type is not T.IDENT or tok.lexeme not in KARAKA_NAMES:
            return None
        following = self.tokens[self.pos + 1].type
        if following in (T.COMMA, T.RPAREN, T.COLON, T.ASSIGN):
            return None                            # it is the name itself
        self._advance()
        return KARAKA_NAMES[tok.lexeme]

    def _return_type(self) -> str:
        """`कार्यम् योग(अ, ब) : पूर्णाङ्कः { ... }`"""
        return self._read_type() if self._match(T.COLON) else ANY_TYPE

    def if_stmt(self) -> If:
        line = self._previous().line
        condition = self.expression()
        then_branch = self.block()
        else_branch: Stmt | None = None
        if self._match(T.ELSE):
            if self._match(T.IF):
                else_branch = self.if_stmt()
            else:
                else_branch = self.block()
        return If(condition, then_branch, else_branch, line)

    def while_stmt(self) -> While:
        line = self._previous().line
        condition = self.expression()
        body = self.block()
        return While(condition, body, line)

    def for_each_stmt(self) -> ForEach:
        line = self._previous().line
        wrapped = self._match(T.LPAREN)
        var = self._expect(T.IDENT, "चरनाम अपेक्षितम् / expected a loop variable")
        self._expect(T.IN, "'अन्तः' (in) अपेक्षितम् / expected 'अन्तः' after the loop variable")
        iterable = self.expression()
        if wrapped:
            self._expect(T.RPAREN, "')' अपेक्षितम् / expected ')'")
        body = self.block()
        return ForEach(var.lexeme, iterable, body, line)

    def repeat_stmt(self) -> Repeat:
        line = self._previous().line
        count = self.expression()
        body = self.block()
        return Repeat(count, body, line)

    def print_stmt(self) -> Print:
        """मुद्रय अ, ब।   and the call form   मुद्रय(अ, ब)।"""
        line = self._previous().line
        args: list[Expr] = []
        if self._check(T.SEMI, T.RBRACE, T.EOF):
            self._end_of_statement()
            return Print(args, line)

        if self._check(T.LPAREN):                 # try the call form first
            saved = self.pos
            try:
                self._advance()
                if not self._check(T.RPAREN):
                    while True:
                        args.append(self.expression())
                        if not self._match(T.COMMA):
                            break
                self._expect(T.RPAREN, "')' अपेक्षितम् / expected ')'")
                if self.current.type in _CONTINUES_EXPR:
                    raise ParseError("पुनः प्रयत्नः / retry as a command", line)
                self._end_of_statement()
                return Print(args, line)
            except ParseError:
                self.pos = saved                  # it was `मुद्रय (अ+ब) * २।`
                args = []

        while True:                                # the plain command form
            args.append(self.expression())
            if not self._match(T.COMMA):
                break
        self._end_of_statement()
        return Print(args, line)

    def import_stmt(self) -> Import:
        """आनय "गणितम्"।  /  आनय "गणितम्" इति ग।  /  आनय "गणितम्" तः योगः, वर्गः।"""
        line = self._previous().line
        target = self._expect(T.STRING, "सञ्चिकानाम अपेक्षितम् / expected a module name")
        alias: str | None = None
        names: list[str] = []
        if self._match(T.AS):
            alias = self._expect(T.IDENT, "नाम अपेक्षितम् / expected a name after 'इति'").lexeme
        elif self._match(T.FROM):
            while True:
                names.append(
                    self._expect(T.IDENT, "नाम अपेक्षितम् / expected a name after 'तः'").lexeme
                )
                if not self._match(T.COMMA):
                    break
        self._end_of_statement()
        return Import(str(target.value), alias, names, line)

    def switch_stmt(self) -> Switch:
        """विकल्पः (क) { पक्षे १, २: ... अन्यथा: ... }

        A पक्षः runs to the next पक्षे, the अन्यथा, or the closing brace — there
        is no fall-through to stop, so nothing has to be written to stop it.
        """
        line = self._advance().line                      # विकल्पः
        had_paren = bool(self._match(T.LPAREN))
        subject = self.expression()
        if had_paren:
            self._expect(T.RPAREN, "')' अपेक्षितम् / expected ')' after the subject")
        self._expect(T.LBRACE, "'{' अपेक्षितम् / expected '{' to open the विकल्पः")

        cases: list[SwitchCase] = []
        seen_default = False
        while not self._check(T.RBRACE, T.EOF):
            if self._match(T.CASE):                      # पक्षे १, २:
                case_line = self._previous().line
                values = [self.expression()]
                while self._match(T.COMMA):
                    values.append(self.expression())
            elif self._match(T.ELSE):                    # अन्यथा:
                case_line = self._previous().line
                values = []
                if seen_default:
                    raise ParseError(
                        "एकम् एव 'अन्यथा' विकल्पे / a विकल्पः may have only one अन्यथा",
                        case_line, self._previous().col,
                    )
                seen_default = True
            else:
                tok = self.current
                raise ParseError(
                    "'पक्षे' अथवा 'अन्यथा' अपेक्षितम् / expected 'पक्षे' or 'अन्यथा' "
                    f"inside a विकल्पः — किन्तु प्राप्तम् / but found {tok.lexeme!r}",
                    tok.line, tok.col,
                )
            self._expect(T.COLON, "':' अपेक्षितम् / expected ':' after the पक्षः")

            body: list[Stmt] = []
            while not self._check(T.CASE, T.ELSE, T.RBRACE, T.EOF):
                body.append(self.statement())
            cases.append(SwitchCase(values, body, case_line))

        self._expect(T.RBRACE, "'}' अपेक्षितम् / expected '}' to close the विकल्पः")
        return Switch(subject, cases, line)

    def try_stmt(self) -> Try:
        line = self._previous().line
        body = self.block()
        catch_var: str | None = None
        catch_body: Block | None = None
        finally_body: Block | None = None

        if self._match(T.CATCH):
            wrapped = self._match(T.LPAREN)
            if self._check(T.IDENT):
                catch_var = self._advance().lexeme
            if wrapped:
                self._expect(T.RPAREN, "')' अपेक्षितम् / expected ')' after the दोषे variable")
            catch_body = self.block()

        if self._match(T.FINALLY):
            finally_body = self.block()

        if catch_body is None and finally_body is None:
            raise ParseError(
                "'दोषे' अथवा 'अन्ततः' अपेक्षितम् / a प्रयत्नः needs a दोषे or अन्ततः block",
                line,
            )
        return Try(body, catch_var, catch_body, finally_body, line)

    def throw_stmt(self) -> Throw:
        line = self._previous().line
        value = self.expression()
        self._end_of_statement()
        return Throw(value, line)

    def return_stmt(self) -> Return:
        line = self._previous().line
        value: Expr | None = None
        if not self._check(T.SEMI, T.RBRACE, T.EOF):
            value = self.expression()
        self._end_of_statement()
        return Return(value, line)

    def block(self) -> Block:
        brace = self._expect(T.LBRACE, "'{' अपेक्षितम् / expected '{' to open a block")
        stmts: list[Stmt] = []
        while not self._check(T.RBRACE, T.EOF):
            stmts.append(self.statement())
        self._expect(T.RBRACE, "'}' अपेक्षितम् / expected '}' to close the block")
        return Block(stmts, brace.line)

    def expression_stmt(self) -> ExpressionStmt:
        line = self.current.line
        expr = self.expression()
        self._end_of_statement()
        return ExpressionStmt(expr, line)

    # ======================================================================
    # expressions
    # ======================================================================
    def expression(self) -> Expr:
        return self.assignment()

    def assignment(self) -> Expr:
        target = self.logic_or()
        if self._match(T.ASSIGN):
            eq = self._previous()
            value = self.assignment()          # right associative
            return self._store(target, value, eq)
        if self._match(T.OP_ASSIGN):
            op = self._previous()
            value = self.assignment()
            # क += १  ≡  क = क + १. Desugaring here keeps every later stage —
            # analyser, compiler, all three VMs — unaware that the form exists.
            combined = Binary(self._reread(target), op.lexeme[:-1], value, op.line)
            return self._store(target, combined, op)
        return target

    def _store(self, target: Expr, value: Expr, at: Token) -> Expr:
        if isinstance(target, Identifier):
            return Assign(target.name, value, at.line)
        if isinstance(target, IndexGet):
            return IndexSet(target.target, target.index, value, at.line)
        raise ParseError(
            "अयोग्यम् नियोजनलक्ष्यम् / invalid assignment target", at.line, at.col
        )

    @staticmethod
    def _reread(target: Expr) -> Expr:
        """The read half of a compound assignment.

        `स[क] += १` reads and writes the same place, so the target expression
        is evaluated twice — keep the index simple if it has side effects.
        """
        if isinstance(target, Identifier):
            return Identifier(target.name, target.line)
        if isinstance(target, IndexGet):
            return IndexGet(target.target, target.index, target.line)
        return target

    def logic_or(self) -> Expr:
        expr = self.logic_and()
        while self._match(T.OR):
            op = self._previous()
            expr = Logical(expr, "वा", self.logic_and(), op.line)
        return expr

    def logic_and(self) -> Expr:
        expr = self.equality()
        while self._match(T.AND):
            op = self._previous()
            expr = Logical(expr, "च", self.equality(), op.line)
        return expr

    def equality(self) -> Expr:
        expr = self.comparison()
        while self._match(T.EQ, T.NE):
            op = self._previous()
            expr = Binary(expr, op.lexeme, self.comparison(), op.line)
        return expr

    def comparison(self) -> Expr:
        expr = self.term()
        while self._match(T.LT, T.LE, T.GT, T.GE):
            op = self._previous()
            expr = Binary(expr, op.lexeme, self.term(), op.line)
        return expr

    def term(self) -> Expr:
        expr = self.factor()
        while self._match(T.PLUS, T.MINUS):
            op = self._previous()
            expr = Binary(expr, op.lexeme, self.factor(), op.line)
        return expr

    def factor(self) -> Expr:
        expr = self.power()
        while self._match(T.STAR, T.SLASH, T.PERCENT):
            op = self._previous()
            expr = Binary(expr, op.lexeme, self.power(), op.line)
        return expr

    def power(self) -> Expr:
        base = self.unary()
        if self._match(T.CARET):
            op = self._previous()
            return Binary(base, "^", self.power(), op.line)   # right associative
        return base

    def unary(self) -> Expr:
        if self._match(T.MINUS, T.NOT):
            op = self._previous()
            return Unary(op.lexeme, self.unary(), op.line)
        return self.postfix()

    def postfix(self) -> Expr:
        expr = self.primary()
        while True:
            if self._match(T.LPAREN):
                expr = self.finish_call(expr)
            elif self._match(T.LBRACKET):
                bracket = self._previous()
                index = self.expression()
                self._expect(T.RBRACKET, "']' अपेक्षितम् / expected ']' after the index")
                expr = IndexGet(expr, index, bracket.line)
            elif self._match(T.DOT):
                dot = self._previous()
                name = self._expect(T.IDENT, "कुञ्जिकानाम अपेक्षितम् / expected a key name after '.'")
                expr = IndexGet(expr, Literal(name.lexeme, dot.line), dot.line)
            else:
                return expr

    def finish_call(self, callee: Expr) -> Expr:
        """Arguments are positional, or labelled with the kāraka they fill:

            छानय(अङ्काः, परीक्षा)
            छानय(करणम्: परीक्षा, अपादानम्: अङ्काः)      # order no longer matters
        """
        paren = self._previous()
        args: list[Expr] = []
        karakas: list[str | None] = []
        if not self._check(T.RPAREN):
            while True:
                label: str | None = None
                tok = self.current
                if (tok.type is T.IDENT and tok.lexeme in KARAKA_NAMES
                        and self.tokens[self.pos + 1].type is T.COLON):
                    self._advance()               # the kāraka name
                    self._advance()               # ':'
                    label = KARAKA_NAMES[tok.lexeme]
                args.append(self.expression())
                karakas.append(label)
                if not self._match(T.COMMA):
                    break
        self._expect(T.RPAREN, "')' अपेक्षितम् / expected ')' after the arguments")
        return Call(callee, args, karakas, paren.line)

    def primary(self) -> Expr:
        tok = self.current

        if self._match(T.NUMBER, T.STRING):
            return Literal(self._previous().value, tok.line)
        if self._match(T.TRUE):
            return Literal(True, tok.line)
        if self._match(T.FALSE):
            return Literal(False, tok.line)
        if self._match(T.NULL):
            return Literal(None, tok.line)
        if self._match(T.IDENT):
            return Identifier(self._previous().lexeme, tok.line)

        if self._match(T.LPAREN):
            expr = self.expression()
            self._expect(T.RPAREN, "')' अपेक्षितम् / expected ')' after the expression")
            return expr

        if self._match(T.LBRACKET):
            elements: list[Expr] = []
            if not self._check(T.RBRACKET):
                while True:
                    elements.append(self.expression())
                    if not self._match(T.COMMA):
                        break
                    if self._check(T.RBRACKET):     # trailing comma
                        break
            self._expect(T.RBRACKET, "']' अपेक्षितम् / expected ']' to close the सूची")
            return ListLit(elements, tok.line)

        if self._match(T.LBRACE):
            pairs: list[tuple[Expr, Expr]] = []
            if not self._check(T.RBRACE):
                while True:
                    key = self.expression()
                    self._expect(T.COLON, "':' अपेक्षितम् / expected ':' between key and value")
                    pairs.append((key, self.expression()))
                    if not self._match(T.COMMA):
                        break
                    if self._check(T.RBRACE):       # trailing comma
                        break
            self._expect(T.RBRACE, "'}' अपेक्षितम् / expected '}' to close the कोश")
            return DictLit(pairs, tok.line)

        if self._match(T.FUNC):
            params = self.params()
            return_type = self._return_type()
            body = self.block()
            return FunctionExpr(params, body, "अनाम", return_type, tok.line)

        raise ParseError(
            f"अप्रत्याशितम् चिह्नम् / unexpected token {tok.lexeme!r}", tok.line, tok.col
        )


def parse(tokens: list[Token], filename: str = "<वाक्>") -> Program:
    """Convenience wrapper."""
    return Parser(tokens, filename).parse()
