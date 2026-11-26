#!/usr/bin/env python3
"""Locate llms.txt files affected by git changes or explicit paths."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

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


def relpath(path: Path, root: Path) -> str:
    value = path.resolve().relative_to(root.resolve()).as_posix()
    return "llms.txt" if value == "llms.txt" else value


def run_git(root: Path, args: list[str]) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def git_paths(root: Path, mode: str | None) -> list[str]:
    if not mode or mode == "working":
        tracked = run_git(root, ["diff", "--name-only"])
        untracked = run_git(root, ["ls-files", "--others", "--exclude-standard"])
        return tracked + untracked
    if mode == "staged":
        return run_git(root, ["diff", "--cached", "--name-only"])
    if mode.startswith("since:"):
        rev = mode.split(":", 1)[1]
        if not rev:
            raise SystemExit("--git since:<rev> requires a revision")
        return run_git(root, ["diff", "--name-only", rev])
    raise SystemExit("--git must be one of: working, staged, since:<rev>")


def has_excluded_part(path: Path, excluded_names: set[str]) -> bool:
    return any(part in excluded_names for part in path.parts)


def is_agent_skill_path(path: Path, map_agent_skills_to_root: bool) -> bool:
    parts = path.parts
    if not map_agent_skills_to_root:
        return False
    return len(parts) >= 3 and parts[0] == ".agents" and parts[1] == "skills"


def nearest_llms(root: Path, subject: Path, excluded_names: set[str]) -> Path | None:
    current = subject if subject.is_dir() else subject.parent
    if not current.exists():
        current = subject.parent
    while True:
        if not has_excluded_part(current, excluded_names):
            candidate = root / current / "llms.txt"
            if candidate.exists():
                return candidate
        if current == Path(".") or str(current) == "":
            break
        current = current.parent
    candidate = root / "llms.txt"
    return candidate if candidate.exists() else None


def parent_llms(root: Path, primary: Path, excluded_names: set[str]) -> list[Path]:
    parents: list[Path] = []
    primary_dir = primary.parent.resolve().relative_to(root.resolve())
    current = primary_dir.parent
    while True:
        if has_excluded_part(current, excluded_names):
            if current == Path(".") or str(current) == "":
                break
            current = current.parent
            continue
        candidate = root / current / "llms.txt"
        if candidate.exists() and candidate != primary:
            parents.append(candidate)
        if current == Path(".") or str(current) == "":
            break
        current = current.parent
    root_llms = root / "llms.txt"
    if root_llms.exists() and root_llms != primary and root_llms not in parents:
        parents.append(root_llms)
    return parents


def add_unique(target: list[Path | str], value: Path | str) -> None:
    if value not in target:
        target.append(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Repository root, default: current directory")
    parser.add_argument("--git", help="Read changed paths from git: working, staged, since:<rev>")
    parser.add_argument("--paths", nargs="*", help="Explicit changed paths")
    parser.add_argument(
        "--exclude-name",
        action="append",
        default=[],
        help="Additional directory name to exclude when locating llms.txt",
    )
    parser.add_argument(
        "--include-agents",
        action="store_true",
        help="Include .agents when searching for llms.txt",
    )
    parser.add_argument(
        "--map-agent-skills-to-root",
        action="store_true",
        help="Treat .agents/skills as root-mapped llms.txt path",
    )
    parser.add_argument(
        "--no-map-agent-skills-to-root",
        dest="map_agent_skills_to_root",
        action="store_false",
        help="Do not treat .agents/skills specially",
    )
    parser.set_defaults(map_agent_skills_to_root=True)
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    if not (root / ".git").exists():
        raise SystemExit(f"not a git repository root: {root}")

    excluded_names = build_excluded_names(args.exclude_name, args.include_agents)

    raw_paths = list(args.paths or [])
    if args.git or not raw_paths:
        raw_paths.extend(git_paths(root, args.git))

    primary: list[Path] = []
    parents: list[Path] = []
    excluded: list[str] = []
    missing: list[str] = []

    for raw in sorted(set(raw_paths)):
        rel = Path(raw)
        if rel.is_absolute():
            try:
                rel = rel.resolve().relative_to(root)
            except ValueError:
                add_unique(excluded, raw)
                continue

        if is_agent_skill_path(rel, args.map_agent_skills_to_root):
            root_llms = root / "llms.txt"
            if root_llms.exists():
                add_unique(primary, root_llms)
            else:
                add_unique(missing, f"{raw} -> llms.txt")
            continue

        if has_excluded_part(rel, excluded_names):
            add_unique(excluded, raw)
            continue

        candidate = nearest_llms(root, rel, excluded_names)
        if candidate:
            add_unique(primary, candidate)
            for parent in parent_llms(root, candidate, excluded_names):
                add_unique(parents, parent)
        else:
            add_unique(missing, raw)

    sections: list[tuple[str, list[str]]] = [
        ("primary", [relpath(path, root) for path in primary]),
        ("parents", [relpath(path, root) for path in parents if path not in primary]),
        ("excluded", excluded),
        ("missing", missing),
    ]

    for name, values in sections:
        print(f"{name}:")
        if values:
            for value in values:
                print(f"  - {value}")
        else:
            print("  - none")

    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
