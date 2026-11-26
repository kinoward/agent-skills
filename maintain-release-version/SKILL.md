---
name: maintain-release-version
description: Maintain repository release versions and changelog entries for a single-version project. Use when updating or validating CHANGELOG.md, VERSION, package.json version fields, optional README project version text, release notes, or when deriving version bumps from git history and Conventional Commits.
---

# Maintain Release Version

## Overview

Use this skill to keep release history complete and version files synchronized for a single-version repository or project. It keeps one project version across `VERSION`, `CHANGELOG.md`, and any discovered package files; it does not manage independent package releases.

## Rules

- Follow Semantic Versioning shape: package versions are `X.Y.Z`; `VERSION` and release headings use `vX.Y.Z`.
- Keep one version across discovered `package.json` files that declare a `version` field. The validator discovers the root package and workspace package files from `package.json` workspaces and `pnpm-workspace.yaml`.
- Keep README version text synchronized with `VERSION` only when the target project already uses README version text.
- Maintain `CHANGELOG.md` in Keep a Changelog style: `# Changelog` and newest release first. Do not include an `Unreleased` section or the word `Unreleased`.
- Do not use raw git log output as changelog content. Rewrite entries into concise, human-readable changes.
- Prefix every changelog bullet with the source git commit short hash and Conventional Commit type/scope in this exact shape: ``- `abc1234` `feat(web)`: Human-readable change.`` Use `docs`, `chore(repo)`, `fix`, and similar prefixes from the original commit header.
- Do not write changelog/version bookkeeping into `CHANGELOG.md`. Changes that only update `CHANGELOG.md`, `VERSION`, package `version` fields, README version text, release metadata, or related llms navigation are release maintenance and must not become changelog entries.
- Do not update MIME parameters such as `version=0.0.4`; only update project release versions.

## Reconnaissance

Start every release run with read-only checks before proposing a bump:

1. Read `VERSION`, `CHANGELOG.md`, optional README version text, and discovered package files.
2. Find the latest reachable `vX.Y.Z` tag; if none exists, find the latest commit that changed `VERSION`.
3. List unrecorded commits in stable order with `git rev-list --reverse <base>..HEAD`.
4. Check whether discovered package versions, optional README version text, and the latest changelog heading already match `VERSION`.
5. Present the proposed next version and changelog scope before writing files.
6. If no scanned commit maps to `fix`/`feat`/`perf` or an explicit breaking-change run, stop and report “no release needed”.

## Git History Workflow

1. Read `VERSION`, `CHANGELOG.md`, discovered package files, and optional README version text.
2. Find the scan base:
   - Prefer the latest reachable `vX.Y.Z` git tag.
   - If no tag exists, use the latest commit that changed `VERSION`.
3. Scan unrecorded commits in stable graph order:
   `git rev-list --reverse <base>..HEAD`
4. Compute version progression commit-by-commit in order:
   - `fix` and `perf` each bump patch by 1.
   - `feat` bumps minor by 1 and resets patch to 0.
   - Breaking commits (`!`, `BREAKING CHANGE:`, or `BREAKING-CHANGE:`) must stop this workflow until a target major is explicitly confirmed by the user.
   - Non-release commits (`docs`, `chore`, `refactor`, `test`, `build`, `ci`, `style`, and other non-breaking types) do not trigger release.
5. Release bookkeeping commits are excluded from changelog inclusion and version calculation.
6. Create exactly one new release section for a release run, with final version based on the sequential bump result. Do not create one section per bump.
7. Do not add an `Unreleased` heading before or after the release section.
8. Treat the release/version commit that updates `VERSION` as the next scan anchor, so previously recorded commits are not collected again.

## Bump Policy

- `!` in the Conventional Commit header, `BREAKING CHANGE:`, or `BREAKING-CHANGE:` in the body/footer means breaking and must be handled with explicit user confirmation.
- `feat` bumping: minor+1, patch reset to 0.
- `fix` bumping: patch+1.
- `perf` bumping: patch+1.
- `docs`, `chore`, `refactor`, `test`, `build`, `ci`, `style`, and other non-breaking non-release types do not trigger release by default.
- Do **not** use aggregate/max-impact logic. Apply bumps sequentially in `git rev-list --reverse <base>..HEAD` order.
- Non-triggering scanned commits may still be listed in CHANGELOG if they are within a window that has a real `fix`/`perf`/`feat` or user-approved breaking release.

## Release Execution Rules

- If a scanned window contains only non-triggering commits, do not create a new patch release and do not bump version.
- Breaking runs must stop unless `--expected-version` is provided explicitly (for example `--expected-version v1.0.0`).
- If breaking is confirmed, run once with the agreed version and do not create per-commit intermediate release headings/sections.

## Changelog Mapping

- `feat` -> `Added`
- `fix` -> `Fixed`
- security-sensitive fixes -> `Security`
- deprecations -> `Deprecated`
- removals -> `Removed`
- docs, chore, build, ci, style, refactor, test, perf, and release maintenance -> `Changed`
- Mark breaking entries clearly in the release text.
- Omit entries whose only user-visible meaning is that `CHANGELOG.md`, `VERSION`, package versions, README version text, or release metadata changed.
- Keep every bullet traceable: start it with the commit hash and Conventional Commit prefix before the human-readable summary.

## External References

- `release-please`, `semantic-release`, and Changesets are mature references for Conventional Commit parsing, SemVer impact, release PRs, and changelog automation.
- GitHub `github-release` and Vercel `autoship` are useful staged-review references: analyze changes, propose a release type, generate a summary, then get review before writing or publishing.
- Do not adopt independent package releases, `Unreleased` sections, automatic publishing, changeset files, or root-only package release assumptions unless the target project explicitly uses a different release workflow. This skill's default is one fixed repository/project version and the bundled validator remains the gate.

## Failure Handling

- If no tag exists and `VERSION` has no history, stop and ask for an explicit base version instead of inventing history.
- If a commit is not Conventional Commit formatted, stop and ask for an explicit decision to fix the commit history, exclude the commit as release bookkeeping, or choose another scan base. Do not invent a changelog prefix that the validator cannot verify.
- If no release-triggering commit (`fix`, `perf`, `feat`) is found in the scan window, report no release needed; do not produce a docs/chore-only patch bump.
- If a breaking commit is found and no explicit target version is set, stop with a `--expected-version` prompt and do not auto-bump major/minor.
- If `CHANGELOG.md` already records a commit, do not duplicate that commit in the new release section.
- If version files disagree, synchronize them to the single target version before validating.
- If validator output reports an unexpected git-derived version, re-check the scan base, unrecorded commits, and release bookkeeping exclusions.

## Validation

Run project validation after release edits:

```bash
TARGET_REPO="$PWD"
SKILL_DIR="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}/maintain-release-version"
python "$SKILL_DIR/scripts/validate_release_version.py" --repo "$TARGET_REPO"
```

For breaking commits, validate with explicit target:

```bash
TARGET_REPO="$PWD"
SKILL_DIR="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}/maintain-release-version"
python "$SKILL_DIR/scripts/validate_release_version.py" --repo "$TARGET_REPO" --expected-version vX.Y.Z
```

Also run `git diff --check` for release file edits.

Only when editing this skill or its bundled validator/tests, run skill self-validation:

```bash
SKILL_DIR="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}/maintain-release-version"
python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" "$SKILL_DIR"
cd "$SKILL_DIR"
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s scripts -p 'test_validate_release_version.py'
```

Do not run full project checks for version metadata alone. Run target project checks only when the release work also changes code, package configuration beyond version fields, or other paths whose local rules require validation. Examples in JavaScript projects may include:

```bash
pnpm lint
pnpm typecheck
pnpm build
```

## Finish Handoff

After release edits and validation pass, use `git-commit-to-main` to commit the release maintenance changes unless the user explicitly asks not to commit.

- Tell `git-commit-to-main` that the intended scope is `CHANGELOG.md`, `VERSION`, discovered package files, optional README version text, and any related `llms.txt` files changed by the release work.
- Recommend this Conventional Commit message shape: `chore(release): publish vX.Y.Z`.
- Let `git-commit-to-main` handle contribution checks, branch creation, staging, commits, validation, and fast-forward merge back to `main`.
- Do not include release/version bookkeeping as a `CHANGELOG.md` entry.
- Do not leave version or changelog history edits uncommitted unless the user explicitly asks not to commit.
- Do not stage, commit, branch, merge, push, or create pull requests directly from this skill.
