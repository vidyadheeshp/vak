# -*- coding: utf-8 -*-
"""स्वत्वम् — the copyright line the generated pages carry.

Read out of LICENSE rather than retyped, so the holder and the year on the
pages cannot drift from the licence that actually governs the code. If the
LICENSE is ever amended, the pages follow on the next build.
"""
from __future__ import annotations

import datetime
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPO = "https://github.com/vidyadheeshp/vak"


def _from_license() -> tuple[str, str]:
    """(years, holder) — from the LICENSE's own copyright line."""
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    match = re.search(r"Copyright \(c\) ([\d–—,\s-]+) (.+)", text)
    if not match:                                      # pragma: no cover
        return str(datetime.date.today().year), "Vidyadheesh Pandurangi"
    return match.group(1).strip(), match.group(2).strip()


YEARS, HOLDER = _from_license()


def copyright_html(licence_href: str | None = None) -> str:
    """The notice, as one paragraph. `licence_href` lets a page point at a
    local copy of the licence; otherwise it points at the repository."""
    href = licence_href or f"{REPO}/blob/main/LICENSE"
    return (f'<p class="copyright">© {YEARS} {HOLDER}. '
            f'वाक् is free software, released under the '
            f'<a href="{href}">MIT Licence</a> — use it, change it, teach with '
            f'it, ship it.</p>')


def copyright_line() -> str:
    """The same thing as plain text, for a place that cannot take markup."""
    return f"© {YEARS} {HOLDER} · MIT Licence"


if __name__ == "__main__":                                   # pragma: no cover
    print(copyright_line())
    print(copyright_html())
