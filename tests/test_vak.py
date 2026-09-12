"""
परीक्षाः — the test suite of Vāk.

    python -m tests.test_vak        # or:  python tests/test_vak.py
No third-party dependencies; it is a plain unittest suite.
"""

from __future__ import annotations

import inspect
import io
import json
import os
import re
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
from vaak.builtins import BUILTIN_DOCS           # noqa: E402
from vaak.compiler import compile_program        # noqa: E402
from vaak.kosha import chunk_to_kosha, to_kosha  # noqa: E402
from vaak.native import build_executable, find_gcc  # noqa: E402
from vaak.graph import graph_of_source           # noqa: E402
from vaak.selfhost import (                      # noqa: E402
    bootstrap_available,
    compile_kosha_with_vak,
    compile_with_vak,
    graph_with_vak,
    parse_with_vak,
    run_with_vak,
)
from vaak.vm import VM                           # noqa: E402
from vaak.errors import LexError, ParseError, RuntimeVakError, VakError  # noqa: E402
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


class TestKarakaGraph(unittest.TestCase):
    """कारकालेखः — the graph of who plays what role in which action.

    The graph is not a new analysis; it is the analyser's own binding rule
    written down as a picture. A call's arguments are matched to a कार्यम्'s
    parameters exactly as कारकैः_क्रमय matches them — labelled ones to their
    named slots, the rest into the free slots in order — so anything the graph
    draws as अनुक्तम् or न्यूनम् is what the compiler would do or refuse.
    """

    def graph(self, source: str) -> dict:
        return graph_of_source(source, "<परीक्षा>")

    def test_an_action_lists_its_slots_in_declared_order(self):
        g = self.graph("कार्यम् लिखतु(कर्ता शब्दः क, करणम् शब्दः ख = \"लेखन्या\",\n"
                       "              कर्म शब्दः ग) : शब्दः { प्रत्यागच्छ क + ख + ग। }\n")
        self.assertEqual(len(g["कार्याणि"]), 1)
        act = g["कार्याणि"][0]
        self.assertEqual(act["नाम"], "लिखतु")
        self.assertEqual([p["कारकम्"] for p in act["प्राचलाः"]],
                         ["कर्ता", "करणम्", "कर्म"])
        self.assertEqual([p["मूलम्"] for p in act["प्राचलाः"]],
                         [False, True, False])
        self.assertEqual(act["दोषाः"], [])

    def test_a_labelled_call_binds_by_name_whatever_the_order(self):
        g = self.graph("कार्यम् लिखतु(कर्ता शब्दः क, कर्म शब्दः ग) : शब्दः {\n"
                       "    प्रत्यागच्छ क + ग।\n}\n"
                       "मुद्रय लिखतु(कर्म: \"ख\", कर्ता: \"अ\")।\n")
        bonds = g["आह्वानानि"][0]["बन्धाः"]
        self.assertEqual([(b["कारकम्"], b["रीतिः"], b["मूल्यम्"]) for b in bonds],
                         [("कर्ता", "नाम्ना", '"अ"'), ("कर्म", "नाम्ना", '"ख"')])

    def test_an_unstated_role_with_a_default_is_anuktam_not_a_fault(self):
        """अनुक्तम् कारकम् — 'देवदत्तः पचति' names no कर्म and is still a
        sentence. The graph draws the slot, marks it unspoken, and reports
        no fault; the same call with no default would be न्यूनम्."""
        g = self.graph("कार्यम् लिखतु(कर्ता शब्दः क, करणम् शब्दः ख = \"लेखन्या\",\n"
                       "              कर्म शब्दः ग) : शब्दः { प्रत्यागच्छ क + ख + ग। }\n"
                       "मुद्रय लिखतु(कर्ता: \"क\", कर्म: \"ग\")।\n")
        call = g["आह्वानानि"][0]
        ways = {b["कारकम्"]: b["रीतिः"] for b in call["बन्धाः"]}
        self.assertEqual(ways["करणम्"], "अनुक्तम्")
        self.assertEqual(call["दोषाः"], [])

    def test_an_unstated_role_without_a_default_is_nyunam(self):
        g = self.graph("कार्यम् लिखतु(कर्ता शब्दः क, कर्म शब्दः ग) : शब्दः {\n"
                       "    प्रत्यागच्छ क + ग।\n}\n"
                       "मुद्रय लिखतु(कर्ता: \"क\")।\n")
        call = g["आह्वानानि"][0]
        ways = {b["कारकम्"]: b["रीतिः"] for b in call["बन्धाः"]}
        self.assertEqual(ways["कर्म"], "न्यूनम्")
        self.assertEqual(call["दोषाः"], ["न्यूनम्: कर्म"])

    def test_two_karta_slots_are_a_fault_on_the_action(self):
        """एककर्तृत्वम् — one agent to an action. The analyser refuses it, and
        the graph must show the same refusal without being told."""
        g = self.graph("कार्यम् क(कर्ता शब्दः अ, कर्ता शब्दः ब) { मुद्रय अ, ब। }\n")
        self.assertTrue(g["कार्याणि"][0]["दोषाः"])

    def test_a_call_records_the_action_it_sits_inside(self):
        g = self.graph("कार्यम् अ(कर्म पूर्णाङ्कः सङ्ख्या) { प्रत्यागच्छ सङ्ख्या। }\n"
                       "कार्यम् ब() { प्रत्यागच्छ अ(१)। }\n"
                       "मुद्रय ब()।\n")
        inside = {c["कार्यम्"]: c["अन्तः"] for c in g["आह्वानानि"]}
        self.assertEqual(inside["अ"], "ब")
        self.assertIsNone(inside["ब"])

    def test_the_graph_of_every_example_is_built_by_python_and_by_vak_alike(self):
        """The differential that matters: वाक्-in-वाक् builds the same graph as
        the Python module, over every example that ships. The two walkers were
        written separately from the same rule; if they ever disagree, one of
        them has stopped describing the language."""
        if not bootstrap_available():
            self.skipTest("no bootstrap")
        for path in sorted((ROOT / "examples").glob("*.vak")):
            with self.subTest(example=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertEqual(graph_with_vak(source),
                                 graph_of_source(source, path.name))

    def test_the_cli_prints_the_same_graph_as_json(self):
        path = ROOT / "examples" / "13_karaka.vak"
        result = subprocess.run([sys.executable, "-m", "vaak", "--graph", str(path)],
                                capture_output=True, encoding="utf-8", cwd=str(ROOT))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout),
                         graph_of_source(path.read_text(encoding="utf-8"), path.name))


class TestThePlaygroundCarriesTheKarakaGraph(unittest.TestCase):
    """आलेखः क्रीडाक्षेत्रे — the live graph panel, as committed.

    docs/playground.html is a generated file that is also a shipped one: what
    is in the repository is what GitHub Pages serves. The renderer lives in
    docs/playground_graph.{js,css} and is inlined at build time, so an edit to
    either without a rebuild would serve a page that quietly lags its source.
    """

    def page(self) -> str:
        return (ROOT / "docs" / "playground.html").read_text(encoding="utf-8")

    def test_the_panel_and_its_tab_are_in_the_markup(self):
        page = self.page()
        for needle in ('id="tab-graph"', 'id="graph-status"',
                       'class="kg-pane" id="graph"', "आलेखः · kāraka graph"):
            self.assertIn(needle, page)

    def test_the_renderer_is_inlined_from_its_own_files(self):
        page = self.page()
        css = (ROOT / "docs" / "playground_graph.css").read_text(encoding="utf-8")
        self.assertTrue(css.strip() in page,
                        "playground_graph.css is stale in the page "
                        "— run python docs/build_playground.py")
        from vaak.tokens import KARAKA_ORDER, KARAKA_VIBHAKTI
        js = ((ROOT / "docs" / "playground_graph.js").read_text(encoding="utf-8")
              .replace("__KARAKA_ORDER__",
                       json.dumps(list(KARAKA_ORDER), ensure_ascii=False))
              .replace("__KARAKA_TABLE__",
                       json.dumps({r: KARAKA_VIBHAKTI[r] for r in KARAKA_ORDER},
                                  ensure_ascii=False)))
        self.assertTrue(js.strip() in page,
                        "playground_graph.js is stale in the page "
                        "— run python docs/build_playground.py")

    def test_the_legend_comes_from_the_language_not_a_copy(self):
        """The six roles and their vibhakti are stated in vaak/tokens.py. The
        page is handed that table rather than repeating it, because a legend
        that drifts from the analyser teaches the wrong grammar."""
        from vaak.tokens import KARAKA_ORDER, KARAKA_VIBHAKTI
        page = self.page()
        self.assertNotIn("__KARAKA_ORDER__", page)
        self.assertNotIn("__KARAKA_TABLE__", page)
        self.assertIn(json.dumps(list(KARAKA_ORDER), ensure_ascii=False), page)
        self.assertIn(json.dumps({r: KARAKA_VIBHAKTI[r] for r in KARAKA_ORDER},
                                 ensure_ascii=False), page)

    def test_the_engine_in_the_page_answers_alekhah(self):
        """The panel asks the engine for `--आलेखः`; an engine built before the
        flag existed would leave the tab permanently blank."""
        self.assertIn("--आलेखः", self.page())


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

class TestErrorStream(unittest.TestCase):
    """दोषलिख writes to stderr. Without it a program cannot separate its
    diagnostics from its output, and piping one Vāk program into another
    would interleave warnings with data."""

    PROGRAM = ('मुद्रय "फलम्"।\n'
               'दोषलिख("सूचना")।')

    def test_it_goes_to_stderr_not_stdout(self):
        out, err = io.StringIO(), io.StringIO()
        import contextlib
        with redirect_stdout(out), contextlib.redirect_stderr(err):
            run_source(self.PROGRAM, "प.vak")
        self.assertEqual(out.getvalue().strip(), "फलम्")
        self.assertEqual(err.getvalue().strip(), "सूचना")

    def test_every_engine_separates_the_streams_the_same_way(self):
        """The five-engine rule reaches the streams too: it is not enough that
        each engine prints the right bytes, they must print them to the right
        place."""
        path = pathlib.Path(tempfile.mkdtemp()) / "प.vak"
        path.write_text(self.PROGRAM, encoding="utf-8")
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        for flags in ([], ["--vm"], ["--self"]):
            with self.subTest(engine=" ".join(flags) or "interpreter"):
                done = subprocess.run(
                    [sys.executable, "-m", "vaak", *flags, str(path)],
                    capture_output=True, cwd=str(ROOT), env=env)
                self.assertEqual(done.stdout.decode("utf-8").strip(), "फलम्")
                self.assertEqual(done.stderr.decode("utf-8").strip(), "सूचना")

    def test_it_is_documented_and_known_to_every_engine(self):
        from vaak.builtins import BUILTIN_DOCS
        self.assertIn("दोषलिख", {b[0] for b in BUILTIN_DOCS})
        for f in ("स्वयंसिद्धिः/अर्थविश्लेषकः.vak",
                  "स्वयंसिद्धिः/संकलकः.vak",
                  "native/antarnihitani.c"):
            with self.subTest(file=f):
                text = (ROOT / f).read_text(encoding="utf-8")
                self.assertIn("दोषलिख", text,
                              f"{f} does not know about दोषलिख")


class TestBitOperations(unittest.TestCase):
    """कणगणितम् — bit operations as built-in functions rather than operators,
    because ^ is already exponentiation in Vāk and six new operators would
    need tokens and precedence in two parsers and three machines."""

    def run_vak(self, src: str) -> str:
        buf = io.StringIO()
        with redirect_stdout(buf):
            run_source(src, "प.vak")
        return buf.getvalue().strip()

    def test_the_six_operations(self):
        cases = [("प्रतिच्छेदः(१२, १०)", 12 & 10),
                 ("संयोगः(१२, १०)", 12 | 10),
                 ("वियोगः(१२, १०)", 12 ^ 10),
                 ("पूरकः(१२)", ~12),
                 ("वामसारः(१, ४)", 1 << 4),
                 ("दक्षिणसारः(१६, २)", 16 >> 2)]
        for expr, want in cases:
            with self.subTest(expression=expr):
                self.assertEqual(self.run_vak(f"मुद्रय {expr}।"), str(want))

    def test_complement_is_arbitrary_precision_not_width_limited(self):
        """Integers are signed and unbounded, so ~n is -(n+1) as in Python,
        not a flip within a fixed width as in C. Worth pinning down: it is the
        one bit operation whose answer depends on that choice."""
        self.assertEqual(self.run_vak("मुद्रय पूरकः(०)।"), "-1")
        self.assertEqual(self.run_vak("मुद्रय पूरकः(-१)।"), "0")

    def test_shifting_past_64_bits_does_not_wrap(self):
        self.assertEqual(self.run_vak("मुद्रय वामसारः(१, ७०)।"), str(1 << 70))

    def test_a_negative_shift_is_an_error(self):
        with self.assertRaises(RuntimeVakError):
            self.run_vak("मुद्रय वामसारः(१, -१)।")

    def test_a_non_integer_is_an_error(self):
        for expr in ('प्रतिच्छेदः("क", १)', "संयोगः(१.५, १)", "पूरकः(सत्य)"):
            with self.subTest(expression=expr):
                with self.assertRaises(RuntimeVakError):
                    self.run_vak(f"मुद्रय {expr}।")

    def test_every_engine_computes_them_alike(self):
        """Every engine, not every file.

        This began as a grep of three source files for each name. It passed,
        and all six of these were missing from यन्त्रम्.vak — the engine the
        grep did not list. Reading source proves a name was typed somewhere;
        only running it proves an engine can do the arithmetic.

        TestEveryEngineKnowsEveryBuiltin generalises this to all 46.
        """
        for expr, want in [("प्रतिच्छेदः(१२, १०)", 12 & 10),
                           ("संयोगः(१२, १०)", 12 | 10),
                           ("वियोगः(१२, १०)", 12 ^ 10),
                           ("पूरकः(१२)", ~12),
                           ("वामसारः(१, ४)", 1 << 4),
                           ("दक्षिणसारः(१६, २)", 16 >> 2)]:
            source = f"मुद्रय {expr}।"
            buf = io.StringIO()
            with redirect_stdout(buf):
                run_with_vak(source)
            for engine, printed in [("tree", output(source)),
                                    ("vm", vm_output(source)),
                                    ("यन्त्रम्.vak", buf.getvalue().strip())]:
                with self.subTest(expression=expr, engine=engine):
                    self.assertEqual(printed, str(want))


# A signature whose defaulted करणम् sits *between* two required roles, so the
# call that drops it could not be written with positional defaults at all.
WRITE_WITH = (
    'कार्यम् लिख(कर्ता शब्दः क, करणम् शब्दः स = "लेखन्या", कर्म शब्दः ग) : शब्दः {\n'
    '    प्रत्यागच्छ क + " " + स + " " + ग।\n'
    "}\n"
    'मुद्रय लिख(कर्ता: "कालिदासः", कर्म: "मेघदूतम्")।'
)


class TestDefaultArguments(unittest.TestCase):
    """मूलमूल्यानि — a parameter that need not be stated.

    अनुक्तम् कारकम्: Sanskrit does not require every kāraka to appear.
    देवदत्तः पचति is a whole sentence naming neither the करणम् nor the कर्म.
    A parameter with a default is the same thing — the role exists, and this
    call does not state it.
    """

    LIST_FILTER = (
        "कार्यम् छानय(अपादानम् सूची संग्रहः, करणम् किमपि परीक्षा = शून्य) : सूची {\n"
        "    यदि (परीक्षा == शून्य) { प्रत्यागच्छ संग्रहः। }\n"
        "    सूची फलम् = []।\n"
        "    प्रत्येकम् (स अन्तः संग्रहः) { यदि (परीक्षा(स)) { योजय(फलम्, स)। } }\n"
        "    प्रत्यागच्छ फलम्।\n"
        "}\n"
        "मान अ = [१, २, ३, ४]।\n"
    )

    def codes(self, source: str) -> list[str]:
        return [d.code for d in check_source(source).diagnostics if d.fatal]

    def vak_vm_output(self, source: str) -> str:
        buf = io.StringIO()
        with redirect_stdout(buf):
            run_with_vak(source)
        return buf.getvalue().strip()

    def assert_all_engines(self, source: str, expected: str):
        """The invariant the language rests on: one output, every engine."""
        self.assertEqual(output(source), expected, "tree-walker")
        self.assertEqual(vm_output(source), expected, "SanskritVM")
        self.assertEqual(self.vak_vm_output(source), expected, "यन्त्रम्.vak")
        buf = io.StringIO()
        with redirect_stdout(buf):
            VM("<प>").run(compile_with_vak(source, "<प>"))
        self.assertEqual(buf.getvalue().strip(), expected, "compiled by Vāk")

    # ------------------------------------------------------ the plain case
    def test_an_omitted_argument_takes_its_default(self):
        self.assert_all_engines(
            "कार्यम् क(अ, ब = ५) { प्रत्यागच्छ अ + ब। } मुद्रय क(१), क(१, २)।",
            "6 3")

    def test_every_literal_kind_may_be_a_default(self):
        for literal, printed in (("५", "5"), ("-५", "-5"), ("२.५", "2.5"),
                                 ('"क"', "क"), ("सत्य", "सत्य"),
                                 ("असत्य", "असत्य"), ("शून्य", "शून्यम्")):
            with self.subTest(default=literal):
                self.assert_all_engines(
                    "कार्यम् क(ब = " + literal + ") { प्रत्यागच्छ ब। } मुद्रय क()।",
                    printed)

    # ------------------------------------------- अनुक्तम् कारकम्, out of order
    def test_a_karaka_labelled_argument_may_be_omitted(self):
        self.assert_all_engines(
            self.LIST_FILTER + "मुद्रय छानय(अपादानम्: अ)।", "[1, 2, 3, 4]")

    def test_a_default_may_be_dropped_from_anywhere_not_only_the_right(self):
        """The point of doing this with roles rather than positions. A
        positional default can only be dropped from the right; a labelled one
        can be dropped from the middle, which is the freedom the vibhakti
        gives a sentence."""
        self.assert_all_engines(WRITE_WITH, "कालिदासः लेखन्या मेघदूतम्")

    def test_the_role_may_still_be_stated_in_any_order(self):
        self.assert_all_engines(
            self.LIST_FILTER
            + "मुद्रय छानय(करणम्: कार्यम्(क) { प्रत्यागच्छ क > २। }, अपादानम्: अ)।",
            "[3, 4]")

    # -------------------------------------------------------- what is refused
    def test_only_a_literal_may_be_a_default(self):
        """Deliberately narrow. A literal costs nothing to rebuild per call,
        so Python's mutable-default trap cannot arise and no engine has to
        evaluate code while binding arguments."""
        for bad in ("[]", "{}", "१ + १", "क()", "अ"):
            with self.subTest(default=bad):
                with self.assertRaises(ParseError):
                    parse(tokenize("कार्यम् क(ब = " + bad + ") { प्रत्यागच्छ ब। }"))

    def test_a_default_may_not_precede_a_required_parameter(self):
        with self.assertRaises(ParseError):
            parse(tokenize("कार्यम् क(अ = १, ब) { प्रत्यागच्छ ब। }"))

    def test_a_default_is_checked_against_the_declared_type(self):
        self.assertEqual(self.codes('कार्यम् क(पूर्णाङ्कः ब = "अ") { प्रत्यागच्छ ब। }'),
                         ["प्रकारदोषः"])
        self.assertEqual(self.codes("कार्यम् क(पूर्णाङ्कः ब = ५) { प्रत्यागच्छ ब। }"), [])
        self.assertEqual(self.codes("कार्यम् क(किमपि ब = शून्य) { प्रत्यागच्छ ब। }"), [])

    def test_arity_became_a_range(self):
        src = "कार्यम् क(अ, ब = ५) { प्रत्यागच्छ अ + ब। }\n"
        self.assertEqual(self.codes(src + "मुद्रय क()।"), ["प्राचलदोषः"])
        self.assertEqual(self.codes(src + "मुद्रय क(१, २, ३)।"), ["प्राचलदोषः"])
        self.assertEqual(self.codes(src + "मुद्रय क(१)।"), [])

    def test_the_range_is_shown_as_least_to_total(self):
        diagnostics = check_source(
            "कार्यम् क(अ, ब = ५) { प्रत्यागच्छ अ + ब। } मुद्रय क()।").diagnostics
        self.assertIn("1–2", diagnostics[0].message)

    def test_a_missing_role_names_itself(self):
        """The diagnostic has to say *which* kāraka was not supplied — with
        roles free to appear in any order, position cannot tell the reader."""
        source = self.LIST_FILTER + "मुद्रय छानय(करणम्: शून्य)।"
        for name, engine in (("tree", output), ("vm", vm_output),
                             ("यन्त्रम्.vak", self.vak_vm_output)):
            with self.subTest(engine=name):
                with self.assertRaises(RuntimeVakError) as caught:
                    engine(source)
                self.assertIn("न्यूनाः प्राचलाः: अपादानम्", str(caught.exception))

    # ------------------------------------------------------------ round trip
    def test_the_default_survives_the_kosha(self):
        """कोशः is how the Vāk-written compiler and the Python VM exchange a
        chunk. A default dropped in that exchange would show up only as a
        wrong answer, far from its cause."""
        source = 'कार्यम् क(पूर्णाङ्कः ब = ५, शब्दः स = "अ") { प्रत्यागच्छ ब। }'
        mine = chunk_to_kosha(compile_program(parse(tokenize(source))))
        theirs = chunk_to_kosha(compile_with_vak(source, "<वाक्>"))
        self.assertEqual(mine, theirs)
        self.assertIn("मूलमूल्यम्", repr(mine))


@unittest.skipIf(GCC is None, "C-संकलकः न प्राप्तः / no C compiler available")
class TestDefaultArgumentsNatively(unittest.TestCase):
    """The C runtime rebuilds a default from the literal stored in its
    Prachala rather than carrying a value, so it is the engine where a
    divergence would appear first."""

    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp(prefix="vak-mula-"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def native_output(self, source: str, name: str = "mula") -> str:
        path = self.dir / (name + ".vak")
        path.write_text(source, encoding="utf-8")
        exe = build_executable(source, path, self.dir)
        proc = subprocess.run([str(exe.resolve())], capture_output=True)
        self.assertEqual(proc.returncode, 0,
                         proc.stderr.decode("utf-8", "replace")[:400])
        return proc.stdout.decode("utf-8", "replace").replace("\r\n", "\n").strip()

    def test_an_omitted_argument_takes_its_default(self):
        self.assertEqual(
            self.native_output(
                "कार्यम् क(अ, ब = ५) { प्रत्यागच्छ अ + ब। } मुद्रय क(१), क(१, २)।"),
            "6 3")

    def test_every_literal_kind_rebuilds(self):
        self.assertEqual(
            self.native_output(
                'कार्यम् क(अ = ५, ब = २.५, स = "क", द = सत्य, य = शून्य) '
                "{ प्रत्यागच्छ [अ, ब, स, द, य]। } मुद्रय क()।", "sarve"),
            '[5, 2.5, "क", सत्य, शून्यम्]')

    def test_a_role_dropped_from_the_middle(self):
        self.assertEqual(self.native_output(WRITE_WITH, "madhye"),
                         "कालिदासः लेखन्या मेघदूतम्")


class TestEveryEngineKnowsEveryBuiltin(unittest.TestCase):
    """पञ्चयन्त्राणि, एकः कोशः — five engines, one set of built-ins.

    This class exists because a textual version of it did not work. The bit
    operations shipped with a test that grepped three source files for each
    name; it passed, and all seven built-ins from that commit were missing
    from यन्त्रम्.vak — the one engine the grep did not name. Four engines had
    them and the fifth did not, which is precisely the divergence the whole
    project is built to prevent.

    So neither check here reads source. One resolves every name on every
    engine, the other calls a builtin on every engine and requires the answers
    to match. A file the author forgot cannot be forgotten twice.
    """

    #: Built-ins that cannot be called in a test: they read stdin, touch the
    #: filesystem, return the time or a random number, or raise by design.
    #: They are still covered by the name-resolution test below.
    IMPURE = {
        "पठ", "काल", "यादृच्छिक", "दोष", "प्राचलाः", "खण्डम्_चालय",
        "सञ्चिकापठ", "सञ्चिकापङ्क्तयः", "सञ्चिकालिख", "सञ्चिकायोजय",
        "सञ्चिकास्ति", "सञ्चिकानाशय", "निर्देशिका", "लिख", "दोषलिख",
    }

    #: One call per built-in, chosen to give a printable answer.
    CALLS = {
        "प्रतिच्छेदः": "प्रतिच्छेदः(१२, १०)", "संयोगः": "संयोगः(१२, १०)",
        "वियोगः": "वियोगः(१२, १०)", "पूरकः": "पूरकः(१२)",
        "वामसारः": "वामसारः(१, ४)", "दक्षिणसारः": "दक्षिणसारः(१६, २)",
        "लक्षणम्": "लक्षणम्(दीर्घता).नाम", "प्रयुज्": 'प्रयुज्(दीर्घता, ["अआ"])',
        "प्रकार": 'प्रकार("अ")', "संख्या": 'संख्या("१२")', "शब्द": "शब्द(१२)",
        "देवनागरी": "देवनागरी(१२)", "दीर्घता": "दीर्घता([१, २, ३])",
        "सूची": 'सूची("अआ")', "परास": "परास(३)", "योजय": "योजय([१], २)",
        "निष्कास": "निष्कास([१, २], ०)", "अस्ति": "अस्ति([१, २], २)",
        "कुञ्जिकाः": 'कुञ्जिकाः({"अ": १})', "मूल्यानि": 'मूल्यानि({"अ": १})',
        "क्रम": "क्रम([३, १, २])", "विपर्यय": "विपर्यय([१, २])",
        "विभज": 'विभज("अ,ब", ",")', "संयोज": 'संयोज(["अ", "ब"], "-")',
        "योग": "योग([१, २, ३])", "न्यूनतम": "न्यूनतम([३, १])",
        "अधिकतम": "अधिकतम([३, १])", "मूल": "मूल(१६)", "पूर्ण": "पूर्ण(३.७)",
        "अक्षराणि": 'अक्षराणि("वाक्")', "संकेतः": 'संकेतः("अ")',
        "वर्णः": "वर्णः(२३०५)", "अंशः": "अंशः([१, २, ३], १)",
        "मुद्रय": None,          # a statement, not a callable name
    }

    def engines(self, source: str) -> dict[str, str]:
        """What each Python-hosted engine prints. The native binary is covered
        by the name-resolution test, which compiles once for all of them."""
        out = {"tree": output(source), "vm": vm_output(source)}
        buf = io.StringIO()
        with redirect_stdout(buf):
            run_with_vak(source)
        out["यन्त्रम्.vak"] = buf.getvalue().strip()
        buf = io.StringIO()
        with redirect_stdout(buf):
            VM("<प>").run(compile_with_vak(source, "<प>"))
        out["compiled by Vāk"] = buf.getvalue().strip()
        return out

    def test_every_name_resolves_on_every_engine(self):
        """Binding a built-in to a name proves each engine's *front end* knows
        it — the analyser accepts it and the compiler emits a reference rather
        than an undefined name. Built-ins are first-class values, so this needs
        no argument for any of them and one program covers all 46 at once.

        It does not prove the name can be *called*: the compiler settles that a
        name is a built-in and emits आ_अन्तर्निहितम्_गृहाण, so the runtime
        dispatch is never consulted here. That is what the differential below
        is for, and removing one entry from यन्त्रम्.vak's dispatch was used to
        confirm it fails when it should."""
        names = [n for n, _roman, _doc in BUILTIN_DOCS if n != "मुद्रय"]
        source = "\n".join(f"मान न्_{i} = {name}। मुद्रय प्रकार(न्_{i})।"
                           for i, name in enumerate(names))
        expected = "\n".join(["कार्यम्"] * len(names))
        for engine, printed in self.engines(source).items():
            with self.subTest(engine=engine):
                self.assertEqual(printed, expected)

    def test_every_pure_builtin_answers_alike_on_every_engine(self):
        """Resolving a name is not the same as being able to call it: a
        built-in can sit in the name table and be missing from the dispatch.
        This calls one and requires the engines to agree, which is the
        project's own standard of proof."""
        for name, _roman, _doc in BUILTIN_DOCS:
            if name in self.IMPURE or self.CALLS.get(name) is None:
                continue
            with self.subTest(builtin=name):
                answers = self.engines(f"मुद्रय {self.CALLS[name]}।")
                distinct = set(answers.values())
                self.assertEqual(len(distinct), 1,
                                 f"{name}: engines disagree — {answers}")

    def test_a_builtin_answers_to_its_roman_spelling_on_every_engine(self):
        """Every built-in has an ASCII spelling so the language can be written
        without a Devanagari keyboard. That worked in three engines and not in
        the other two, for every built-in, until the compilers were made to
        emit the canonical name: the C runtime and यन्त्रम्.vak key their tables
        in Devanagari, and were being handed `dirghata`.

        Romanised *keywords* were never affected — the lexer folds those into
        one token. Built-in names are ordinary identifiers and get no fold.
        """
        for roman, devanagari in [("dirghata", "दीर्घता"), ("purakah", "पूरकः"),
                                  ("yoga", "योग"), ("vamasarah", "वामसारः")]:
            with self.subTest(builtin=roman):
                call = {"dirghata": '([१, २, ३])', "purakah": "(१२)",
                        "yoga": "([१, २, ३])", "vamasarah": "(१, ४)"}[roman]
                answers = self.engines(f"मुद्रय {roman}{call}।")
                answers.update(self.engines(f"मुद्रय {devanagari}{call}।"))
                self.assertEqual(len(set(answers.values())), 1,
                                 f"{roman}/{devanagari}: {answers}")

    def test_the_declared_name_tables_have_not_drifted(self):
        """Two Vāk files declare their own list of built-in names, and the two
        lists are deliberately different shapes:

        संकलकः.vak matches names as the programmer typed them, so it must hold
        *both* spellings — and it is paired, Devanagari then roman, which is
        what lets it map either to the canonical one without a second table.

        यन्त्रम्.vak only ever sees what the compiler emitted, and the compiler
        emits the canonical name, so Devanagari alone is correct there. Listing
        roman names in it would be dead weight that looked like coverage.

        Read with Vāk's own parser rather than a regex: this checks a data table
        against its source of truth, not behaviour inferred from text.
        """
        devanagari = {n for n, _r, _d in BUILTIN_DOCS}
        roman = {r for _n, r, _d in BUILTIN_DOCS}

        def declared(stem: str) -> list[str]:
            path = ROOT / "स्वयंसिद्धिः" / f"{stem}.vak"
            program = parse(tokenize(path.read_text(encoding="utf-8"), str(path)))
            for statement in program.statements:
                if getattr(statement, "name", None) == "अन्तर्निहितनामानि":
                    return [e.value for e in statement.value.elements]
            self.fail(f"अन्तर्निहितनामानि not found in {path.name}")

        compiler = declared("संकलकः")
        self.assertEqual(devanagari - set(compiler), set(), "संकलकः.vak: missing")
        self.assertEqual(roman - set(compiler), set(), "संकलकः.vak: missing roman")
        self.assertEqual(set(compiler) - devanagari - roman, set(),
                         "संकलकः.vak: named but not a built-in")
        # the pairing is load-bearing: अन्तर्निहितमूलनाम reads the head of a pair
        self.assertEqual(len(compiler) % 2, 0, "संकलकः.vak: table is not paired")
        for i in range(0, len(compiler), 2):
            with self.subTest(pair=compiler[i]):
                self.assertIn(compiler[i], devanagari)
                self.assertIn(compiler[i + 1], roman)
                self.assertIn((compiler[i], compiler[i + 1]),
                              {(n, r) for n, r, _d in BUILTIN_DOCS})

        machine = set(declared("यन्त्रम्"))
        self.assertEqual(devanagari - machine, set(), "यन्त्रम्.vak: missing")
        self.assertEqual(machine & roman, set(),
                         "यन्त्रम्.vak: roman names here are dead weight")
        self.assertEqual(machine - devanagari - {"मुद्रय"}, set(),
                         "यन्त्रम्.vak: named but not a built-in")

    def test_the_call_table_covers_every_pure_builtin(self):
        """The guard on the guard. A built-in added without an entry here
        would silently skip the differential above — which is the same shape
        of hole the grep had."""
        uncovered = [n for n, _r, _d in BUILTIN_DOCS
                     if n not in self.IMPURE and n not in self.CALLS]
        self.assertEqual(uncovered, [],
                         "add a call for these to CALLS, or list them in IMPURE")


@unittest.skipIf(GCC is None, "C-संकलकः न प्राप्तः / no C compiler available")
class TestNativeKnowsEveryBuiltin(unittest.TestCase):
    """The fifth engine, checked the same way — separately because it compiles."""

    def test_every_name_resolves_natively(self):
        names = [n for n, _roman, _doc in BUILTIN_DOCS if n != "मुद्रय"]
        source = "\n".join(f"मान न्_{i} = {name}। मुद्रय प्रकार(न्_{i})।"
                           for i, name in enumerate(names))
        directory = Path(tempfile.mkdtemp(prefix="vak-builtins-"))
        try:
            path = directory / "sarve.vak"
            path.write_text(source, encoding="utf-8")
            exe = build_executable(source, path, directory)
            proc = subprocess.run([str(exe.resolve())], capture_output=True)
            self.assertEqual(proc.returncode, 0,
                             proc.stderr.decode("utf-8", "replace")[:400])
            printed = proc.stdout.decode("utf-8", "replace").replace("\r\n", "\n")
            self.assertEqual(printed.strip(), "\n".join(["कार्यम्"] * len(names)))
        finally:
            shutil.rmtree(directory, ignore_errors=True)


class TestApplyAndReflection(unittest.TestCase):
    """प्रयुज् च लक्षणम् — building a call, and asking what a कार्यम् wants.

    Until these, a Vāk program could not forward an argument list, write a
    wrapper around an arbitrary function, or ask a function what roles it
    declares. All three are ordinary things to want, and none of them is about
    Sanskrit: the language simply had no apply and no reflection.
    """

    FILTER = ('कार्यम् छानय(अपादानम् सूची संग्रहः, करणम् किमपि परीक्षा = शून्य) : सूची {\n'
              '    प्रत्यागच्छ संग्रहः।\n'
              '}\n')
    WRITE = ('कार्यम् लिखतु(कर्ता शब्दः क, करणम् शब्दः स = "लेखन्या",\n'
             '              कर्म शब्दः ग) : शब्दः {\n'
             '    प्रत्यागच्छ क + "|" + ग + "|" + स।\n'
             '}\n')

    def engines(self, source: str) -> dict[str, str]:
        out = {"tree": output(source), "vm": vm_output(source)}
        buf = io.StringIO()
        with redirect_stdout(buf):
            run_with_vak(source)
        out["यन्त्रम्.vak"] = buf.getvalue().strip()
        buf = io.StringIO()
        with redirect_stdout(buf):
            VM("<प>").run(compile_with_vak(source, "<प>"))
        out["compiled by Vāk"] = buf.getvalue().strip()
        return out

    def assert_agree(self, source: str, expected: str):
        for engine, printed in self.engines(source).items():
            with self.subTest(engine=engine):
                self.assertEqual(printed, expected)

    # ------------------------------------------------------------- प्रयुज्
    def test_a_list_is_applied_positionally(self):
        self.assert_agree("कार्यम् य(अ, ब, स) { प्रत्यागच्छ अ + ब + स। }\n"
                          "मुद्रय प्रयुज्(य, [१, २, ३])।", "6")

    def test_a_kosha_is_applied_by_role(self):
        self.assert_agree(self.WRITE + 'मुद्रय प्रयुज्(लिखतु, '
                          '{"कर्ता": "क", "कर्म": "ग"})।', "क|ग|लेखन्या")

    def test_a_role_key_may_use_any_of_its_spellings(self):
        """कारकनामानि accepts three spellings per role in source, so the keys
        of an applied कोशः must accept them too — otherwise a program written
        in ASCII could not use this form at all."""
        for keys in ('{"कर्ता": "क", "कर्म": "ग"}',
                     '{"karta": "क", "karma": "ग"}',
                     '{"कर्मन्": "ग", "कर्ता": "क"}'):
            with self.subTest(keys=keys):
                self.assert_agree(self.WRITE + f"मुद्रय प्रयुज्(लिखतु, {keys})।",
                                  "क|ग|लेखन्या")

    def test_a_defaulted_role_may_be_left_out_of_the_kosha(self):
        self.assert_agree(self.FILTER + 'मुद्रय प्रयुज्(छानय, '
                          '{"अपादानम्": [१, २]})।', "[1, 2]")

    def test_a_builtin_can_be_applied(self):
        # दीर्घता counts code points, so वाक् is व ा क ् — four, not two aksharas
        self.assert_agree('मुद्रय प्रयुज्(दीर्घता, ["वाक्"])।', "4")

    def test_an_inline_closure_can_be_applied(self):
        """The closure exists only on the stack. The C runtime freed it the
        moment the call began and then read it — see the native test below."""
        self.assert_agree("मुद्रय प्रयुज्(कार्यम्(अ, ब) { प्रत्यागच्छ अ * ब। }, "
                          "[६, ७])।", "42")

    def test_a_wrapper_can_forward_an_argument_list(self):
        """The thing that was impossible: one function standing in front of
        another without knowing how many arguments it takes."""
        self.assert_agree(
            "कार्यम् गणयित्वा(कार्यम् क, सूची अर्घाः) {\n"
            '    मुद्रय "आह्वानम्:", दीर्घता(अर्घाः)।\n'
            "    प्रत्यागच्छ प्रयुज्(क, अर्घाः)।\n"
            "}\n"
            "कार्यम् य(अ, ब, स) { प्रत्यागच्छ अ + ब + स। }\n"
            "मुद्रय गणयित्वा(य, [१, २, ३])।", "आह्वानम्: 3\n6")

    # ------------------------------------------------------ what it refuses
    def test_a_key_that_is_not_a_karaka_is_refused(self):
        for engine, run in [("tree", output), ("vm", vm_output)]:
            with self.subTest(engine=engine):
                with self.assertRaises(RuntimeVakError) as caught:
                    run(self.FILTER + 'मुद्रय प्रयुज्(छानय, {"नाम": १})।')
                self.assertIn("इति कारकम् न", str(caught.exception))

    def test_the_bundle_must_be_a_list_or_a_dictionary(self):
        with self.assertRaises(RuntimeVakError):
            output("कार्यम् क(अ) { प्रत्यागच्छ अ। } मुद्रय प्रयुज्(क, ५)।")

    def test_it_must_be_called_directly(self):
        """प्रयुज् becomes one instruction, and an instruction cannot be
        handed around as a value. Three engines could have supported the
        indirect form and two could not, so all five refuse it."""
        source = ("कार्यम् क(अ) { प्रत्यागच्छ अ। }\n"
                  "मान ग = प्रयुज्।\n"
                  "मुद्रय ग(क, [१])।")
        for engine, run in [("tree", output), ("vm", vm_output)]:
            with self.subTest(engine=engine):
                with self.assertRaises(RuntimeVakError) as caught:
                    run(source)
                self.assertIn("साक्षात् एव आह्वातव्यम्", str(caught.exception))

    def test_a_local_named_prayuj_shadows_the_form(self):
        self.assert_agree(
            "कार्यम् बाह्यम्() {\n"
            '    मान प्रयुज् = कार्यम्(अ, ब) { प्रत्यागच्छ "आच्छादितम्"। }।\n'
            "    प्रत्यागच्छ प्रयुज्(१, २)।\n"
            "}\n"
            "मुद्रय बाह्यम्()।", "आच्छादितम्")

    # ------------------------------------------------------------ लक्षणम्
    def test_a_function_reports_its_parameters_and_roles(self):
        source = self.FILTER + ("कोशः ल = लक्षणम्(छानय)।\n"
                                "मुद्रय ल.नाम, ल.प्राचलसंख्या, ल.प्रतिफलप्रकारः।\n"
                                "प्रत्येकम् (प्रा अन्तः ल.प्राचलाः) {\n"
                                "    मुद्रय प्रा.कारकम्, प्रा.प्रकारः, प्रा.नाम, प्रा.मूलमस्ति।\n"
                                "}")
        self.assert_agree(source,
                          "छानय 2 सूची\n"
                          "अपादानम् सूची संग्रहः असत्य\n"
                          "करणम् किमपि परीक्षा सत्य")

    def test_a_default_comes_back_with_the_parameter(self):
        self.assert_agree(
            'कार्यम् क(शब्दः स = "नमस्ते") { प्रत्यागच्छ स। }\n'
            "मुद्रय लक्षणम्(क).प्राचलाः[०].मूलमूल्यम्।", "नमस्ते")

    def test_a_builtin_reports_its_arity_and_nothing_it_cannot_know(self):
        """किमपि for the return type, deliberately: that is the analyser's
        knowledge, and two of the five engines have no way to reach it.
        Reporting it from three and not the others would be a divergence."""
        self.assert_agree("कोशः ल = लक्षणम्(दीर्घता)।\n"
                          "मुद्रय ल.नाम, ल.अन्तर्निहितम्, ल.प्राचलसंख्या, "
                          "ल.प्रतिफलप्रकारः, दीर्घता(ल.प्राचलाः)।",
                          "दीर्घता सत्य 1 किमपि 0")

    def test_reflection_and_apply_compose(self):
        """The pair earns its place together: read the roles a function wants,
        then build the call from them."""
        self.assert_agree(
            self.WRITE
            + "कोशः अर्घाः = {}।\n"
              "प्रत्येकम् (प्रा अन्तः लक्षणम्(लिखतु).प्राचलाः) {\n"
              "    यदि (न प्रा.मूलमस्ति) { अर्घाः[प्रा.कारकम्] = प्रा.नाम। }\n"
              "}\n"
              "मुद्रय प्रयुज्(लिखतु, अर्घाः)।", "क|ग|लेखन्या")

    def test_lakshanam_refuses_what_is_not_a_function(self):
        with self.assertRaises(RuntimeVakError):
            output("मुद्रय लक्षणम्(५)।")


@unittest.skipIf(GCC is None, "C-संकलकः न प्राप्तः / no C compiler available")
class TestApplyNatively(unittest.TestCase):
    """The C runtime, where a closure's lifetime is managed by hand."""

    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp(prefix="vak-prayuj-"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def native_output(self, source: str, name: str = "prayuj") -> str:
        path = self.dir / f"{name}.vak"
        path.write_text(source, encoding="utf-8")
        exe = build_executable(source, path, self.dir)
        proc = subprocess.run([str(exe.resolve())], capture_output=True)
        self.assertEqual(proc.returncode, 0,
                         f"exit {proc.returncode}: "
                         + proc.stderr.decode("utf-8", "replace")[:400])
        return proc.stdout.decode("utf-8", "replace").replace("\r\n", "\n").strip()

    def test_a_closure_that_lives_only_on_the_stack_survives_its_own_call(self):
        """A use-after-free, and it predates प्रयुज्: the frame kept the
        Avarana pointer without taking a reference, so an आवरणम् held nowhere
        else was freed as the call began. कार्यम्(अ){...}(१) segfaulted on the
        ordinary call path too — प्रयुज् only made it easy to hit."""
        self.assertEqual(
            self.native_output("मुद्रय कार्यम्(अ, ब) { प्रत्यागच्छ अ * ब। }(६, ७)।",
                               "anamaka"),
            "42")
        self.assertEqual(
            self.native_output("मुद्रय प्रयुज्(कार्यम्(अ, ब) { प्रत्यागच्छ अ * ब। }, "
                               "[६, ७])।", "prayukta"),
            "42")

    def test_both_forms_natively(self):
        self.assertEqual(
            self.native_output(
                'कार्यम् ल(कर्ता शब्दः क, करणम् शब्दः स = "लेखन्या",\n'
                '          कर्म शब्दः ग) : शब्दः { प्रत्यागच्छ क + "|" + ग + "|" + स। }\n'
                "कार्यम् य(अ, ब, स) { प्रत्यागच्छ अ + ब + स। }\n"
                "मुद्रय प्रयुज्(य, [१, २, ३])।\n"
                'मुद्रय प्रयुज्(ल, {"karta": "क", "कर्म": "ग"})।', "ubhau"),
            "6\nक|ग|लेखन्या")

    def test_reflection_natively(self):
        self.assertEqual(
            self.native_output(
                "कार्यम् छानय(अपादानम् सूची स, करणम् किमपि प = शून्य) : सूची "
                "{ प्रत्यागच्छ स। }\n"
                "मुद्रय लक्षणम्(छानय).प्राचलाः[०].कारकम्, "
                "लक्षणम्(छानय).प्राचलाः[१].मूलमस्ति।", "lakshana"),
            "अपादानम् सत्य")


class TestDoWhile(unittest.TestCase):
    """कुरु { ... } यावत् (शर्तः)। — the body first, the question after.

    The one loop shape Vāk lacked. It needed no new instruction: a यावत् loop
    already compiles to JUMP_IF_FALSE and JUMP_BACK, and a post-test loop is
    those same two in the other order. That is why the C runtime is untouched
    by this feature — there was no opcode for it to learn.
    """

    def engines(self, source: str) -> dict[str, str]:
        out = {"tree": output(source), "vm": vm_output(source)}
        buf = io.StringIO()
        with redirect_stdout(buf):
            run_with_vak(source)
        out["यन्त्रम्.vak"] = buf.getvalue().strip()
        buf = io.StringIO()
        with redirect_stdout(buf):
            VM("<प>").run(compile_with_vak(source, "<प>"))
        out["compiled by Vāk"] = buf.getvalue().strip()
        return out

    def assert_agree(self, source: str, expected: str):
        for engine, printed in self.engines(source).items():
            with self.subTest(engine=engine):
                self.assertEqual(printed, expected)

    def test_the_body_runs_before_the_test(self):
        self.assert_agree("मान क = ०।\n"
                          "कुरु { क = क + १। } यावत् (क < ५)।\n"
                          "मुद्रय क।", "5")

    def test_it_runs_once_even_when_the_test_is_false(self):
        """The whole point of the construct, and what यावत् cannot do."""
        self.assert_agree("मान क = ०।\n"
                          "कुरु { क = क + १०। } यावत् (असत्य)।\n"
                          "मुद्रय क।", "10")
        self.assert_agree("मान क = ०।\n"
                          "यावत् (असत्य) { क = क + १०। }\n"
                          "मुद्रय क।", "0")

    def test_anuvarta_jumps_to_the_test_not_the_top(self):
        """अनुवर्त in a post-test loop must land on the condition. Landing on
        the top of the body instead would skip the test and spin forever, and
        the bytecode makes that an easy mistake — the jump target is the one
        thing the two loop shapes do not share."""
        self.assert_agree("मान क = ०।\nमान योगः = ०।\n"
                          "कुरु {\n"
                          "    क = क + १।\n"
                          "    यदि (क % २ == ०) { अनुवर्त। }\n"
                          "    योगः = योगः + क।\n"
                          "} यावत् (क < ६)।\n"
                          "मुद्रय क, योगः।", "6 9")

    def test_virama_leaves_the_loop(self):
        self.assert_agree("मान क = ०।\n"
                          "कुरु { क = क + १। यदि (क == ३) { विरम। } } यावत् (सत्य)।\n"
                          "मुद्रय क।", "3")

    def test_they_nest(self):
        self.assert_agree("मान फलम् = \"\"।\nमान इ = ०।\n"
                          "कुरु {\n"
                          "    इ = इ + १।\n"
                          "    मान ज = ०।\n"
                          "    कुरु { ज = ज + १। } यावत् (ज < २)।\n"
                          "    फलम् = फलम् + शब्द(इ) + \":\" + शब्द(ज) + \" \"।\n"
                          "} यावत् (इ < ३)।\n"
                          "मुद्रय फलम्।", "1:2 2:2 3:2")

    def test_the_ascii_spelling_works(self):
        self.assert_agree("मान क = ०।\n"
                          "kuru { क = क + १। } yavat (क < ४)।\n"
                          "मुद्रय क।", "4")

    def test_the_block_must_be_followed_by_yavat(self):
        with self.assertRaises(ParseError):
            parse(tokenize("कुरु { मुद्रय १। }"))

    def test_virama_outside_any_loop_is_still_caught(self):
        self.assertEqual([d.code for d in check_source("विरम।").diagnostics if d.fatal],
                         ["प्रवाहदोषः"])

    def test_both_front_ends_agree_on_the_tree_and_the_bytecode(self):
        """कुरु adds a field to the यावद्वाक्यम् कोशः, which both parsers must
        write and both compilers must read. A flag one side forgets would show
        up as a loop that tests in the wrong place — not as a crash."""
        source = ("मान क = ०।\n"
                  "कुरु { क = क + १। यदि (क == २) { अनुवर्त। } } यावत् (क < ४)।\n"
                  "यावत् (क < ६) { क = क + १। }\n"
                  "मुद्रय क।")
        self.assertEqual(to_kosha(parse(tokenize(source, "<प>"))),
                         parse_with_vak(source))
        self.assertEqual(
            chunk_to_kosha(compile_program(parse(tokenize(source, "<प>")), "<प>")),
            chunk_to_kosha(compile_with_vak(source, "<प>")))

    def test_kuru_still_lexes_inside_a_longer_name(self):
        """आह्वानम्_कुरु is one identifier in the self-hosted VM. Making कुरु a
        keyword must not split it."""
        self.assert_agree("कार्यम् आह्वानम्_कुरु() { प्रत्यागच्छ ७। }\n"
                          "मुद्रय आह्वानम्_कुरु()।", "7")


@unittest.skipIf(GCC is None, "C-संकलकः न प्राप्तः / no C compiler available")
class TestDoWhileNatively(unittest.TestCase):
    """The C runtime was not changed for this feature. That is the claim, and
    this is what checks it."""

    def test_it_runs_natively_without_a_new_opcode(self):
        directory = Path(tempfile.mkdtemp(prefix="vak-kuru-"))
        try:
            source = ("मान क = ०।\n"
                      "कुरु { क = क + १। यदि (क % २ == ०) { अनुवर्त। } } यावत् (क < ५)।\n"
                      "मान ग = ०।\n"
                      "कुरु { ग = ग + १००। } यावत् (असत्य)।\n"
                      "मुद्रय क, ग।")
            path = directory / "kuru.vak"
            path.write_text(source, encoding="utf-8")
            exe = build_executable(source, path, directory)
            proc = subprocess.run([str(exe.resolve())], capture_output=True)
            self.assertEqual(proc.returncode, 0,
                             proc.stderr.decode("utf-8", "replace")[:400])
            printed = proc.stdout.decode("utf-8", "replace").replace("\r\n", "\n")
            self.assertEqual(printed.strip(), "5 100")
        finally:
            shutil.rmtree(directory, ignore_errors=True)


class TestVersionIsStatedOnce(unittest.TestCase):
    """एकः एव अङ्कः — the version number lives in five files.

    vaak/__init__.py is the source of truth; pyproject.toml decides what pip
    installs, the README prints it in two sample outputs, and the editor
    extension names it. Nothing kept them in step, and a bump is exactly when
    that goes wrong: the wheel would say one thing and --version another.
    """

    def released(self) -> str:
        from vaak import __version__
        return __version__

    def test_pyproject_matches_the_package(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        found = re.search(r'^version = "([^"]+)"', text, re.M)
        self.assertIsNotNone(found, "no version in pyproject.toml")
        self.assertEqual(found.group(1), self.released())

    def test_the_readme_samples_match_the_package(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        quoted = set(re.findall(r"वाक् \(Vāk\) (\d+\.\d+\.\d+)", text))
        self.assertTrue(quoted, "the README quotes no version")
        self.assertEqual(quoted, {self.released()})

    def test_the_extension_readme_matches_the_package(self):
        text = (ROOT / "vscode-vak" / "README.md").read_text(encoding="utf-8")
        quoted = set(re.findall(r"Version (\d+\.\d+\.\d+)\.", text))
        self.assertEqual(quoted, {self.released()})

    def test_the_self_hosted_toolchain_reports_the_package_version(self):
        """स्वयंसिद्धिः/वाक्.vak states its own version, in Devanagari numerals,
        and that is what `--version` prints from every GitHub release binary
        and from the playground. It said ०.११.१ through the whole of 0.12.0,
        because this class looked for ASCII digits and never read the file."""
        text = (ROOT / "स्वयंसिद्धिः" / "वाक्.vak").read_text(encoding="utf-8")
        found = re.search(r'ध्रुव शब्दः रूपम् = "वाक् ([०-९.]+)', text)
        self.assertIsNotNone(found, "वाक्.vak no longer declares रूपम्")
        ascii_ = found.group(1).translate(str.maketrans("०१२३४५६७८९", "0123456789"))
        self.assertEqual(ascii_, self.released())

    def test_the_story_marks_the_current_version_as_released(self):
        """docs/build_story.py distinguishes versions that were cut from
        stages numbered afterwards, and keeps a third mark for work that is
        written but unreleased. Whatever __version__ says must not be sitting
        in that third set."""
        text = (ROOT / "docs" / "build_story.py").read_text(encoding="utf-8")
        pending = re.search(r"^PENDING[^=]*= (.+)$", text, re.M)
        self.assertIsNotNone(pending, "PENDING went missing from the story")
        self.assertNotIn(self.released(), pending.group(1))


class TestWhatTheWheelDoesNotShip(unittest.TestCase):
    """चक्रे यत् नास्ति — the two parts of Vāk a pip install leaves behind.

    pyproject.toml packages only `vaak`, deliberately: the C runtime and the
    Vāk-written toolchain belong to the repository. That is a fine decision
    and it is documented — but it means two of the five engines are simply
    absent from an installed copy, and each has to say so.

    --self said so. --run-native did not: installing vak-lang 0.12.0 into a
    clean virtualenv and running it produced

        cc1.exe: fatal error: .../site-packages/native/yantram.c:
        No such file or directory

    which tells the reader nothing about what to do. Found by installing the
    published wheel rather than by testing the clone, which is the only way
    this class of fault shows up at all.
    """

    def test_a_clone_has_both(self):
        """The guards must be false only when something is genuinely missing —
        if either went true-by-accident here, the tests below would pass
        while proving nothing."""
        from vaak.native import runtime_available
        from vaak.selfhost import bootstrap_available
        self.assertTrue(runtime_available(), "native/*.c missing from the clone")
        self.assertTrue(bootstrap_available(), "स्वयंसिद्धिः missing from the clone")

    def test_the_native_back_end_explains_its_absence(self):
        import vaak.native as native
        original = native.NATIVE_DIR
        native.NATIVE_DIR = pathlib.Path(tempfile.gettempdir()) / "नास्ति-native"
        try:
            self.assertFalse(native.runtime_available())
            with self.assertRaises(VakError) as caught:
                native.build_executable("मुद्रय १।", pathlib.Path("क.vak"))
            message = str(caught.exception)
            self.assertIn("git clone", message)
            self.assertIn("native/*.c", message)
            self.assertNotIn("cc1", message)
        finally:
            native.NATIVE_DIR = original

    def test_the_self_hosted_front_end_explains_its_absence(self):
        import vaak.selfhost as selfhost
        source = inspect.getsource(selfhost)
        self.assertIn("git clone", source,
                      "the स्वयंसिद्धिः guard stopped telling the reader what to do")

    def test_the_packaging_decision_that_makes_those_guards_load_bearing(self):
        """If the wheel ever starts shipping these, the guards become dead
        code and this test should be the thing that says so."""
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('packages = ["vaak"]', text)
        self.assertNotIn("native", text.split("[tool.setuptools.package-data]")[-1])


class TestThePlaygroundEngineIsCurrent(unittest.TestCase):
    """क्रीडाक्षेत्रस्य यन्त्रम् — the engine a visitor actually runs.

    The playground runs Vāk in the browser from one WebAssembly build of the
    self-hosted toolchain. _wasm/ is gitignored, so the engine is committed
    only inlined into docs/playground.html — and that page now carries the
    record of what its engine was built from. These tests read the page, so
    they work on any clone and in CI, where _wasm/ does not exist.

    The engine once fell twelve days behind: it predated default arguments,
    the bit operations, दोषलिख, प्रयुज्, लक्षणम् and कुरु, and the page's own
    samples failed with `')' अपेक्षितम् — किन्तु प्राप्तम् '='`. The first
    check written for it hashed only native/*.c, which is not even all of the
    engine — the Vāk-written toolchain is compiled into it too — and it lived
    in a gitignored file, so it skipped everywhere but one machine.
    """

    PAGE = ROOT / "docs" / "playground.html"

    def engine_module(self):
        sys.path.insert(0, str(ROOT / "docs"))
        import importlib
        return importlib.import_module("engine")      # side-effect free

    def test_the_page_says_what_its_engine_was_built_from(self):
        engine = self.engine_module()
        prints = engine.fingerprint_in_page(self.PAGE.read_text(encoding="utf-8"))
        self.assertIsNotNone(
            prints, "docs/playground.html does not record what its engine was "
                    "built from — build it with docs/build_wasm.py")
        self.assertIn("generated", prints)

    def test_the_engine_is_not_older_than_the_language(self):
        """The fingerprint is of the generated C, which is a deterministic
        function of the Vāk-written toolchain, the compiler, the C emitter and
        the runtime together — so a change to any of them shows up here, and
        a change to none of them cannot."""
        engine = self.engine_module()
        recorded = engine.fingerprint_in_page(self.PAGE.read_text(encoding="utf-8"))
        moved = engine.drift(recorded, engine.fingerprint())
        self.assertEqual(moved, [], "\n".join(
            ["the playground's engine is older than the language it documents — "
             "run `python docs/build_wasm.py` then `python docs/build_playground.py`"]
            + moved))

    def test_the_fingerprint_is_deterministic(self):
        """If generating the C twice gave different text, every build would
        look stale and the check would teach people to ignore it."""
        engine = self.engine_module()
        self.assertEqual(engine.generate_engine_c(), engine.generate_engine_c())

    def test_a_toolchain_change_moves_the_fingerprint(self):
        """The failure the first version of this check had: it could not see
        the Vāk-written toolchain at all."""
        engine = self.engine_module()
        before = engine.fingerprint()
        after = engine.fingerprint(engine.generate_engine_c() + "\n/* a parser change */")
        self.assertNotEqual(before["generated"], after["generated"])
        self.assertTrue(engine.drift(before, after))

    def test_the_documented_samples_only_use_what_the_page_can_run(self):
        page = self.PAGE.read_text(encoding="utf-8")
        found = re.search(r"var SAMPLES = (\{.*?\});\n", page, re.S)
        self.assertIsNotNone(found, "no SAMPLES in the playground")
        for name, source in json.loads(found.group(1)).items():
            with self.subTest(sample=name):
                self.assertEqual(check_source(source).errors, [],
                                 f"the {name} sample does not analyse cleanly")


@unittest.skipIf(shutil.which("node") is None, "node not found — cannot run the page's engine")
class TestThePlaygroundRunsItsOwnSamples(unittest.TestCase):
    """The page's engine, taken out of the page and run under Node exactly as
    the page runs it — a fresh module per run, the standard library written
    into its filesystem, callMain on a path — and held to the Python engine.

    Hashing inputs says whether the engine is current. Only running it says
    whether it works: the rebuild that brought it up to date also exposed a
    runtime fault that no hash could have seen.
    """

    HARNESS = r"""
const path = require("path"), fs = require("fs");
const VakModule = require(path.resolve(process.argv[2]));
const LIBRARY = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
function feeder(text) {
  const bytes = new TextEncoder().encode(text || ""); let i = 0;
  return () => (i < bytes.length ? bytes[i++] : null);
}
(async () => {
  const cases = JSON.parse(fs.readFileSync(0, "utf8")), results = [];
  for (const c of cases) {
    const out = [], err = []; let threw = null;
    let given = c.stdin || ""; if (given && !/\n$/.test(given)) given += "\n";
    const mod = await VakModule({ noInitialRun: true, stdin: feeder(given),
      print: (t) => out.push(t), printErr: (t) => err.push(t) });
    for (const p of Object.keys(LIBRARY)) {
      try { mod.FS.mkdirTree(p.slice(0, p.lastIndexOf("/"))); } catch (e) {}
      mod.FS.writeFile(p, LIBRARY[p]);
    }
    mod.FS.writeFile("/program.vak", c.source);
    try { mod.callMain(c.args || ["/program.vak"]); } catch (e) { threw = String(e && e.message || e); }
    results.push({ out: out.join("\n"), err: err.join("\n"), threw });
  }
  process.stdout.write(JSON.stringify(results));
})();
"""

    #: Samples that read the input pane get the same line in both engines.
    STDIN = {"प्रदानम्": "राम\n२५\n"}

    #: Beyond the samples: every feature added after the engine last fell
    #: behind, and the path the runtime fault was on.
    EXTRA = {
        "कुरु": "मान क = ०।\nकुरु { क = क + १। यदि (क % २ == ०) { अनुवर्त। } } यावत् (क < ५)।\nमुद्रय क।",
        "default in the middle":
            'कार्यम् ल(कर्ता शब्दः क, करणम् शब्दः स = "ल", कर्म शब्दः ग) : शब्दः '
            '{ प्रत्यागच्छ क + स + ग। }\nमुद्रय ल(कर्ता: "अ", कर्म: "ब")।',
        "लक्षणम् sees the default on the right parameter":
            "कार्यम् छ(अपादानम् सूची स, करणम् किमपि प = शून्य) : सूची { प्रत्यागच्छ स। }\n"
            "मुद्रय लक्षणम्(छ).प्राचलाः[०].मूलमस्ति, लक्षणम्(छ).प्राचलाः[१].मूलमस्ति।",
        "a string default": 'कार्यम् क(ब = "स्वागतम्") { प्रत्यागच्छ ब। }\nमुद्रय क()।',
        "प्रयुज्": "कार्यम् य(अ, ब, स) { प्रत्यागच्छ अ + ब + स। }\nमुद्रय प्रयुज्(य, [१, २, ३])।",
        "bit operations": "मुद्रय प्रतिच्छेदः(१२, १०), पूरकः(१२), वामसारः(१, ४)।",
        "romanised built-ins": "मुद्रय dirghata([१, २, ३]), purakah(१२)।",
    }

    #: Programs whose kāraka graph the page draws. The आलेखः panel renders
    #: whatever `--आलेखः` prints, so a graph that differs from the Python one
    #: is a picture the page would teach from, wrongly and silently.
    GRAPHS = {
        "a default in the middle, left unstated":
            'कार्यम् ल(कर्ता शब्दः क, करणम् शब्दः स = "ल", कर्म शब्दः ग) : शब्दः '
            '{ प्रत्यागच्छ क + स + ग। }\nमुद्रय ल(कर्ता: "अ", कर्म: "ब")।',
        "a role neither given nor defaulted":
            "कार्यम् ल(कर्ता शब्दः क, कर्म शब्दः ग) : शब्दः { प्रत्यागच्छ क + ग। }\n"
            'मुद्रय ल(कर्ता: "अ")।',
        "an action handed to another as its करणम्":
            "कार्यम् समः(पूर्णाङ्कः सङ्ख्या) : सत्यता { प्रत्यागच्छ सङ्ख्या % २ == ०। }\n"
            "कार्यम् छ(अपादानम् सूची स, करणम् कार्यम् प) : सूची { प्रत्यागच्छ स। }\n"
            "मुद्रय छ(अपादानम्: [१, २], करणम्: समः)।",
    }

    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp(prefix="vak-page-engine-"))
        page = (ROOT / "docs" / "playground.html").read_text(encoding="utf-8")
        scripts = re.findall(r"<script>(.*?)</script>", page, re.S)
        engine = next((s for s in scripts if "var VakModule=" in s), None)
        if engine is None:
            raise unittest.SkipTest("no engine inlined in docs/playground.html")
        (cls.dir / "engine.js").write_text(engine, encoding="utf-8")
        (cls.dir / "harness.js").write_text(cls.HARNESS, encoding="utf-8")
        (cls.dir / "library.json").write_text(
            re.search(r"var LIBRARY = (\{.*?\});\n", page, re.S).group(1), encoding="utf-8")
        samples = json.loads(re.search(r"var SAMPLES = (\{.*?\});\n", page, re.S).group(1))
        cls.cases = [(f"sample {k}", v, cls.STDIN.get(k, "")) for k, v in samples.items()]
        cls.cases += [(k, v, "") for k, v in cls.EXTRA.items()]
        cls.graphs = list(cls.GRAPHS.items())
        payload = [{"source": s, "stdin": i} for _n, s, i in cls.cases]
        payload += [{"source": s, "stdin": "", "args": ["--आलेखः", "/program.vak"]}
                    for _n, s in cls.graphs]
        proc = subprocess.run(
            ["node", str(cls.dir / "harness.js"), str(cls.dir / "engine.js"),
             str(cls.dir / "library.json")],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True, text=True, encoding="utf-8", timeout=600)
        if proc.returncode != 0:
            raise AssertionError("the page's engine did not run:\n" + proc.stderr[:2000])
        cls.results = json.loads(proc.stdout)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def python(self, source: str, given: str) -> str:
        buf = io.StringIO()
        saved, sys.stdin = sys.stdin, io.StringIO(given)
        try:
            with redirect_stdout(buf):
                run_source(source, "<प>")
        finally:
            sys.stdin = saved
        return buf.getvalue().rstrip("\n")

    def test_it_draws_the_same_karaka_graph_as_python(self):
        """The live आलेखः panel, end to end: the engine as committed in the
        page, asked for the graph exactly as the panel asks for it."""
        drawn = self.results[len(self.cases):]
        self.assertEqual(len(drawn), len(self.graphs))
        for (name, source), result in zip(self.graphs, drawn):
            with self.subTest(case=name):
                self.assertIsNone(result["threw"], result["threw"])
                self.assertEqual(json.loads(result["out"]),
                                 graph_of_source(source, "<प>"),
                                 f"stderr: {result['err'][:300]}")

    def test_every_case_matches_the_python_engine(self):
        for (name, source, given), result in zip(self.cases, self.results):
            with self.subTest(case=name):
                self.assertIsNone(result["threw"], result["threw"])
                self.assertEqual(result["out"].rstrip("\n"), self.python(source, given),
                                 f"stderr: {result['err'][:300]}")


@unittest.skipIf(GCC is None, "C-संकलकः न प्राप्तः / no C compiler available")
class TestTheSelfHostedToolchainOnTheCRuntime(unittest.TestCase):
    """स्वयंसिद्धिः देशीयरूपेण — the combination no test used to run.

    Vāk's engines were tested as the tree-walker, the Python VM, the Vāk front
    end on the Python VM, the Vāk VM on Python, and Python-compiled code on the
    C runtime. Not as the Vāk-written compiler running *on* the C runtime,
    compiling a program at run time and handing it to the C VM — which is what
    the playground is, and what the Linux, macOS and Windows downloads on a
    GitHub release are.

    That hand-over converts a compiled कार्यम् from कोशाः into C structs, and it
    never read the five default-argument fields. They were malloc'd and left
    as heap garbage, so in 0.12.0's release binaries and in the rebuilt
    playground a default landed on the wrong parameter, or on none.
    """

    PROGRAMS = {
        "default in the middle":
            ('कार्यम् ल(कर्ता शब्दः क, करणम् शब्दः स = "ल", कर्म शब्दः ग) : शब्दः '
             '{ प्रत्यागच्छ क + स + ग। }\nमुद्रय ल(कर्ता: "अ", कर्म: "ब")।'),
        "every literal kind":
            ('कार्यम् क(अ = ५, ब = २.५, स = "क", द = सत्य, य = शून्य) '
             "{ प्रत्यागच्छ [अ, ब, स, द, य]। }\nमुद्रय क()।"),
        "लक्षणम् reports each default where it is":
            ("कार्यम् छ(अपादानम् सूची स, करणम् किमपि प = शून्य) : सूची { प्रत्यागच्छ स। }\n"
             "मुद्रय लक्षणम्(छ).प्राचलाः[०].मूलमस्ति, लक्षणम्(छ).प्राचलाः[१].मूलमस्ति।"),
        "प्रयुज् by role, default unstated":
            ('कार्यम् ल(कर्ता शब्दः क, करणम् शब्दः स = "ल", कर्म शब्दः ग) : शब्दः '
             '{ प्रत्यागच्छ क + स + ग। }\n'
             'मुद्रय प्रयुज्(ल, {"कर्ता": "अ", "कर्म": "ब"})।'),
        "कुरु": "मान क = ०।\nकुरु { क = क + १। } यावत् (असत्य)।\nमुद्रय क।",
    }

    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp(prefix="vak-selfhosted-native-"))
        toolchain = ROOT / "स्वयंसिद्धिः" / "वाक्.vak"
        cls.exe = build_executable(toolchain.read_text(encoding="utf-8"), toolchain, cls.dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def test_it_agrees_with_the_python_engine(self):
        for name, source in self.PROGRAMS.items():
            with self.subTest(program=name):
                program = self.dir / f"p{abs(hash(name))}.vak"
                program.write_text(source, encoding="utf-8")
                proc = subprocess.run([str(self.exe.resolve()), str(program)],
                                      capture_output=True, timeout=120)
                printed = proc.stdout.decode("utf-8", "replace").replace("\r\n", "\n").strip()
                self.assertEqual(proc.returncode, 0,
                                 proc.stderr.decode("utf-8", "replace")[:400] + printed[:400])
                self.assertEqual(printed, output(source))

    def test_it_draws_the_same_karaka_graph(self):
        """--आलेखः on the C runtime is what the playground's live graph is.
        The panel draws whatever this prints, so a graph that differs here is
        a graph the page would draw wrongly, silently, for every learner."""
        source = (ROOT / "examples" / "13_karaka.vak").read_text(encoding="utf-8")
        program = self.dir / "alekha.vak"
        program.write_text(source, encoding="utf-8")
        proc = subprocess.run([str(self.exe.resolve()), "--आलेखः", str(program)],
                              capture_output=True, timeout=120)
        printed = proc.stdout.decode("utf-8", "replace")
        self.assertEqual(proc.returncode, 0,
                         proc.stderr.decode("utf-8", "replace")[:400])
        self.assertEqual(json.loads(printed),
                         graph_of_source(source, "13_karaka.vak"))


class TestTheStoryDatesWhatItCan(unittest.TestCase):
    """कथायाः तिथयः — dates from the tags, and only where they exist.

    Acts I to IV happened before the first commit, which is a squash of
    everything up to 0.10.0. They carry no dates and must not be given any:
    the page's whole argument is that its numbers are real.
    """

    def page(self) -> str:
        return (ROOT / "docs" / "story.html").read_text(encoding="utf-8")

    def tags(self) -> dict[str, str]:
        try:
            names = subprocess.run(["git", "-C", str(ROOT), "tag", "-l", "v*"],
                                   capture_output=True, text=True,
                                   check=True).stdout.split()
        except Exception:
            return {}
        out = {}
        for tag in names:
            when = subprocess.run(
                ["git", "-C", str(ROOT), "log", "-1", "--format=%cs",
                 f"{tag}^{{commit}}"],
                capture_output=True, text=True, check=True).stdout.strip()
            out[tag.lstrip("v")] = when
        return out

    def test_a_dated_chip_carries_its_real_release_date(self):
        tags = self.tags()
        if not tags:
            self.skipTest("no git history here — a tarball, not a clone")
        shown = dict(re.findall(
            r'<span class="ver cut"[^>]*>([\d.]+)</span>'
            r'<time class="when" datetime="([\d-]+)"', self.page()))
        self.assertTrue(shown, "no dated versions on the story page")
        for version, when in shown.items():
            if version in tags:
                with self.subTest(version=version):
                    self.assertEqual(when, tags[version])

    def test_a_released_version_is_never_drawn_as_retrospective(self):
        """REAL was hand-written, and bumping __version__ to 0.12.0 silently
        dropped 0.11.1 out of it — a version that is on PyPI was being drawn
        as a stage numbered after the fact."""
        tags = self.tags()
        if not tags:
            self.skipTest("no git history here — a tarball, not a clone")
        page = self.page()
        chips = re.findall(r'<span class="(ver[^"]*)"( title="[^"]*")?>([\d.]+)</span>', page)
        for version in tags:
            with self.subTest(version=version):
                drawn = [(cls, title) for cls, title, v in chips if v == version]
                # Every chip for a tagged version is drawn as released — and
                # carries the title that says so, since a chip missing it is
                # how the फलम् chapter's went unnoticed until 0.12.1 existed.
                for cls, title in drawn:
                    self.assertEqual(cls, "ver cut", f"{version} drawn as {cls!r}")
                    self.assertEqual(title, ' title="a released version"',
                                     f"{version} chip without its title")

    @unittest.skipIf(shutil.which("git") is None, "git not found")
    def test_a_shallow_clone_is_refused_rather_than_misdated(self):
        """CI checked out shallow, so the regenerated story dated 0.10.0 as the
        day of the push and dropped two releases — and the docs job failed on
        every commit for three days before anyone looked. Now the builder
        refuses a history it cannot read correctly."""
        directory = Path(tempfile.mkdtemp(prefix="vak-shallow-"))
        try:
            clone = directory / "clone"
            subprocess.run(["git", "clone", "-q", "--depth", "1",
                            ROOT.resolve().as_uri(), str(clone)],
                           check=True, capture_output=True)
            shutil.copy(ROOT / "docs" / "build_story.py", clone / "docs" / "build_story.py")
            before = (clone / "docs" / "story.html").read_bytes()
            proc = subprocess.run([sys.executable, "docs/build_story.py"], cwd=clone,
                                  capture_output=True, text=True, encoding="utf-8",
                                  errors="replace")
            self.assertNotEqual(proc.returncode, 0, "a shallow clone was accepted")
            self.assertIn("shallow", proc.stdout + proc.stderr)
            self.assertEqual((clone / "docs" / "story.html").read_bytes(), before,
                             "a page with wrong dates was written anyway")
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    def test_the_undated_stages_stay_undated(self):
        """A stage numbered in retrospect must never sprout a date."""
        page = self.page()
        retrospective = re.findall(
            r'<span class="ver" title="numbered in retrospect">([\d.]+)</span>'
            r'(<time)?', page)
        self.assertTrue(retrospective, "no retrospective stages on the page")
        for version, dated in retrospective:
            with self.subTest(version=version):
                self.assertEqual(dated, "", f"{version} was given a date it "
                                            f"cannot have — it predates the repository")


class TestTheEditorExtensionIsCurrent(unittest.TestCase):
    """विस्तारकः — the VS Code extension is generated; the committed copy must
    be what the generator would write today.

    Its grammar, package.json and README are all derived from vaak/tokens.py
    and vaak/builtins.py, which is the point: highlighting that cannot drift
    from the language. But nothing ran the generator. Through 0.12.0 and
    0.12.1 the extension still called itself 0.11.1 and highlighted none of
    प्रयुज्, लक्षणम्, the bit operations or दोषलिख — and even regenerated, it
    left कुरु as plain text, because DO was a new keyword kind that no
    hand-listed highlighting category included.
    """

    OUTPUTS = {
        "syntaxes/vak.tmLanguage.json": lambda m: json.dumps(m.grammar, ensure_ascii=False, indent=2),
        "package.json": lambda m: json.dumps(m.PACKAGE, ensure_ascii=False, indent=2),
        "language-configuration.json":
            lambda m: json.dumps(m.LANGUAGE_CONFIG, ensure_ascii=False, indent=2),
        "extension.js": lambda m: m.EXTENSION_JS,
        "translit.js": lambda m: m.translit_js(),
        "README.md": lambda m: m.README,
        ".vscodeignore": lambda m: m.VSCODEIGNORE,
    }

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / "vscode-vak"))
        import importlib
        cls.module = importlib.import_module("build_extension")   # writes only in main()

    def test_every_generated_file_matches_the_generator(self):
        for name, render in self.OUTPUTS.items():
            with self.subTest(file=name):
                committed = (ROOT / "vscode-vak" / name).read_text(encoding="utf-8")
                self.assertEqual(
                    committed.replace("\r\n", "\n"), render(self.module).replace("\r\n", "\n"),
                    f"vscode-vak/{name} is stale — run `python vscode-vak/build_extension.py`")

    def test_the_grammar_checks_pass(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            failures = self.module.verify()
        self.assertEqual(failures, 0, buf.getvalue())

    def test_every_keyword_kind_is_highlighted(self):
        """The failure that left कुरु unhighlighted, stated directly."""
        m = self.module
        highlighted = m.CONTROL | m.DECL | m.IMPORT | m.CONSTANTS | m.OPERATOR_WORDS | {"PRINT"}
        orphans = sorted({kind.name for kind in KEYWORDS.values()} - highlighted)
        self.assertEqual(orphans, [], "keyword kinds with no highlighting rule")

    def test_every_builtin_is_highlighted(self):
        grammar = (ROOT / "vscode-vak" / "syntaxes" / "vak.tmLanguage.json").read_text(encoding="utf-8")
        for devanagari, roman, _doc in BUILTIN_DOCS:
            with self.subTest(builtin=devanagari):
                self.assertIn(devanagari, grammar)
                self.assertIn(roman, grammar)

    def test_the_extension_states_the_package_version(self):
        from vaak import __version__
        package = json.loads((ROOT / "vscode-vak" / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package["version"], __version__)


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

    def test_the_bootstrap_table_states_real_line_counts(self):
        """README's bootstrap table gives a line count per stage. Those numbers
        are an argument — how much of Vāk is written in Vāk — so they have to be
        measured, not remembered. Every one of them had drifted by the time the
        graph stage was added, some by a third."""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        rows = re.findall(r"\[([^\]]+\.vak)\]\(स्वयंसिद्धिः/[^)]+\.vak\)\s*\|\s*(\d+) \|",
                          readme)
        self.assertTrue(rows, "the bootstrap table has no rows to check")
        wrong = []
        for name, stated in rows:
            path = ROOT / "स्वयंसिद्धिः" / name
            real = len(path.read_text(encoding="utf-8").splitlines())
            if real != int(stated):
                wrong.append(f"{name}: README says {stated}, the file has {real}")
        self.assertEqual(wrong, [], "; ".join(wrong))

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
