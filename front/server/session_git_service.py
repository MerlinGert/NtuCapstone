import subprocess
import threading
from pathlib import Path
from typing import Any


TRACE_BOT_NAME = "ManiScope Trace Bot"
TRACE_BOT_EMAIL = "maniscope-trace@local"
_repo_locks: dict[Path, threading.RLock] = {}
_repo_locks_guard = threading.Lock()


class SessionGitError(RuntimeError):
    pass


def _repo_lock(session_dir: Path) -> threading.RLock:
    resolved = session_dir.resolve()
    with _repo_locks_guard:
        if resolved not in _repo_locks:
            _repo_locks[resolved] = threading.RLock()
        return _repo_locks[resolved]


def _run_git(session_dir: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(session_dir), *args],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError as error:
        raise SessionGitError(str(error)) from error


def _check_git(session_dir: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    result = _run_git(session_dir, args)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or f"git {' '.join(args)} failed"
        raise SessionGitError(message)
    return result


def ensure_session_repo(session_dir: Path) -> None:
    session_dir.mkdir(parents=True, exist_ok=True)
    with _repo_lock(session_dir):
        if not (session_dir / ".git").exists():
            try:
                result = subprocess.run(
                    ["git", "init", "--quiet", str(session_dir)],
                    capture_output=True,
                    check=False,
                    text=True,
                )
            except OSError as error:
                raise SessionGitError(str(error)) from error
            if result.returncode != 0:
                message = result.stderr.strip() or result.stdout.strip() or "git init failed"
                raise SessionGitError(message)

        _check_git(session_dir, ["config", "user.name", TRACE_BOT_NAME])
        _check_git(session_dir, ["config", "user.email", TRACE_BOT_EMAIL])
        _check_git(session_dir, ["config", "commit.gpgsign", "false"])


def _stage_trace_files(session_dir: Path) -> None:
    paths = [
        "session-meta.json",
        "live-session.json",
        "current-state.json",
        "images",
    ]
    existing_paths = [path for path in paths if (session_dir / path).exists()]
    if existing_paths:
        _check_git(session_dir, ["add", "--", *existing_paths])


def _commit_message(
    event_type: str,
    session_id: str,
    action_count: int,
    annotation_count: int,
    image_count: int,
    updated_at: str,
    detail: dict[str, Any] | None,
) -> tuple[str, str]:
    detail = detail or {}
    subject = _commit_subject(event_type, detail)
    body_lines = [
        f"Event: {event_type}",
        f"Session: {session_id}",
        f"Actions: {action_count}",
        f"Annotations: {annotation_count}",
        f"Images: {image_count}",
        f"Updated: {updated_at}",
    ]

    for key in ("actionIndex", "actionType", "annotationId", "sourceView", "targetView", "coin", "appendedActions", "appendedAnnotations"):
        value = detail.get(key)
        if value is not None:
            body_lines.append(f"{key}: {value}")

    return subject, "\n".join(body_lines)


def _commit_subject(event_type: str, detail: dict[str, Any]) -> str:
    if event_type in {"user_action_append", "user_action_upsert"}:
        action_type = detail.get("actionType") or "user action"
        source_view = detail.get("sourceView")
        suffix = f" {source_view}" if source_view else ""
        return f"event: {action_type}{suffix}"
    if event_type == "user_action_delete":
        return "event: delete user action"
    if event_type in {"annotation_append", "annotation_upsert"}:
        source_view = detail.get("sourceView") or "annotation"
        annotation_id = detail.get("annotationId")
        suffix = f" #{annotation_id}" if annotation_id is not None else ""
        return f"annotation: update {source_view}{suffix}"
    if event_type == "annotation_delete":
        return "annotation: delete annotation"
    if event_type == "trace_reorder":
        return "event: reorder trace"
    if event_type == "trace_append_import":
        return "debug: append imported trace slice"
    if event_type == "settings_update":
        return "settings: update trace settings"
    if event_type == "full_sync":
        return "sync: update live trace"
    if event_type == "session_init":
        return "session: initialize trace"
    return f"trace: {event_type.replace('_', ' ')}"


def commit_trace_state(
    session_dir: Path,
    event_type: str,
    session_id: str,
    action_count: int,
    annotation_count: int,
    image_count: int,
    updated_at: str,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    with _repo_lock(session_dir):
        ensure_session_repo(session_dir)
        _stage_trace_files(session_dir)

        result = _run_git(session_dir, ["diff", "--cached", "--quiet"])
        if result.returncode == 0:
            return {"committed": False, "reason": "no_changes"}
        if result.returncode != 1:
            message = result.stderr.strip() or result.stdout.strip() or "git diff --cached failed"
            raise SessionGitError(message)

        subject, body = _commit_message(
            event_type,
            session_id,
            action_count,
            annotation_count,
            image_count,
            updated_at,
            detail,
        )
        _check_git(session_dir, ["commit", "--quiet", "-m", subject, "-m", body])
        commit_sha = _check_git(session_dir, ["rev-parse", "--short", "HEAD"]).stdout.strip()
        return {
            "committed": True,
            "commit": commit_sha,
            "message": subject,
        }


def list_trace_versions(session_dir: Path, limit: int = 50) -> list[dict[str, str]]:
    safe_limit = min(max(limit, 1), 200)
    with _repo_lock(session_dir):
        ensure_session_repo(session_dir)
        has_head = _run_git(session_dir, ["rev-parse", "--verify", "HEAD"])
        if has_head.returncode != 0:
            return []

        result = _check_git(
            session_dir,
            ["log", f"--max-count={safe_limit}", "--pretty=format:%h%x1f%H%x1f%cI%x1f%s"],
        )
    versions = []
    for line in result.stdout.splitlines():
        short_sha, sha, committed_at, subject = line.split("\x1f", 3)
        versions.append(
            {
                "shortSha": short_sha,
                "sha": sha,
                "committedAt": committed_at,
                "message": subject,
            }
        )
    return versions
