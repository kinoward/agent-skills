# Distillation Policy

Use this reference to decide what session-derived knowledge can become durable documentation.

## Write

Write only stable, reusable knowledge:

- confirmed project facts, boundaries, or source-of-truth ownership
- repeated agent mistakes and the executable rule that prevents recurrence
- durable validation workflows or command sequences
- decisions that are still true after checking the current repository
- concrete follow-up tasks that belong in the target project's TODO system

## Do Not Write

Do not write:

- raw transcripts, full user prompts, screenshots, terminal dumps, or large tool outputs
- token values, API keys, private keys, DB URLs, artifact URLs, production URLs, or credentials
- one-off command failures, transient container state, local row counts, cache paths, temp files, or old runtime state
- speculative plans, unconfirmed product ideas, or abandoned implementation branches
- content already recoverable from current code, tests, git diff, or commit history unless it changes future agent behavior

## Evidence Standard

Each durable finding should have at least one evidence anchor:

- session id and timestamp
- cwd or repository path
- current file or documentation path that confirms the finding
- test, command, or validation result

Evidence anchors are for agent review. Do not turn them into long lists of local paths in permanent docs unless the target project uses that format.

## Open-Source References

Borrow patterns, not dependencies:

- OpenHands context condenser: rolling history summarization.
- Aider chat history summarization: token-budgeted head summarization while preserving recent context.
- LangGraph memory docs: distinguish short-term conversation state from long-term memory.
- Mem0 and Graphiti: retain provenance and distinguish durable facts from raw episodes.
- detect-secrets and Presidio: useful references for secret/PII scanning, but no local redactor is complete.

Do not introduce persistent memory services, graph databases, external APIs, or state files unless the user asks for that as a separate project decision.

## Output Shape

Prefer a short candidate list before editing:

- finding
- why it matters
- evidence anchor
- proposed target document
- reason it is durable
- disposition: `write`, `already-covered`, `skill-update`, `todo`, or `discard`

Generate candidate findings, reasons, target-document suggestions, and durable documentation text in the requested artifact language. Default to Simplified Chinese (`zh-Hans`) unless the user explicitly requests another language.

Do not silently omit a durable finding only because it is already documented. Mark it `already-covered`, cite the existing source of truth, and include it in the final handoff so the user can see the distillation result.

Discard candidates that fail the durability or privacy checks.
