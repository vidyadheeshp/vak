"""
कोशरूपम् — the AST written as plain कोशाः (dictionaries).

This is the contract between the two parsers. The Python parser builds
dataclasses; the Vāk parser in स्वयंसिद्धिः/व्याकरणम्.vak builds कोशाः. Both
describe the same tree, so `to_kosha()` lets the test suite compare them node
for node — and it is what the Vāk compiler consumes.

Every node is a कोशः with a `रूपम्` (form) naming it, its own fields, and the
line it came from:

    { "रूपम्": "द्विपदी", "वामम्": {...}, "संकारकः": "+", "दक्षिणम्": {...},
      "पङ्क्तिः": ४ }
"""

from __future__ import annotations

from typing import Any

from . import ast_nodes as A

# Python class name -> the Sanskrit name of that node form
NODE_NAMES: dict[str, str] = {
    "Program": "कार्यक्रमः",
    "Literal": "मूल्यम्",
    "ListLit": "सूचीरचना",
    "DictLit": "कोशरचना",
    "Identifier": "नाम",
    "Unary": "एकपदी",
    "Binary": "द्विपदी",
    "Logical": "तार्किकम्",
    "Assign": "नियोजनम्",
    "IndexGet": "सूचकग्रहणम्",
    "IndexSet": "सूचकन्यासः",
    "Call": "आह्वानम्",
    "FunctionExpr": "अनामकार्यम्",
    "Param": "प्राचलः",
    "ExpressionStmt": "पदवाक्यम्",
    "VarDecl": "चरघोषणा",
    "Print": "मुद्रणम्",
    "Block": "खण्डः",
    "If": "यदिवाक्यम्",
    "While": "यावद्वाक्यम्",
    "ForEach": "प्रत्येकवाक्यम्",
    "Repeat": "आवृत्तिवाक्यम्",
    "Switch": "विकल्पवाक्यम्",
    "SwitchCase": "पक्षः",
    "Try": "प्रयत्नवाक्यम्",
    "Throw": "उत्सर्गः",
    "Import": "आयातः",
    "FunctionDecl": "कार्यघोषणा",
    "Return": "प्रत्यागमनम्",
    "Break": "विरामः",
    "Continue": "अनुवर्तनम्",
}


def to_kosha(node: Any) -> Any:
    """Turn a Python AST node into the कोशः form the Vāk parser produces."""
    if node is None:
        return None
    if isinstance(node, list):
        return [to_kosha(item) for item in node]
    if isinstance(node, tuple):
        return [to_kosha(item) for item in node]

    form = NODE_NAMES.get(type(node).__name__)
    if form is None:                                  # a bare value
        return node
    line = getattr(node, "line", 0)

    if isinstance(node, A.Program):
        return {"रूपम्": form, "वाक्यानि": to_kosha(node.statements), "पङ्क्तिः": line}
    if isinstance(node, A.Literal):
        return {"रूपम्": form, "मूल्यम्": node.value, "पङ्क्तिः": line}
    if isinstance(node, A.ListLit):
        return {"रूपम्": form, "अङ्गानि": to_kosha(node.elements), "पङ्क्तिः": line}
    if isinstance(node, A.DictLit):
        return {"रूपम्": form, "युग्मानि": to_kosha(node.pairs), "पङ्क्तिः": line}
    if isinstance(node, A.Identifier):
        return {"रूपम्": form, "नाम": node.name, "पङ्क्तिः": line}
    if isinstance(node, A.Unary):
        return {"रूपम्": form, "संकारकः": node.op, "दक्षिणम्": to_kosha(node.right),
                "पङ्क्तिः": line}
    if isinstance(node, (A.Binary, A.Logical)):
        return {"रूपम्": form, "वामम्": to_kosha(node.left), "संकारकः": node.op,
                "दक्षिणम्": to_kosha(node.right), "पङ्क्तिः": line}
    if isinstance(node, A.Assign):
        return {"रूपम्": form, "नाम": node.name, "मूल्यम्": to_kosha(node.value),
                "पङ्क्तिः": line}
    if isinstance(node, A.IndexGet):
        return {"रूपम्": form, "लक्ष्यम्": to_kosha(node.target),
                "सूचकः": to_kosha(node.index), "पङ्क्तिः": line}
    if isinstance(node, A.IndexSet):
        return {"रूपम्": form, "लक्ष्यम्": to_kosha(node.target),
                "सूचकः": to_kosha(node.index), "मूल्यम्": to_kosha(node.value),
                "पङ्क्तिः": line}
    if isinstance(node, A.Call):
        karakas = list(node.arg_karakas) or [None] * len(node.args)
        return {"रूपम्": form, "कार्यपदम्": to_kosha(node.callee),
                "प्राचलाः": to_kosha(node.args), "कारकाः": karakas, "पङ्क्तिः": line}
    if isinstance(node, A.FunctionExpr):
        return {"रूपम्": form, "नाम": node.name, "प्राचलाः": to_kosha(node.params),
                "शरीरम्": to_kosha(node.body), "प्रतिफलप्रकारः": node.return_type,
                "पङ्क्तिः": line}
    if isinstance(node, A.Param):
        return {"रूपम्": form, "नाम": node.name, "प्रकारः": node.type,
                "कारकम्": node.karaka}
    if isinstance(node, A.ExpressionStmt):
        return {"रूपम्": form, "पदम्": to_kosha(node.expr), "पङ्क्तिः": line}
    if isinstance(node, A.VarDecl):
        return {"रूपम्": form, "नाम": node.name, "मूल्यम्": to_kosha(node.value),
                "ध्रुवः": node.constant, "प्रकारः": node.type, "पङ्क्तिः": line}
    if isinstance(node, A.Print):
        return {"रूपम्": form, "प्राचलाः": to_kosha(node.args), "पङ्क्तिः": line}
    if isinstance(node, A.Block):
        return {"रूपम्": form, "वाक्यानि": to_kosha(node.statements), "पङ्क्तिः": line}
    if isinstance(node, A.If):
        return {"रूपम्": form, "परीक्षा": to_kosha(node.condition),
                "तदा": to_kosha(node.then_branch), "अन्यथापक्षः": to_kosha(node.else_branch),
                "पङ्क्तिः": line}
    if isinstance(node, A.While):
        return {"रूपम्": form, "परीक्षा": to_kosha(node.condition),
                "शरीरम्": to_kosha(node.body), "पङ्क्तिः": line}
    if isinstance(node, A.ForEach):
        return {"रूपम्": form, "चरः": node.var, "संग्रहः": to_kosha(node.iterable),
                "शरीरम्": to_kosha(node.body), "पङ्क्तिः": line}
    if isinstance(node, A.Repeat):
        return {"रूपम्": form, "गणना": to_kosha(node.count),
                "शरीरम्": to_kosha(node.body), "पङ्क्तिः": line}
    if isinstance(node, A.Switch):
        return {"रूपम्": form, "विषयः": to_kosha(node.subject),
                "पक्षाः": to_kosha(node.cases), "पङ्क्तिः": line}
    if isinstance(node, A.SwitchCase):
        return {"रूपम्": form, "मूल्यानि": to_kosha(node.values),
                "वाक्यानि": to_kosha(node.body), "पङ्क्तिः": line}
    if isinstance(node, A.Try):
        return {"रूपम्": form, "शरीरम्": to_kosha(node.body), "दोषचरः": node.catch_var,
                "दोषशरीरम्": to_kosha(node.catch_body),
                "अन्तशरीरम्": to_kosha(node.finally_body), "पङ्क्तिः": line}
    if isinstance(node, A.Throw):
        return {"रूपम्": form, "मूल्यम्": to_kosha(node.value), "पङ्क्तिः": line}
    if isinstance(node, A.Import):
        return {"रूपम्": form, "पथः": node.path, "उपनाम": node.alias,
                "नामानि": list(node.names), "पङ्क्तिः": line}
    if isinstance(node, A.FunctionDecl):
        return {"रूपम्": form, "नाम": node.name, "प्राचलाः": to_kosha(node.params),
                "शरीरम्": to_kosha(node.body), "प्रतिफलप्रकारः": node.return_type,
                "पङ्क्तिः": line}
    if isinstance(node, A.Return):
        return {"रूपम्": form, "मूल्यम्": to_kosha(node.value), "पङ्क्तिः": line}
    if isinstance(node, (A.Break, A.Continue)):
        return {"रूपम्": form, "पङ्क्तिः": line}
    raise TypeError(f"अज्ञातम् रूपम् / cannot serialise {type(node).__name__}")


# --------------------------------------------------------------------------
# संकलितम् कोशरूपम् — a compiled Chunk as plain कोशाः, so the Python compiler
# and the Vāk compiler in स्वयंसिद्धिः/संकलकः.vak can be compared instruction
# for instruction.
# --------------------------------------------------------------------------
def chunk_to_kosha(chunk: Any) -> dict:
    from .compiler import CompiledFunction

    def constant(value: Any) -> Any:
        if isinstance(value, CompiledFunction):
            return {
                "रूपम्": "संकलितकार्यम्",
                "नाम": value.name,
                "प्राचलाः": [to_kosha(p) for p in value.params],
                "प्रतिफलप्रकारः": value.return_type,
                "खण्डः": chunk_to_kosha(value.chunk),
            }
        if isinstance(value, tuple):
            return [constant(v) for v in value]
        return value

    return {
        "नाम": chunk.name,
        "सङ्केताः": list(chunk.code),
        "ध्रुवाः": [constant(c) for c in chunk.constants],
        "पङ्क्तयः": list(chunk.lines),
    }


def kosha_to_chunk(kosha: dict) -> Any:
    """The reverse road: a कोशः built by the Vāk compiler becomes a real Chunk
    the SanskritVM can execute. This is what closes the bootstrap loop."""
    from .compiler import Chunk, CompiledFunction

    def constant(value: Any) -> Any:
        if isinstance(value, dict) and value.get("रूपम्") == "संकलितकार्यम्":
            return CompiledFunction(
                name=value["नाम"],
                params=[A.Param(p["नाम"], p["प्रकारः"], p["कारकम्"])
                        for p in value["प्राचलाः"]],
                return_type=value["प्रतिफलप्रकारः"],
                chunk=kosha_to_chunk(value["खण्डः"]),
            )
        return value

    chunk = Chunk(kosha["नाम"])
    chunk.code = [int(word) for word in kosha["सङ्केताः"]]
    chunk.lines = [int(line) for line in kosha["पङ्क्तयः"]]
    chunk.constants = [constant(c) for c in kosha["ध्रुवाः"]]
    return chunk
