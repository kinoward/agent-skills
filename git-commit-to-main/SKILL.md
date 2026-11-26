---
name: git-commit-to-main
description: 'Local-only workflow that runs target project maintenance when applicable, then analyzes current git changes, splits them into logical commit groups, creates a Conventional Branch, generates Conventional Commit messages by orchestrating make-repo-contribution, conventional-branch, commit-message-storyteller, conventional-commit, and git-commit, fast-forwards the branch into main, and deletes the local branch. Use when the user asks to commit local changes, split commits, commit and merge to main, or quickly finish the local git workflow. Do not use for push, PR, GitHub issues, remote branches, or online GitHub workflows.'
---

# Git Commit to Main

## Overview

Use this skill to finish a local-only git workflow from dirty worktree to clean `main`. Before the commit workflow begins, it runs target project maintenance skills when the project has `llms.txt`, `TODO.md`, or local rules that require them. It then coordinates the five git workflow skills available to the agent; it does not replace their rules.

This skill must not push, create PRs, create issues, manage remote branches, or access GitHub online state. If the user asks for any remote or GitHub action, stop and route to the future remote workflow instead.

When this skill references other git workflow skills, this local-only rule takes precedence over any pull, push, PR, issue, remote branch, or GitHub online guidance in those skills.

When running bundled maintenance scripts, resolve user-level skills with `SKILL_ROOT="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}"` unless the target project documents a different skill root.

## Required Skill Order

1. If the target project has `llms.txt` files or local rules requiring them, read and apply `maintain-llms-txt` to locate, update, and validate affected navigation files for the current working tree.
2. If the target project has `TODO.md` or local rules requiring task-file maintenance, read and apply `maintain-todo-md` when the current diff, git history, conversation, or project evidence changes project memory.
3. Read and apply `make-repo-contribution` for contribution safety and repository guidance.
4. Use `conventional-branch` to choose and validate the temporary branch name.
5. Use `commit-message-storyteller` to explain why each logical commit exists.
6. Use `conventional-commit` to verify each commit message shape.
7. Use `git-commit` to stage the intended files and execute each commit.

## Workflow

### 1. Pre-maintenance

- Run `maintain-llms-txt` first against the current working tree when applicable.
- Run `maintain-todo-md` second when applicable.
- Treat any maintenance edits as ordinary working tree changes handled by this skill's later inspect, group, and commit steps.
- If an applicable maintenance skill fails validation, stop and report the failure instead of beginning the commit workflow.

### 2. Inspect

- Run `git status -sb`.
- Run `git diff --stat` and inspect the actual diff before staging.
- Identify and report staged, unstaged, untracked, and deleted files separately.
- If any changes are already staged at startup, list the staged content and the remaining unstaged/untracked/deleted content, then ask whether the staged changes belong in this workflow. Do not modify the index or commit until the user confirms the scope.
- Refuse to proceed if secrets, real `.env` files, private keys, production connection strings, generated build output, dependency folders, or cache files would be committed.
- If the worktree contains unrelated user changes that cannot be grouped safely, list the groups and ask for scope before staging.

### 3. Group

- Group changes by intent, not by directory alone.
- Prefer separate commits for release/version updates, navigation docs, code behavior, tests, configuration, and generated artifacts.
- Include pre-maintenance `llms.txt` and `TODO.md` edits in the logical group they support, unless they clearly warrant their own maintenance commit.
- Keep one commit when all files serve one clear purpose.
- Do not split a file with unrelated hunks unless interactive staging is safe and necessary; otherwise ask for direction.

### 4. Branch

- After the worktree scope is confirmed, switch to `main` and create a new temporary branch before committing.
- If the current branch is not `main` and contains local commits that are not merged into `main`, stop and report those commits instead of mixing existing branch history into this workflow.
- Generate the branch with Conventional Branch format: `<type>/<description>`.
- Default to `chore/<description>` for repository maintenance and docs-only local workflows; use `feature/`, `bugfix/`, `hotfix/`, or `release/` only when the diff warrants it.
- Never create `codex/` prefixed branches unless the user explicitly asks.

### 5. Commit

For each group:

- Stage only the files in that group.
- Generate a Conventional Commit message that explains the intent.
- Keep the subject under 72 characters and in imperative mood.
- Use a body when the reason is not obvious from the subject.
- Commit with `git commit`; do not use `--no-verify` unless the user explicitly asks.
- After each commit, confirm no unintended files are staged.

### 6. Validate

- Run the smallest relevant checks for the changed files before merging.
- Always run `git diff --check` if there are still unstaged changes or before final merge when docs are involved.
- If the change touches `llms.txt`, run the validation command documented by `maintain-llms-txt` from the user-level skill root.
- If the change touches `TODO.md`, run the validation command documented by `maintain-todo-md` from the user-level skill root.
- Do not run skill self-validation such as `quick_validate.py` or bundled skill tests merely because a skill was used during the workflow.
- Run skill self-validation only when staged files include skill implementation, metadata, scripts, references, assets, or tests.
- If checks fail, fix the problem before merging or stop with the failure details.

### 7. Merge to Main

- Switch to `main`.
- Merge only with `git merge --ff-only <branch>`.
- Never use `git merge --no-ff` in this skill.
- If fast-forward fails, rebase the work branch onto `main` only when the resolution is straightforward and safe. If conflicts or risk remain, stop and report the reason.
- After a successful fast-forward merge, delete the local temporary branch with `git branch -d <branch>`.

## Final Report

Report:

- branch name created and deleted
- commit hashes and messages
- validation commands run and results
- final branch and clean/dirty status
- whether anything was intentionally not committed

Do not report push, PR, or remote state because this skill is local-only.
