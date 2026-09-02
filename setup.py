# -*- coding: utf-8 -*-
"""Packaging shim, for one job: the README's links.

README.md links to files by relative path — `docs/manual.html`,
`examples/13_karaka.vak`, `vak/पुस्तकालयः/गणितम्.vak`. GitHub resolves those.
PyPI does not: it renders the README on its own page, where every one of the
69 relative links is a dead end.

Rather than keep a second README that drifts, the links are rewritten to
absolute GitHub URLs here, at build time. The file in the repository stays
readable and its links stay relative.

Everything else about the package is declared in pyproject.toml.
"""
from __future__ import annotations

import pathlib
import re

from setuptools import setup

HERE = pathlib.Path(__file__).resolve().parent
BLOB = "https://github.com/vidyadheeshp/vak/blob/main/"
TREE = "https://github.com/vidyadheeshp/vak/tree/main/"


def absolute_readme() -> str:
    text = (HERE / "README.md").read_text(encoding="utf-8")

    def fix(match: re.Match) -> str:
        label, target = match.group(1), match.group(2)
        if target.startswith(("http://", "https://", "#", "mailto:")):
            return match.group(0)
        # an in-page anchor on a relative file still points at the file
        path, _, anchor = target.partition("#")
        base = TREE if path.endswith("/") else BLOB
        url = base + path.lstrip("./")
        if anchor:
            url += "#" + anchor
        return f"[{label}]({url})"

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", fix, text)


setup(long_description=absolute_readme(),
      long_description_content_type="text/markdown")
