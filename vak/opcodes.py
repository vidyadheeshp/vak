"""
आदेशाः — the instruction set of the SanskritVM (संस्कृतयन्त्रम्).

A flat list of integers is the bytecode: an opcode followed by however many
operands it takes. Every instruction has a Sanskrit name, which is what the
disassembler prints:

    ०००४  ४ | स्थापय        १  '५'
    ०००६  ५ | योगः
    ०००७  ५ | मुद्रय         १

The machine is a stack machine over the same Environment chain the
tree-walking interpreter uses, so closure and scope semantics are identical
in both engines and their output can be compared instruction for instruction.

स्थाननिर्णयः — a name the compiler can see declared in an enclosing scope is
resolved at compile time to (how many scopes out, which binding in it), and
read with स्थानात्_गृहाण instead of searching the chain by name.  The name is
carried as a third operand so the machine can check that the binding it lands
on really is the one meant; if it is not — or the program put something
unexpected in that scope — it falls back to the search and is still correct.
"""

from __future__ import annotations

from enum import IntEnum


class Op(IntEnum):
    # --- मूल्यानि / values ------------------------------------------------
    CONST = 0           # स्थापय        push constants[a]
    NIL = 1             # शून्यम्        push शून्य
    TRUE = 2            # सत्यम्         push सत्य
    FALSE = 3           # असत्यम्        push असत्य
    POP = 4             # त्यज           discard the top
    DUP = 5             # द्वित्वम्       duplicate the top

    # --- चराः / variables -------------------------------------------------
    DEF_VAR = 10        # घोषय          define constants[a] with type constants[b]
    DEF_CONST = 11      # ध्रुवं_घोषय    the same, but immutable
    GET_VAR = 12        # गृहाण         push the value of constants[a]
    SET_VAR = 13        # न्यसय         assign the top to constants[a]
    GET_BUILTIN = 16    # अन्तर्निहितम्_गृहाण  constants[a] names a built-in
    GET_LOCAL = 14      # स्थानात्_गृहाण  a parents up, binding b, named constants[c]
    SET_LOCAL = 15      # स्थाने_न्यसय    the same, assigning the top

    # --- गणितम् / arithmetic ----------------------------------------------
    ADD = 20            # योगः
    SUB = 21            # वियोगः
    MUL = 22            # गुणनम्
    DIV = 23            # भागः
    MOD = 24            # शेषः
    POW = 25            # घातः
    NEG = 26            # ऋणम्
    NOT = 27            # निषेधः

    # --- तुलना / comparison -----------------------------------------------
    EQ = 30             # समम्
    NE = 31             # असमम्
    LT = 32             # न्यूनम्
    LE = 33             # न्यूनसमम्
    GT = 34             # अधिकम्
    GE = 35             # अधिकसमम्

    # --- प्रवाहः / control flow -------------------------------------------
    JUMP = 40           # लङ्घय          ip += a
    JUMP_IF_FALSE = 41  # असत्ये_लङ्घय   ip += a when the top is falsey (kept)
    JUMP_IF_TRUE = 42   # सत्ये_लङ्घय    ip += a when the top is truthy (kept)
    JUMP_BACK = 43      # पुनरागच्छ      ip -= a

    # --- परिवेशः / scopes -------------------------------------------------
    SCOPE_PUSH = 50     # परिवेशम्_आरभ
    SCOPE_POP = 51      # परिवेशम्_त्यज

    # --- संग्रहाः / collections -------------------------------------------
    BUILD_LIST = 60     # सूचीम्_रचय     take a values off the stack
    BUILD_DICT = 61     # कोशम्_रचय      take 2a values off the stack
    INDEX_GET = 62      # सूचकात्_गृहाण
    INDEX_SET = 63      # सूचके_न्यसय

    # --- कार्याणि / functions ---------------------------------------------
    CLOSURE = 70        # आवरणम्         make a closure from constants[a]
    CALL = 71           # आह्वय          call with a arguments
    CALL_LABELLED = 72  # कारकैः_आह्वय   call with a arguments labelled by constants[b]
    RETURN = 73         # प्रत्यागच्छ

    # --- आज्ञाः / commands ------------------------------------------------
    PRINT = 80          # मुद्रय          print a values

    # --- पुनरावृत्तिः / iteration -----------------------------------------
    ITER_NEW = 90       # पुनरावर्तकम्_रचय
    ITER_NEXT = 91      # पुनरावर्तय     push the next item, or jump +a when done

    # --- दोषाः / exceptions -----------------------------------------------
    SETUP_TRY = 100     # प्रयत्नम्_आरभ  handler at +a, finally at +b (-1 = none)
    POP_TRY = 101       # प्रयत्नम्_त्यज
    THROW = 102         # उत्सृज
    END_FINALLY = 103   # अन्ततः_समापय   re-raise if we were unwinding

    # --- आयातः / modules --------------------------------------------------
    IMPORT = 110        # आनय            constants[a] = (path, alias, names)

    HALT = 255          # विरम


SANSKRIT: dict[Op, str] = {
    Op.CONST: "स्थापय", Op.NIL: "शून्यम्", Op.TRUE: "सत्यम्", Op.FALSE: "असत्यम्",
    Op.POP: "त्यज", Op.DUP: "द्वित्वम्",
    Op.DEF_VAR: "घोषय", Op.DEF_CONST: "ध्रुवं_घोषय", Op.GET_VAR: "गृहाण",
    Op.SET_VAR: "न्यसय",
    Op.GET_LOCAL: "स्थानात्_गृहाण", Op.SET_LOCAL: "स्थाने_न्यसय",
    Op.GET_BUILTIN: "अन्तर्निहितम्_गृहाण",
    Op.ADD: "योगः", Op.SUB: "वियोगः", Op.MUL: "गुणनम्", Op.DIV: "भागः",
    Op.MOD: "शेषः", Op.POW: "घातः", Op.NEG: "ऋणम्", Op.NOT: "निषेधः",
    Op.EQ: "समम्", Op.NE: "असमम्", Op.LT: "न्यूनम्", Op.LE: "न्यूनसमम्",
    Op.GT: "अधिकम्", Op.GE: "अधिकसमम्",
    Op.JUMP: "लङ्घय", Op.JUMP_IF_FALSE: "असत्ये_लङ्घय", Op.JUMP_IF_TRUE: "सत्ये_लङ्घय",
    Op.JUMP_BACK: "पुनरागच्छ",
    Op.SCOPE_PUSH: "परिवेशम्_आरभ", Op.SCOPE_POP: "परिवेशम्_त्यज",
    Op.BUILD_LIST: "सूचीम्_रचय", Op.BUILD_DICT: "कोशम्_रचय",
    Op.INDEX_GET: "सूचकात्_गृहाण", Op.INDEX_SET: "सूचके_न्यसय",
    Op.CLOSURE: "आवरणम्", Op.CALL: "आह्वय", Op.CALL_LABELLED: "कारकैः_आह्वय",
    Op.RETURN: "प्रत्यागच्छ",
    Op.PRINT: "मुद्रय",
    Op.ITER_NEW: "पुनरावर्तकम्_रचय", Op.ITER_NEXT: "पुनरावर्तय",
    Op.SETUP_TRY: "प्रयत्नम्_आरभ", Op.POP_TRY: "प्रयत्नम्_त्यज",
    Op.THROW: "उत्सृज", Op.END_FINALLY: "अन्ततः_समापय",
    Op.IMPORT: "आनय",
    Op.HALT: "विरम",
}

# how many operand words follow each opcode
OPERANDS: dict[Op, int] = {
    Op.CONST: 1, Op.NIL: 0, Op.TRUE: 0, Op.FALSE: 0, Op.POP: 0, Op.DUP: 0,
    Op.DEF_VAR: 2, Op.DEF_CONST: 2, Op.GET_VAR: 1, Op.SET_VAR: 1,
    Op.GET_LOCAL: 3, Op.SET_LOCAL: 3, Op.GET_BUILTIN: 1,
    Op.ADD: 0, Op.SUB: 0, Op.MUL: 0, Op.DIV: 0, Op.MOD: 0, Op.POW: 0,
    Op.NEG: 0, Op.NOT: 0,
    Op.EQ: 0, Op.NE: 0, Op.LT: 0, Op.LE: 0, Op.GT: 0, Op.GE: 0,
    Op.JUMP: 1, Op.JUMP_IF_FALSE: 1, Op.JUMP_IF_TRUE: 1, Op.JUMP_BACK: 1,
    Op.SCOPE_PUSH: 0, Op.SCOPE_POP: 0,
    Op.BUILD_LIST: 1, Op.BUILD_DICT: 1, Op.INDEX_GET: 0, Op.INDEX_SET: 0,
    Op.CLOSURE: 1, Op.CALL: 1, Op.CALL_LABELLED: 2, Op.RETURN: 0,
    Op.PRINT: 1,
    Op.ITER_NEW: 0, Op.ITER_NEXT: 1,
    Op.SETUP_TRY: 2, Op.POP_TRY: 0, Op.THROW: 0, Op.END_FINALLY: 0,
    Op.IMPORT: 1,
    Op.HALT: 0,
}
