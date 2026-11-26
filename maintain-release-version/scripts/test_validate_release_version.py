"""Tests for validate_release_version.py with temporary git repositories."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from validate_release_version import expected_latest_version


VALIDATOR = Path(__file__).with_name("validate_release_version.py")
PACKAGE_NAME = "sample-package"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _write_package_json(
    path: Path,
    version: str,
    *,
    workspaces: list[str] | None = None,
    workspace_object: list[str] | None = None,
) -> None:
    data: dict[str, object] = {"name": PACKAGE_NAME, "version": version}
    if workspaces is not None:
        data["workspaces"] = workspaces
    if workspace_object is not None:
        data["workspaces"] = {"packages": workspace_object}

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data) + "\n", encoding="utf-8")


def _write_package_version_only(path: Path, version: str) -> None:
    if path.exists():
        try:
            data: dict = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {"name": PACKAGE_NAME}
    else:
        data = {"name": PACKAGE_NAME}

    data["version"] = version
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data) + "\n", encoding="utf-8")


def _init_repo(
    base_version: str,
    tmpdir: Path,
    *,
    include_readme: bool = True,
    readme_text: str | None = None,
    create_root_package: bool = True,
    root_workspaces: list[str] | None = None,
    root_workspace_object: list[str] | None = None,
    pnpm_workspace_globs: list[str] | None = None,
    workspace_package_dirs: list[str] | None = None,
) -> list[Path]:
    _git(tmpdir, "init", "-b", "main")
    _git(tmpdir, "config", "user.name", "Release Validator Test")
    _git(tmpdir, "config", "user.email", "validator@test.local")

    (tmpdir / "VERSION").write_text(f"v{base_version}\n", encoding="utf-8")
    if include_readme:
        (tmpdir / "README.md").write_text(
            readme_text or f"# repo\n\nVersion: v{base_version}\n",
            encoding="utf-8",
        )

    package_paths: list[Path] = []
    if create_root_package:
        root_package = tmpdir / "package.json"
        _write_package_json(
            root_package,
            base_version,
            workspaces=root_workspaces,
            workspace_object=root_workspace_object,
        )
        package_paths.append(root_package)

    workspace_package_dirs = workspace_package_dirs or []
    for directory in workspace_package_dirs:
        package_json = tmpdir / directory / "package.json"
        _write_package_json(package_json, base_version)
        package_paths.append(package_json)

    if pnpm_workspace_globs:
        (tmpdir / "pnpm-workspace.yaml").write_text(
            "packages:\n"
            + "\n".join(f"  - {entry}" for entry in pnpm_workspace_globs)
            + "\n",
            encoding="utf-8",
        )

    (tmpdir / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## [v{base_version}] - 2026-01-01\n",
        encoding="utf-8",
    )
    (tmpdir / "work.txt").write_text("base\n", encoding="utf-8")

    _git(tmpdir, "add", ".")
    _git(tmpdir, "commit", "-m", f"chore(release): publish v{base_version}")
    _git(tmpdir, "tag", f"v{base_version}")

    return package_paths


def _add_commit(tmpdir: Path, subject: str, body: str | None = None) -> None:
    work = tmpdir / "work.txt"
    work.write_text(work.read_text(encoding="utf-8") + f"{subject}\n", encoding="utf-8")
    _git(tmpdir, "add", "work.txt")
    if body:
        _git(tmpdir, "commit", "-m", subject, "-m", body)
    else:
        _git(tmpdir, "commit", "-m", subject)


def _write_release_files(
    tmpdir: Path,
    version: str,
    changelog_body: str = "",
    package_paths: list[Path] | None = None,
    *,
    include_readme: bool = True,
    readme_text: str | None = None,
) -> None:
    package_paths = package_paths or [
        p for p in sorted(tmpdir.rglob("package.json")) if ".git" not in p.parts
    ]

    (tmpdir / "VERSION").write_text(f"v{version}\n", encoding="utf-8")
    if include_readme:
        (tmpdir / "README.md").write_text(
            readme_text or f"# repo\n\nVersion: v{version}\n",
            encoding="utf-8",
        )

    for package_path in package_paths:
        _write_package_version_only(package_path, version)

    (tmpdir / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## [v{version}] - 2026-01-02\n"
        f"{changelog_body}\n"
        "\n## [v0.2.3] - 2026-01-01\n",
        encoding="utf-8",
    )


def _commit_release_files(
    tmpdir: Path,
    version: str,
    subject: str,
    changelog_body: str = "",
    package_paths: list[Path] | None = None,
) -> None:
    if package_paths is None:
        package_paths = [
            p
            for p in sorted(tmpdir.rglob("package.json"))
            if p.suffix == ".json" and ".git" not in p.parts
        ]

    _write_release_files(tmpdir, version, changelog_body, package_paths)
    _git(tmpdir, "add", "VERSION", "CHANGELOG.md")
    if (tmpdir / "README.md").exists():
        _git(tmpdir, "add", "README.md")
    for package_path in package_paths:
        _git(tmpdir, "add", str(package_path.relative_to(tmpdir)))
    _git(tmpdir, "commit", "-m", subject)


def _run_validator(tmpdir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python", str(VALIDATOR), "--repo", str(tmpdir), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


class ValidateReleaseVersionTests(unittest.TestCase):
    def test_non_trigger_commits_do_not_bump(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo("0.2.3", repo)

            _add_commit(repo, "docs(readme): update documentation")
            _add_commit(repo, "chore(repo): maintenance task")

            version, base_version, has_release_trigger = expected_latest_version(repo)
            self.assertEqual(version, "v0.2.3")
            self.assertEqual(base_version, "v0.2.3")
            self.assertFalse(has_release_trigger)

    def test_non_trigger_commit_types_do_not_bump(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo("0.2.3", repo)

            for subject in (
                "docs(readme): update documentation",
                "chore(repo): maintenance task",
                "refactor(core): simplify helper",
                "test(core): add coverage",
                "build(repo): tune build config",
                "ci(repo): update workflow",
                "style(ui): format controls",
            ):
                _add_commit(repo, subject)

            version, base_version, has_release_trigger = expected_latest_version(repo)
            self.assertEqual(version, "v0.2.3")
            self.assertEqual(base_version, "v0.2.3")
            self.assertFalse(has_release_trigger)

    def test_release_bookkeeping_commits_are_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            package_paths = _init_repo("0.2.3", repo)
            _commit_release_files(repo, "0.2.4", "chore(release): publish v0.2.4", package_paths=package_paths)

            version, base_version, has_release_trigger = expected_latest_version(repo)
            self.assertEqual(version, "v0.2.3")
            self.assertEqual(base_version, "v0.2.3")
            self.assertFalse(has_release_trigger)

    def test_release_bookkeeping_changelog_entry_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            package_paths = _init_repo("0.2.3", repo)
            _add_commit(repo, "fix(core): patch small bug")
            fix_hash = _git(repo, "rev-parse", "--short", "HEAD")
            _commit_release_files(
                repo,
                "0.2.4",
                "chore(release): update v0.2.4",
                "",
                package_paths=package_paths,
            )
            release_hash = _git(repo, "rev-parse", "--short", "HEAD")
            _write_release_files(
                repo,
                "0.2.4",
                "\n### Fixed\n\n"
                f"- `{fix_hash}` `fix(core)`: Patched a small bug.\n"
                f"- `{release_hash}` `chore(release)`: Published release.",
                package_paths=package_paths,
            )

            result = _run_validator(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("release bookkeeping commit", result.stdout)

    def test_fix_mentioning_release_metadata_still_bumps(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo("0.2.3", repo)
            _add_commit(
                repo,
                "fix(api): repair metadata endpoint",
                "This fixes release metadata shown to users.",
            )

            version, base_version, has_release_trigger = expected_latest_version(repo)
            self.assertEqual(version, "v0.2.4")
            self.assertEqual(base_version, "v0.2.3")
            self.assertTrue(has_release_trigger)

    def test_fix_changelog_entry_can_mention_release_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            package_paths = _init_repo("0.2.3", repo)
            _add_commit(
                repo,
                "fix(api): repair release metadata endpoint",
                "This fixes release metadata shown to users.",
            )
            fix_hash = _git(repo, "rev-parse", "--short", "HEAD")
            _write_release_files(
                repo,
                "0.2.4",
                "\n### Fixed\n\n"
                f"- `{fix_hash}` `fix(api)`: Repaired release metadata endpoint.",
                package_paths=package_paths,
            )

            result = _run_validator(repo)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_release_must_preserve_previous_changelog_history(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            package_paths = _init_repo("0.2.3", repo)
            _add_commit(repo, "fix(core): patch small bug")
            fix_hash = _git(repo, "rev-parse", "--short", "HEAD")
            _write_release_files(
                repo,
                "0.2.4",
                "\n### Fixed\n\n"
                f"- `{fix_hash}` `fix(core)`: Patched a small bug.",
                package_paths=package_paths,
            )
            (repo / "CHANGELOG.md").write_text(
                "# Changelog\n\n"
                "## [v0.2.4] - 2026-01-02\n\n"
                "### Fixed\n\n"
                f"- `{fix_hash}` `fix(core)`: Patched a small bug.\n",
                encoding="utf-8",
            )

            result = _run_validator(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must preserve previous release history", result.stdout)

    def test_one_fix(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo("0.2.3", repo)
            _add_commit(repo, "fix(core): patch small bug")

            version, base_version, has_release_trigger = expected_latest_version(repo)
            self.assertEqual(version, "v0.2.4")
            self.assertEqual(base_version, "v0.2.3")
            self.assertTrue(has_release_trigger)

    def test_one_perf(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo("0.2.3", repo)
            _add_commit(repo, "perf(core): reduce latency")

            version, base_version, has_release_trigger = expected_latest_version(repo)
            self.assertEqual(version, "v0.2.4")
            self.assertEqual(base_version, "v0.2.3")
            self.assertTrue(has_release_trigger)

    def test_three_fixes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo("0.2.3", repo)
            _add_commit(repo, "fix(core): patch one")
            _add_commit(repo, "fix(ui): patch two")
            _add_commit(repo, "fix(web): patch three")

            version, base_version, has_release_trigger = expected_latest_version(repo)
            self.assertEqual(version, "v0.2.6")
            self.assertEqual(base_version, "v0.2.3")
            self.assertTrue(has_release_trigger)

    def test_feat_resets_patch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo("0.2.3", repo)
            _add_commit(repo, "feat(web): add new feature")

            version, base_version, has_release_trigger = expected_latest_version(repo)
            self.assertEqual(version, "v0.3.0")
            self.assertEqual(base_version, "v0.2.3")
            self.assertTrue(has_release_trigger)

    def test_fix_feat_fix_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo("0.2.3", repo)
            _add_commit(repo, "fix(core): patch issue")
            _add_commit(repo, "feat(web): add feature")
            _add_commit(repo, "fix(core): patch after release feature")

            version, base_version, has_release_trigger = expected_latest_version(repo)
            self.assertEqual(version, "v0.3.1")
            self.assertEqual(base_version, "v0.2.3")
            self.assertTrue(has_release_trigger)

    def test_breaking_commit_requires_expected_version(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo("0.2.3", repo)
            _add_commit(
                repo,
                "feat(api)!: change payload format",
                "BREAKING CHANGE: payload schema changed",
            )

            with self.assertRaisesRegex(
                ValueError,
                "found a breaking change commit but no --expected-version",
            ):
                expected_latest_version(repo)

    def test_breaking_hyphen_footer_requires_expected_version(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo("0.2.3", repo)
            _add_commit(
                repo,
                "fix(api): change payload format",
                "BREAKING-CHANGE: payload schema changed",
            )

            with self.assertRaisesRegex(
                ValueError,
                "found a breaking change commit but no --expected-version",
            ):
                expected_latest_version(repo)

    def test_invalid_expected_version_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo("0.2.3", repo)
            _add_commit(
                repo,
                "feat(api)!: change payload format",
                "BREAKING CHANGE: payload schema changed",
            )

            result = _run_validator(repo, "--expected-version", "bad-version")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid --expected-version", result.stdout)

    def test_docs_only_bump_is_rejected_by_cli(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo("0.2.3", repo)
            _add_commit(repo, "docs(readme): update documentation")
            _write_release_files(repo, "0.2.4")

            result = _run_validator(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("No release-triggering commits", result.stdout)

    def test_breaking_run_with_expected_version(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo("0.2.3", repo)
            _add_commit(
                repo,
                "feat(api)!: change payload format",
                "BREAKING CHANGE: payload schema changed",
            )

            version, base_version, has_release_trigger = expected_latest_version(
                repo, "v1.0.0"
            )
            self.assertEqual(version, "v1.0.0")
            self.assertEqual(base_version, "v0.2.3")
            self.assertTrue(has_release_trigger)

    def test_breaking_after_nonbreaking_commits_with_expected_version(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo("0.2.3", repo)
            _add_commit(repo, "fix(core): patch issue")
            _add_commit(
                repo,
                "feat(api)!: change payload format",
                "BREAKING CHANGE: payload schema changed",
            )
            _add_commit(repo, "fix(core): follow-up fix")

            version, base_version, has_release_trigger = expected_latest_version(
                repo, "v1.0.0"
            )
            self.assertEqual(version, "v1.0.0")
            self.assertEqual(base_version, "v0.2.3")
            self.assertTrue(has_release_trigger)

    def test_root_only_package_json_without_app_or_package_folder(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            package_paths = _init_repo(
                "0.2.3",
                repo,
                workspace_package_dirs=[],
            )

            self.assertEqual(len(package_paths), 1)
            self.assertEqual(package_paths[0], repo / "package.json")

            result = _run_validator(repo)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_no_package_json_releases_validation_still_runs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo(
                "0.2.3",
                repo,
                create_root_package=False,
            )

            result = _run_validator(repo)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_pnpm_workspace_discovery_discovers_custom_workspace_packages(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            package_paths = _init_repo(
                "0.2.3",
                repo,
                pnpm_workspace_globs=["services/*"],
                workspace_package_dirs=["services/api", "services/ui"],
            )

            mismatched = package_paths[1]
            _write_package_version_only(mismatched, "0.2.4")

            result = _run_validator(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("version is '0.2.4'", result.stdout)

    def test_root_workspaces_array_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            package_paths = _init_repo(
                "0.2.3",
                repo,
                root_workspaces=["modules/*"],
                workspace_package_dirs=["modules/core"],
            )

            mismatch = package_paths[1]
            _write_package_version_only(mismatch, "0.2.4")

            result = _run_validator(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("version is '0.2.4'", result.stdout)

    def test_root_workspaces_object_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            package_paths = _init_repo(
                "0.2.3",
                repo,
                root_workspace_object=["libs/*"],
                workspace_package_dirs=["libs/core"],
            )

            mismatch = package_paths[1]
            _write_package_version_only(mismatch, "0.2.4")

            result = _run_validator(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("version is '0.2.4'", result.stdout)

    def test_readme_can_be_missing_or_without_version_text(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo(
                "0.2.3",
                repo,
                include_readme=False,
            )

            result = _run_validator(repo)
            self.assertEqual(result.returncode, 0, result.stdout)

            (repo / "README.md").write_text(
                "# repo\n\nRelease docs without explicit version marker.\n",
                encoding="utf-8",
            )
            result = _run_validator(repo)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_release_bookkeeping_paths_are_driven_by_discovered_workspace_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            package_paths = _init_repo(
                "0.2.3",
                repo,
                pnpm_workspace_globs=["services/*"],
                workspace_package_dirs=["services/api"],
            )
            _add_commit(repo, "fix(core): patch small bug")
            fix_hash = _git(repo, "rev-parse", "--short", "HEAD")

            _commit_release_files(
                repo,
                "0.2.4",
                "chore(release): publish v0.2.4",
                "\n### Fixed\n\n"
                f"- `{fix_hash}` `fix(core)`: Patched a small bug.",
                package_paths=package_paths,
            )
            release_hash = _git(repo, "rev-parse", "--short", "HEAD")
            _write_release_files(
                repo,
                "0.2.4",
                "\n### Fixed\n\n"
                f"- `{fix_hash}` `fix(core)`: Patched a small bug.\n"
                f"- `{release_hash}` `chore(release)`: Published release.",
                package_paths=package_paths,
            )

            result = _run_validator(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("references release bookkeeping commit", result.stdout)

    def test_release_bookkeeping_allows_nested_llms_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            package_paths = _init_repo("0.2.3", repo)
            _add_commit(repo, "fix(core): patch small bug")

            nested_llms = repo / "docs" / "agent" / "llms.txt"
            nested_llms.parent.mkdir(parents=True)
            nested_llms.write_text(
                "# Agent Docs\n\n"
                "> Agent documentation index.\n\n"
                "Details.\n\n"
                "## Key Files\n\n"
                "## Boundaries\n\n"
                "## Validation\n\n"
                "## Related\n",
                encoding="utf-8",
            )

            _commit_release_files(
                repo,
                "0.2.4",
                "chore(release): publish v0.2.4",
                package_paths=package_paths,
            )
            _git(repo, "add", "docs/agent/llms.txt")
            _git(repo, "commit", "--amend", "--no-edit")

            version, base_version, has_release_trigger = expected_latest_version(repo)
            self.assertEqual(version, "v0.2.4")
            self.assertEqual(base_version, "v0.2.3")
            self.assertTrue(has_release_trigger)


if __name__ == "__main__":
    unittest.main()
