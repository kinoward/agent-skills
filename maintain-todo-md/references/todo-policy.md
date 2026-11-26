# TODO.md Policy

## Required Shape

By default, the root `TODO.md` must contain these sections in order. Follow
target project local rules when they define a different task file or section
model.

1. `# TODO`
2. `## Next`
3. `## Backlog`
4. `## Blocked`
5. `## Done ✓`

Use GFM task lines:

- `- [ ]` for open work.
- `- [x]` for completed work.

## Section Semantics

- `Next`: work that should be considered soon.
- `Backlog`: valuable work without immediate scheduling.
- `Blocked`: work waiting on external decisions, credentials, vendor choices, or product inputs.
- `Done ✓`: completed repository milestones or maintenance actions.

## Metadata

Allowed optional metadata:

- `#tag` for domain or purpose.
- `@owner` when a person or role is known.
- `+project` for a larger initiative.
- `due:YYYY-MM-DD` only for real deadlines.

## Maintenance Rules

- Prefer one-line tasks.
- Keep completed items in `Done ✓`.
- Do not mark ambiguous work complete.
- Do not store secrets, credentials, production URLs, or sensitive user data.
