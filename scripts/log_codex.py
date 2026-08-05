#!/usr/bin/env python3
"""Collect real Codex user prompts from local transcripts into the AI log.

Codex stores JSONL transcripts below ``CODEX_HOME/sessions`` (normally
``~/.codex/sessions``).  This scanner is intentionally run by the git pre-push
hook because not every Codex surface executes project-local prompt hooks.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator


VN_TZ = timezone(timedelta(hours=7))
DEFAULT_LOOKBACK_HOURS = 168  # A week avoids losing prompts between infrequent pushes.


def git(repo_root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=repo_root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def normalize_path(value: str | Path) -> str:
    try:
        return os.path.normcase(os.path.abspath(os.path.expanduser(str(value))))
    except (OSError, TypeError, ValueError):
        return ""


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def iter_jsonl(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    try:
        with path.open(encoding="utf-8-sig", errors="replace") as stream:
            for line_no, line in enumerate(stream, 1):
                try:
                    item = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    continue
                if isinstance(item, dict):
                    yield line_no, item
    except OSError:
        return


def strings_in(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings_in(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings_in(child)


def is_real_user_prompt(prompt: Any) -> bool:
    if not isinstance(prompt, str) or not prompt.strip():
        return False
    stripped = prompt.strip()
    # Codex may inject workspace metadata as a user-role message. It is context,
    # not a prompt authored by the student, so never submit it as AI usage.
    return not (
        stripped.startswith("<environment_context>")
        and stripped.endswith("</environment_context>")
    )


def transcript_belongs_to_repo(items: list[tuple[int, dict[str, Any]]], repo_root: Path) -> bool:
    repo = normalize_path(repo_root)
    session_cwd = ""
    for _, item in items:
        if item.get("type") == "session_meta":
            session_cwd = normalize_path((item.get("payload") or {}).get("cwd", ""))
            break

    if session_cwd:
        try:
            # Normal case: Codex was opened at the repo or inside it.
            if os.path.commonpath([repo, session_cwd]) == repo:
                return True
        except ValueError:
            pass

    # Codex desktop is often opened one level above the repo. Attribute that
    # session only when its transcript actually references this repo path (for
    # example in a shell tool's workdir); do not blindly claim sibling repos.
    repo_slash = repo.replace("\\", "/")
    for _, item in items:
        for value in strings_in(item):
            candidate = value.lower().replace("\\\\", "\\")
            if repo.lower() in candidate or repo_slash.lower() in candidate.replace("\\", "/"):
                return True
    return False


def load_seen_ids(log_dir: Path) -> set[str]:
    seen: set[str] = set()
    paths = [log_dir / "session.jsonl", *sorted((log_dir / "archive").glob("*.jsonl"))]
    paths.extend(log_dir.glob("session.pending.*.jsonl"))
    for path in paths:
        for _, entry in iter_jsonl(path):
            entry_id = entry.get("entry_id")
            if isinstance(entry_id, str) and entry_id:
                seen.add(entry_id)
    return seen


def collect(
    sessions_root: Path, repo_root: Path, cutoff: datetime | None, seen: set[str]
) -> list[dict[str, Any]]:
    repo_url = git(repo_root, "remote", "get-url", "origin")
    repo = repo_url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
    branch = git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    commit = git(repo_root, "rev-parse", "--short", "HEAD")
    student = git(repo_root, "config", "user.email") or os.environ.get("USERNAME", "unknown")
    entries: list[dict[str, Any]] = []

    for transcript in sessions_root.rglob("*.jsonl"):
        try:
            if cutoff and datetime.fromtimestamp(transcript.stat().st_mtime, timezone.utc) < cutoff:
                continue
        except OSError:
            continue

        items = list(iter_jsonl(transcript))
        if not items or not transcript_belongs_to_repo(items, repo_root):
            continue

        session_id = ""
        model = "codex"
        for _, item in items:
            if item.get("type") == "session_meta":
                payload = item.get("payload") or {}
                session_id = str(payload.get("session_id") or payload.get("id") or "")
                model = str(payload.get("model") or payload.get("model_provider") or "codex")
                break
        if not session_id:
            session_id = transcript.stem

        for line_no, item in items:
            payload = item.get("payload") or {}
            if item.get("type") != "event_msg" or payload.get("type") != "user_message":
                continue
            prompt = payload.get("message")
            if not is_real_user_prompt(prompt):
                continue
            timestamp = item.get("timestamp") or payload.get("timestamp") or ""
            timestamp_dt = parse_time(timestamp)
            if cutoff and timestamp_dt and timestamp_dt < cutoff:
                continue
            entry_id = f"codex-{session_id}-{line_no}"
            if entry_id in seen:
                continue
            entries.append(
                {
                    "ts": timestamp or datetime.now(VN_TZ).isoformat(),
                    "tool": "codex",
                    "event": "UserPromptSubmit",
                    "entry_id": entry_id,
                    "session_id": session_id,
                    "model": model,
                    "repo": repo,
                    "branch": branch,
                    "commit": commit,
                    "student": student,
                    "prompt": prompt.strip()[:1000],
                    "response_summary": "",
                }
            )
            seen.add(entry_id)

    entries.sort(key=lambda entry: entry["ts"])
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect Codex prompts from local transcripts")
    parser.add_argument("--hours", type=int, default=DEFAULT_LOOKBACK_HOURS)
    parser.add_argument("--all", action="store_true", help="scan all available transcripts")
    parser.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    sessions_root = codex_home / "sessions"
    if not sessions_root.is_dir():
        print(f"[codex-log] No sessions directory: {sessions_root}", file=sys.stderr)
        return 0

    log_dir = Path(os.environ.get("AI_LOG_DIR", repo_root / ".ai-log"))
    if not log_dir.is_absolute():
        log_dir = repo_root / log_dir
    cutoff = None if args.all else datetime.now(timezone.utc) - timedelta(hours=max(args.hours, 0))
    entries = collect(sessions_root, repo_root, cutoff, load_seen_ids(log_dir))

    if args.dry_run:
        print(f"[codex-log] Would log {len(entries)} new prompt(s).")
        return 0
    if not entries:
        print("[codex-log] No new prompts found.", file=sys.stderr)
        return 0

    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / "session.jsonl").open("a", encoding="utf-8") as stream:
        for entry in entries:
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[codex-log] Logged {len(entries)} prompt(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
