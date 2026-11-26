#!/usr/bin/env python3
"""Collect redacted Codex session-history metadata for distillation.

The script is intentionally read-only and stateless. It discovers JSONL session
files, filters them by time and cwd, emits bounded snippets and failure signals,
and never writes processed markers or raw transcript copies.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1
MAX_SNIPPETS_PER_SESSION = 5
MAX_TOOL_FAILURES_PER_SESSION = 5
DEFAULT_SNIPPET_CHARS = 240
DEFAULT_MAX_SESSIONS = 40
DEFAULT_MAX_SNIPPETS_TOTAL = 120

ZH_HANS_LANGUAGES = {"zh", "zh-cn", "zh-hans", "zh-hans-cn"}

EN_LABELS = {
    "title": "Session History Candidates",
    "generated": "Generated",
    "language": "Language",
    "window": "Window",
    "workdir": "Workdir",
    "scope": "Scope",
    "output_dir": "Output dir",
    "redaction_enabled": "Redaction enabled",
    "dry_run": "Dry run",
    "sessions_returned_omitted": "Sessions returned/omitted",
    "snippets_returned": "Snippets returned",
    "counts": "Counts",
    "sessions": "Sessions",
    "no_sessions": "No matching sessions found.",
    "timestamp": "Timestamp",
    "cwd": "Cwd",
    "source": "Source",
    "subagent": "Subagent",
    "git_branch": "Git branch",
    "messages_tool_calls_tool_failures": "Messages/tool calls/tool failures",
    "snippets": "Snippets",
    "tool_failure_signals": "Tool failure signals",
}

ZH_HANS_LABELS = {
    "title": "会话历史候选",
    "generated": "生成时间",
    "language": "产物语言",
    "window": "时间窗口",
    "workdir": "工作目录",
    "scope": "范围",
    "output_dir": "输出目录",
    "redaction_enabled": "脱敏已启用",
    "dry_run": "试运行",
    "sessions_returned_omitted": "返回/省略会话",
    "snippets_returned": "返回摘录",
    "counts": "统计",
    "sessions": "会话",
    "no_sessions": "未找到匹配会话。",
    "timestamp": "时间",
    "cwd": "工作目录",
    "source": "来源",
    "subagent": "Subagent",
    "git_branch": "Git 分支",
    "messages_tool_calls_tool_failures": "消息/工具调用/工具失败",
    "snippets": "摘录",
    "tool_failure_signals": "工具失败信号",
}

ZH_HANS_COUNT_LABELS = {
    "scanned_files": "已扫描文件",
    "parsed_files": "已解析文件",
    "candidate_sessions": "候选会话",
    "excluded_by_time": "按时间排除",
    "excluded_by_cwd": "按工作目录排除",
    "excluded_by_subagent_filter": "按 subagent 过滤排除",
    "duplicate_sessions": "重复会话",
    "read_errors": "读取错误",
    "temp_files_created": "已创建临时文件",
}

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9_]{16,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{12,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(
        r"(?i)\b([A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|PRIVATE_KEY|API_KEY|DATABASE_URL|DIRECT_URL|ARTIFACT_URL)[A-Z0-9_]*)\s*=\s*([^\s]+)"
    ),
    re.compile(
        r"(?i)([\"']?(?:api[_-]?key|token|secret|password|private[_-]?key|database[_-]?url|direct[_-]?url|artifact[_-]?url)[\"']?\s*[:=]\s*[\"'])([^\"'\s,}]+)([\"']?)"
    ),
    re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{12,}\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"https?://[^\s)>\]}\"']+"),
]

SENSITIVE_WORDS = (
    "error",
    "failed",
    "failure",
    "traceback",
    "exception",
    "nonzero",
    "permission denied",
    "not found",
    "timed out",
)


@dataclass
class ParsedTime:
    value: datetime
    input: str


def local_now() -> datetime:
    return datetime.now().astimezone()


def uses_zh_hans(language: str) -> bool:
    return language.lower().replace("_", "-") in ZH_HANS_LANGUAGES


def markdown_labels(language: str) -> dict[str, str]:
    if uses_zh_hans(language):
        return ZH_HANS_LABELS
    return EN_LABELS


def markdown_bool(value: bool, language: str) -> str:
    if uses_zh_hans(language):
        return "是" if value else "否"
    return str(value)


def count_label(key: str, language: str) -> str:
    if uses_zh_hans(language):
        return ZH_HANS_COUNT_LABELS.get(key, key)
    return key


def parse_time_spec(raw: str, now: datetime, *, is_until: bool = False) -> ParsedTime:
    value = raw.strip()
    lower = value.lower()
    if lower == "now":
        return ParsedTime(now, raw)

    relative = re.fullmatch(r"(\d+)([smhdw])", lower)
    if relative:
        amount = int(relative.group(1))
        unit = relative.group(2)
        delta_by_unit = {
            "s": timedelta(seconds=amount),
            "m": timedelta(minutes=amount),
            "h": timedelta(hours=amount),
            "d": timedelta(days=amount),
            "w": timedelta(weeks=amount),
        }
        return ParsedTime(now - delta_by_unit[unit], raw)

    normalized = value.replace("Z", "+00:00")
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
            parsed_date = date.fromisoformat(normalized)
            base = datetime.combine(parsed_date, datetime.max.time() if is_until else datetime.min.time())
            return ParsedTime(base.replace(tzinfo=now.tzinfo), raw)
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise SystemExit(f"Invalid time value '{raw}'. Use now, 7d, 12h, or ISO date/time.") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=now.tzinfo)
    return ParsedTime(parsed.astimezone(now.tzinfo), raw)


def parse_json_time(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone()


def resolve_path(raw: str | Path) -> Path:
    return Path(raw).expanduser().resolve(strict=False)


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def cwd_matches(session_cwd: str | None, workdir: Path, scope: str) -> bool:
    if not session_cwd:
        return False
    session_path = resolve_path(session_cwd)
    if scope == "exact":
        return session_path == workdir
    if scope == "within-root":
        return session_path == workdir or is_within(session_path, workdir)
    if scope == "repo-family":
        return session_path == workdir or is_within(session_path, workdir) or same_git_common_dir(session_path, workdir)
    raise ValueError(f"Unknown scope: {scope}")


def git_common_dir(path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--git-common-dir"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    common_dir = result.stdout.strip()
    if not common_dir:
        return None
    common_path = Path(common_dir)
    if not common_path.is_absolute():
        common_path = path / common_path
    return str(resolve_path(common_path))


def same_git_common_dir(left: Path, right: Path) -> bool:
    left_common = git_common_dir(left)
    right_common = git_common_dir(right)
    return bool(left_common and right_common and left_common == right_common)


def default_sources() -> list[Path]:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    return [codex_home / "sessions", codex_home / "archived_sessions"]


def path_date_hint(path: Path) -> date | None:
    parts = path.parts
    for index in range(len(parts) - 2):
        year, month, day = parts[index : index + 3]
        if not (re.fullmatch(r"\d{4}", year) and re.fullmatch(r"\d{2}", month) and re.fullmatch(r"\d{2}", day)):
            continue
        try:
            return date(int(year), int(month), int(day))
        except ValueError:
            return None
    for part in parts:
        match = re.search(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)", part)
        if not match:
            continue
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
    return None


def path_may_overlap_window(path: Path, since: datetime | None, until: datetime | None) -> bool:
    if since is None or until is None:
        return True
    hinted_date = path_date_hint(path)
    if hinted_date is None:
        return True
    return since.date() <= hinted_date <= until.date()


def iter_jsonl_files(
    sources: Iterable[Path], *, since: datetime | None = None, until: datetime | None = None
) -> Iterable[Path]:
    seen: set[Path] = set()
    for source in sources:
        resolved = resolve_path(source)
        if not resolved.exists():
            continue
        if resolved.is_file() and resolved.suffix == ".jsonl":
            if resolved not in seen:
                seen.add(resolved)
                yield resolved
            continue
        if resolved.is_dir():
            if not path_may_overlap_window(resolved, since, until):
                continue
            for root, dirnames, filenames in os.walk(resolved):
                root_path = Path(root)
                dirnames[:] = sorted(
                    dirname
                    for dirname in dirnames
                    if path_may_overlap_window(root_path / dirname, since, until)
                )
                for filename in sorted(filenames):
                    if not filename.endswith(".jsonl"):
                        continue
                    candidate = resolve_path(root_path / filename)
                    if candidate not in seen and path_may_overlap_window(candidate, since, until):
                        seen.add(candidate)
                        yield candidate


def redact_text(text: str, enabled: bool) -> str:
    if not enabled:
        return text
    redacted = text
    for pattern in SECRET_PATTERNS:
        if pattern.pattern.startswith("(?i)\\b([A-Z0-9_]*"):
            redacted = pattern.sub(lambda match: f"{match.group(1)}=[REDACTED]", redacted)
        elif "(?:api[_-]?key" in pattern.pattern:
            redacted = pattern.sub(lambda match: f"{match.group(1)}[REDACTED]{match.group(3)}", redacted)
        else:
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def clean_snippet(text: str, *, redact: bool, limit: int = DEFAULT_SNIPPET_CHARS) -> str:
    text = redact_text(text, redact)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "..."
    return text


def payload_text_chunks(content: Any) -> list[str]:
    chunks: list[str] = []
    if isinstance(content, str):
        return [content]
    if not isinstance(content, list):
        return chunks
    for item in content:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type in {"input_text", "output_text", "text"} and isinstance(item.get("text"), str):
            chunks.append(item["text"])
    return chunks


def looks_like_failure(text: str) -> bool:
    lowered = text.lower()
    if re.search(r"(process exited with code|exit code:)\s*[1-9]\d*", lowered):
        return True
    if "collab spawn failed" in lowered or "tool call failed" in lowered:
        return True
    if "traceback" in lowered or "exception" in lowered:
        return True

    success_patterns = (
        r"\bno errors? found\b",
        r"\b0 errors?\b",
        r"\b0 failures?\b",
        r"\bno failures?\b",
        r"\bvalidation passed\b",
        r"\btests? passed\b",
        r"\bpassed:\s*\d+\b",
    )
    if any(re.search(pattern, lowered) for pattern in success_patterns):
        return False
    if re.search(r"(process exited with code|exit code:)\s*0", lowered):
        return False
    return any(word in lowered for word in SENSITIVE_WORDS)


def is_subagent_meta(meta: dict[str, Any]) -> bool:
    thread_source = meta.get("thread_source")
    if thread_source and thread_source != "user":
        return True
    return bool(
        meta.get("parent_thread_id")
        or meta.get("forked_from_id")
        or meta.get("agent_nickname")
        or meta.get("agent_role")
    )


def session_summary(
    path: Path,
    meta: dict[str, Any],
    timestamp: datetime | None,
    *,
    message_count: int = 0,
    tool_call_count: int = 0,
    tool_failure_count: int = 0,
    snippets: list[dict[str, str]] | None = None,
    tool_failures: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    session_id = meta.get("id") or meta.get("session_id") or path.stem
    git = meta.get("git") if isinstance(meta.get("git"), dict) else {}
    return {
        "session_id": str(session_id),
        "path": str(path),
        "timestamp": timestamp.isoformat() if timestamp else None,
        "cwd": meta.get("cwd"),
        "thread_source": meta.get("thread_source"),
        "is_subagent": is_subagent_meta(meta),
        "agent_nickname": meta.get("agent_nickname"),
        "parent_thread_id": meta.get("parent_thread_id"),
        "forked_from_id": meta.get("forked_from_id"),
        "git_branch": git.get("branch"),
        "message_count": message_count,
        "tool_call_count": tool_call_count,
        "tool_failure_count": tool_failure_count,
        "snippets": snippets or [],
        "tool_failures": tool_failures or [],
    }


def read_session_metadata(path: Path) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    meta: dict[str, Any] | None = None
    fallback_timestamp: datetime | None = None

    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                fallback_timestamp = fallback_timestamp or parse_json_time(record.get("timestamp"))
                payload = record.get("payload")
                if not isinstance(payload, dict):
                    continue
                if record.get("type") == "session_meta":
                    meta = payload
                    break
    except OSError as exc:
        return None, {"error": f"Unable to read {path}: {exc}"}

    if meta is None:
        return None, {"error": f"No session_meta found in {path}"}

    timestamp = parse_json_time(str(meta.get("timestamp") or "")) or fallback_timestamp
    return session_summary(path, meta, timestamp), {}


def read_session(path: Path, *, redact: bool, snippets_enabled: bool) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    meta: dict[str, Any] | None = None
    fallback_timestamp: datetime | None = None
    message_count = 0
    tool_call_count = 0
    tool_failure_count = 0
    snippets: list[dict[str, str]] = []
    tool_failures: list[dict[str, str]] = []

    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                fallback_timestamp = fallback_timestamp or parse_json_time(record.get("timestamp"))
                payload = record.get("payload")
                if not isinstance(payload, dict):
                    continue

                if record.get("type") == "session_meta" and meta is None:
                    meta = payload
                    continue

                if record.get("type") != "response_item":
                    continue

                payload_type = payload.get("type")
                if payload_type == "message":
                    role = payload.get("role")
                    if role in {"user", "assistant"}:
                        message_count += 1
                        if snippets_enabled and len(snippets) < MAX_SNIPPETS_PER_SESSION:
                            text = " ".join(payload_text_chunks(payload.get("content")))
                            snippet = clean_snippet(text, redact=redact)
                            if snippet:
                                snippets.append({"role": str(role), "text": snippet})
                elif payload_type == "function_call":
                    tool_call_count += 1
                elif payload_type == "function_call_output":
                    output = payload.get("output")
                    output_text = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
                    if looks_like_failure(output_text):
                        tool_failure_count += 1
                        if len(tool_failures) < MAX_TOOL_FAILURES_PER_SESSION:
                            tool_failures.append(
                                {
                                    "call_id": str(payload.get("call_id") or ""),
                                    "snippet": clean_snippet(output_text, redact=redact),
                                }
                            )
    except OSError as exc:
        return None, {"error": f"Unable to read {path}: {exc}"}

    if meta is None:
        return None, {"error": f"No session_meta found in {path}"}

    timestamp = parse_json_time(str(meta.get("timestamp") or "")) or fallback_timestamp
    return (
        session_summary(
            path,
            meta,
            timestamp,
            message_count=message_count,
            tool_call_count=tool_call_count,
            tool_failure_count=tool_failure_count,
            snippets=snippets,
            tool_failures=tool_failures,
        ),
        {},
    )


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    now = local_now()
    since = parse_time_spec(args.since, now)
    until = parse_time_spec(args.until, now, is_until=True)
    if since.value > until.value:
        raise SystemExit("--since must be earlier than or equal to --until")

    workdir = resolve_path(args.workdir)
    output_dir = resolve_path(args.output_dir)
    sources = [Path(source) for source in args.source] if args.source else default_sources()
    source_paths = [str(resolve_path(source)) for source in sources]

    counts = {
        "scanned_files": 0,
        "parsed_files": 0,
        "candidate_sessions": 0,
        "excluded_by_time": 0,
        "excluded_by_cwd": 0,
        "excluded_by_subagent_filter": 0,
        "duplicate_sessions": 0,
        "read_errors": 0,
        "temp_files_created": 0,
    }
    sessions: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    seen_session_ids: set[str] = set()

    for path in iter_jsonl_files(sources, since=since.value, until=until.value):
        counts["scanned_files"] += 1
        summary, error = read_session_metadata(path)
        if error:
            counts["read_errors"] += 1
            errors.append(error)
            continue
        if summary is None:
            continue
        counts["parsed_files"] += 1

        session_timestamp = parse_json_time(summary.get("timestamp"))
        if session_timestamp is None or session_timestamp < since.value or session_timestamp > until.value:
            counts["excluded_by_time"] += 1
            continue
        if not cwd_matches(summary.get("cwd"), workdir, args.scope):
            counts["excluded_by_cwd"] += 1
            continue
        if args.exclude_subagents and summary["is_subagent"]:
            counts["excluded_by_subagent_filter"] += 1
            continue
        if not args.include_subagents and summary["is_subagent"]:
            counts["excluded_by_subagent_filter"] += 1
            continue

        session_id = summary["session_id"]
        if session_id in seen_session_ids:
            counts["duplicate_sessions"] += 1
            continue

        summary, error = read_session(path, redact=not args.no_redact, snippets_enabled=not args.no_snippets)
        if error:
            counts["read_errors"] += 1
            errors.append(error)
            continue
        if summary is None:
            continue
        seen_session_ids.add(session_id)
        sessions.append(summary)

    sessions.sort(key=lambda item: item.get("timestamp") or "")
    counts["candidate_sessions"] = len(sessions)
    snippets_seen = 0
    visible_sessions = sessions[-args.max_sessions :]
    for session in visible_sessions:
        session_snippets = session.get("snippets") or []
        remaining = max(args.max_snippets_total - snippets_seen, 0)
        if remaining <= 0:
            session["snippets"] = []
        elif len(session_snippets) > remaining:
            session["snippets"] = session_snippets[:remaining]
        snippets_seen += len(session.get("snippets") or [])
    omitted_sessions = max(len(sessions) - len(visible_sessions), 0)

    return {
        "schema_version": SCHEMA_VERSION,
        "language": args.language,
        "generated_at": now.isoformat(),
        "dry_run": bool(args.dry_run),
        "redaction_enabled": not args.no_redact,
        "window": {
            "since_input": since.input,
            "until_input": until.input,
            "since": since.value.isoformat(),
            "until": until.value.isoformat(),
            "timezone": str(now.tzinfo),
        },
        "workdir": {"path": str(workdir), "scope": args.scope},
        "output_dir": str(output_dir),
        "source_paths": source_paths,
        "filters": {
            "include_subagents": args.include_subagents,
            "exclude_subagents": args.exclude_subagents,
            "no_snippets": args.no_snippets,
            "max_sessions": args.max_sessions,
            "max_snippets_total": args.max_snippets_total,
        },
        "counts": counts,
        "sessions": visible_sessions,
        "output_limits": {
            "sessions_returned": len(visible_sessions),
            "sessions_omitted": omitted_sessions,
            "snippets_returned": snippets_seen,
        },
        "errors": errors[:20],
    }


def render_markdown(report: dict[str, Any]) -> str:
    language = str(report.get("language") or "en")
    labels = markdown_labels(language)
    lines = [
        f"# {labels['title']}",
        "",
        f"- {labels['generated']}: `{report['generated_at']}`",
        f"- {labels['language']}: `{language}`",
        f"- {labels['window']}: `{report['window']['since']}` to `{report['window']['until']}` ({report['window']['timezone']})",
        f"- {labels['workdir']}: `{report['workdir']['path']}`",
        f"- {labels['scope']}: `{report['workdir']['scope']}`",
        f"- {labels['output_dir']}: `{report['output_dir']}`",
        f"- {labels['redaction_enabled']}: `{markdown_bool(bool(report['redaction_enabled']), language)}`",
        f"- {labels['dry_run']}: `{markdown_bool(bool(report['dry_run']), language)}`",
        f"- {labels['sessions_returned_omitted']}: `{report['output_limits']['sessions_returned']}` / `{report['output_limits']['sessions_omitted']}`",
        f"- {labels['snippets_returned']}: `{report['output_limits']['snippets_returned']}`",
        "",
        f"## {labels['counts']}",
        "",
    ]
    for key, value in report["counts"].items():
        rendered_key = count_label(str(key), language)
        lines.append(f"- {rendered_key}: {value}")
    lines.extend(["", f"## {labels['sessions']}", ""])

    if not report["sessions"]:
        lines.append(labels["no_sessions"])
        return "\n".join(lines) + "\n"

    for session in report["sessions"]:
        lines.extend(
            [
                f"### {session['session_id']}",
                "",
                f"- {labels['timestamp']}: `{session.get('timestamp')}`",
                f"- {labels['cwd']}: `{session.get('cwd')}`",
                f"- {labels['source']}: `{session.get('thread_source')}`",
                f"- {labels['subagent']}: `{markdown_bool(bool(session.get('is_subagent')), language)}`",
                f"- {labels['git_branch']}: `{session.get('git_branch')}`",
                f"- {labels['messages_tool_calls_tool_failures']}: `{session.get('message_count')}` / `{session.get('tool_call_count')}` / `{session.get('tool_failure_count')}`",
            ]
        )
        if session.get("snippets"):
            lines.append(f"- {labels['snippets']}:")
            for snippet in session["snippets"]:
                lines.append(f"  - `{snippet['role']}`: {snippet['text']}")
        if session.get("tool_failures"):
            lines.append(f"- {labels['tool_failure_signals']}:")
            for failure in session["tool_failures"]:
                lines.append(f"  - `{failure['call_id']}`: {failure['snippet']}")
        lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", default="7d", help="Start time: now, 7d, 12h, or ISO date/time. Default: 7d.")
    parser.add_argument("--until", default="now", help="End time: now, 7d, 12h, or ISO date/time. Default: now.")
    parser.add_argument("--workdir", default=os.getcwd(), help="Project work directory to match. Default: cwd.")
    parser.add_argument(
        "--language",
        default="zh-Hans",
        help="Artifact/report language. Default: zh-Hans. Use en for English labels; other values are preserved in JSON metadata.",
    )
    parser.add_argument(
        "--scope",
        choices=["within-root", "exact", "repo-family"],
        default="within-root",
        help="How to match session cwd against workdir. Default: within-root.",
    )
    parser.add_argument("--output-dir", default=os.getcwd(), help="Target project directory for later documentation routing.")
    parser.add_argument("--source", action="append", default=[], help="Session JSONL file or directory. Repeatable.")
    parser.add_argument("--include-subagents", action="store_true", default=True, help="Include subagent sessions. Default: true.")
    parser.add_argument("--exclude-subagents", action="store_true", help="Exclude sessions that look like subagent work.")
    parser.add_argument(
        "--max-sessions",
        type=int,
        default=DEFAULT_MAX_SESSIONS,
        help=f"Maximum most-recent sessions to emit. Default: {DEFAULT_MAX_SESSIONS}.",
    )
    parser.add_argument(
        "--max-snippets-total",
        type=int,
        default=DEFAULT_MAX_SNIPPETS_TOTAL,
        help=f"Maximum snippets to emit across all sessions. Default: {DEFAULT_MAX_SNIPPETS_TOTAL}.",
    )
    parser.add_argument("--no-snippets", action="store_true", help="Emit metadata and failure signals without message snippets.")
    parser.add_argument("--dry-run", action="store_true", help="Mark output as dry run. The script is read-only either way.")
    parser.add_argument("--no-redact", action="store_true", help="Disable redaction. Avoid for documentation workflows.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    args = parser.parse_args(argv)
    if args.include_subagents and args.exclude_subagents:
        # argparse default keeps include true; exclusion wins when requested.
        args.include_subagents = False
    if args.max_sessions < 1:
        raise SystemExit("--max-sessions must be at least 1")
    if args.max_snippets_total < 0:
        raise SystemExit("--max-snippets-total must be at least 0")
    args.language = args.language.strip()
    if not args.language:
        raise SystemExit("--language must not be empty")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = build_report(args)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
