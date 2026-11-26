#!/usr/bin/env python3
"""session-cleanup helper.

  sweep.py scan [PATH ...] [--since WHEN] [--keep GLOB ...]
      List cleanup candidates compactly. Git repos: untracked files (whole
      untracked dirs collapsed) and modified tracked files. Other dirs: entries
      created since --since (required there). Protected paths are marked, never offered.
  sweep.py trash PATH ... [--keep GLOB ...]
      Move paths to the Trash (fallback: ~/.agents-session-trash/<time>/) and
      report how much disk space they hold. Refuses protected, tracked or root paths.

WHEN: "2026-11-27 10:00", "2026-11-27T10:00", epoch seconds, or relative "90m" / "3h" / "2d".
Stdlib only.
"""
import argparse
import fnmatch
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HOME = Path.home()
ORCA_DATA = Path(os.environ.get("ORCA_USER_DATA_PATH") or HOME / "Library/Application Support/orca")

# Session records, harness state and secrets: never offered, never moved.
PROTECTED_ROOTS = [
    HOME / ".claude", HOME / ".codex", HOME / ".gemini", HOME / ".cursor",
    HOME / ".hermes", HOME / ".agents", HOME / ".orca", HOME / ".local/share/opencode",
    HOME / ".ssh", HOME / ".gnupg", HOME / ".config", ORCA_DATA,
]
# Temp areas inside a protected root that may still be cleaned.
ALLOWED_INSIDE_PROTECTED = [ORCA_DATA / "chat-scratch"]
PROTECTED_PARTS = {".git", ".claude", ".codex", ".gemini", ".agents", ".cursor", ".orca", ".specstory",
                   "sessions", "archived_sessions", "transcripts"}
PROTECTED_GLOBS = ["*.jsonl", ".env", ".env.*", "*.pem", "*.key", "id_rsa*", "id_ed25519*",
                   "AGENTS.md", "CLAUDE.md", "GEMINI.md"]
# Dependency / cache dirs: out of scope, not walked.
SKIP_DIRS = {"node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache",
             ".next", "dist", "build", "target", ".cache", "Library", ".Trash"}


def parse_when(s):
    if s is None:
        return None
    s = s.strip()
    units = {"m": 60, "h": 3600, "d": 86400}
    if s[-1:] in units and s[:-1].isdigit():
        return time.time() - int(s[:-1]) * units[s[-1]]
    if s.replace(".", "", 1).isdigit():
        return float(s)
    return datetime.fromisoformat(s.replace(" ", "T")).timestamp()


def is_protected(p: Path, keep):
    p = p.absolute()
    if any(p == a or a in p.parents for a in ALLOWED_INSIDE_PROTECTED):
        return False
    if any(p == r or r in p.parents for r in PROTECTED_ROOTS):
        return True
    if PROTECTED_PARTS.intersection(p.parts):
        return True
    # A glob matches the name, the absolute path, or any trailing part of it ("data/*", "out/**/*.csv").
    name, full = p.name, str(p)
    return any(fnmatch.fnmatch(name, g) or fnmatch.fnmatch(full, g) or fnmatch.fnmatch(full, "*/" + g)
               for g in PROTECTED_GLOBS + keep)


def contains_protected(p: Path, keep):
    if not p.is_dir() or p.is_symlink():
        return False
    for root, dirs, files in os.walk(p):
        for n in dirs + files:
            if is_protected(Path(root) / n, keep):
                return True
    return False


def disk_usage(p: Path):
    """Bytes actually allocated on disk (st_blocks), not following symlinks."""
    try:
        st = p.lstat()
    except FileNotFoundError:
        return 0
    total = st.st_blocks * 512
    if p.is_dir() and not p.is_symlink():
        for root, dirs, files in os.walk(p):
            for n in dirs + files:
                try:
                    total += os.lstat(os.path.join(root, n)).st_blocks * 512
                except OSError:
                    pass
    return total


def born(p: Path):
    st = p.lstat()
    return getattr(st, "st_birthtime", st.st_mtime)


def human(n):
    for unit in ("B", "K", "M", "G"):
        if n < 1024 or unit == "G":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024


def stamp(t):
    return datetime.fromtimestamp(t).strftime("%m-%d %H:%M")


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout


def git_root(p: Path):
    r = subprocess.run(["git", "-C", str(p if p.is_dir() else p.parent), "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True)
    return Path(r.stdout.strip()) if r.returncode == 0 else None


def scan_git(root: Path, since, keep):
    branch = git(root, "branch", "--show-current").strip() or "detached"
    print(f"# git {root} ({branch})")
    total = 0
    for rel in filter(None, git(root, "ls-files", "--others", "--exclude-standard", "--directory", "-z").split("\0")):
        p = root / rel.rstrip("/")
        t = born(p)
        if since and t < since:
            continue
        if is_protected(p, keep) or contains_protected(p, keep):
            print(f"P  {'-':>7}  {stamp(t)}  {rel}")
            continue
        size = disk_usage(p)
        total += size
        print(f"U  {human(size):>7}  {stamp(t)}  {rel}")
    for line in filter(None, git(root, "status", "--porcelain", "--untracked-files=no").splitlines()):
        print(f"M  {'-':>7}  {'':11}  {line[3:]}  [{line[:2].strip()}]")
    print(f"# untracked total {human(total)}")


def scan_plain(base: Path, since, keep, depth=4):
    print(f"# dir {base} (created since {stamp(since)})")
    total = 0

    def walk(d: Path, level):
        nonlocal total
        try:
            entries = sorted(d.iterdir())
        except (PermissionError, FileNotFoundError):
            return
        for p in entries:
            if p.name in SKIP_DIRS or (p.is_dir() and is_protected(p, keep) and not p.is_symlink()
                                       and not any(a == p or p in a.parents for a in ALLOWED_INSIDE_PROTECTED)):
                continue
            try:
                t = born(p)
            except OSError:
                continue
            if t >= since:
                rel = p.relative_to(base)
                if is_protected(p, keep) or contains_protected(p, keep):
                    print(f"P  {'-':>7}  {stamp(t)}  {rel}")
                    continue
                size = disk_usage(p)
                total += size
                print(f"N  {human(size):>7}  {stamp(t)}  {rel}{'/' if p.is_dir() else ''}")
            elif p.is_dir() and not p.is_symlink() and level < depth:
                walk(p, level + 1)

    walk(base, 1)
    print(f"# new total {human(total)}")


def cmd_scan(a):
    since = parse_when(a.since)
    seen = set()
    for raw in a.paths or ["."]:
        p = Path(raw).expanduser().absolute()
        root = git_root(p)
        if root:
            if root not in seen:
                seen.add(root)
                scan_git(root, since, a.keep)
        elif since is None:
            print(f"# dir {p}: not a git repo, pass --since to scan it", file=sys.stderr)
        else:
            scan_plain(p, since, a.keep)
    print("# U=untracked N=new M=modified tracked (report only) P=protected (never touch)")


def refuse_reason(p: Path, keep):
    if not p.exists() and not p.is_symlink():
        return "missing"
    if p in (Path("/"), HOME):
        return "root or home"
    if is_protected(p, keep) or contains_protected(p, keep):
        return "protected"
    if (p / ".git").exists():
        return "repository root"
    root = git_root(p)
    if root and subprocess.run(["git", "-C", str(root), "ls-files", "--error-unmatch", str(p)],
                               capture_output=True).returncode == 0:
        return "tracked by git"
    return None


def move_to_trash(paths):
    if shutil.which("trash"):
        subprocess.run(["trash", *map(str, paths)], check=True)
        return "废纸篓"
    if shutil.which("gio"):
        subprocess.run(["gio", "trash", *map(str, paths)], check=True)
        return "废纸篓"
    dest = HOME / ".agents-session-trash" / datetime.now().strftime("%Y%m%d-%H%M%S")
    for p in paths:
        target = dest / str(p.absolute()).lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(target))
    return str(dest)


def cmd_trash(a):
    ok, total = [], 0
    for raw in a.paths:
        p = Path(raw).expanduser().absolute()
        reason = refuse_reason(p, a.keep)
        if reason:
            print(f"SKIP  {p}  ({reason})")
            continue
        size = disk_usage(p)
        total += size
        ok.append(p)
        print(f"MOVE  {human(size):>7}  {p}")
    if not ok:
        print("# nothing moved")
        return 1 if a.paths else 0
    where = move_to_trash(ok)
    note = "清空废纸篓后才真正释放磁盘空间" if where == "废纸篓" else "删除该目录后才真正释放磁盘空间"
    print(f"# moved {len(ok)} item(s), {human(total)} -> {where}（{note}）")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("paths", nargs="*")
    s.add_argument("--since")
    s.add_argument("--keep", action="append", default=[], help="extra protected glob (repeatable)")
    t = sub.add_parser("trash")
    t.add_argument("paths", nargs="+")
    t.add_argument("--keep", action="append", default=[], help="extra protected glob (repeatable)")
    a = ap.parse_args()
    return cmd_scan(a) if a.cmd == "scan" else cmd_trash(a)


if __name__ == "__main__":
    sys.exit(main() or 0)
