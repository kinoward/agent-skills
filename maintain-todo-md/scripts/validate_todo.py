#!/usr/bin/env python3
"""Validate the repository TODO.md format."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED_SECTIONS = ["## Next", "## Backlog", "## Blocked", "## Done ✓"]
CHECKBOX_RE = re.compile(r"^\s*- \[( |x|X)\] .+")
ANY_CHECKBOX_RE = re.compile(r"^\s*- \[[^\]]+\] ")
DUE_RE = re.compile(r"\bdue:([0-9]{4}-[0-9]{2}-[0-9]{2})\b")
BAD_DUE_RE = re.compile(r"\bdue:(\S+)")


def section_for_line(lines: list[str], index: int) -> str | None:
    current: str | None = None
    for line in lines[: index + 1]:
        if line.startswith("## "):
            current = line.strip()
    return current


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("todo", nargs="?", default="TODO.md", help="TODO.md path")
    args = parser.parse_args()

    path = Path(args.todo)
    if not path.exists():
        raise SystemExit(f"TODO file not found: {path}")

    text = path.read_text()
    lines = text.splitlines()
    errors: list[str] = []

    if not lines or lines[0] != "# TODO":
        errors.append("first line must be exactly '# TODO'")

    positions: list[int] = []
    for section in REQUIRED_SECTIONS:
        try:
            positions.append(lines.index(section))
        except ValueError:
            errors.append(f"missing section: {section}")
    if len(positions) == len(REQUIRED_SECTIONS) and positions != sorted(positions):
        errors.append("sections must appear in order: Next, Backlog, Blocked, Done ✓")

    for idx, line in enumerate(lines, 1):
        if ANY_CHECKBOX_RE.match(line) and not CHECKBOX_RE.match(line):
            errors.append(f"line {idx}: checkbox must be '- [ ]' or '- [x]'")
        if CHECKBOX_RE.match(line):
            section = section_for_line(lines, idx - 1)
            marker = line.strip()[3]
            if section == "## Done ✓" and marker not in {"x", "X"}:
                errors.append(f"line {idx}: Done ✓ tasks must be completed")
            if section != "## Done ✓" and marker in {"x", "X"}:
                errors.append(f"line {idx}: completed tasks belong in Done ✓")
        for bad in BAD_DUE_RE.findall(line):
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", bad):
                errors.append(f"line {idx}: invalid due date '{bad}', use due:YYYY-MM-DD")
        for due in DUE_RE.findall(line):
            year, month, day = [int(part) for part in due.split("-")]
            if not (1 <= month <= 12 and 1 <= day <= 31 and year >= 2000):
                errors.append(f"line {idx}: invalid due date '{due}'")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"TODO validation failed: {len(errors)} error(s)")
        return 1

    print(f"TODO validation passed: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
