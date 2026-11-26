# Document Routing

Use this reference before writing session-derived knowledge into a project.

## Discover Local Rules First

Read the target output directory's local rules before editing:

- root `AGENTS.md`
- nearest directory `AGENTS.md`
- root and relevant directory `llms.txt`
- documentation policy, validation policy, ADR policy, TODO policy, or equivalents

When a project has no explicit policy, prefer creating a concise candidate report for the user instead of inventing a new documentation structure.

Language priority is: explicit user request first, then this skill's default artifact language (`zh-Hans`), then the target project's style rules. Local project rules can shape terminology and tone, but they should not override an explicit user-requested language.

## Common Routes

- Agent process rules and repeated agent pitfalls: agent policy or project memory docs.
- Durable architecture constraints: architecture docs.
- Major technical decisions: ADR docs.
- Internal product principles: product docs.
- Public user-facing behavior: product documentation source, not internal agent docs.
- Concrete follow-up work: TODO or issue tracker.

Use the target project's existing names and conventions. Do not assume `docs/agent`, `docs/architecture`, or `TODO.md` exist outside the target project unless local rules define them.

## Minimal Edit Rule

Make the smallest edit that preserves the durable knowledge. Avoid broad rewrites, new taxonomy, or cross-document duplication.

Before writing, verify the proposed target document still agrees with current code and current docs. Session history can be stale.

## Validation Routing

- If `llms.txt` changes, run that project's llms validator or at least link/format checks.
- If TODO changes, run that project's TODO validator when available.
- If architecture, ADR, API, env, or security docs change, run the documented checks for those areas.
- Always run whitespace/diff checks available in the project.
