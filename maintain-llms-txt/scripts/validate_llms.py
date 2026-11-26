#!/usr/bin/env python3
"""Validate repository llms.txt coverage, structure, and links."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

EXCLUDED_NAMES = {
    ".git",
    ".agents",
    "node_modules",
    ".next",
    ".turbo",
    ".local",
    "dist",
    "build",
    "coverage",
    "out",
    ".cache",
    ".vercel",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "tmp",
    "generated",
}


def build_excluded_names(extra_names: list[str], include_agents: bool) -> set[str]:
    excluded = set(EXCLUDED_NAMES)
    excluded.update(name for name in extra_names if name)
    if include_agents:
        excluded.discard(".agents")
    return excluded

REQUIRED_SECTIONS = [
    "## Key Files",
    "## Boundaries",
    "## Validation",
    "## Related",
]

LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def is_excluded(path: Path, excluded_names: set[str]) -> bool:
    return any(part in excluded_names for part in path.parts)


def llms_path_for_dir(directory: Path) -> Path:
    return Path("llms.txt") if directory == Path(".") else directory / "llms.txt"


def expected_paths(root: Path, excluded_names: set[str]) -> set[Path]:
    expected: set[Path] = set()
    for current, dirs, _files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in excluded_names]
        rel_dir = Path(current).relative_to(root)
        expected.add(llms_path_for_dir(rel_dir))
    return expected


def actual_paths(root: Path, excluded_names: set[str]) -> tuple[set[Path], list[Path]]:
    included: set[Path] = set()
    excluded_hits: list[Path] = []
    for path in root.rglob("llms.txt"):
        rel = path.relative_to(root)
        if is_excluded(rel, excluded_names):
            excluded_hits.append(rel)
        else:
            included.add(rel)
    return included, excluded_hits


def validate_shape(root: Path, rel: Path, errors: list[str]) -> None:
    path = root / rel
    text = path.read_text()
    lines = text.splitlines()
    if not lines or not lines[0].startswith("# "):
        errors.append(f"{rel}: first line must be an H1")
    if len(lines) < 3 or lines[1] != "" or not lines[2].startswith("> "):
        errors.append(f"{rel}: line 3 must be a blockquote summary after a blank line")
    for section in REQUIRED_SECTIONS:
        if section not in text:
            errors.append(f"{rel}: missing {section}")


def validate_links(root: Path, rel: Path, errors: list[str]) -> None:
    path = root / rel
    text = path.read_text()
    for match in LINK_RE.finditer(text):
        target = unquote(match.group(1).strip().strip("<>"))
        if target.startswith("#") or SCHEME_RE.match(target):
            continue
        resolved = (path.parent / target).resolve()
        try:
            resolved.relative_to(root.resolve())
        except ValueError:
            errors.append(f"{rel}: link escapes repo: {target}")
            continue
        if not resolved.exists():
            errors.append(f"{rel}: missing link target: {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Repository root, default: current directory")
    parser.add_argument(
        "--exclude-name",
        action="append",
        default=[],
        help="Additional directory name to exclude from coverage",
    )
    parser.add_argument(
        "--include-agents",
        action="store_true",
        help="Include .agents when walking the repository for coverage",
    )
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    if not (root / ".git").exists():
        raise SystemExit(f"not a git repository root: {root}")

    excluded_names = build_excluded_names(args.exclude_name, args.include_agents)

    expected = expected_paths(root, excluded_names)
    actual, excluded_hits = actual_paths(root, excluded_names)
    errors: list[str] = []

    for rel in sorted(expected - actual):
        errors.append(f"missing llms.txt: {rel}")
    for rel in sorted(actual - expected):
        errors.append(f"unexpected llms.txt: {rel}")
    for rel in sorted(excluded_hits):
        errors.append(f"excluded directory contains llms.txt: {rel}")

    for rel in sorted(actual & expected):
        validate_shape(root, rel, errors)
        validate_links(root, rel, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"llms validation failed: {len(errors)} error(s)")
        return 1

    print(f"llms validation passed: {len(actual)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
