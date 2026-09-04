"""
परीक्षाः — the test suite of Vāk.

    python -m tests.test_vak        # or:  python tests/test_vak.py
No third-party dependencies; it is a plain unittest suite.
"""

from __future__ import annotations

import io
import os
import shutil
import pathlib
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vaak import check_source, run_source        # noqa: E402
from vaak.analyzer import SemanticError          # noqa: E402
from vaak.compiler import compile_program        # noqa: E402
from vaak.kosha import chunk_to_kosha, to_kosha  # noqa: E402
from vaak.native import build_executable, find_gcc  # noqa: E402
from vaak.selfhost import (                      # noqa: E402
    compile_kosha_with_vak,
    compile_with_vak,
    parse_with_vak,
    run_with_vak,
)
from vaak.vm import VM                           # noqa: E402
from vaak.errors import LexError, ParseError, RuntimeVakError  # noqa: E402
from vaak.interpreter import Interpreter, VakThrow  # noqa: E402
from vaak.lexer import tokenize                  # noqa: E402
from vaak.opcodes import Op                      # noqa: E402
from vaak.parser import parse                    # noqa: E402
from vaak.tokens import KEYWORDS, T              # noqa: E402


def output(source: str) -> str:
    """Run a program and capture everything it printed."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        run_source(source)
    return buf.getvalue().strip()


def value(expression: str):
    """Evaluate a single expression and return its value."""
    interp = Interpreter()
    program = parse(tokenize(f"{expression};"))
    return interp.run(program)


# ==========================================================================
class TestLexer(unittest.TestCase):
    def test_devanagari_numerals(self):
        toks = tokenize("१२३")
        self.assertEqual(toks[0].type, T.NUMBER)
        self.assertEqual(toks[0].value, 123)

    def test_mixed_numerals_and_floats(self):
        self.assertEqual(tokenize("३.१४")[0].value, 3.14)
        self.assertEqual(tokenize("42")[0].value, 42)

    def test_keywords_in_both_scripts(self):
        self.assertEqual(tokenize("मान")[0].type, T.LET)
        self.assertEqual(tokenize("mana")[0].type, T.LET)
        self.assertEqual(tokenize("यावत्")[0].type, T.WHILE)

    def test_identifier_with_matras_is_not_a_keyword(self):
        toks = tokenize("नामधेयम्")
        self.assertEqual(toks[0].type, T.IDENT)
        self.assertEqual(toks[0].lexeme, "नामधेयम्")

    def test_danda_is_a_terminator(self):
        self.assertEqual([t.type for t in tokenize("क।")][:2], [T.IDENT, T.SEMI])
        self.assertEqual([t.type for t in tokenize("क॥")][:2], [T.IDENT, T.SEMI])

    def test_comments_are_skipped(self):
        self.assertEqual(tokenize("# टिप्पणी\n५")[0].value, 5)
        self.assertEqual(tokenize("/* अ */ ६")[0].value, 6)

    def test_strings_with_escapes(self):
        self.assertEqual(tokenize(r'"अ\nब"')[0].value, "अ\nब")

    def test_unterminated_string(self):
        with self.assertRaises(LexError):
            tokenize('"अपूर्णः')


class TestParser(unittest.TestCase):
    def test_precedence(self):
        self.assertEqual(value("२ + ३ * ४"), 14)
        self.assertEqual(value("(२ + ३) * ४"), 20)
        self.assertEqual(value("२ ^ ३ ^ २"), 512)      # right associative

    def test_unary(self):
        self.assertEqual(value("-५ + ३"), -2)
        self.assertEqual(value("न असत्य"), True)

    def test_terminators_are_optional(self):
        self.assertEqual(output("मुद्रय(१)\nमुद्रय(२)"), "1\n2")

    def test_syntax_error(self):
        with self.assertRaises(ParseError):
            parse(tokenize("मान = ५"))
        with self.assertRaises(ParseError):
            parse(tokenize("यदि (सत्य) मुद्रय(१)"))     # a block is required


class TestValuesAndOperators(unittest.TestCase):
    def test_arithmetic(self):
        self.assertEqual(value("१० / ४"), 2.5)
        self.assertEqual(value("१० / ५"), 2)
        self.assertEqual(value("१० % ३"), 1)

    def test_string_concatenation(self):
        self.assertEqual(value('"सं" + "स्कृतम्"'), "संस्कृतम्")
        self.assertEqual(value('"क" + १'), "क1")

    def test_equality_is_type_aware(self):
        self.assertIs(value("१ == सत्य"), False)
        self.assertIs(value('"१" == १'), False)
        self.assertIs(value("१ == १.०"), True)

    def test_logical_short_circuit(self):
        self.assertEqual(output('असत्य च दोष("न भवेत्")\nमुद्रय("ठीकम्")'), "ठीकम्")

    def test_division_by_zero(self):
        with self.assertRaises(RuntimeVakError):
            value("१ / ०")

    def test_type_names(self):
        self.assertEqual(value("प्रकार(१)"), "पूर्णाङ्कः")
        self.assertEqual(value("प्रकार(१.५)"), "दशांशः")
        self.assertEqual(value('प्रकार("क")'), "शब्दः")
        self.assertEqual(value("प्रकार([])"), "सूची")
        self.assertEqual(value("प्रकार({})"), "कोशः")
        self.assertEqual(value("प्रकार(शून्य)"), "शून्यम्")
        self.assertEqual(value("प्रकार(लिख)"), "कार्यम्")


class TestCompoundAssignment(unittest.TestCase):
    """संयुक्तनियोजनम् — क += १ and friends."""

    def test_every_operator(self):
        src = ("मान क = १०। क += ५। मुद्रय क। क -= ३। मुद्रय क। क *= २। मुद्रय क। "
               "क /= ४। मुद्रय क। क %= ४। मुद्रय क। क ^= ३। मुद्रय क।")
        self.assertEqual(output(src), "15\n12\n24\n6\n2\n8")

    def test_on_a_list_element(self):
        self.assertEqual(output("मान स = [१, २]। स[०] += १००। मुद्रय स।"), "[101, 2]")

    def test_on_a_dictionary_key(self):
        self.assertEqual(output('कोशः क = {"अ": १}। क.अ += ९। मुद्रय क।'), '{"अ": 10}')

    def test_string_concatenation(self):
        self.assertEqual(output('शब्दः श = "सं"। श += "स्कृतम्"। मुद्रय श।'), "संस्कृतम्")

    def test_declared_types_still_bind(self):
        with self.assertRaises(RuntimeVakError):
            run_source('पूर्णाङ्कः क = ५। क /= २।')      # 2.5 is not a पूर्णाङ्कः

    def test_it_is_desugaring_not_a_new_node(self):
        """क += १ must parse to exactly the tree क = क + १ parses to."""
        self.assertEqual(to_kosha(parse(tokenize("क += १।"))),
                         to_kosha(parse(tokenize("क = क + १।"))))

    def test_the_analyser_sees_through_it(self):
        self.assertEqual([d.code for d in check_source('पूर्णाङ्कः क = ५। क += "अ"।')
                          .diagnostics if d.fatal], ["प्रकारदोषः"])


class TestControlFlow(unittest.TestCase):
    def test_if_else_chain(self):
        src = """
        मान क = ५।
        यदि (क > १०) { मुद्रय("अ") } अन्यथा यदि (क > ३) { मुद्रय("ब") } अन्यथा { मुद्रय("स") }
        """
        self.assertEqual(output(src), "ब")

    def test_while_with_break_and_continue(self):
        src = """
        मान क = ०।
        मान फलम् = []।
        यावत् (सत्य) {
            क = क + १।
            यदि (क % २ == ०) { अनुवर्त। }
            यदि (क > ७) { विरम। }
            योजय(फलम्, क)।
        }
        मुद्रय(फलम्)।
        """
        self.assertEqual(output(src), "[1, 3, 5, 7]")

    def test_for_each_over_list_string_and_dict(self):
        self.assertEqual(output("प्रत्येकम् (क अन्तः [१,२]) { मुद्रय(क) }"), "1\n2")
        self.assertEqual(output('प्रत्येकम् (क अन्तः "अब") { मुद्रय(क) }'), "अ\nब")
        self.assertEqual(output('प्रत्येकम् (क अन्तः {"अ": १}) { मुद्रय(क) }'), "अ")

    def test_scopes_are_nested(self):
        src = """
        मान क = "बाह्यम्"।
        { मान क = "आन्तरम्"। मुद्रय(क)। }
        मुद्रय(क)।
        """
        self.assertEqual(output(src), "आन्तरम्\nबाह्यम्")


class TestFunctions(unittest.TestCase):
    def test_recursion(self):
        src = """
        कार्यम् क्रमगुणितम्(संख्या_) {
            यदि (संख्या_ <= १) { प्रत्यागच्छ १। }
            प्रत्यागच्छ संख्या_ * क्रमगुणितम्(संख्या_ - १)।
        }
        मुद्रय(क्रमगुणितम्(६))।
        """
        self.assertEqual(output(src), "720")

    def test_closure_keeps_its_environment(self):
        src = """
        कार्यम् निर्माता() {
            मान गणकः = ०।
            प्रत्यागच्छ कार्यम्() { गणकः = गणकः + १। प्रत्यागच्छ गणकः। }।
        }
        मान ग = निर्माता()।
        ग()। ग()।
        मुद्रय(ग())।
        """
        self.assertEqual(output(src), "3")

    def test_function_is_a_value(self):
        src = """
        कार्यम् प्रयुज्(फ, म) { प्रत्यागच्छ फ(म)। }
        मुद्रय(प्रयुज्(कार्यम्(क) { प्रत्यागच्छ क * ३। }, ७))।
        """
        self.assertEqual(output(src), "21")

    def test_arity_is_checked(self):
        with self.assertRaises(RuntimeVakError):
            run_source("कार्यम् क(अ, ब) { प्रत्यागच्छ अ। } क(१)।")

    def test_missing_return_gives_null(self):
        self.assertEqual(output("कार्यम् क() { } मुद्रय(क())।"), "शून्यम्")


class TestCollections(unittest.TestCase):
    def test_list_index_and_assignment(self):
        src = "मान स = [१,२,३]। स[०] = ९। मुद्रय(स, स[-१])।"
        self.assertEqual(output(src), "[9, 2, 3] 3")

    def test_index_out_of_range(self):
        with self.assertRaises(RuntimeVakError):
            run_source("मान स = [१]। मुद्रय(स[५])।")

    def test_dict_dot_and_bracket_access(self):
        src = 'मान क = {"नाम": "वाक्"}। क.वर्षम् = २०२६। मुद्रय(क.नाम, क["वर्षम्"])।'
        self.assertEqual(output(src), "वाक् 2026")

    def test_missing_key(self):
        with self.assertRaises(RuntimeVakError):
            run_source('मान क = {}। मुद्रय(क.अज्ञातम्)।')

    def test_builtins(self):
        self.assertEqual(value("योग(परास(१, ११))"), 55)
        self.assertEqual(value("क्रम([३,१,२])"), [1, 2, 3])
        self.assertEqual(value('विभज("अ ब स", " ")'), ["अ", "ब", "स"])
        self.assertEqual(value('संयोज(["अ","ब"], "-")'), "अ-ब")
        self.assertEqual(value("देवनागरी(२०२६)"), "२०२६")
        self.assertEqual(value('संख्या("१२३")'), 123)


class TestErrors(unittest.TestCase):
    def test_undefined_name(self):
        with self.assertRaises(RuntimeVakError):
            run_source("मुद्रय(अज्ञातम्)।")

    def test_constant_cannot_be_reassigned(self):
        with self.assertRaises(RuntimeVakError):
            run_source("ध्रुव क = १। क = २।")

    def test_error_reports_a_line_number(self):
        try:
            with redirect_stdout(io.StringIO()):
                run_source("मुद्रय(१)।\nमुद्रय(२)।\nमुद्रय(अज्ञातम्)।")
        except RuntimeVakError as err:
            self.assertEqual(err.line, 3)
        else:  # pragma: no cover
            self.fail("अपेक्षितः दोषः न आगतः / expected an error")

    def test_builtins_are_shadowable(self):
        self.assertEqual(output("मान योग = ५। मुद्रय(योग)।"), "5")


class TestMergedCanon(unittest.TestCase):
    """Both spellings of every merged keyword must mean the same thing."""

    def test_function_and_return_aliases(self):
        canon = "कार्यम् क() { प्रत्यागच्छ १। } मुद्रय क()।"
        alias = "कार्य क() { प्रतिदा १। } लिख(क())।"
        self.assertEqual(output(canon), "1")
        self.assertEqual(output(alias), "1")

    def test_print_command_and_call_forms(self):
        self.assertEqual(output('मुद्रय "अ", १।'), "अ 1")
        self.assertEqual(output('मुद्रय("अ", १)।'), "अ 1")
        self.assertEqual(output("मुद्रय (२ + ३) * २।"), "10")
        self.assertEqual(output("मुद्रय।"), "")

    def test_repeat_loop(self):
        self.assertEqual(output('आवृत्तिः (३) { मुद्रय "ॐ"। }'), "ॐ\nॐ\nॐ")
        self.assertEqual(output('आवृत्तिः (०) { मुद्रय "अ"। }'), "")

    def test_repeat_honours_break(self):
        src = 'मान क = ०। आवृत्तिः (१०) { क = क + १। यदि (क == ४) { विरम। } } मुद्रय क।'
        self.assertEqual(output(src), "4")

    def test_romanized_program(self):
        src = 'mana x = 5; yadi (x > 3) { mudraya "mahat"; } anyatha { mudraya "alpam"; }'
        self.assertEqual(output(src), "mahat")

    def test_functions_are_hoisted(self):
        src = "मुद्रय पश्चात्()। कार्यम् पश्चात्() { प्रत्यागच्छ \"आगतम्\"। }"
        self.assertEqual(output(src), "आगतम्")


class TestTypes(unittest.TestCase):
    def test_typed_declaration_forms(self):
        self.assertEqual(output("पूर्णाङ्कः क = ५। मुद्रय क।"), "5")
        self.assertEqual(output('मान क : शब्दः = "अ"। मुद्रय क।'), "अ")
        self.assertEqual(output("मान पूर्णाङ्कः क = ५। मुद्रय क।"), "5")
        self.assertEqual(output("ध्रुव दशांशः प = ३.५। मुद्रय प।"), "3.5")

    def test_declaration_type_is_enforced(self):
        with self.assertRaises(RuntimeVakError) as ctx:
            run_source('पूर्णाङ्कः क = "अ"।')
        self.assertEqual(ctx.exception.code, "प्रकारदोषः")

    def test_assignment_type_is_enforced(self):
        with self.assertRaises(RuntimeVakError):
            run_source('पूर्णाङ्कः क = ५। क = "अ"।')

    def test_untyped_variables_stay_free(self):
        self.assertEqual(output('मान क = "अ"। क = ५। मुद्रय क।'), "5")

    def test_parameter_and_return_types(self):
        src = "कार्यम् द्वि(पूर्णाङ्कः क) : पूर्णाङ्कः { प्रत्यागच्छ क * २। } मुद्रय द्वि(४)।"
        self.assertEqual(output(src), "8")
        with self.assertRaises(RuntimeVakError):
            run_source('कार्यम् द्वि(पूर्णाङ्कः क) { प्रत्यागच्छ क। } द्वि("अ")।')
        with self.assertRaises(RuntimeVakError):
            run_source('कार्यम् द्वि() : पूर्णाङ्कः { प्रत्यागच्छ "अ"। } द्वि()।')

    def test_int_widens_to_dashamsha_but_not_the_reverse(self):
        self.assertEqual(output("दशांशः क = ५। मुद्रय क।"), "5")
        with self.assertRaises(RuntimeVakError):
            run_source("पूर्णाङ्कः क = ५.५।")

    def test_type_names_are_not_reserved_words(self):
        self.assertEqual(output('मुद्रय सूची("अब")।'), '["अ", "ब"]')
        self.assertEqual(output('मुद्रय शब्द(१२)।'), "12")


class TestExceptions(unittest.TestCase):
    def test_catch_a_builtin_error(self):
        src = 'प्रयत्नः { मुद्रय १ / ०। } दोषे (द) { मुद्रय द.प्रकारः। }'
        self.assertEqual(output(src), "गणितदोषः")

    def test_error_codes(self):
        cases = {
            "१ / ०": "गणितदोषः",
            "अज्ञातम्": "नामदोषः",
            '"अ" - १': "प्रकारदोषः",
        }
        for expression, code in cases.items():
            with self.subTest(expression=expression):
                src = f'प्रयत्नः {{ मुद्रय {expression}। }} दोषे (द) {{ मुद्रय द.प्रकारः। }}'
                self.assertEqual(output(src), code)

    def test_finally_always_runs(self):
        ok = 'प्रयत्नः { मुद्रय "अ"। } दोषे (द) { } अन्ततः { मुद्रय "ब"। }'
        self.assertEqual(output(ok), "अ\nब")
        bad = 'प्रयत्नः { उत्सृज "क"। } दोषे (द) { मुद्रय "अ"। } अन्ततः { मुद्रय "ब"। }'
        self.assertEqual(output(bad), "अ\nब")

    def test_finally_without_catch_lets_the_error_through(self):
        with self.assertRaises(RuntimeVakError):
            run_source('प्रयत्नः { उत्सृज "क"। } अन्ततः { }')

    def test_throw_a_kosha_keeps_its_fields(self):
        src = ('प्रयत्नः { उत्सृज {"प्रकारः": "मम्दोषः", "सन्देशः": "सन्देशोऽयम्"}। } '
               'दोषे (द) { मुद्रय द.प्रकारः, द.सन्देशः। }')
        self.assertEqual(output(src), "मम्दोषः सन्देशोऽयम्")

    def test_throw_a_plain_value_is_wrapped(self):
        src = 'प्रयत्नः { उत्सृज "सरलः"। } दोषे (द) { मुद्रय द.प्रकारः, द.सन्देशः। }'
        self.assertEqual(output(src), "उपयोक्तृदोषः सरलः")

    def test_rethrow_travels_outward(self):
        src = """
        कार्यम् आन्तरम्() { उत्सृज "गभीरः"। }
        प्रयत्नः {
            प्रयत्नः { आन्तरम्()। } दोषे (द) { उत्सृज द। }
        } दोषे (द) { मुद्रय "बाह्ये:", द.सन्देशः। }
        """
        self.assertEqual(output(src), "बाह्ये: गभीरः")

    def test_catch_variable_is_optional(self):
        self.assertEqual(output('प्रयत्नः { उत्सृज "क"। } दोषे { मुद्रय "गृहीतम्"। }'), "गृहीतम्")

    def test_uncaught_throw_becomes_a_runtime_error(self):
        with self.assertRaises(RuntimeVakError) as ctx:
            run_source('उत्सृज "अगृहीतः"।')
        self.assertEqual(ctx.exception.code, "उपयोक्तृदोषः")
        self.assertIn("अगृहीतः", ctx.exception.message)

    def test_dosha_builtin_is_catchable(self):
        src = 'प्रयत्नः { दोष("सन्देशः", "मम्दोषः")। } दोषे (द) { मुद्रय द.प्रकारः। }'
        self.assertEqual(output(src), "मम्दोषः")

    def test_try_needs_a_handler(self):
        with self.assertRaises(ParseError):
            parse(tokenize("प्रयत्नः { }"))

    def test_loop_control_survives_a_try(self):
        src = """
        मान फलम् = []।
        प्रत्येकम् (क अन्तः [१, २, ३, ४]) {
            प्रयत्नः {
                यदि (क == २) { अनुवर्त। }
                यदि (क == ४) { विरम। }
                योजय(फलम्, क)।
            } अन्ततः { }
        }
        मुद्रय फलम्।
        """
        self.assertEqual(output(src), "[1, 3]")


class TestAnalyzer(unittest.TestCase):
    """अर्थविश्लेषकः — the static pass."""

    def codes(self, source: str) -> list[str]:
        return [d.code for d in check_source(source).diagnostics if d.fatal]

    def warnings(self, source: str) -> list[str]:
        return [d.code for d in check_source(source).diagnostics if not d.fatal]

    def test_clean_program_has_no_diagnostics(self):
        self.assertEqual(check_source("मान क = ५। मुद्रय क।").diagnostics, [])

    def test_undefined_name_is_static(self):
        self.assertEqual(self.codes("मुद्रय अज्ञातम्।"), ["नामदोषः"])

    def test_type_mismatch_is_static(self):
        self.assertEqual(self.codes('पूर्णाङ्कः क = "अ"।'), ["प्रकारदोषः"])
        self.assertEqual(self.codes('पूर्णाङ्कः क = ५। क = "अ"।'), ["प्रकारदोषः"])
        self.assertEqual(self.codes('मुद्रय "अ" - १।'), ["प्रकारदोषः"])
        self.assertEqual(self.codes('मुद्रय "अ" < १।'), ["प्रकारदोषः"])

    def test_gradual_typing_stays_quiet(self):
        self.assertEqual(self.codes("कार्यम् क(म) { प्रत्यागच्छ म। } पूर्णाङ्कः अ = क(५)।"), [])
        self.assertEqual(self.codes("मान क = ५। क = \"अ\"।"), [])

    def test_constant_reassignment_is_static(self):
        self.assertEqual(self.codes("ध्रुव क = १। क = २।"), ["ध्रुवदोषः"])

    def test_arity_is_static(self):
        self.assertEqual(self.codes("कार्यम् क(अ, ब) { } क(१)।"), ["प्राचलदोषः"])
        self.assertEqual(self.codes("मुद्रय मूल(१, २)।"), ["प्राचलदोषः"])

    def test_control_flow_placement(self):
        self.assertEqual(self.codes("प्रत्यागच्छ ५।"), ["प्रवाहदोषः"])
        self.assertEqual(self.codes("विरम।"), ["प्रवाहदोषः"])
        self.assertEqual(self.codes("अनुवर्त।"), ["प्रवाहदोषः"])
        self.assertEqual(self.codes("कार्यम् क() { प्रत्यागच्छ ५। }"), [])
        self.assertEqual(self.codes("यावत् (सत्य) { विरम। }"), [])

    def test_return_type_is_checked(self):
        self.assertEqual(
            self.codes('कार्यम् क() : पूर्णाङ्कः { प्रत्यागच्छ "अ"। }'), ["प्रकारदोषः"]
        )

    def test_unreachable_code_warns(self):
        self.assertIn(
            "अगम्यदोषः",
            self.warnings("कार्यम् क() { प्रत्यागच्छ १। मुद्रय २। }"),
        )

    def test_missing_return_warns(self):
        self.assertIn(
            "प्रतिफलसूचना",
            self.warnings("कार्यम् क(अ) : पूर्णाङ्कः { यदि (अ) { प्रत्यागच्छ १। } }"),
        )

    def test_hoisted_call_is_accepted(self):
        self.assertEqual(self.codes("मुद्रय क()। कार्यम् क() { प्रत्यागच्छ १। }"), [])

    def test_iteration_target_is_checked(self):
        self.assertEqual(self.codes("प्रत्येकम् (क अन्तः सत्य) { }"), ["प्रकारदोषः"])
        self.assertEqual(self.codes('प्रत्येकम् (क अन्तः "अब") { }'), [])

    def test_analysis_does_not_run_the_program(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            check_source('मुद्रय "न मुद्रणीयम्"।')
        self.assertEqual(buf.getvalue(), "")

    def test_run_source_with_check_raises(self):
        with self.assertRaises(SemanticError):
            run_source('पूर्णाङ्कः क = "अ"।', check=True)


class TestKarakas(unittest.TestCase):
    """कारकपरीक्षा — the grammar of roles."""

    def codes(self, source: str) -> list[str]:
        return [d.code for d in check_source(source).diagnostics if d.fatal]

    def warnings(self, source: str) -> list[str]:
        return [d.code for d in check_source(source).diagnostics if not d.fatal]

    FILTER = """
    कार्यम् छानय(अपादानम् सूची संग्रहः, करणम् कार्यम् परीक्षा) : सूची {
        सूची फलम् = []।
        प्रत्येकम् (स अन्तः संग्रहः) { यदि (परीक्षा(स)) { योजय(फलम्, स)। } }
        प्रत्यागच्छ फलम्।
    }
    मान सम = कार्यम्(क) { प्रत्यागच्छ क % २ == ०। }।
    """

    def test_karaka_marked_function_is_clean(self):
        self.assertEqual(check_source(self.FILTER).diagnostics, [])

    def test_karaka_is_not_a_reserved_word(self):
        self.assertEqual(self.codes("कार्यम् क(कर्म, अन्यत्) { प्रत्यागच्छ कर्म। }"), [])

    def test_only_one_karma_and_one_karta(self):
        self.assertEqual(
            self.codes("कार्यम् क(कर्म शब्दः अ, कर्म शब्दः ब) : शब्दः { प्रत्यागच्छ अ। }"),
            ["कारकदोषः"],
        )

    def test_order_is_free(self):
        self.assertEqual(
            self.codes("कार्यम् क(करणम् कार्यम् प, कर्म शब्दः स) : शब्दः { प्रत्यागच्छ स। }"),
            [],
        )

    def test_role_type_sensibility_warns(self):
        self.assertIn(
            "कारकसूचना",
            self.warnings("कार्यम् क(अपादानम् पूर्णाङ्कः अ) : पूर्णाङ्कः { प्रत्यागच्छ अ। }"),
        )

    def test_transitive_function_should_yield(self):
        self.assertIn(
            "कारकसूचना",
            self.warnings("कार्यम् क(कर्म शब्दः स) : शून्यम् { मुद्रय स। }"),
        )

    def test_labelled_arguments_are_order_free(self):
        src = self.FILTER + """
        मुद्रय छानय(अपादानम्: [१,२,३,४], करणम्: सम)।
        मुद्रय छानय(करणम्: सम, अपादानम्: [१,२,३,४])।
        """
        self.assertEqual(check_source(src).diagnostics, [])
        self.assertEqual(output(src), "[2, 4]\n[2, 4]")

    def test_mixed_positional_and_labelled(self):
        src = self.FILTER + "मुद्रय छानय([१,२,३,४], करणम्: सम)।"
        self.assertEqual(output(src), "[2, 4]")

    def test_unknown_label_is_rejected(self):
        src = self.FILTER + "मुद्रय छानय(कर्ता: [१], करणम्: सम)।"
        self.assertEqual(self.codes(src), ["कारकदोषः"])

    def test_duplicate_label_is_rejected(self):
        src = self.FILTER + "मुद्रय छानय(करणम्: सम, करणम्: सम)।"
        self.assertIn("कारकदोषः", self.codes(src))

    def test_labels_on_a_roleless_function_fail_at_runtime(self):
        with self.assertRaises(RuntimeVakError):
            run_source("कार्यम् क(अ, ब) { प्रत्यागच्छ अ। } क(कर्म: १, करणम्: २)।")


class TestModules(unittest.TestCase):
    """आनय — modules, and the सञ्चिका built-ins."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="vak-"))
        (self.dir / "गणकः.vak").write_text(
            "ध्रुव पूर्णाङ्कः आरम्भः = १००।\n"
            "कार्यम् द्विगुणम्(अङ्कः क) : अङ्कः { प्रत्यागच्छ क * २। }\n",
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_in_dir(self, source: str) -> str:
        path = self.dir / "मुख्यम्.vak"
        path.write_text(source, encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            run_source(source, str(path))
        return buf.getvalue().strip()

    def test_module_binds_under_its_own_name(self):
        self.assertEqual(
            self.run_in_dir('आनय "गणकः"।\nमुद्रय गणकः.आरम्भः, गणकः.द्विगुणम्(२१)।'),
            "100 42",
        )

    def test_module_alias(self):
        self.assertEqual(self.run_in_dir('आनय "गणकः" इति ग।\nमुद्रय ग.आरम्भः।'), "100")

    def test_selective_import(self):
        self.assertEqual(
            self.run_in_dir('आनय "गणकः" तः द्विगुणम्।\nमुद्रय द्विगुणम्(५)।'), "10"
        )

    def test_missing_export_is_an_error(self):
        with self.assertRaises(RuntimeVakError) as ctx:
            self.run_in_dir('आनय "गणकः" तः अविद्यमानम्।')
        self.assertEqual(ctx.exception.code, "आयातदोषः")

    def test_missing_module_is_an_error(self):
        with self.assertRaises(RuntimeVakError) as ctx:
            self.run_in_dir('आनय "नास्तिकः"।')
        self.assertEqual(ctx.exception.code, "आयातदोषः")

    def test_module_runs_only_once(self):
        (self.dir / "एकवारम्.vak").write_text('मुद्रय "चालितम्"।', encoding="utf-8")
        out = self.run_in_dir('आनय "एकवारम्"।\nआनय "एकवारम्" इति द्वितीयम्।')
        self.assertEqual(out, "चालितम्")

    def test_standard_library_is_on_the_path(self):
        self.assertEqual(
            self.run_in_dir('आनय "गणितम्"।\nमुद्रय गणितम्.क्रमगुणितम्(५)।'), "120"
        )
        self.assertEqual(
            self.run_in_dir('आनय "शब्दाः" तः विलोमः_वा।\nमुद्रय विलोमः_वा("कनक")।'), "सत्य"
        )

    def test_file_round_trip(self):
        target = (self.dir / "लेख्यम्.txt").as_posix()
        out = self.run_in_dir(f'''
            सञ्चिकालिख("{target}", "अ\\nआ\\n")।
            सञ्चिकायोजय("{target}", "इ\\n")।
            मुद्रय दीर्घता(सञ्चिकापङ्क्तयः("{target}"))।
            मुद्रय सञ्चिकास्ति("{target}")।
            मुद्रय सञ्चिकानाशय("{target}")।
            मुद्रय सञ्चिकास्ति("{target}")।
        ''')
        self.assertEqual(out, "3\nसत्य\nसत्य\nअसत्य")

    def test_reading_a_missing_file_raises(self):
        with self.assertRaises(RuntimeVakError) as ctx:
            run_source('सञ्चिकापठ("क्वापि-नास्ति-५३७.txt")।')
        self.assertEqual(ctx.exception.code, "सञ्चिकादोषः")


class TestAksharas(unittest.TestCase):
    """अक्षराणि — syllable-aware string handling."""

    def test_splitting_by_syllable(self):
        self.assertEqual(value('अक्षराणि("वाक्")'), ["वा", "क्"])
        self.assertEqual(value('अक्षराणि("संस्कृतम्")'), ["सं", "स्कृ", "त", "म्"])

    def test_reversal_is_syllable_aware(self):
        self.assertEqual(value('विपर्यय("कनक")'), "कनक")
        self.assertEqual(value('विपर्यय("वाक्")'), "क्वा")

    def test_ascii_is_untouched(self):
        self.assertEqual(value('विपर्यय("abc")'), "cba")


def vm_output(source: str, filename: str = "<वाक्>") -> str:
    """Compile to bytecode and run the result on the SanskritVM."""
    program = parse(tokenize(source, filename), filename)
    buf = io.StringIO()
    with redirect_stdout(buf):
        VM(filename).run(compile_program(program, filename))
    return buf.getvalue().strip()


class TestCompilerAndVM(unittest.TestCase):
    """संकलकः + संस्कृतयन्त्रम् — the bytecode engine."""

    def test_arithmetic_and_precedence(self):
        self.assertEqual(vm_output("मुद्रय २ + ३ * ४।"), "14")
        self.assertEqual(vm_output("मुद्रय २ ^ ३ ^ २।"), "512")
        self.assertEqual(vm_output("मुद्रय १० / ४, १० / ५, १० % ३।"), "2.5 2 1")

    def test_variables_and_scopes(self):
        src = 'मान क = "बाह्यम्"। { मान क = "आन्तरम्"। मुद्रय क। } मुद्रय क।'
        self.assertEqual(vm_output(src), "आन्तरम्\nबाह्यम्")

    def test_control_flow(self):
        src = """
        मान फलम् = []।
        प्रत्येकम् (क अन्तः परास(१, १०)) {
            यदि (क % २ == ०) { अनुवर्त। }
            यदि (क > ७) { विरम। }
            योजय(फलम्, क)।
        }
        मुद्रय फलम्।
        """
        self.assertEqual(vm_output(src), "[1, 3, 5, 7]")

    def test_repeat_and_while(self):
        self.assertEqual(vm_output('आवृत्तिः (३) { मुद्रय "ॐ"। }'), "ॐ\nॐ\nॐ")
        self.assertEqual(
            vm_output("मान क = ३। यावत् (क > ०) { मुद्रय क। क = क - १। }"), "3\n2\n1"
        )

    def test_functions_recursion_and_closures(self):
        self.assertEqual(
            vm_output("कार्यम् क(न्) { यदि (न् <= १) { प्रत्यागच्छ १। } "
                      "प्रत्यागच्छ न् * क(न् - १)। } मुद्रय क(१०)।"),
            "3628800",
        )
        self.assertEqual(
            vm_output("कार्यम् निर्माता() { मान ग = ०। "
                      "प्रत्यागच्छ कार्यम्() { ग = ग + १। प्रत्यागच्छ ग। }। } "
                      "मान ग = निर्माता()। ग()। ग()। मुद्रय ग()।"),
            "3",
        )

    def test_hoisting(self):
        self.assertEqual(vm_output("मुद्रय क()। कार्यम् क() { प्रत्यागच्छ ५। }"), "5")

    def test_types_are_enforced(self):
        with self.assertRaises(RuntimeVakError) as ctx:
            vm_output('कार्यम् अ(म) { प्रत्यागच्छ म। } पूर्णाङ्कः क = अ("शब्दः")।')
        self.assertEqual(ctx.exception.code, "प्रकारदोषः")

    def test_exceptions(self):
        self.assertEqual(
            vm_output('प्रयत्नः { मुद्रय १ / ०। } दोषे (द) { मुद्रय द.प्रकारः। } '
                      'अन्ततः { मुद्रय "अन्ततः"। }'),
            "गणितदोषः\nअन्ततः",
        )
        self.assertEqual(
            vm_output('प्रयत्नः { उत्सृज {"प्रकारः": "मम्", "सन्देशः": "स"}। } '
                      'दोषे (द) { मुद्रय द.प्रकारः, द.सन्देशः। }'),
            "मम् स",
        )

    def test_exception_crosses_frames(self):
        src = """
        कार्यम् आन्तरम्() { उत्सृज "गभीरः"। }
        कार्यम् मध्यमम्() { आन्तरम्()। मुद्रय "न दृश्यते"। }
        प्रयत्नः { मध्यमम्()। } दोषे (द) { मुद्रय "बाह्ये:", द.सन्देशः। }
        """
        self.assertEqual(vm_output(src), "बाह्ये: गभीरः")

    def test_finally_runs_while_unwinding(self):
        src = """
        कार्यम् क() { प्रयत्नः { उत्सृज "क"। } अन्ततः { मुद्रय "अन्ततः"। } }
        प्रयत्नः { क()। } दोषे (द) { मुद्रय "गृहीतः"। }
        """
        self.assertEqual(vm_output(src), "अन्ततः\nगृहीतः")

    def test_karaka_labels_on_the_vm(self):
        src = """
        कार्यम् छानय(अपादानम् सूची स, करणम् कार्यम् प) : सूची {
            सूची फलम् = []।
            प्रत्येकम् (क अन्तः स) { यदि (प(क)) { योजय(फलम्, क)। } }
            प्रत्यागच्छ फलम्।
        }
        मान सम = कार्यम्(क) { प्रत्यागच्छ क % २ == ०। }।
        मुद्रय छानय(करणम्: सम, अपादानम्: [१,२,३,४])।
        """
        self.assertEqual(vm_output(src), "[2, 4]")

    def test_modules_on_the_vm(self):
        self.assertEqual(
            vm_output('आनय "गणितम्"। मुद्रय गणितम्.क्रमगुणितम्(५)।'), "120"
        )

    def test_disassembly_is_readable(self):
        chunk = compile_program(parse(tokenize('मुद्रय ५ + ३।')))
        text = chunk.disassemble()
        self.assertIn("स्थापय", text)
        self.assertIn("योगः", text)
        self.assertIn("मुद्रय", text)


class TestDifferential(unittest.TestCase):
    """उभयोः यन्त्रयोः समानम् फलम् — both engines must agree, exactly."""

    PROGRAMS = [
        "मुद्रय १ + २ * ३ - ४ / २।",
        'मुद्रय "क" + १, न सत्य, ३ < ४ च ५ >= ५।',
        "मान स = [३,१,२]। स[०] = ९। मुद्रय स, क्रम(स), दीर्घता(स)।",
        'कोशः क = {"अ": १}। क.ब = २। मुद्रय कुञ्जिकाः(क), मूल्यानि(क)।',
        "कार्यम् फ(न्) { यदि (न् < २) { प्रत्यागच्छ न्। } प्रत्यागच्छ फ(न्-१) + फ(न्-२)। } मुद्रय फ(१५)।",
        'प्रत्येकम् (क अन्तः "वाक्") { मुद्रय क। }',
        'प्रयत्नः { मान क = [१]। मुद्रय क[९]। } दोषे (द) { मुद्रय द.प्रकारः। } अन्ततः { मुद्रय "अ"। }',
        "मान ग = ०। आवृत्तिः (५) { ग = ग + १। यदि (ग == ३) { विरम। } } मुद्रय ग।",
        'आनय "शब्दाः" तः विलोमः_वा। मुद्रय विलोमः_वा("कनक")।',
    ]

    def test_programs_agree(self):
        for source in self.PROGRAMS:
            with self.subTest(source=source[:40]):
                self.assertEqual(output(source), vm_output(source))

    def test_examples_agree(self):
        for path in sorted((ROOT / "examples").glob("[0-9][0-9]_*.vak")):
            with self.subTest(example=path.name):
                source = path.read_text(encoding="utf-8")
                tree = io.StringIO()
                with redirect_stdout(tree):
                    run_source(source, str(path))
                self.assertEqual(tree.getvalue(), vm_output(source, str(path)) + "\n")


class TestBootstrap(unittest.TestCase):
    """स्वयंसिद्धिः — the lexer written in Vāk must agree with the Python one."""

    @classmethod
    def setUpClass(cls):
        driver = ROOT / "स्वयंसिद्धिः" / "चालकः.vak"
        cls.interp = Interpreter(str(driver))
        run_source('आनय "शब्दविभाजकः" तः विभज_मूलम्।', str(driver), cls.interp)
        cls.vak_lexer = cls.interp.globals.get("विभज_मूलम्")

    def lex_in_vak(self, source: str) -> list:
        return self.vak_lexer.call(self.interp, [source])

    @staticmethod
    def category(token) -> str:
        if token.type is T.EOF:
            return "समाप्तिः"
        if token.lexeme in KEYWORDS:
            return "कीलकम्"
        return {T.NUMBER: "अङ्कः", T.STRING: "शब्दः", T.IDENT: "नाम"}.get(
            token.type, "चिह्नम्"
        )

    def assert_agrees(self, source: str, label: str = "") -> None:
        mine = self.lex_in_vak(source)
        theirs = tokenize(source, label or "<परीक्षा>")
        self.assertEqual(len(mine), len(theirs), f"{label}: token counts differ")
        for index, (a, b) in enumerate(zip(mine, theirs)):
            self.assertEqual(
                (a["प्रकारः"], a["पदम्"], a["मूल्यम्"], a["पङ्क्तिः"]),
                (self.category(b), b.lexeme, b.value, b.line),
                f"{label}: चिह्नम् {index}",
            )

    def test_basic_forms(self):
        self.assert_agrees('मान क = ५। यदि (क > ३.५) { मुद्रय "महत्"। }')

    def test_numerals_in_both_scripts(self):
        self.assert_agrees("१२३ + 456 - ७.५ * 0.25")

    def test_operators_and_danda(self):
        self.assert_agrees("अ == ब != स <= द >= इ && उ || न ऊ। ऋ॥ ॠ;")

    def test_comments_and_strings(self):
        self.assert_agrees('# टिप्पणी\n/* अन्या */ "अ\\nब" \'क\' // अन्ते\nमान क')

    def test_conjuncts_and_matras_in_names(self):
        self.assert_agrees("संस्कृतम् नामधेयम् कार्यम्_१ योग_2 total")

    def test_unterminated_string_is_reported(self):
        # उत्सृज travels as a VakThrow when the कार्यम् is called from Python
        with self.assertRaises(VakThrow) as ctx:
            self.lex_in_vak('"अपूर्णः')
        self.assertEqual(ctx.exception.payload["प्रकारः"], "अक्षरदोषः")

    def test_agrees_on_real_programs(self):
        for name in ("01_namaste.vak", "10_granthalaya.vak", "13_karaka.vak"):
            path = ROOT / "examples" / name
            with self.subTest(example=name):
                self.assert_agrees(path.read_text(encoding="utf-8"), name)

    def test_the_lexer_lexes_its_own_source(self):
        """स्वयंसिद्धेः प्रथमम् सोपानम् — the bootstrap milestone."""
        path = ROOT / "स्वयंसिद्धिः" / "शब्दविभाजकः.vak"
        source = path.read_text(encoding="utf-8")
        mine = self.lex_in_vak(source)
        self.assert_agrees(source, path.name)
        self.assertGreater(len(mine), 1000)


class TestBootstrapParser(unittest.TestCase):
    """स्वयंसिद्धेः द्वितीयम् सोपानम् — the parser written in Vāk."""

    SAMPLES = [
        'मान क = ५। यदि (क > ३) { मुद्रय "महत्"। } अन्यथा { मुद्रय "अल्पम्"। }',
        "कार्यम् क(पूर्णाङ्कः अ, कर्म शब्दः ब) : शब्दः { प्रत्यागच्छ ब + अ। }",
        'मान स = [१, २.५, "क", सत्य, शून्य]। मान को = {"अ": [१], "ब": {}}।',
        "यावत् (क < १०) { क = क + १। यदि (क == ५) { अनुवर्त। } विरम। }",
        "प्रत्येकम् (क अन्तः परास(१, ५)) { मुद्रय क। } आवृत्तिः (३) { मुद्रय \"ॐ\"। }",
        'प्रयत्नः { उत्सृज "क"। } दोषे (द) { मुद्रय द.सन्देशः। } अन्ततः { मुद्रय "अ"। }',
        'आनय "गणितम्"। आनय "शब्दाः" इति श। आनय "क" तः अ, ब।',
        "मुद्रय अ, ब। मुद्रय(अ, ब)। मुद्रय (अ + ब) * २।",
        "छानय(अपादानम्: स, करणम्: प)। क[०] = १। को.कुञ्जिका = २।",
        "मान फ = कार्यम्(क) : अङ्कः { प्रत्यागच्छ -क ^ २ % ३। }।",
        "मुद्रय अ == ब != स < द <= इ > उ >= ऊ च ऋ वा न ॠ।",
        "मान क = १। क += २। क -= ३। क *= ४। क /= ५। क %= ६। क ^= ७। मुद्रय क।",
        'सूची स = [१]। स[०] += १। कोशः को = {"अ": १}। को.अ *= २। मुद्रय स, को।',
    ]

    def parsed(self, source: str):
        return parse_with_vak(source)

    def assert_trees_agree(self, source: str, label: str = "") -> None:
        mine = self.parsed(source)
        theirs = to_kosha(parse(tokenize(source, label or "<परीक्षा>")))
        self.assertEqual(mine, theirs, f"{label or source[:40]}: वाक्यरचना भिन्ना")

    def test_every_construct_parses_the_same(self):
        for index, source in enumerate(self.SAMPLES):
            with self.subTest(sample=index):
                self.assert_trees_agree(source)

    def test_syntax_errors_are_reported(self):
        with self.assertRaises(VakThrow) as ctx:
            self.parsed("मान = ५।")
        self.assertEqual(ctx.exception.payload["प्रकारः"], "व्याकरणदोषः")

    def test_agrees_on_real_programs(self):
        for name in ("05_karya.vak", "12_dosha.vak", "13_karaka.vak"):
            path = ROOT / "examples" / name
            with self.subTest(example=name):
                self.assert_trees_agree(path.read_text(encoding="utf-8"), name)

    def test_the_parser_parses_its_own_source(self):
        path = ROOT / "स्वयंसिद्धिः" / "व्याकरणम्.vak"
        self.assert_trees_agree(path.read_text(encoding="utf-8"), path.name)


class TestBootstrapCompiler(unittest.TestCase):
    """स्वयंसिद्धेः तृतीयम् सोपानम् — the compiler written in Vāk."""

    def assert_bytecode_agrees(self, source: str, label: str = "") -> None:
        mine = compile_kosha_with_vak(source)
        theirs = chunk_to_kosha(compile_program(parse(tokenize(source, label or "<परीक्षा>"))))
        self.assertEqual(mine["सङ्केताः"], theirs["सङ्केताः"], f"{label}: आदेशाः भिन्नाः")
        self.assertEqual(mine, theirs, f"{label}: खण्डः भिन्नः")

    def test_every_construct_compiles_the_same(self):
        for index, source in enumerate(TestBootstrapParser.SAMPLES):
            with self.subTest(sample=index):
                self.assert_bytecode_agrees(source)

    def test_agrees_on_real_programs(self):
        for name in ("04_yavat.vak", "09_pratyekam.vak", "12_dosha.vak", "13_karaka.vak"):
            path = ROOT / "examples" / name
            with self.subTest(example=name):
                self.assert_bytecode_agrees(path.read_text(encoding="utf-8"), name)

    def test_the_compiler_compiles_its_own_source(self):
        """वाक् वाचम् संकलयति — Vāk compiles Vāk, to the same bytecode."""
        path = ROOT / "स्वयंसिद्धिः" / "संकलकः.vak"
        self.assert_bytecode_agrees(path.read_text(encoding="utf-8"), path.name)

    def test_the_vak_vm_runs_every_construct(self):
        """स्वयंसिद्धेः चतुर्थम् सोपानम् — the VM itself written in Vāk."""
        cases = [
            ('मुद्रय "नमस्ते", ५ + ३ * २।', "नमस्ते 11"),
            ('मान क = ५। यदि (क > ३) { मुद्रय "महत्"। } अन्यथा { मुद्रय "अल्पम्"। }', "महत्"),
            ("मान स = ०। यावत् (स < ५) { स = स + १। } मुद्रय स।", "5"),
            ("आवृत्तिः (३) { मुद्रय \"ॐ\"। }", "ॐ\nॐ\nॐ"),
            ("प्रत्येकम् (क अन्तः [१,२,३]) { यदि (क == २) { अनुवर्त। } मुद्रय क। }", "1\n3"),
            ("कार्यम् व(अ) { प्रत्यागच्छ अ * अ। } मुद्रय व(१२)।", "144"),
            ("कार्यम् क्र(न्) { यदि (न् <= १) { प्रत्यागच्छ १। } प्रत्यागच्छ न् * क्र(न् - १)। } "
             "मुद्रय क्र(८)।", "40320"),
            ("कार्यम् नि() { मान ग = ०। प्रत्यागच्छ कार्यम्() { ग = ग + १। प्रत्यागच्छ ग। }। } "
             "मान ग = नि()। ग()। मुद्रय ग()।", "2"),
            ('मान को = {"अ": [१, २]}। को.ब = ३। मुद्रय को.अ[१], को["ब"], दीर्घता(को)।', "2 3 2"),
            ('प्रयत्नः { मुद्रय १ / ०। } दोषे (द) { मुद्रय द.प्रकारः। } अन्ततः { मुद्रय "अ"। }',
             "गणितदोषः\nअ"),
            ('आनय "गणितम्"। मुद्रय गणितम्.क्रमगुणितम्(५)।', "120"),
            ("पूर्णाङ्कः क = ५। प्रयत्नः { क = \"अ\"। } दोषे (द) { मुद्रय द.प्रकारः। }",
             "प्रकारदोषः"),
        ]
        for source, expected in cases:
            with self.subTest(source=source[:40]):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    run_with_vak(source)
                self.assertEqual(buf.getvalue().strip(), expected)

    def test_the_vak_vm_matches_the_python_vm_on_examples(self):
        for name in ("03_yadi.vak", "06_suchi.vak", "12_dosha.vak", "13_karaka.vak"):
            path = ROOT / "examples" / name
            source = path.read_text(encoding="utf-8")
            with self.subTest(example=name):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    run_with_vak(source)
                self.assertEqual(buf.getvalue(), vm_output(source, str(path)) + "\n")

    def test_self_compiled_bytecode_runs_on_the_vm(self):
        """The loop closed: compiled by Vāk, executed by the SanskritVM."""
        for name in ("01_namaste.vak", "08_fibonacci.vak", "12_dosha.vak"):
            path = ROOT / "examples" / name
            source = path.read_text(encoding="utf-8")
            with self.subTest(example=name):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    VM(str(path)).run(compile_with_vak(source, str(path)))
                self.assertEqual(buf.getvalue(), vm_output(source, str(path)) + "\n")


GCC = find_gcc()


@unittest.skipIf(GCC is None, "C-संकलकः न प्राप्तः / no C compiler available")
class TestNative(unittest.TestCase):
    """देशीयः चालकः — the native back end: Vāk → C → .exe."""

    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp(prefix="vak-native-"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def native_output(self, source: str, name: str = "pariksha", cwd: str = ".") -> str:
        path = self.dir / f"{name}.vak"
        path.write_text(source, encoding="utf-8")
        exe = build_executable(source, path, self.dir)
        proc = subprocess.run([str(exe.resolve())], capture_output=True, cwd=cwd)
        self.assertEqual(proc.returncode, 0,
                         proc.stderr.decode("utf-8", "replace")[:400])
        return proc.stdout.decode("utf-8", "replace").replace("\r\n", "\n").strip()

    def test_values_and_arithmetic(self):
        self.assertEqual(self.native_output('मुद्रय "नमस्ते", २ + ३ * ४, १० / ४, १० / ५।'),
                         "नमस्ते 14 2.5 2")
        self.assertEqual(self.native_output("मुद्रय २ ^ १०, -७ % ३, ३.१४१५९।"),
                         "1024 2 3.14159")

    def test_strings_are_utf8_and_akshara_aware(self):
        self.assertEqual(
            self.native_output('मुद्रय दीर्घता("संस्कृतम्"), अक्षराणि("वाक्"), विपर्यय("कनक")।'),
            ' 9 ["वा", "क्"] कनक'.strip())

    def test_collections(self):
        self.assertEqual(
            self.native_output('मान स = [३,१,२]। स[०] = ९। '
                               'मुद्रय स, क्रम(स), दीर्घता(स), योग([१,२,३])।'),
            "[9, 1, 2] [1, 2, 9] 3 6")
        self.assertEqual(
            self.native_output('कोशः क = {"अ": १}। क.ब = २। मुद्रय क, कुञ्जिकाः(क)।'),
            '{"अ": 1, "ब": 2} ["अ", "ब"]')

    def test_control_flow_and_functions(self):
        self.assertEqual(
            self.native_output("कार्यम् क्र(न्) { यदि (न् <= १) { प्रत्यागच्छ १। } "
                               "प्रत्यागच्छ न् * क्र(न् - १)। } मुद्रय क्र(१२)।"),
            "479001600")
        self.assertEqual(
            self.native_output("कार्यम् नि() { मान ग = ०। "
                               "प्रत्यागच्छ कार्यम्() { ग = ग + १। प्रत्यागच्छ ग। }। } "
                               "मान ग = नि()। ग()। मुद्रय ग()।"),
            "2")

    def test_exceptions(self):
        self.assertEqual(
            self.native_output('प्रयत्नः { मुद्रय १ / ०। } दोषे (द) { मुद्रय द.प्रकारः। } '
                               'अन्ततः { मुद्रय "अन्ततः"। }'),
            "गणितदोषः\nअन्ततः")

    def test_types_and_karakas(self):
        self.assertEqual(
            self.native_output("पूर्णाङ्कः क = ५। प्रयत्नः { कार्यम् अ(म) { प्रत्यागच्छ म। } "
                               'क = अ("शब्दः")। } दोषे (द) { मुद्रय द.प्रकारः। }'),
            "प्रकारदोषः")
        self.assertEqual(
            self.native_output("कार्यम् छानय(अपादानम् सूची स, करणम् कार्यम् प) : सूची {"
                               " सूची फ = []। प्रत्येकम् (क अन्तः स) { यदि (प(क)) "
                               "{ योजय(फ, क)। } } प्रत्यागच्छ फ। }"
                               " मान सम = कार्यम्(क) { प्रत्यागच्छ क % २ == ०। }।"
                               " मुद्रय छानय(करणम्: सम, अपादानम्: [१,२,३,४])।"),
            "[2, 4]")

    def test_a_devanagari_filename_still_builds(self):
        self.assertEqual(self.native_output('मुद्रय "नाम"।', "प्रोग्रामः"), "नाम")

    def test_modules_are_linked_in(self):
        self.assertEqual(
            self.native_output('आनय "गणितम्"। मुद्रय गणितम्.क्रमगुणितम्(५), '
                               'गणितम्.मसाभा(४८, १८)।'),
            "120 6")

    def test_every_example_matches_the_interpreter(self):
        for path in sorted((ROOT / "examples").glob("[0-9][0-9]_*.vak")):
            with self.subTest(example=path.name):
                source = path.read_text(encoding="utf-8")
                host = io.StringIO()
                with redirect_stdout(host):
                    run_source(source, str(path))
                exe = build_executable(source, path, self.dir)
                proc = subprocess.run([str(exe.resolve())], capture_output=True, cwd=str(ROOT))
                self.assertEqual(proc.returncode, 0,
                                 proc.stderr.decode("utf-8", "replace")[:400])
                got = proc.stdout.decode("utf-8", "replace").replace("\r\n", "\n")
                self.assertEqual(got, host.getvalue())


class TestExamples(unittest.TestCase):
    def test_every_example_runs(self):
        for path in sorted((ROOT / "examples").glob("[0-9][0-9]_*.vak")):
            with self.subTest(example=path.name):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    run_source(path.read_text(encoding="utf-8"), str(path))
                self.assertTrue(buf.getvalue().strip(), f"{path.name} किमपि न अलिखत्")

    def test_every_example_passes_the_analyser(self):
        library = sorted((ROOT / "vaak" / "पुस्तकालयः").glob("*.vak"))
        for path in sorted((ROOT / "examples").glob("*.vak")) + library:
            with self.subTest(example=path.name):
                report = check_source(path.read_text(encoding="utf-8"), path.name)
                self.assertEqual(
                    [d.message for d in report.errors], [],
                    f"{path.name}:\n{report.render(filename=path.name)}",
                )




class TestVakAnalyzer(unittest.TestCase):
    """स्वयंसिद्धेः पञ्चमम् सोपानम् — the semantic analyser written in Vāk.

    वाक्-लिखितः विश्लेषकः पैथन्-विश्लेषकेन सह अक्षरशः सम्मतः भवेत्।
    Every diagnostic — code, line and message, in emission order — must match
    the Python analyser exactly, on clean programs and on broken ones alike.
    """

    HARNESS = ROOT / "tests" / "विश्लेषकपरीक्षा.vak"
    BROKEN = ROOT / "tests" / "दुष्टनमूनाः"

    def run_vak(self, *args: str) -> str:
        result = subprocess.run(
            [sys.executable, "-m", "vaak", *args], capture_output=True, cwd=str(ROOT),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        text = result.stdout.decode("utf-8", "replace")
        self.assertEqual(
            result.returncode, 0,
            "the Vāk toolchain failed:\n" + text
            + result.stderr.decode("utf-8", "replace"),
        )
        return text.replace("\r\n", "\n")

    def analyse_in_vak(self, path: pathlib.Path) -> list:
        rel = path.resolve().relative_to(ROOT).as_posix()
        rows = []
        for line in self.run_vak(str(self.HARNESS), rel).splitlines():
            if line.strip():
                kind, code, num, message = line.split("|", 3)
                rows.append((kind, code, int(num), message))
        return rows

    @staticmethod
    def analyse_in_python(path: pathlib.Path) -> list:
        report = check_source(path.read_text(encoding="utf-8"), path.name)
        return [("दोषः" if d.fatal else "सूचना", d.code, d.line, d.message)
                for d in report.diagnostics]

    def assert_agrees(self, path: pathlib.Path) -> None:
        self.assertEqual(self.analyse_in_vak(path), self.analyse_in_python(path),
                         path.name + ": the two analysers disagree")

    def test_broken_programs_agree(self):
        """एकैकः दोषप्रकारः — one deliberately broken program per diagnostic kind."""
        paths = sorted(self.BROKEN.glob("*.vak"))
        self.assertGreaterEqual(len(paths), 40, "the broken-program battery is missing")
        for path in paths:
            with self.subTest(program=path.name):
                self.assertTrue(self.analyse_in_python(path),
                                path.name + " produces no diagnostics at all")
                self.assert_agrees(path)

    def test_examples_agree(self):
        """उदाहरणानि निर्दोषाणि — and the Vāk analyser must agree that they are."""
        clean = sorted((ROOT / "tests" / "शुद्धनमूनाः").glob("*.vak"))
        for path in sorted((ROOT / "examples").glob("*.vak")) + clean:
            with self.subTest(example=path.name):
                self.assertEqual([r for r in self.analyse_in_python(path)
                                  if r[0] == "दोषः"], [])
                self.assert_agrees(path)

    def test_analyses_the_toolchain_itself(self):
        """विश्लेषकः स्वम् एव विश्लेषयति — including the file it is written in."""
        for name in ("अर्थविश्लेषकः.vak", "व्याकरणम्.vak", "संकलकः.vak", "वाक्.vak"):
            with self.subTest(stage=name):
                self.assert_agrees(ROOT / "स्वयंसिद्धिः" / name)

    def test_driver_check_matches_python_check(self):
        """वाक् --परीक्षा — the Vāk driver renders the report the Python CLI does."""
        target = self.BROKEN / "मिश्रम्_२.vak"
        rel = target.resolve().relative_to(ROOT).as_posix()
        source = target.read_text(encoding="utf-8")
        mine = self.run_vak(str(ROOT / "स्वयंसिद्धिः" / "वाक्.vak"),
                            "--", "--परीक्षा", rel).strip()
        theirs = check_source(source, rel).render(source, rel).strip()
        self.assertEqual(mine, theirs)



class TestSlotResolution(unittest.TestCase):
    """स्थाननिर्णयः — a name the compiler can see declared is read by place.

    The whole thing rests on one property: the compiler's picture of the scopes
    and the machine's actual scopes must be the same shape.  The VM counts every
    time a resolved instruction lands somewhere other than the binding it was
    compiled for, and these tests insist that number stays zero — on the
    examples, on the standard library, and on the toolchain's own source.
    """

    def run_counting(self, source: str, filename: str = "<वाक्>") -> tuple[str, int]:
        machine = VM(filename)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            machine.run(compile_program(parse(tokenize(source, filename), filename),
                                        filename))
        return buffer.getvalue().strip(), machine.slot_misses

    def test_locals_resolve_and_never_miss(self):
        sources = [
            "कार्यम् क(अ, ब) : पूर्णाङ्कः { मान ग = अ + ब। प्रत्यागच्छ ग। } मुद्रय क(१, २)।",
            "मान क = १। { मान क = २। मुद्रय क। } मुद्रय क।",
            "प्रत्येकम् (क अन्तः [१, २, ३]) { मान ख = क * २। मुद्रय ख। }",
            "प्रयत्नः { उत्सृज \"क\"। } दोषे (द) { मुद्रय द.सन्देशः। }",
            "कार्यम् बाह्यम्() { मान ग = ५। कार्यम् अन्तरम्() : पूर्णाङ्कः "
            "{ प्रत्यागच्छ ग। } मुद्रय अन्तरम्()। } बाह्यम्()।",
            "मान ग = ०। यावत् (ग < ३) { ग += १। } मुद्रय ग।",
            "कार्यम् योजकः(आधारः) : कार्यम् { प्रत्यागच्छ कार्यम्(क) : पूर्णाङ्कः "
            "{ प्रत्यागच्छ आधारः + क। }। } मान द = योजकः(१०)। मुद्रय द(१), द(२)।",
        ]
        for source in sources:
            with self.subTest(source=source[:44]):
                walked = output(source)
                ran, misses = self.run_counting(source)
                self.assertEqual(ran, walked, "the VM and the interpreter disagree")
                self.assertEqual(misses, 0, "a resolved slot landed on the wrong binding")

    def test_every_example_resolves_cleanly(self):
        library = sorted((ROOT / "vaak" / "पुस्तकालयः").glob("*.vak"))
        toolchain = sorted((ROOT / "स्वयंसिद्धिः").glob("*.vak"))
        for path in sorted((ROOT / "examples").glob("*.vak")) + library + toolchain:
            with self.subTest(program=path.name):
                _, misses = self.run_counting(path.read_text(encoding="utf-8"),
                                              str(path))
                self.assertEqual(misses, 0,
                                 f"{path.name}: a resolved slot missed its binding")

    def test_globals_are_not_slot_resolved(self):
        """वैश्विकाः न निर्णीयन्ते — the global scope already holds every built-in
        before the program starts, so the compiler cannot number it and must not
        try.  A top-level चर read from inside a कार्यम् is still a search."""
        source = ("मान वैश्विकम् = ५।\n"
                  "कार्यम् क() : पूर्णाङ्कः { प्रत्यागच्छ वैश्विकम्। }")
        chunk = compile_program(parse(tokenize(source, "<प>"), "<प>"), "<प>")
        inner = next(c for c in chunk.constants if hasattr(c, "chunk")).chunk
        self.assertIn(Op.GET_VAR, inner.code)
        self.assertNotIn(Op.GET_LOCAL, inner.code)

    def test_a_builtin_is_reached_directly(self):
        """अन्तर्निहितम् यत् प्रोग्रामः क्वापि न घोषयति — no search at all."""
        chunk = compile_program(parse(tokenize("मुद्रय दीर्घता([१, २])।"), "<प>"), "<प>")
        self.assertIn(Op.GET_BUILTIN, chunk.code)
        self.assertNotIn(Op.GET_VAR, chunk.code)

    def test_a_shadowed_builtin_is_not(self):
        """तत् एव नाम यदि प्रोग्रामः क्वापि घोषयति, तर्हि अन्वेषणम् एव।"""
        source = ("कार्यम् दीर्घता(अ) : पूर्णाङ्कः { प्रत्यागच्छ ०। }\n"
                  "मुद्रय दीर्घता([१])।")
        chunk = compile_program(parse(tokenize(source, "<प>"), "<प>"), "<प>")
        self.assertNotIn(Op.GET_BUILTIN, chunk.code)
        self.assertIn(Op.GET_VAR, chunk.code)

    def test_a_shadowed_builtin_really_wins_at_run_time(self):
        """आच्छादनम् केवलम् संकलनकाले न — चालनकाले अपि तत् एव भवति।"""
        source = ('कार्यम् दीर्घता(अ) : शब्दः { प्रत्यागच्छ "मम"। }\n'
                  "मुद्रय दीर्घता([१, २, ३])।")
        self.assertEqual(output(source), "मम")
        self.assertEqual(vm_output(source), "मम")

    def test_locals_are_resolved(self):
        chunk = compile_program(
            parse(tokenize("कार्यम् क(अ) : पूर्णाङ्कः { प्रत्यागच्छ अ। }"), "<प>"), "<प>")
        inner = next(c for c in chunk.constants if hasattr(c, "chunk")).chunk
        self.assertIn(Op.GET_LOCAL, inner.code)

    def test_the_vak_compiler_agrees_instruction_for_instruction(self):
        """उभौ संकलकौ समौ — the Vāk-written compiler must resolve the same
        slots the Python one does, or the two would not agree byte for byte."""
        for path in sorted((ROOT / "examples").glob("*.vak")):
            with self.subTest(example=path.name):
                source = path.read_text(encoding="utf-8")
                mine = chunk_to_kosha(compile_with_vak(source, str(path)))
                theirs = chunk_to_kosha(
                    compile_program(parse(tokenize(source, str(path)), str(path)),
                                    str(path)))
                self.assertEqual(mine, theirs)



class TestSwitch(unittest.TestCase):
    """विकल्पः / पक्षे — a choice among alternatives.

    विकल्पः is Pāṇini's word for an optional alternative in a rule, and पक्षे is
    the locative — "in this case" — matching दोषे, the locative Vāk already uses
    for catch.  पक्षाः do not fall through: choosing one is the whole of it.
    """

    WEEKDAY = """कार्यम् वासरः(कर्म पूर्णाङ्कः वारः) : शब्दः {
        विकल्पः (वारः) {
            पक्षे १: प्रत्यागच्छ "सोमः"।
            पक्षे २, ३: प्रत्यागच्छ "मध्यमः"।
            अन्यथा: प्रत्यागच्छ "अन्यः"।
        }
    }"""

    def test_matches_one_case(self):
        self.assertEqual(output(self.WEEKDAY + "\nमुद्रय वासरः(१)।"), "सोमः")

    def test_several_values_share_a_case(self):
        self.assertEqual(output(self.WEEKDAY + "\nमुद्रय वासरः(२), वासरः(३)।"),
                         "मध्यमः मध्यमः")

    def test_falls_to_the_default(self):
        self.assertEqual(output(self.WEEKDAY + "\nमुद्रय वासरः(९)।"), "अन्यः")

    def test_no_fall_through(self):
        """पक्षाः स्वतन्त्राः — matching one runs only that one."""
        self.assertEqual(
            output('मान क = १। विकल्पः (क) { पक्षे १: मुद्रय "अ"। पक्षे २: मुद्रय "ब"। '
                   'अन्यथा: मुद्रय "ग"। }'),
            "अ")

    def test_default_wherever_it_is_written(self):
        """अन्यथा is the fallback even when it is written first."""
        self.assertEqual(
            output('मान क = २। विकल्पः (क) { अन्यथा: मुद्रय "शेषः"। पक्षे २: मुद्रय "द्वौ"। }'),
            "द्वौ")

    def test_unmatched_without_default_does_nothing(self):
        self.assertEqual(
            output('मान क = ९। विकल्पः (क) { पक्षे १: मुद्रय "अ"। } मुद्रय "अनन्तरम्"।'),
            "अनन्तरम्")

    def test_parentheses_are_optional(self):
        self.assertEqual(output('मान क = १। विकल्पः क { पक्षे १: मुद्रय "अ"। }'), "अ")

    def test_subject_is_evaluated_once(self):
        self.assertEqual(
            output('मान गणना = ०। कार्यम् विषयः() : पूर्णाङ्कः { गणना += १। प्रत्यागच्छ २। }\n'
                   'विकल्पः (विषयः()) { पक्षे १: मुद्रय "अ"। पक्षे २: मुद्रय "ब"। }\n'
                   'मुद्रय गणना।'),
            "ब\n1")

    def test_strings_and_mixed_values(self):
        self.assertEqual(
            output('विकल्पः ("ॐ") { पक्षे "अ", "ॐ": मुद्रय "मिलितम्"। अन्यथा: मुद्रय "न"। }'),
            "मिलितम्")

    def test_case_body_is_its_own_scope(self):
        self.assertEqual(
            output('मान क = १। मान ख = "बहिः"।\n'
                   'विकल्पः (क) { पक्षे १: { मान ख = "अन्तः"। मुद्रय ख। } }\n'
                   'मुद्रय ख।'),
            "अन्तः\nबहिः")

    def test_nested(self):
        self.assertEqual(
            output('मान क = १। मान ख = २।\n'
                   'विकल्पः (क) { पक्षे १: विकल्पः (ख) { पक्षे २: मुद्रय "अन्तः"। } '
                   'अन्यथा: मुद्रय "बहिः"। }'),
            "अन्तः")

    def test_break_belongs_to_the_enclosing_loop(self):
        """पक्षाः do not fall through, so विरम is free to mean the loop."""
        self.assertEqual(
            output('प्रत्येकम् (क अन्तः [१, २, ३]) { विकल्पः (क) { पक्षे २: विरम। '
                   'अन्यथा: मुद्रय क। } }'),
            "1")

    def test_continue_too(self):
        self.assertEqual(
            output('प्रत्येकम् (क अन्तः [१, २, ३]) { विकल्पः (क) { पक्षे २: अनुवर्त। '
                   'अन्यथा: मुद्रय क। } }'),
            "1\n3")

    # -- what the analyser must say ---------------------------------------
    def test_duplicate_case_is_an_error(self):
        report = check_source('मान क = १। विकल्पः (क) { पक्षे १: मुद्रय "अ"। '
                              'पक्षे १: मुद्रय "ब"। अन्यथा: मुद्रय "ग"। }')
        self.assertIn("प्रवाहदोषः", [d.code for d in report.errors])

    def test_impossible_case_is_an_error(self):
        report = check_source('पूर्णाङ्कः क = १। विकल्पः (क) { पक्षे "अ": मुद्रय "न"। '
                              'अन्यथा: मुद्रय "ग"। }')
        self.assertIn("प्रकारदोषः", [d.code for d in report.errors])

    def test_missing_default_is_only_advice(self):
        report = check_source('मान क = १। विकल्पः (क) { पक्षे १: मुद्रय "अ"। }')
        self.assertTrue(report.ok)
        self.assertIn("प्रवाहसूचना", [d.code for d in report.warnings])

    def test_two_defaults_are_rejected(self):
        with self.assertRaises(ParseError):
            parse(tokenize('मान क = १। विकल्पः (क) { अन्यथा: मुद्रय "अ"। '
                           'अन्यथा: मुद्रय "ब"। }'))

    def test_a_switch_can_satisfy_a_return_type(self):
        """Every पक्षः returns and there is an अन्यथा, so every path returns."""
        report = check_source(self.WEEKDAY)
        self.assertEqual([d.code for d in report.warnings], [])

    def test_without_a_default_it_cannot(self):
        report = check_source('कार्यम् क(अ) : शब्दः { विकल्पः (अ) { '
                              'पक्षे १: प्रत्यागच्छ "अ"। } }')
        self.assertIn("प्रतिफलसूचना", [d.code for d in report.warnings])

    # -- every engine agrees ------------------------------------------------
    def test_vm_matches_the_interpreter(self):
        for source in (self.WEEKDAY + "\nमुद्रय वासरः(१), वासरः(३), वासरः(९)।",
                       'प्रत्येकम् (क अन्तः [१, २, ३]) { विकल्पः (क) { पक्षे २: अनुवर्त। '
                       'अन्यथा: मुद्रय क। } }',
                       'विकल्पः ("ॐ") { पक्षे "ॐ": मुद्रय "प्रणवः"। अन्यथा: मुद्रय "न"। }'):
            with self.subTest(source=source[:40]):
                self.assertEqual(vm_output(source), output(source))

    def test_the_vak_toolchain_agrees(self):
        """Both parsers build the same tree, and both compilers the same code."""
        for source in (self.WEEKDAY,
                       'मान क = २। विकल्पः (क) { पक्षे १, २: मुद्रय "अ"। अन्यथा: मुद्रय "ब"। }',
                       'मान क = १। विकल्पः (क) { अन्यथा: मुद्रय "सर्वदा"। }'):
            with self.subTest(source=source[:40]):
                tree = parse(tokenize(source, "<प>"), "<प>")
                self.assertEqual(parse_with_vak(source), to_kosha(tree))
                self.assertEqual(
                    chunk_to_kosha(compile_with_vak(source, "<प>")),
                    chunk_to_kosha(compile_program(tree, "<प>")))



class TestInput(unittest.TestCase):
    """पठ — reading from the user.

    The engines must agree here too, and the case that catches them out is the
    end of input: the C runtime returns the empty string, so every other engine
    has to as well.  Before this test existed, Python raised EOFError and
    printed a bare traceback.
    """

    def run_with_input(self, source: str, given: str, *extra: str) -> str:
        path = pathlib.Path(tempfile.mkdtemp()) / "प्रदानम्.vak"
        path.write_text(source, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "vaak", *extra, str(path)],
            input=given.encode("utf-8"), capture_output=True, cwd=str(ROOT),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        self.assertEqual(result.returncode, 0,
                         result.stderr.decode("utf-8", "replace"))
        return result.stdout.decode("utf-8", "replace").replace("\r\n", "\n").strip()

    def test_reads_a_line(self):
        self.assertEqual(
            self.run_with_input('मुद्रय "नमस्ते," + पठ()।', "विद्याधीश\n"),
            "नमस्ते,विद्याधीश")

    def test_prompt_is_printed(self):
        self.assertEqual(
            self.run_with_input('शब्दः क = पठ("नाम? ")। मुद्रय क।', "राम\n"),
            "नाम? राम")

    def test_reads_a_number(self):
        self.assertEqual(
            self.run_with_input("पूर्णाङ्कः क = संख्या(पठ())। मुद्रय क * २।", "२१\n"),
            "42")

    def test_devanagari_numerals_are_read(self):
        self.assertEqual(
            self.run_with_input("मुद्रय संख्या(पठ()) + १।", "९९\n"), "100")

    def test_end_of_input_gives_the_empty_string(self):
        """The C runtime returns "" here, so the others must too."""
        self.assertEqual(
            self.run_with_input('मुद्रय "[" + पठ() + "]"।', ""), "[]")

    def test_reading_past_the_end_does_not_crash(self):
        source = 'शब्दः अ = पठ()। शब्दः ब = पठ()। मुद्रय अ, "|", दीर्घता(ब)।'
        self.assertEqual(self.run_with_input(source, "एकम्\n"), "एकम् | 0")

    def test_every_engine_reads_the_same(self):
        source = ('शब्दः नाम = पठ()। पूर्णाङ्कः वयः = संख्या(पठ())।\n'
                  'मुद्रय नाम, वयः + १, दीर्घता(पठ())।')
        given = "राम\n४१\n"
        expected = self.run_with_input(source, given)
        for engine in (["--vm"], ["--self-vm"]):
            with self.subTest(engine=engine[0]):
                self.assertEqual(self.run_with_input(source, given, *engine),
                                 expected)



class TestStringGrowth(unittest.TestCase):
    """`x = x + y` grows the string in place when it is safe to.

    Building a string of n characters used to copy n²/2 bytes.  The machine now
    grows it in place, but only after proving that nothing else can see the
    string and that the assignment which follows will be accepted.  These tests
    are mostly about the second half of that: a ध्रुव and an alias must both come
    out untouched, because the growth happens before the assignment does.
    """

    def native(self, source: str) -> str:
        """Run it on वाक्.exe, where the optimisation lives."""
        exe = ROOT / "वाक्.exe"
        if not exe.exists():
            self.skipTest("वाक्.exe not built")
        path = pathlib.Path(tempfile.mkdtemp()) / "वर्धनम्.vak"
        path.write_text(source, encoding="utf-8")
        r = subprocess.run([str(exe), str(path)], capture_output=True, cwd=str(ROOT))
        return r.stdout.decode("utf-8", "replace").replace("\r\n", "\n").strip()

    def both(self, source: str) -> str:
        """The interpreter and वाक्.exe must agree — that is the whole point."""
        walked = output(source)
        self.assertEqual(self.native(source), walked)
        return walked

    def test_builds_a_string(self):
        self.assertEqual(
            self.both('शब्दः अ = ""। आवृत्तिः (५) { अ = अ + "क"। } मुद्रय अ।'),
            "ककककक")

    def test_compound_assignment_too(self):
        self.assertEqual(
            self.both('शब्दः अ = "क"। अ += "ख"। अ += "ग"। मुद्रय अ।'), "कखग")

    def test_an_alias_is_not_disturbed(self):
        """ब holds the same string, so अ must not grow in place."""
        self.assertEqual(
            self.both('शब्दः अ = "क"। शब्दः ब = अ। अ = अ + "ख"। मुद्रय अ, ब।'),
            "कख क")

    def test_a_string_in_a_list_is_not_disturbed(self):
        self.assertEqual(
            self.both('शब्दः अ = "क"। सूची स = [अ]। अ = अ + "ख"। मुद्रय अ, स।'),
            'कख ["क"]')

    def test_a_constant_is_not_damaged_by_a_refused_assignment(self):
        """The growth happens before the assignment; a ध्रुव refuses it, and must
        be left exactly as it was."""
        source = ('कार्यम् रचय() : शब्दः { प्रत्यागच्छ "अ" + "ब"। }\n'
                  'ध्रुव शब्दः क = रचय()।\n'
                  'प्रयत्नः { क = क + "ग"। } दोषे (द) { मुद्रय द.प्रकारः। }\n'
                  'मुद्रय क।')
        self.assertEqual(self.native(source), "ध्रुवदोषः\nअब")

    def test_a_grown_string_still_works_as_a_dictionary_key(self):
        """Growing invalidates the cached hash — if it did not, the lookup
        would silently miss."""
        self.assertEqual(
            self.both('शब्दः कुं = "अ"। कुं = कुं + "ब"।\n'
                      'कोशः को = {}। को[कुं] = ४२।\n'
                      'मुद्रय को["अब"], अस्ति(को, "अब")।'),
            "42 सत्य")

    def test_a_grown_string_still_counts_its_aksharas(self):
        """The akṣara count is cached too."""
        self.assertEqual(
            self.both('शब्दः द = "क"। द = द + "ष्ण"। मुद्रय अक्षराणि(द), दीर्घता(द)।'),
            '["क", "ष्ण"] 4')

    def test_other_operands_are_untouched(self):
        self.assertEqual(self.both('मुद्रय १ + २, "x" + "y", [१] + [२]।'),
                         "3 xy [1, 2]")

    def test_growth_is_linear(self):
        """Twice the work should take about twice the time, not four times.
        The bound is loose because this is a wall clock on a shared machine —
        it is here to catch a return to quadratic, not to measure anything."""
        import time
        exe = ROOT / "वाक्.exe"
        if not exe.exists():
            self.skipTest("वाक्.exe not built")

        def seconds(n: int) -> float:
            source = (f'शब्दः अ = ""। पूर्णाङ्कः क = ०।\n'
                      f'यावत् (क < {n}) {{ अ = अ + "क"। क += १। }}\n'
                      f'मुद्रय दीर्घता(अ)।')
            path = pathlib.Path(tempfile.mkdtemp()) / "प.vak"
            path.write_text(source, encoding="utf-8")
            best = 9e9
            for _ in range(3):
                start = time.perf_counter()
                r = subprocess.run([str(exe), str(path)], capture_output=True)
                best = min(best, time.perf_counter() - start)
                self.assertEqual(r.returncode, 0)
            return best

        small, large = seconds(20_000), seconds(80_000)
        # quadratic would be ~16×; linear is ~4×.  Anything under 8× is not
        # quadratic, and the slack absorbs process startup and a noisy machine.
        self.assertLess(large, small * 8,
                        f"string building looks quadratic again: "
                        f"20k took {small:.3f}s, 80k took {large:.3f}s")


class TestByteOrderMark(unittest.TestCase):
    """Notepad and PowerShell write a UTF-8 BOM by default, so a beginner's
    very first .vak file is likely to carry one.  It used to be reported as an
    unknown character, which is true and useless."""

    SOURCE = 'मुद्रय "नमस्ते जगत्"।'
    BOM = "﻿"

    def test_leading_bom_is_ignored(self):
        out = io.StringIO()
        with redirect_stdout(out):
            run_source(self.BOM + self.SOURCE)
        self.assertEqual(out.getvalue().strip(), "नमस्ते जगत्")

    def test_bom_only_stripped_at_the_start(self):
        """A BOM in the middle is still a real error — it is not whitespace."""
        with self.assertRaises(LexError):
            run_source(self.SOURCE + self.BOM + self.SOURCE)

    def test_bom_file_runs_through_the_cli(self):
        path = pathlib.Path(tempfile.mkdtemp()) / "परीक्षा.vak"
        path.write_text(self.SOURCE, encoding="utf-8-sig")
        self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"))
        out = io.StringIO()
        with redirect_stdout(out):
            run_source(path.read_text(encoding="utf-8"))
        self.assertEqual(out.getvalue().strip(), "नमस्ते जगत्")

    def test_launcher_scripts_are_ascii(self):
        """cmd.exe reads a .cmd in the console's OEM codepage, so Devanagari in
        a REM line comes back as bytes it then tries to execute."""
        root = pathlib.Path(__file__).resolve().parent.parent
        raw = (root / "vaak.cmd").read_bytes()
        try:
            raw.decode("ascii")
        except UnicodeDecodeError as exc:
            self.fail(f"vaak.cmd must be ASCII for cmd.exe to parse it: {exc}")

class TestTypingAid(unittest.TestCase):
    """The romanised typing aid must never turn a valid Vāk program into an
    invalid one. Phonetic rules are right for names the author invents and
    wrong for the language's own words: `mana` transliterates to मन, but the
    keyword is मान."""

    @staticmethod
    def _is_devanagari(word: str) -> bool:
        return any("ऀ" <= c <= "ॿ" for c in word)

    def test_every_romanised_keyword_maps_to_a_real_keyword(self):
        from vaak.tokens import KEYWORDS
        from vaak.translit import keyword_map

        mapping = keyword_map()
        devanagari_keywords = {w for w in KEYWORDS if self._is_devanagari(w)}
        for roman, dev in mapping.items():
            if roman in KEYWORDS:
                self.assertIn(dev, devanagari_keywords,
                              f"{roman!r} maps to {dev!r}, which is not a keyword")

    def test_the_map_covers_every_romanised_keyword(self):
        from vaak.tokens import KEYWORDS
        from vaak.translit import keyword_map

        mapping = keyword_map()
        missing = [w for w in KEYWORDS
                   if not self._is_devanagari(w) and w not in mapping]
        self.assertEqual(missing, [], f"not in the typing map: {missing}")

    def test_the_map_is_needed(self):
        """If phonetic transliteration ever became correct for every keyword
        this test would fail, and the map could go. It is not: 22 of the 33
        ASCII keywords differ."""
        from vaak.tokens import KEYWORDS
        from vaak.translit import devanagari, keyword_map

        mapping = keyword_map()
        differ = [w for w in KEYWORDS
                  if w in mapping and not self._is_devanagari(w)
                  and devanagari(w) != mapping[w]]
        self.assertTrue(differ, "the keyword map no longer changes anything")

    def test_converted_keywords_still_lex_as_keywords(self):
        """The point of the map, end to end: what it produces must tokenise as
        the same keyword the romanised form did."""
        from vaak.lexer import tokenize
        from vaak.tokens import KEYWORDS
        from vaak.translit import keyword_map

        for roman, dev in keyword_map().items():
            if roman not in KEYWORDS:
                continue
            with self.subTest(keyword=roman):
                self.assertEqual(tokenize(dev)[0].type, tokenize(roman)[0].type)

    def test_a_typed_program_still_runs_after_conversion(self):
        from vaak.translit import keyword_map

        mapping = keyword_map()
        words = "mana x = 5. mudraya x.".replace(".", "।").split()
        converted = " ".join(mapping.get(w, w) for w in words)
        out = io.StringIO()
        with redirect_stdout(out):
            run_source(converted)
        self.assertEqual(out.getvalue().strip(), "5")

    def test_ordinary_names_are_still_phonetic(self):
        """Names the author invents are not in the map and must fall through
        to the phonetic rules."""
        from vaak.translit import devanagari, keyword_map

        mapping = keyword_map()
        self.assertNotIn("naama", mapping)
        self.assertEqual(devanagari("naama"), "नाम")

class TestStandardLibraryAdditions(unittest.TestCase):
    """गणितम्.वर्गमूलम् (issue #1) and शब्दाः.छिन्द (issue #2)."""

    def run_vak(self, source: str) -> str:
        buf = io.StringIO()
        with redirect_stdout(buf):
            run_source(source, str(ROOT / "प.vak"))
        return buf.getvalue().strip()

    # ---------------------------------------------------------- वर्गमूलम्
    def test_square_root_of_perfect_squares(self):
        out = self.run_vak(
            'आनय "गणितम्"।\n'
            'प्रत्येकम् (क अन्तः [०, १, ४, ९, १६, १४४, १०००० ]) {\n'
            '    मुद्रय गणितम्.वर्गमूलम्(क)।\n'
            '}')
        got = [float(x) for x in out.splitlines()]
        self.assertEqual(got, [0.0, 1.0, 2.0, 3.0, 4.0, 12.0, 100.0])

    def test_square_root_converges(self):
        out = self.run_vak('आनय "गणितम्"।\nमुद्रय गणितम्.वर्गमूलम्(२)।')
        self.assertAlmostEqual(float(out), 2 ** 0.5, places=12)

    def test_square_root_of_a_negative_is_an_error(self):
        """उत्सृज surfaces as a RuntimeVakError when nothing catches it, and
        the message should say what went wrong, not only that it did."""
        with self.assertRaises(RuntimeVakError) as caught:
            self.run_vak('आनय "गणितम्"।\nमुद्रय गणितम्.वर्गमूलम्(-१)।')
        self.assertIn("ऋणसंख्यायाः", str(caught.exception))

    def test_square_root_of_a_negative_can_be_caught(self):
        out = self.run_vak(
            'आनय "गणितम्"।\n'
            'प्रयत्नः { मुद्रय गणितम्.वर्गमूलम्(-१)। }\n'
            'दोषे (त्रुटिः) { मुद्रय त्रुटिः.प्रकारः। }')
        self.assertEqual(out, "मूल्यदोषः")

    # -------------------------------------------------------------- छिन्द
    def test_trim_both_ends(self):
        out = self.run_vak(
            'आनय "शब्दाः"।\n'
            'मुद्रय "[" + शब्दाः.छिन्द("   नमस्ते   ") + "]"।')
        self.assertEqual(out, "[नमस्ते]")

    def test_trim_one_end_at_a_time(self):
        out = self.run_vak(
            'आनय "शब्दाः"।\n'
            'मुद्रय "[" + शब्दाः.आदौ_छिन्द("  क  ") + "]"।\n'
            'मुद्रय "[" + शब्दाः.अन्ते_छिन्द("  क  ") + "]"।')
        self.assertEqual(out.splitlines(), ["[क  ]", "[  क]"])

    def test_trim_handles_empty_and_all_whitespace(self):
        out = self.run_vak(
            'आनय "शब्दाः"।\n'
            'मुद्रय "[" + शब्दाः.छिन्द("") + "]"।\n'
            'मुद्रय "[" + शब्दाः.छिन्द("     ") + "]"।')
        self.assertEqual(out.splitlines(), ["[]", "[]"])

    def test_trim_leaves_inner_whitespace_alone(self):
        out = self.run_vak(
            'आनय "शब्दाः"।\n'
            'मुद्रय "[" + शब्दाः.छिन्द("  अ ब  ") + "]"।')
        self.assertEqual(out, "[अ ब]")

    def test_whitespace_predicate_covers_tab_newline_return(self):
        out = self.run_vak(
            'आनय "शब्दाः"।\n'
            'प्रत्येकम् (अ अन्तः [" ", "\\t", "\\n", "\\r", "क", ""]) {\n'
            '    मुद्रय शब्दाः.रिक्तम्_वा(अ)।\n'
            '}')
        self.assertEqual(out.splitlines(),
                         ["सत्य", "सत्य", "सत्य", "सत्य", "असत्य", "असत्य"])
    # -------------------------------------------------------- प्रतिस्थापय
    def test_replace_every_occurrence(self):
        out = self.run_vak(
            'आनय "शब्दाः"।\n'
            'मुद्रय शब्दाः.प्रतिस्थापय("नमस्ते जगत्", "जगत्", "विश्व")।\n'
            'मुद्रय शब्दाः.प्रतिस्थापय("अअअ", "अ", "ब")।')
        self.assertEqual(out.splitlines(), ["नमस्ते विश्व", "बबब"])

    def test_replacement_containing_the_target_does_not_feed_itself(self):
        """The scan steps over what it wrote, so this terminates and doubles
        rather than looping forever."""
        out = self.run_vak(
            'आनय "शब्दाः"।\n'
            'मुद्रय शब्दाः.प्रतिस्थापय("अअ", "अ", "अअ")।')
        self.assertEqual(out, "अअअअ")

    def test_replace_with_empty_deletes(self):
        out = self.run_vak(
            'आनय "शब्दाः"।\n'
            'मुद्रय "[" + शब्दाः.प्रतिस्थापय("ककक", "क", "") + "]"।')
        self.assertEqual(out, "[]")

    def test_empty_target_returns_the_string_unchanged(self):
        """An empty needle matches everywhere and would never advance."""
        out = self.run_vak(
            'आनय "शब्दाः"।\n'
            'मुद्रय "[" + शब्दाः.प्रतिस्थापय("क", "", "ख") + "]"।')
        self.assertEqual(out, "[क]")

    def test_replace_with_no_match_is_the_identity(self):
        out = self.run_vak(
            'आनय "शब्दाः"।\n'
            'मुद्रय शब्दाः.प्रतिस्थापय("abc", "z", "y")।')
        self.assertEqual(out, "abc")

    # -------------------------------------- बहुलकः, विचरणम्, प्रमाणविचलनम्
    def test_mode(self):
        out = self.run_vak(
            'आनय "गणितम्"।\n'
            'मुद्रय गणितम्.बहुलकः([१, २, २, ३, ३, ३])।\n'
            'मुद्रय गणितम्.बहुलकः([७])।')
        self.assertEqual(out.splitlines(), ["3", "7"])

    def test_mode_breaks_a_tie_toward_the_smaller_value(self):
        """Documented behaviour, not an accident: sorting first makes it
        deterministic regardless of the order the values arrived in."""
        out = self.run_vak(
            'आनय "गणितम्"।\n'
            'मुद्रय गणितम्.बहुलकः([३, १, १, २, २])।\n'
            'मुद्रय गणितम्.बहुलकः([२, २, १, १, ३])।')
        self.assertEqual(out.splitlines(), ["1", "1"])

    def test_variance_and_standard_deviation(self):
        """The textbook example: population variance 4, so σ is 2."""
        out = self.run_vak(
            'आनय "गणितम्"।\n'
            'मुद्रय गणितम्.विचरणम्([२, ४, ४, ४, ५, ५, ७, ९])।\n'
            'मुद्रय गणितम्.प्रमाणविचलनम्([२, ४, ४, ४, ५, ५, ७, ९])।')
        got = [float(x) for x in out.splitlines()]
        self.assertAlmostEqual(got[0], 4.0, places=10)
        self.assertAlmostEqual(got[1], 2.0, places=10)

    def test_variance_of_one_value_is_zero(self):
        """Population, not sample — so a population of one has no spread,
        rather than dividing by zero."""
        out = self.run_vak('आनय "गणितम्"।\nमुद्रय गणितम्.विचरणम्([५])।')
        self.assertAlmostEqual(float(out), 0.0, places=12)

    def test_empty_list_is_an_error_for_all_three(self):
        for fn in ("बहुलकः", "विचरणम्", "प्रमाणविचलनम्"):
            with self.subTest(function=fn):
                with self.assertRaises(RuntimeVakError):
                    self.run_vak(f'आनय "गणितम्"।\nमुद्रय गणितम्.{fn}([])।')

class TestUnusedVariableWarning(unittest.TestCase):
    """Issue #7. A warning, not an error — the program is still valid."""

    def codes(self, source: str) -> list[str]:
        return [d.code for d in check_source(source, "प.vak").diagnostics]

    def test_a_declared_and_unread_variable_warns(self):
        self.assertIn("अप्रयुक्तसूचना",
                      self.codes("कार्यम् क() { मान अ = ५। }"))

    def test_a_variable_that_is_read_does_not(self):
        self.assertNotIn("अप्रयुक्तसूचना",
                         self.codes("कार्यम् क() { मान अ = ५। मुद्रय अ। }"))

    def test_calling_a_variable_counts_as_reading_it(self):
        """The call path resolves the callee itself and never reaches the
        identifier handler, so it has to mark the read separately. This was a
        real false positive before it did."""
        self.assertNotIn("अप्रयुक्तसूचना", self.codes(
            "कार्यम् क() { मान फ = कार्यम्() { प्रत्यागच्छ १। }। प्रत्यागच्छ फ()। }"))

    def test_assigning_is_not_reading(self):
        """Writing to a variable you never read is exactly the mistake this
        warning is for."""
        self.assertIn("अप्रयुक्तसूचना",
                      self.codes("कार्यम् क() { मान अ = ५। अ = ६। }"))

    def test_a_leading_underscore_says_it_is_deliberate(self):
        self.assertNotIn("अप्रयुक्तसूचना",
                         self.codes("कार्यम् क() { मान _अ = ५। }"))

    def test_parameters_are_not_reported(self):
        """A parameter is named because the language requires a name there,
        not because the author promised to use it."""
        self.assertNotIn("अप्रयुक्तसूचना",
                         self.codes("कार्यम् क(अ) { मुद्रय १। }"))

    def test_loop_and_catch_variables_are_not_reported(self):
        for src in ("कार्यम् क() { प्रत्येकम् (अ अन्तः [१]) { मुद्रय २। } }",
                    "कार्यम् क() { प्रयत्नः { मुद्रय १। } दोषे (द) { मुद्रय २। } }"):
            with self.subTest(source=src[:38]):
                self.assertNotIn("अप्रयुक्तसूचना", self.codes(src))

    def test_top_level_declarations_are_exports_not_mistakes(self):
        """गणितम् declares पाई for importers, not for itself. Warning about a
        module's exports would make the warning useless."""
        self.assertNotIn("अप्रयुक्तसूचना", self.codes("ध्रुव पाई = ३.१४।"))

    def test_it_is_a_warning_and_the_program_still_runs(self):
        out = io.StringIO()
        with redirect_stdout(out):
            run_source("कार्यम् क() { मान अ = ५। मुद्रय \"चलति\"। }" + "\n" + "क()।")
        self.assertEqual(out.getvalue().strip(), "चलति")


class TestReplHistory(unittest.TestCase):
    """Issue #9. readline is not in the standard library on Windows, which is
    where Vāk is developed, so the live path is exercised with a stand-in and
    the absent path is exercised for real."""

    def setUp(self):
        from vaak import cli
        self.cli = cli
        self._real_path = cli.history_path

    def tearDown(self):
        self.cli.history_path = self._real_path
        sys.modules.pop("readline", None)

    @staticmethod
    def _fake_readline(calls):
        import types
        fake = types.ModuleType("readline")
        fake.read_history_file = lambda p: calls.append(("read", p))
        fake.write_history_file = lambda p: calls.append(("write", p))
        fake.set_history_length = lambda n: calls.append(("limit", n))
        return fake

    def test_history_goes_beside_the_users_home(self):
        self.assertEqual(self.cli.history_path().name, ".vaak_history")
        self.assertEqual(self.cli.history_path().parent, pathlib.Path.home())

    def test_without_readline_it_returns_none_and_does_not_raise(self):
        """The Windows case, and any build without readline. History not
        persisting is a small loss; refusing to start a REPL is not."""
        import builtins
        real_import = builtins.__import__

        def blocked(name, *args, **kwargs):
            if name == "readline":
                raise ImportError("no readline")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = blocked
        try:
            self.assertIsNone(self.cli.enable_history())
        finally:
            builtins.__import__ = real_import

    def test_with_readline_it_reads_on_start_and_writes_on_exit(self):
        import atexit
        calls: list = []
        sys.modules["readline"] = self._fake_readline(calls)
        self.cli.history_path = lambda: pathlib.Path(tempfile.mkdtemp()) / ".vaak_history"

        registered: list = []
        real_register = atexit.register
        atexit.register = lambda fn, *a, **k: (registered.append(fn), fn)[1]
        try:
            self.assertIsNotNone(self.cli.enable_history())
        finally:
            atexit.register = real_register

        self.assertEqual([c[0] for c in calls], ["read", "limit"])
        self.assertEqual(len(registered), 1, "nothing would save the history")
        registered[0]()
        self.assertEqual([c[0] for c in calls], ["read", "limit", "write"])

    def test_an_unwritable_history_location_is_survivable(self):
        """A read-only home or a full disk must not take the REPL down."""
        calls: list = []
        sys.modules["readline"] = self._fake_readline(calls)
        self.cli.history_path = lambda: pathlib.Path("Z:/nowhere/at/all/.vaak_history")
        self.cli.enable_history()          # must not raise

    def test_the_limit_is_applied(self):
        calls: list = []
        sys.modules["readline"] = self._fake_readline(calls)
        self.cli.history_path = lambda: pathlib.Path(tempfile.mkdtemp()) / ".vaak_history"
        self.cli.enable_history()
        self.assertIn(("limit", self.cli.HISTORY_LIMIT), calls)

class TestPackaging(unittest.TestCase):
    """`twine check` validates the description and nothing else, so an invalid
    trove classifier sails past it and PyPI answers 400 Bad Request with no
    indication of which field is wrong. `Natural Language :: Sanskrit` — which
    PyPI does not define — cost one failed upload before this test existed."""

    OFFICIAL = "https://pypi.org/pypi?:action=list_classifiers"

    @staticmethod
    def _project() -> dict:
        """pyproject's [project] table. tomllib is 3.11+, and Vāk supports
        3.10, so the classifiers are read without it rather than making the
        test suite need a newer Python than the package does."""
        import re

        root = pathlib.Path(__file__).resolve().parent.parent
        text = (root / "pyproject.toml").read_text(encoding="utf-8")
        try:
            import tomllib
            return tomllib.loads(text)["project"]
        except ModuleNotFoundError:
            pass
        # a small reader for the two fields these tests look at
        block = re.search(r"^classifiers = \[(.*?)^\]", text, re.S | re.M)
        classifiers = re.findall(r'"([^"]+)"', block.group(1)) if block else []
        licence = re.search(r'^license = "([^"]+)"', text, re.M)
        project = {"classifiers": classifiers}
        if licence:
            project["license"] = licence.group(1)
        return project

    def _classifiers(self) -> list[str]:
        return self._project()["classifiers"]

    def test_every_classifier_is_one_pypi_defines(self):
        import urllib.error
        import urllib.request
        try:
            with urllib.request.urlopen(self.OFFICIAL, timeout=20) as response:
                official = set(response.read().decode("utf-8").splitlines())
        except (urllib.error.URLError, TimeoutError) as exc:  # offline
            self.skipTest(f"cannot reach PyPI's classifier list: {exc}")
        unknown = [c for c in self._classifiers() if c not in official]
        self.assertEqual(unknown, [],
                         f"PyPI does not define these classifiers, and will "
                         f"reject the upload with 400: {unknown}")

    def test_no_licence_classifier_alongside_the_licence_expression(self):
        """PEP 639 metadata carries `License-Expression`. PyPI rejects an
        upload that also carries a `License ::` classifier."""
        project = self._project()
        if "license" in project:
            clashing = [c for c in project["classifiers"] if c.startswith("License ::")]
            self.assertEqual(clashing, [],
                             "remove the License classifier, or the license field")

class TestDocumentation(unittest.TestCase):
    """The manual is generated, but generation only helps if the generator is
    made to notice what it has not covered.  These hold it to the language."""

    @staticmethod
    def _reference():
        import sys
        docs = pathlib.Path(__file__).resolve().parent.parent / "docs"
        if str(docs) not in sys.path:
            sys.path.insert(0, str(docs))
        import reference
        return reference

    @staticmethod
    def _manual() -> str:
        page = pathlib.Path(__file__).resolve().parent.parent / "docs" / "manual.html"
        return page.read_text(encoding="utf-8")

    def test_reference_tables_have_not_drifted(self):
        problems = self._reference().check()
        self.assertEqual(problems, [], "; ".join(problems))

    def test_every_standard_library_name_is_documented(self):
        missing = [n for n in self._reference().library_names()
                   if n not in self._manual()]
        self.assertEqual(missing, [], f"undocumented library names: {missing}")

    def test_every_diagnostic_is_documented(self):
        man = self._manual()
        ref = self._reference()
        missing = [c for c in ref.diagnostic_codes() if c not in man]
        self.assertEqual(missing, [], f"undocumented diagnostics: {missing}")
        kinds = [k for k, _ in ref.error_kinds() if k not in man]
        self.assertEqual(kinds, [], f"undocumented error kinds: {kinds}")

    def test_every_diagnostic_is_shown_happening(self):
        """The manual lists the diagnostics and also demonstrates each one.
        A list teaches less than watching one fire, so the demonstration must
        cover every code the analyser can emit — not most of them."""
        ref = self._reference()
        shown = {code for code, _src, _msg in ref.demonstrations()}
        missing = [c for c in ref.diagnostic_codes() if c not in shown]
        self.assertEqual(missing, [],
                         f"no broken-program example provokes: {missing}")

    def test_the_demonstrations_are_real_analyser_output(self):
        """Each demonstration must actually produce the message it claims."""
        from vaak import check_source
        for code, src, msg in self._reference().demonstrations():
            with self.subTest(diagnostic=code):
                report = check_source(src, "demo.vak")
                self.assertIn(msg, [d.message for d in report.diagnostics])

    def test_every_command_line_flag_is_documented(self):
        man = self._manual()
        missing = [f for f, _, _ in self._reference().cli_flags() if f not in man]
        self.assertEqual(missing, [], f"undocumented flags: {missing}")

    def test_every_keyword_and_builtin_is_documented(self):
        from vaak.builtins import BUILTIN_DOCS
        from vaak.tokens import KEYWORDS
        man = self._manual()
        dev = [w for w in KEYWORDS
               if any("ऀ" <= c <= "ॿ" for c in w)]
        self.assertEqual([w for w in dev if w not in man], [])
        self.assertEqual([b[0] for b in BUILTIN_DOCS if b[0] not in man], [])

    def test_manual_samples_only_call_names_that_exist(self):
        """A sample that parses can still call a function nobody wrote — the
        manual shipped गणितम्.वर्गमूलम् for a while, which never existed."""
        import re
        from vaak.builtins import BUILTIN_DOCS
        known = {b[0] for b in BUILTIN_DOCS} | self._reference().library_names()
        man = self._manual()
        called = set()
        for mod in ("गणितम्", "शब्दाः"):
            called |= set(re.findall(re.escape(mod) + r"\.([^\s(<]+)\(", man))
        unknown = sorted(called - known)
        self.assertEqual(unknown, [],
                         f"the manual calls names that do not exist: {unknown}")

if __name__ == "__main__":
    unittest.main(verbosity=2)
