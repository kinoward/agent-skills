#!/usr/bin/env python3
"""Validate repository release version consistency."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
HEADING_RE = re.compile(r"^## \[(v[^\]]+)\] - \d{4}-\d{2}-\d{2}$", re.M)
COMMIT_TYPE_RE = re.compile(r"^(?P<type>[a-z]+)(?:\([^)]+\))?(?P<bang>!)?:")
COMMIT_PREFIX_RE = re.compile(r"^(?P<prefix>[a-z]+(?:\([^)]+\))?!?):")
BREAKING_BODY_RE = re.compile(r"(?m)^BREAKING[ -]CHANGE:")
README_SEMVER_RE = re.compile(
    r"\bv\d+\.\d+\.\d+(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?\b"
)
CHANGELOG_ENTRY_RE = re.compile(
    r"^-\s+`(?P<hash>[0-9a-f]{7,40})`\s+"
    r"`(?P<prefix>[a-z]+(?:\([^)]+\))?!?)`:\s+\S"
)
BOOKKEEPING_COMMIT_RE = re.compile(
    r"^chore\(release\):",
    re.I,
)
UNRELEASED_RE = re.compile(r"\bUnreleased\b", re.I)
EXCLUDED_DIRS = {
    ".agents",
    ".git",
    ".next",
    ".turbo",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "out",
}


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc


def _is_excluded_path(path: Path, repo: Path) -> bool:
    try:
        parts = path.relative_to(repo).parts
    except ValueError:
        return False
    return any(part in EXCLUDED_DIRS for part in parts)


def _normalize_glob_entry(value: str) -> str:
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1].strip()
    return value


def _workspace_from_root_package_json(data_or_path: Path | dict) -> list[str]:
    if isinstance(data_or_path, Path):
        data = read_json(data_or_path)
    else:
        data = data_or_path

    workspaces = data.get("workspaces")
    if isinstance(workspaces, list):
        return [_normalize_glob_entry(item) for item in workspaces if isinstance(item, str)]

    if isinstance(workspaces, dict):
        packages = workspaces.get("packages")
        if isinstance(packages, list):
            return [_normalize_glob_entry(item) for item in packages if isinstance(item, str)]

    return []


def _strip_yaml_comment(value: str) -> str:
    return value.split("#", 1)[0].strip()


def _parse_pnpm_workspace_yaml(lines: list[str]) -> list[str]:
    patterns: list[str] = []
    in_packages = False
    packages_indent: int | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if not in_packages:
            inline_match = re.match(r"^\s*packages:\s*\[(.*)\]\s*$", line)
            if inline_match:
                inner = inline_match.group(1).strip()
                if inner:
                    for item in inner.split(","):
                        normalized = _normalize_glob_entry(_strip_yaml_comment(item))
                        if normalized:
                            patterns.append(normalized)
                return patterns

            match = re.match(r"^(\s*)packages:\s*$", line)
            if match:
                in_packages = True
                packages_indent = len(match.group(1))
            continue

        if in_packages:
            item_match = re.match(r"^(\s*)-\s*(.*?)\s*$", line)
            if not item_match:
                if not stripped.startswith("#"):
                    break
                continue

            if packages_indent is not None and len(item_match.group(1)) <= packages_indent:
                break

            normalized = _normalize_glob_entry(_strip_yaml_comment(item_match.group(2)))
            if normalized:
                patterns.append(normalized)

    return patterns


def _workspace_from_pnpm_yaml(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return _parse_pnpm_workspace_yaml(lines)


def _discover_workspace_package_paths(repo: Path, pattern: str) -> list[Path]:
    pattern = pattern.strip()
    if not pattern:
        return []

    try:
        matches = sorted(repo.glob(pattern))
    except (ValueError, re.error):
        return []

    paths: list[Path] = []
    for match in matches:
        if _is_excluded_path(match, repo):
            continue

        if match.is_dir():
            package_json = match / "package.json"
        elif match.name == "package.json":
            package_json = match
        else:
            continue

        if package_json.exists() and not _is_excluded_path(package_json, repo):
            paths.append(package_json)

    return paths


def package_paths(repo: Path) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()

    root_package_json = repo / "package.json"
    workspace_globs: list[str] = []
    if root_package_json.exists():
        try:
            root_package = read_json(root_package_json)
        except ValueError:
            root_package = {}
        if isinstance(root_package, dict) and "version" in root_package:
            paths.append(root_package_json)
        if isinstance(root_package, dict):
            workspace_globs.extend(_workspace_from_root_package_json(root_package))

    workspace_globs.extend(_workspace_from_pnpm_yaml(repo / "pnpm-workspace.yaml"))

    for workspace in workspace_globs:
        for package_path in _discover_workspace_package_paths(repo, workspace):
            if package_path not in seen:
                seen.add(package_path)
                if package_path == root_package_json:
                    continue
                paths.append(package_path)

    return paths


def release_metadata_paths(repo: Path, discovered_packages: list[Path]) -> set[str]:
    paths = {"VERSION", "CHANGELOG.md"}

    if (repo / "llms.txt").exists():
        paths.add("llms.txt")

    if (repo / "README.md").exists():
        paths.add("README.md")

    for package_path in discovered_packages:
        paths.add(package_path.relative_to(repo).as_posix())

    for path in sorted(repo.rglob("llms.txt")):
        if path.is_file() and not _is_excluded_path(path, repo):
            paths.add(path.relative_to(repo).as_posix())

    return paths


def latest_changelog_version(changelog: str) -> str | None:
    match = HEADING_RE.search(changelog)
    return match.group(1) if match else None


def run_git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        raise ValueError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def commit_exists(repo: Path, commit_hash: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{commit_hash}^{{commit}}"],
        cwd=repo,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def commit_prefix(repo: Path, commit_hash: str) -> str:
    subject = run_git(repo, "show", "-s", "--format=%s", commit_hash)
    match = COMMIT_PREFIX_RE.match(subject)
    if not match:
        raise ValueError(f"commit {commit_hash} does not have a Conventional Commit prefix")
    return match.group("prefix")


def parse_version(version: str) -> tuple[int, int, int]:
    raw = version[1:] if version.startswith("v") else version
    match = SEMVER_RE.match(raw)
    if not match:
        raise ValueError(f"invalid SemVer: {version}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def format_version(parts: tuple[int, int, int]) -> str:
    return f"v{parts[0]}.{parts[1]}.{parts[2]}"


def apply_bump(version: tuple[int, int, int], bump: str) -> tuple[int, int, int]:
    major, minor, patch = version
    if bump == "minor":
        return major, minor + 1, 0
    if bump == "patch":
        return major, minor, patch + 1
    raise ValueError(f"unknown bump: {bump}")


def bump_version(version: str, bump: str) -> str:
    return format_version(apply_bump(parse_version(version), bump))


def commit_bump(subject: str, body: str) -> str | None:
    match = COMMIT_TYPE_RE.match(subject)
    if not match:
        raise ValueError(f"commit {subject!r} is not Conventional Commit format")

    commit_type = match.group("type")
    breaking = bool(match.group("bang")) or bool(BREAKING_BODY_RE.search(body))
    if breaking:
        return "breaking"
    if commit_type == "feat":
        return "minor"
    if commit_type in {"fix", "perf"}:
        return "patch"
    return None


def is_release_metadata_path(path: str, known_release_paths: set[str]) -> bool:
    return path in known_release_paths


def commit_changed_paths(repo: Path, commit_hash: str) -> list[str]:
    output = run_git(
        repo,
        "diff-tree",
        "--root",
        "--no-commit-id",
        "--name-only",
        "-r",
        commit_hash,
    )
    return [line.replace("\\", "/") for line in output.splitlines() if line]


def is_release_bookkeeping_commit(
    repo: Path, commit_hash: str, subject: str, known_release_paths: set[str]
) -> bool:
    if not BOOKKEEPING_COMMIT_RE.match(subject):
        return False
    paths = commit_changed_paths(repo, commit_hash)
    return bool(paths) and all(is_release_metadata_path(path, known_release_paths) for path in paths)


def release_base(repo: Path) -> tuple[str, str]:
    tags = run_git(repo, "tag", "--list", "v[0-9]*", "--merged", "HEAD", "--sort=-v:refname")
    if tags:
        tag = tags.splitlines()[0]
        return tag, tag

    version_commits = run_git(repo, "log", "--format=%H", "--", "VERSION")
    if not version_commits:
        raise ValueError("no VERSION history found")

    commit = version_commits.splitlines()[0]
    version = run_git(repo, "show", f"{commit}:VERSION").splitlines()[0].strip()
    return commit, version


def expected_latest_version(
    repo: Path,
    explicit_version: str | None = None,
    known_release_paths: set[str] | None = None,
) -> tuple[str, str, bool]:
    if known_release_paths is None:
        known_release_paths = release_metadata_paths(repo, package_paths(repo))

    base_ref, base_version = release_base(repo)
    base_tuple = parse_version(base_version)
    computed = base_tuple
    saw_scannable_commit = False
    saw_release_trigger = False
    saw_breaking = False

    commits = run_git(repo, "rev-list", "--reverse", f"{base_ref}..HEAD")
    for commit in [line for line in commits.splitlines() if line]:
        subject = run_git(repo, "show", "-s", "--format=%s", commit)
        body = run_git(repo, "show", "-s", "--format=%b", commit)
        if is_release_bookkeeping_commit(repo, commit, subject, known_release_paths):
            continue
        saw_scannable_commit = True
        bump = commit_bump(subject, body)
        if bump is None:
            continue
        if bump == "breaking":
            saw_breaking = True
            continue
        computed = apply_bump(computed, bump)
        saw_release_trigger = True

    if explicit_version:
        expected_explicit = parse_version(explicit_version)
        if explicit_version and not explicit_version.startswith("v"):
            explicit_version = f"v{explicit_version}"
            expected_explicit = parse_version(explicit_version)
        if expected_explicit[0] <= base_tuple[0] and saw_breaking:
            raise ValueError(
                "breaking changes require an explicit major version target; "
                f"provided {format_version(expected_explicit)} does not bump major"
            )
        if not saw_breaking:
            if expected_explicit != computed:
                raise ValueError(
                    f"explicit version {format_version(expected_explicit)} must match "
                    f"the computed version {format_version(computed)} when no breaking commit exists"
                )
        elif expected_explicit <= computed:
            raise ValueError(
                f"explicit version {format_version(expected_explicit)} must be greater than "
                f"the non-breaking progression {format_version(computed)}"
            )
        return format_version(expected_explicit), base_version, saw_release_trigger or saw_breaking

    if saw_breaking:
        raise ValueError(
            "found a breaking change commit but no --expected-version was provided; "
            "set an explicit target version (for example v1.0.0) after confirming target major."
        )

    should_release = saw_scannable_commit and saw_release_trigger
    return (
        format_version(computed if should_release else base_tuple),
        base_version,
        should_release,
    )


def validate_changelog_history(
    changelog: str,
    current_release: str,
    expected_latest: str,
    base_version: str,
    has_release_trigger: bool,
    repo: Path,
    known_release_paths: set[str],
) -> list[str]:
    errors: list[str] = []
    releases = HEADING_RE.findall(changelog)
    changelog_lines = changelog.splitlines()

    if len(releases) != len(set(releases)):
        errors.append("CHANGELOG.md contains duplicate release headings")

    if has_release_trigger:
        if current_release != expected_latest:
            errors.append(
                f"current release {current_release} does not match git-derived release "
                f"{expected_latest}"
            )
        if releases and releases[0] != expected_latest:
            errors.append(
                f"CHANGELOG.md latest release is {releases[0]!r}, expected {expected_latest!r}"
            )
        if base_version != expected_latest and base_version not in releases:
            errors.append(
                "CHANGELOG.md must preserve previous release history; missing "
                f"{base_version!r}"
            )
    else:
        if current_release != base_version:
            errors.append(
                "release scan found no release-triggering commits; release heading should remain "
                f"{base_version!r}"
            )

    sorted_releases = sorted(releases, key=parse_version, reverse=True)
    if releases != sorted_releases:
        errors.append("CHANGELOG.md release headings are not newest-first")

    latest_tuple = parse_version(expected_latest)
    base_tuple = parse_version(base_version)
    intermediate = [
        release
        for release in releases
        if base_tuple < parse_version(release) < latest_tuple
    ]
    if intermediate:
        errors.append(
            "CHANGELOG.md contains intermediate versions within one release run: "
            f"{intermediate}"
        )

    for line_number, line in enumerate(changelog_lines, start=1):
        if not line.startswith("- "):
            continue
        match = CHANGELOG_ENTRY_RE.match(line)
        if not match:
            errors.append(
                "CHANGELOG.md entry must start with git hash and Conventional "
                f"Commit prefix at line {line_number}: {line}"
            )
            continue
        commit_hash = match.group("hash")
        if not commit_exists(repo, commit_hash):
            errors.append(f"CHANGELOG.md entry references unknown commit {commit_hash}")
            continue
        subject = run_git(repo, "show", "-s", "--format=%s", commit_hash)
        if is_release_bookkeeping_commit(repo, commit_hash, subject, known_release_paths):
            errors.append(
                "CHANGELOG.md entry references release bookkeeping commit "
                f"{commit_hash}, which must be omitted"
            )
            continue
        found_prefix = match.group("prefix")
        expected_prefix = commit_prefix(repo, commit_hash)
        if found_prefix != expected_prefix:
            errors.append(
                "CHANGELOG.md entry prefix does not match commit subject for "
                f"{commit_hash}: found {found_prefix!r}, expected {expected_prefix!r}"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="Repository root")
    parser.add_argument(
        "--expected-version",
        help="Explicit target version for breaking-change runs (e.g. v1.0.0)",
    )
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    errors: list[str] = []

    version_path = repo / "VERSION"
    changelog_path = repo / "CHANGELOG.md"
    readme_path = repo / "README.md"

    explicit_version = args.expected_version.strip() if args.expected_version else None
    discovered_packages = package_paths(repo)
    known_release_paths = release_metadata_paths(repo, discovered_packages)

    if not version_path.exists():
        errors.append("VERSION is missing")
        release_version = ""
    else:
        release_version = version_path.read_text(encoding="utf-8").strip()
        if not release_version.startswith("v"):
            errors.append("VERSION must use vX.Y.Z format")
        elif not SEMVER_RE.match(release_version[1:]):
            errors.append(f"VERSION is not valid SemVer: {release_version}")
        else:
            try:
                parse_version(release_version)
            except ValueError as exc:
                errors.append(str(exc))

    if explicit_version:
        if not explicit_version.startswith("v"):
            explicit_version = f"v{explicit_version}"
        try:
            parse_version(explicit_version)
        except ValueError:
            errors.append(f"invalid --expected-version: {explicit_version}")

    if (repo / "CHANGELOGS").exists():
        errors.append("legacy CHANGELOGS file must be removed after migrating to CHANGELOG.md")

    package_version = release_version[1:] if release_version.startswith("v") else release_version
    for path in discovered_packages:
        data = read_json(path)
        found = data.get("version")
        if found != package_version:
            errors.append(
                f"{path.relative_to(repo)} version is {found!r}, expected {package_version!r}"
            )

    expected_latest: str | None = None
    base_version: str | None = None
    has_release_trigger = False
    if explicit_version and not errors:
        try:
            expected_latest, base_version, has_release_trigger = expected_latest_version(
                repo,
                explicit_version,
                known_release_paths=known_release_paths,
            )
        except ValueError as exc:
            errors.append(str(exc))
    elif not errors:
        try:
            expected_latest, base_version, has_release_trigger = expected_latest_version(
                repo,
                known_release_paths=known_release_paths,
            )
        except ValueError as exc:
            errors.append(str(exc))

    if release_version and expected_latest:
        if expected_latest != release_version:
            if has_release_trigger:
                errors.append(
                    f"VERSION is {release_version} but git-derived expected version is "
                    f"{expected_latest}"
                )
            else:
                errors.append(
                    f"No release-triggering commits were found; VERSION should remain "
                    f"{expected_latest}"
                )

    if not changelog_path.exists():
        errors.append("CHANGELOG.md is missing")
    else:
        changelog = changelog_path.read_text(encoding="utf-8")
        if UNRELEASED_RE.search(changelog):
            errors.append("CHANGELOG.md must not contain an Unreleased section or label")
        latest = latest_changelog_version(changelog)
        if latest != release_version:
            errors.append(
                f"CHANGELOG.md latest release is {latest!r}, expected {release_version!r}"
            )
        if release_version and base_version is not None and expected_latest is not None:
            try:
                errors.extend(
                    validate_changelog_history(
                        changelog,
                        release_version,
                        expected_latest,
                        base_version,
                        has_release_trigger,
                        repo,
                        known_release_paths,
                    )
                )
            except ValueError as exc:
                errors.append(str(exc))

    if readme_path.exists():
        readme = readme_path.read_text(encoding="utf-8")
        if release_version and README_SEMVER_RE.search(readme):
            if release_version not in readme:
                errors.append(f"README.md does not contain {release_version}")

    if not errors and not has_release_trigger:
        print("No release-triggering commits found; no release bump required.")

    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1

    print(f"Release version is consistent: {release_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
