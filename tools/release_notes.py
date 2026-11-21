#!/usr/bin/env python3
"""Print the CHANGELOG.md section of one version (the GitHub release notes).

    tools/release_notes.py 0.2.0 [CHANGELOG.md]

Exits 1 when the version has no section or the section is empty, so the
release workflow stops before publishing anything.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def section(text: str, version: str) -> str:
    heading = re.compile(rf"^## \[{re.escape(version)}\][^\n]*\n", re.M)
    m = heading.search(text)
    if not m:
        return ""
    rest = text[m.end():]
    end = re.search(r"^## \[|^\[[^\]]+\]: ", rest, re.M)
    return (rest[:end.start()] if end else rest).strip()


def main(argv: list[str]) -> int:
    if not 1 <= len(argv) <= 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    version = argv[0].removeprefix("v")
    path = Path(argv[1] if len(argv) > 1 else "CHANGELOG.md")
    notes = section(path.read_text(), version)
    if not notes:
        print(f"{path} no tiene una sección «## [{version}]» con contenido", file=sys.stderr)
        return 1
    print(notes)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
