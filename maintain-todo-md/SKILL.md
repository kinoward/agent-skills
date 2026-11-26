---
name: maintain-todo-md
description: 'Maintain a repository TODO.md using markdown task-list conventions, this skill''s default task policy, and target project local rules. Use when adding, updating, moving, closing, validating, or reorganizing TODO.md tasks, backlog items, blocked work, done entries, tags, owners, project markers, or due metadata.'
---

# Maintain TODO.md

## Overview

Use this skill to keep a repository `TODO.md` as a small, git-friendly project memory. It follows `todo-md` and GitHub task-list conventions while staying lightweight.

Community `todo.md` formats and GitHub task lists are references only. By default, this skill maintains a root `TODO.md` with `Next`, `Backlog`, `Blocked`, and `Done ✓`, using `- [ ]` for open tasks and `- [x]` for completed tasks. Follow target project local rules when they define a different task file or section model.

## Scope Boundary

- Only edit the target task file, defaulting to repository root `TODO.md`.
- Use conversation context, review findings, git history, current diffs, changed files, and current project files as read-only evidence for task decisions.
- Do not modify code, release files, issues, pull requests, other docs, or bundled skill resources from this skill.
- Do not generate tasks by sweeping the whole repository. Add, update, close, or remove tasks only when there is clear evidence that the task belongs in project memory.

## Quick Start

1. Open `TODO.md`.
2. Add, move, or complete tasks in the correct section.
3. Keep tasks one line when possible and use clear tags such as `#docs`, `#security`, or `#infra`.
4. Validate:
   ```bash
   TARGET_REPO="$PWD"
   SKILL_DIR="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}/maintain-todo-md"
   python "$SKILL_DIR/scripts/validate_todo.py" "$TARGET_REPO/TODO.md"
   ```

## Workflow

### Add or Update Tasks

- Put immediate work in `Next`.
- Put planned but unscheduled work in `Backlog`.
- Put work waiting on a decision or external condition in `Blocked`.
- Keep completed work in `Done ✓` with `- [x]`.
- Keep ambiguous work open and clarify the task text rather than marking it done.

### Task Lifecycle

- New work: add one concise `- [ ]` line to `Next` or `Backlog`.
- Blocked work: move the unchanged task to `Blocked` and add the blocker inline.
- Unblocked work: move it back to `Next` or `Backlog` and remove stale blocker text.
- Completed work: move it to `Done ✓` and change the marker to `- [x]`.
- Duplicates or obsolete tasks: merge into the surviving task or move to `Done ✓` only when the outcome is actually complete.
- Large initiatives: keep only a tracking item in `TODO.md`; reference an existing issue or design document when available, or leave detailed requirements to the appropriate workflow.

### Metadata

- Use `#tag` for domain or purpose, such as `#docs`, `#security`, or `#infra`.
- Use `@owner` only when a known person or role owns the task.
- Use `+project` only when a task belongs to a clear initiative.
- Use `due:YYYY-MM-DD` sparingly and only when the date is a real external deadline.
- Do not store secrets, credentials, production URLs, or sensitive user data in task text.

### Validate

- Run validation with `scripts/validate_todo.py "$TARGET_REPO/TODO.md"` for the default root task file, or the target project's documented TODO validator when local rules differ.
- Run `git diff --check`.
- If task status is ambiguous, keep it open and clarify in the task text instead of silently marking it done.
- If completed tasks appear outside `Done ✓`, move them there.
- If open tasks appear inside `Done ✓`, either mark them complete only when true or move them back to an open section.
- If due metadata fails validation, rewrite it as `due:YYYY-MM-DD` or remove it.
- If section order fails, restore `Next`, `Backlog`, `Blocked`, and `Done ✓` in that order.
- Do not run skill self-validation such as `quick_validate.py` merely because this skill was used; run it only when editing this skill folder.

## Resources

- Read `references/community-sources.md` when you need the community rationale.
- Read `references/todo-policy.md` before changing section names, metadata rules, or completion rules.
- Use `assets/todo-template.md` when recreating the file.

## Commands

```bash
TARGET_REPO="$PWD"
SKILL_DIR="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}/maintain-todo-md"
python "$SKILL_DIR/scripts/validate_todo.py" "$TARGET_REPO/TODO.md"
```
