"""कारकालेखः — the kāraka graph of a program.

Pāṇini describes a sentence as an action (क्रिया) surrounded by the roles its
participants play — who acts, what is acted on, by what means, from where. A
Vāk program declares the same structure: every कार्यम् is an action whose
parameters name their roles, and every call is a sentence that fills them.
This module draws that out as data, for teaching:

    python -m vaak --graph program.vak

    {"कार्याणि":  [the actions, each with its role slots],
     "आह्वानानि": [the sentences — every call to a declared कार्यम्, and how
                   each slot came to be filled]}

A slot is filled नाम्ना (by naming its role), स्थानेन (by position), left
अनुक्तम् (unstated, falling back to its default), or is न्यूनम् (missing —
an error). The graph is built even for programs that would not run, because a
drawing of *why* a call is wrong is the point of it.

The same algorithm is written in Vāk, in स्वयंसिद्धिः/आलेखः.vak, and the two are
held to identical output. Both walk the कोशः form of the syntax tree that both
parsers already produce, visiting keys in sorted order so that nothing depends
on the order a dictionary happened to be built in.
"""

from __future__ import annotations

from typing import Any

from .values import stringify

#: The roles that may appear at most once in a कार्यम् — Pāṇini's rule that an
#: action has one agent and one patient.
EKA = ("कर्ता", "कर्म")


def _walk(node: Any, visit, stack: list[str]) -> None:
    """Pre-order, keys in sorted order, tracking the enclosing named कार्यम्."""
    if isinstance(node, list):
        for item in node:
            _walk(item, visit, stack)
        return
    if not isinstance(node, dict):
        return
    visit(node, stack)
    declares = node.get("रूपम्") == "कार्यघोषणा"
    if declares:
        stack.append(node["नाम"])
    for key in sorted(node):
        value = node[key]
        if isinstance(value, (dict, list)):
            _walk(value, visit, stack)
    if declares:
        stack.pop()


def label(expr: Any) -> str:
    """A short, stable name for an argument, as it would read in the drawing."""
    if not isinstance(expr, dict):
        return "…"
    form = expr.get("रूपम्")
    if form == "नाम":
        return expr["नाम"]
    if form == "मूल्यम्":
        value = expr.get("मूल्यम्")
        if isinstance(value, str):
            return '"' + value + '"'
        return stringify(value)
    if form == "आह्वानम्":
        callee = expr.get("कार्यपदम्")
        head = callee["नाम"] if isinstance(callee, dict) and callee.get("रूपम्") == "नाम" else "…"
        return head + "(…)"
    if form == "अनामकार्यम्":
        return "कार्यम्(…)"
    if form == "सूचीरचना":
        return "[…]"
    if form == "कोशरचना":
        return "{…}"
    return "…"


def _action(decl: dict) -> dict:
    params = decl.get("प्राचलाः") or []
    faults = []
    for role in EKA:
        count = sum(1 for p in params if p.get("कारकम्") == role)
        if count > 1:
            faults.append(f"{role} इति {count} वारम्")
    return {
        "नाम": decl["नाम"],
        "पङ्क्तिः": decl.get("पङ्क्तिः", 0),
        "प्रतिफलम्": decl.get("प्रतिफलप्रकारः", "किमपि"),
        "प्राचलाः": [{"नाम": p["नाम"], "प्रकारः": p.get("प्रकारः", "किमपि"),
                      "कारकम्": p.get("कारकम्"), "मूलम्": bool(p.get("मूलमस्ति"))}
                     for p in params],
        "दोषाः": faults,
    }


def _sentence(call: dict, decl: dict, enclosing: str | None) -> dict:
    """How one call fills the role slots of the कार्यम् it names — the same
    placement the interpreters perform, done on the tree alone."""
    params = decl.get("प्राचलाः") or []
    args = call.get("प्राचलाः") or []
    labels = call.get("कारकाः") or []
    slot: list[int | None] = [None] * len(params)
    how: list[str | None] = [None] * len(params)
    faults: list[str] = []

    def label_at(i: int) -> str | None:
        return labels[i] if i < len(labels) else None

    for i in range(len(args)):
        role = label_at(i)
        if role is None:
            continue
        at = next((j for j, p in enumerate(params) if p.get("कारकम्") == role), None)
        if at is None:
            faults.append(f"{role} इति कारकम् नास्ति")
        elif slot[at] is not None:
            faults.append(f"{role} द्विः")
        else:
            slot[at], how[at] = i, "नाम्ना"
    for i in range(len(args)):
        if label_at(i) is not None:
            continue
        at = next((j for j in range(len(params)) if slot[j] is None), None)
        if at is None:
            faults.append("अतिरिक्तम्")
        else:
            slot[at], how[at] = i, "स्थानेन"

    bindings = []
    for j, p in enumerate(params):
        entry = {"प्राचलः": p["नाम"], "कारकम्": p.get("कारकम्")}
        if slot[j] is not None:
            entry.update({"रीतिः": how[j], "मूल्यम्": label(args[slot[j]])})
        elif p.get("मूलमस्ति"):
            entry.update({"रीतिः": "अनुक्तम्", "मूल्यम्": None})
        else:
            entry.update({"रीतिः": "न्यूनम्", "मूल्यम्": None})
            faults.append("न्यूनम्: " + (p.get("कारकम्") or p["नाम"]))
        bindings.append(entry)

    return {
        "कार्यम्": decl["नाम"],
        "पङ्क्तिः": call.get("पङ्क्तिः", 0),
        "अन्तः": enclosing,
        "बन्धाः": bindings,
        "दोषाः": faults,
    }


def build(tree: dict) -> dict:
    """The kāraka graph of a program, from its कोशः syntax tree."""
    actions: list[dict] = []
    first: dict[str, dict] = {}

    def collect(node: dict, _stack: list[str]) -> None:
        if node.get("रूपम्") == "कार्यघोषणा":
            actions.append(_action(node))
            first.setdefault(node["नाम"], node)

    _walk(tree, collect, [])

    sentences: list[dict] = []

    def calls(node: dict, stack: list[str]) -> None:
        if node.get("रूपम्") != "आह्वानम्":
            return
        callee = node.get("कार्यपदम्")
        if not (isinstance(callee, dict) and callee.get("रूपम्") == "नाम"):
            return
        decl = first.get(callee["नाम"])
        if decl is not None:
            sentences.append(_sentence(node, decl, stack[-1] if stack else None))

    _walk(tree, calls, [])
    return {"कार्याणि": actions, "आह्वानानि": sentences}


def graph_of_source(source: str, filename: str = "<वाक्>") -> dict:
    """Lex, parse, and build — the parse errors of a broken program propagate."""
    from .kosha import to_kosha
    from .lexer import tokenize
    from .parser import parse

    return build(to_kosha(parse(tokenize(source, filename), filename)))
