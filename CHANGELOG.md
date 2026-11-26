# Changelog

**English** · [简体中文](./CHANGELOG.zh-CN.md)

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.2.0] - 2026-11-27

### Added

- `session-cleanup` skill: close out a session by finishing in-scope loose ends, fixing doc drift, committing session-owned changes, moving throwaway files to the Trash and reporting their size, and re-checking; session records are never moved
- Simplified Chinese versions of the README (`README.zh-CN.md`) and changelog (`CHANGELOG.zh-CN.md`)

### Changed

- Redesigned the README: badges, a skill catalog grouped by category, a diagram of how the skills work together, a requirements table, and the repository layout

## [1.1.0] - 2026-11-26

### Added

- `git-commit-to-main` skill: local commit-splitting and fast-forward-to-main workflow
- `distill-session-history` skill: distill agent session history into durable project knowledge
- `reconcile-project-docs` skill: reconcile project docs with conversation and repository state
- `maintain-llms-txt` skill: maintain and validate `llms.txt` navigation files
- `maintain-release-version` skill: maintain release versions and changelog entries
- `maintain-todo-md` skill: maintain and validate `TODO.md` task lists

## [1.0.0] - 2026-03-22

### Added

- `mise-guide` skill: teaches agents how to use mise for dev tool versions, environment variables, and project tasks

[1.2.0]: https://github.com/kinoward/agent-skills/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/kinoward/agent-skills/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/kinoward/agent-skills/releases/tag/v1.0.0
