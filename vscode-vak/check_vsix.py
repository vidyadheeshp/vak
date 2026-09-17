# -*- coding: utf-8 -*-
"""विसिक्स्-परीक्षा — look inside a packaged .vsix before it is published.

`vsce package` reports a file count and a size and nothing else, so what is
actually in the archive is whatever `.vscodeignore` happened to catch. That
file did not exclude `__pycache__`, which sits in vscode-vak/ on any machine
that has run the generator — so the bytecode of a script the package
deliberately leaves out would have shipped inside it.

A package that installs but carries the wrong files is worse than a failed
build, because it reaches people. Run as:

    python vscode-vak/check_vsix.py path/to/vak-0.13.0.vsix
"""
import json
import sys
import zipfile

#: Everything the extension needs in order to work once installed.
REQUIRED = [
    "extension/package.json",
    "extension/extension.js",
    "extension/translit.js",
    "extension/language-configuration.json",
    "extension/syntaxes/vak.tmLanguage.json",
    "extension/images/icon-128.png",
    "extension/icons/vak-file-light.svg",
    "extension/icons/vak-file-dark.svg",
    # vsce lowercases README.md to readme.md when it packages an extension —
    # confirmed against a real archive built with the actual tool, after this
    # exact-case check rejected the v0.14.0 release over a file that was
    # there all along, just spelled the way vsce always spells it.
    "extension/readme.md",
]

#: Nothing here belongs in a published package. Matched on path segments and
#: suffixes, not as substrings: `extension.vsixmanifest` is a required part of
#: the archive and an unanchored ".vsix" test rejects it.
UNWANTED_DIRS = ("__pycache__",)
UNWANTED_STEMS = ("build_extension", "check_vsix")
UNWANTED_SUFFIXES = (".pyc", ".pyo", ".vsix")


def unwanted(name: str) -> bool:
    parts = name.split("/")
    base = parts[-1]
    return (any(d in parts for d in UNWANTED_DIRS)
            or base.rsplit(".", 1)[0] in UNWANTED_STEMS
            or name.endswith(UNWANTED_SUFFIXES))


def check(path: str) -> int:
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        manifest = json.loads(z.read("extension/package.json").decode("utf-8"))

    problems = []
    for need in REQUIRED:
        if need not in names:
            problems.append(f"missing: {need}")
    for name in names:
        if unwanted(name):
            problems.append(f"should not ship: {name}")

    # The Marketplace listing is built from these; without them the page has
    # no link back to the source and vsce warns while publishing anyway.
    for field in ("name", "publisher", "version", "license", "icon",
                  "repository", "homepage", "bugs"):
        if not manifest.get(field):
            problems.append(f"manifest has no {field}")

    for problem in problems:
        print(f"  VSIX FAIL {problem}")
        # a plain print here reaches the step's raw log only — CI ran this
        # once already and failed silently as far as anyone without log
        # access could tell, because nothing here used the syntax GitHub
        # actually surfaces in the Annotations panel. This does.
        print(f"::error::vsix check failed — {problem}")
    if problems:
        print(f"{len(problems)} problem(s) — not fit to publish")
        print("  full archive listing, for whichever of the above needs it:")
        for name in sorted(names):
            print(f"    {name}")
        return 1

    print(f"  {len(names)} files, nothing unwanted")
    print(f"  {manifest['publisher']}.{manifest['name']} {manifest['version']}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    raise SystemExit(check(sys.argv[1]))
