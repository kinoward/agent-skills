---
name: distill-session-history
description: Review recent Codex or agent session history for a project, distill recurring problems and solutions, and propose durable documentation or project-memory updates. Use when asked to analyze past sessions, mine agent conversations for lessons learned, summarize recent project work into stable knowledge, or run a stateless retrospective over configurable time ranges, work directories, or output directories.
---

# Distill Session History

## Overview

Use this skill to perform a stateless retrospective over project-related Codex or agent sessions. The goal is not to archive chat logs; it is to extract stable, reusable knowledge that belongs in the target project's existing documentation, TODO, ADR, or agent-memory structure.

## Inputs

- Time window: default `--since 7d --until now`; accept a user-provided relative or ISO window.
- Work directory: default to the current repository or execution directory.
- Scope: default `within-root`; use `exact` only when the user wants a single cwd, and `repo-family` when same-repo worktrees should be included.
- Output directory: default to the current project; route final knowledge according to that directory's documentation rules.
- Sources: default to `${CODEX_HOME:-$HOME/.codex}/sessions` and `${CODEX_HOME:-$HOME/.codex}/archived_sessions`; accept explicit exported history paths when provided.
- Artifact language: default generated artifacts to Simplified Chinese (`--language zh-Hans`) unless the user requests another language.

## Workflow

1. Read the target output directory's governing files before analyzing sessions:
   - root and nearest `AGENTS.md`
   - relevant `llms.txt`
   - documentation policy, project-memory, ADR, TODO, or equivalent local sources of truth
2. Prefer open-source precedent before inventing a process. Use OpenHands/Aider/LangGraph as references for rolling conversation summarization, and Mem0/Graphiti as references for provenance and durable-memory boundaries. Do not introduce their persistent services, databases, or state files merely for this skill.
3. Collect candidate sessions with `scripts/collect_session_history.py`.
4. Summarize large histories in layers:
   - first summarize individual sessions or small batches
   - then fuse summaries into recurring issues, confirmed decisions, reusable fixes, and unresolved follow-ups
   - keep recent or high-signal snippets available as evidence, but do not copy full transcripts into final docs
5. Build a candidate finding register before editing docs. Include every high-signal reusable lesson even when it may already be covered elsewhere. For each candidate, record:
   - finding
   - why it matters
   - evidence anchor
   - proposed target document
   - disposition: `write`, `already-covered`, `skill-update`, `todo`, or `discard`
6. Classify each candidate finding:
   - durable project fact
   - agent/process rule
   - architecture or product boundary
   - TODO/follow-up
   - discard as temporary, sensitive, duplicated, or unsupported
7. Route durable findings into the target project's document structure. If a finding is already covered, cite the existing source of truth in the final response instead of silently dropping it. Do not create new document categories when an existing source of truth covers the knowledge.
8. Delete any temporary notes or intermediate batch summaries before finishing. Never write processed-state, analyzed-session, marker, cache, or checkpoint files.
9. In the final response, summarize the candidate register and clearly state where each accepted or already-covered lesson lives.

## Collection Command

Use the helper from the directory that contains this `SKILL.md`. Save the target project directory first, then run the script from the skill directory:

```bash
TARGET_DIR="$PWD"
SKILL_DIR="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}/distill-session-history"
python "$SKILL_DIR/scripts/collect_session_history.py" \
  --since 7d \
  --until now \
  --language zh-Hans \
  --workdir "$TARGET_DIR" \
  --scope within-root \
  --output-dir "$TARGET_DIR" \
  --dry-run
```

Useful options:

- `--source <path>` can be repeated for exported session directories or files.
- `--include-subagents` and `--exclude-subagents` control subagent sessions; by default both user and subagent sessions are included.
- `--max-sessions` and `--max-snippets-total` bound output size; defaults are intentionally conservative.
- `--no-snippets` emits metadata and failure signals without message snippets for safer first-pass scans.
- `--language <tag>` controls generated report labels and downstream artifact language; default is `zh-Hans`, and `en` keeps English labels.
- `--json` emits machine-readable output.
- Redaction is enabled by default and includes common secrets, credential-like key/value pairs, emails, and URLs. Avoid `--no-redact` unless the user explicitly requests local-only debugging and no output will be written into project docs.

Read `references/session-sources.md` before changing session discovery behavior. Read `references/distillation-policy.md` before deciding what can be written into long-term docs. Read `references/document-routing.md` before editing project documents.

## Safety Rules

- Do not store raw transcripts, user secrets, artifact URLs, production URLs, private keys, DB URLs, local runtime data, screenshots, or temporary command output in long-term docs.
- Do not treat one-off failures, speculative ideas, or incomplete plans as stable knowledge.
- Every durable finding must be traceable to evidence such as session id, timestamp, cwd, changed file, existing document, or current repository state.
- Verify a finding against the current repo before writing it; older sessions can be stale.
- If `TODO.md` is changed, use the project's TODO-maintenance workflow and validator.
- If `llms.txt` is changed, use the project's llms-maintenance workflow and validator.

## Validation

After editing this skill, run:

```bash
SKILL_DIR="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}/distill-session-history"
python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" "$SKILL_DIR"
PYTHONDONTWRITEBYTECODE=1 python -m py_compile "$SKILL_DIR/scripts/collect_session_history.py"
python "$SKILL_DIR/scripts/collect_session_history.py" --help
```

For repository documentation changes, also run the target project's required navigation and whitespace checks.
