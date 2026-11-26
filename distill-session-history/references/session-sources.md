# Session Sources

Use this reference when collecting Codex or agent session history.

## Default Sources

- `${CODEX_HOME:-$HOME/.codex}/sessions`: active or recent local session JSONL files, usually under `YYYY/MM/DD`.
- `${CODEX_HOME:-$HOME/.codex}/archived_sessions`: archived JSONL files.
- Explicit `--source` paths: user-provided exported session files or directories.

Do not use shell history, terminal scrollback, browser cache, or app-private databases as default inputs. If an official connector or API becomes available, prefer it over local JSONL path assumptions and update this reference.

## JSONL Expectations

Codex JSONL files commonly contain:

- `session_meta` records with `payload.cwd`, `payload.timestamp`, `payload.id`, `payload.session_id`, `payload.thread_source`, and optional parent/fork metadata.
- `response_item` records with `payload.type` such as `message`, `function_call`, `function_call_output`, `reasoning`, or web/tool search records.
- top-level `timestamp` values that can be used as fallback evidence.

Parse JSON structurally. Do not use grep-style transcript extraction for final analysis.

## Filtering

- `within-root`: include sessions whose cwd is the workdir or a child of it. This is the default for monorepos.
- `exact`: include only sessions whose cwd equals the workdir.
- `repo-family`: include `within-root` plus paths whose Git common directory matches the workdir. Do not include same-name directories without Git common-dir evidence.

Always report the resolved absolute time window and the scope used. Relative windows such as `7d` must be converted to concrete timestamps in output.

When scanning large local history stores, prune files whose path date hint (`YYYY/MM/DD` directories or `YYYY-MM-DD` rollout filenames) cannot overlap the requested time window. Then read only `session_meta` first and apply time, cwd, and subagent filters before parsing a matching file for snippets or failure signals. The JSONL timestamp filter remains authoritative; path hints are only a performance prefilter.

## Subagents

Include subagent sessions by default because they often contain implementation, verification, or review findings. Treat a session as likely subagent work when metadata includes non-user `thread_source`, parent or fork ids, an agent nickname, or similar parent-child fields.

Use `--exclude-subagents` only when the user explicitly wants main-thread history.

## Privacy

Session files can contain secrets, URLs, user content, tool output, logs, and environment details. Keep redaction enabled by default, limit snippets, prefer `--no-snippets` for broad first-pass scans, and never copy raw JSONL or full transcript text into durable project docs.
