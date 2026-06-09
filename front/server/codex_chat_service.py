import json
import logging
import os
import re
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from chat_session_service import finish_analysis_run
from session_tool_service import ensure_baseline_session_tools, ensure_session_tools

router = APIRouter(prefix="/api/chat", tags=["chat"])
baseline_router = APIRouter(prefix="/api/base/chat", tags=["base-chat"])
logger = logging.getLogger(__name__)

SESSION_ID_RE = re.compile(r"^[0-9a-f]{5}$")
THREAD_KEY_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
ANALYSIS_RUN_ID_RE = re.compile(r"^[a-zA-Z0-9_.-]{1,120}$")
WORKSPACE_ROLES = {"human", "agent"}
SESSION_MODES = {"specialized", "baseline"}
ARTIFACT_SUFFIXES = {".json", ".md", ".png", ".jpg", ".jpeg", ".webp"}
TIMELINE_MARKDOWN = "markdown"
TIMELINE_ACTIVITY_SEQUENCE = "activity_sequence"
TIMELINE_ARTIFACT = "artifact"
ACTIVITY_LEVELS = {"primary", "highlight", "detail", "debug", "error", "ephemeral"}
ARTIFACT_KIND_BY_SUFFIX = {
    ".json": "json",
    ".md": "markdown",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
}
MARKDOWN_REF_RE = re.compile(r"(!?)\[([^\]]*)\]\(([^)]*)\)")
CODE_BLOCK_OR_INLINE_RE = re.compile(r"(```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]*`)")
DEFAULT_CODEX_BRIDGE_URL = "http://127.0.0.1:8787"
CODEX_BRIDGE_URL = os.getenv("CODEX_BRIDGE_URL", DEFAULT_CODEX_BRIDGE_URL)
BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
SESSIONS_DIR = REPO_ROOT / ".maniscope-chat" / "sessions"
BASELINE_SESSIONS_DIR = REPO_ROOT / ".maniscope-chat" / "baseline-sessions"


def _validate_session_id(session_id: str) -> None:
    if not SESSION_ID_RE.fullmatch(session_id):
        raise HTTPException(status_code=400, detail="Session ID must be 5 lowercase hex characters")


def _validate_thread_key(thread_key: str) -> None:
    if not THREAD_KEY_RE.fullmatch(thread_key):
        raise HTTPException(status_code=400, detail="Thread key must use letters, numbers, underscores, or hyphens")


def _validate_workspace_role(role: str) -> str:
    if role not in WORKSPACE_ROLES:
        raise HTTPException(status_code=400, detail="workspaceRole must be 'human' or 'agent'")
    return role


def _validate_session_mode(session_mode: str) -> str:
    if session_mode not in SESSION_MODES:
        raise HTTPException(status_code=400, detail="sessionMode must be 'specialized' or 'baseline'")
    return session_mode


def _sessions_dir(session_mode: str = "specialized") -> Path:
    _validate_session_mode(session_mode)
    return BASELINE_SESSIONS_DIR if session_mode == "baseline" else SESSIONS_DIR


def _session_api_prefix(session_mode: str = "specialized") -> str:
    return "/api/base/sessions" if session_mode == "baseline" else "/api/sessions"


def _validate_mode_workspace_role(role: str, session_mode: str = "specialized") -> str:
    session_mode = _validate_session_mode(session_mode)
    if session_mode == "baseline":
        if role != "human":
            raise HTTPException(status_code=400, detail="Baseline chat only supports the human workspace")
        return role
    return _validate_workspace_role(role)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _session_dir(session_id: str, session_mode: str = "specialized") -> Path:
    _validate_session_id(session_id)
    session_dir = _sessions_dir(session_mode) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "images").mkdir(exist_ok=True)
    (session_dir / "artifacts").mkdir(exist_ok=True)
    if session_mode == "baseline":
        ensure_baseline_session_tools(session_dir, session_id)
    else:
        ensure_session_tools(session_dir, session_id)
    return session_dir


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def _read_json(path: Path, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return fallback or {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in {path.name}")


def _artifact_url(session_id: str, artifact_name: str, session_mode: str = "specialized") -> str:
    return f"{_session_api_prefix(session_mode)}/{session_id}/artifacts/{artifact_name}"


def _artifact_kind(path: Path) -> str:
    return ARTIFACT_KIND_BY_SUFFIX.get(path.suffix.lower(), "file")


def _artifact_object(artifact_path: Path) -> dict[str, Any]:
    stat = artifact_path.stat()
    artifact_name = artifact_path.name
    return {
        "id": re.sub(r"[^a-zA-Z0-9_-]+", "-", artifact_name),
        "title": artifact_name,
        "kind": _artifact_kind(artifact_path),
        "path": f"artifacts/{artifact_name}",
        "updatedAt": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def _parse_markdown_destination(raw_destination: str) -> tuple[str, str] | None:
    raw = str(raw_destination or "").strip()
    if not raw:
        return None
    if raw.startswith("<"):
        end = raw.find(">")
        if end > 1:
            return raw[1:end], raw[end + 1 :]
    match = re.match(r"^(\S+)(\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?$", raw)
    if match:
        return match.group(1), match.group(2) or ""
    return raw, ""


def _artifact_from_destination(
    session_id: str,
    session_dir: Path,
    destination: str,
    session_mode: str,
) -> tuple[dict[str, Any], str] | None:
    if not destination:
        return None

    artifact_prefixes = [
        f"{_session_api_prefix(session_mode)}/{session_id}/artifacts/",
        f"/api/sessions/{session_id}/artifacts/",
        f"/api/base/sessions/{session_id}/artifacts/",
    ]
    matching_prefix = next((prefix for prefix in artifact_prefixes if destination.startswith(prefix)), None)
    if matching_prefix:
        artifact_name = unquote(destination.split(matching_prefix, 1)[1].split("?", 1)[0].split("#", 1)[0])
        candidates = [session_dir / "artifacts" / artifact_name]
    else:
        parsed = urlparse(destination)
        candidate_text = parsed.path if parsed.scheme in {"http", "https"} else destination
        candidate_text = unquote(candidate_text.split("?", 1)[0].split("#", 1)[0])
        candidates = []
        if candidate_text.startswith("artifacts/"):
            candidates.append(session_dir / candidate_text)
        elif "/" not in candidate_text and "\\" not in candidate_text:
            candidates.append(session_dir / "artifacts" / candidate_text)
        elif candidate_text:
            candidates.append(Path(candidate_text))

    artifacts_root = (session_dir / "artifacts").resolve()
    for candidate in candidates:
        resolved = candidate.resolve()
        try:
            resolved.relative_to(artifacts_root)
        except ValueError:
            continue
        if resolved.suffix.lower() not in ARTIFACT_SUFFIXES:
            continue
        if not resolved.exists() or not resolved.is_file():
            continue
        artifact = _artifact_object(resolved)
        return artifact, _artifact_url(session_id, artifact["title"], session_mode=session_mode)
    return None


def _split_markdown_protected_segments(content: str) -> list[tuple[bool, str]]:
    segments: list[tuple[bool, str]] = []
    last_index = 0
    for match in CODE_BLOCK_OR_INLINE_RE.finditer(content):
        if match.start() > last_index:
            segments.append((False, content[last_index : match.start()]))
        segments.append((True, match.group(0)))
        last_index = match.end()
    if last_index < len(content):
        segments.append((False, content[last_index:]))
    return segments


def _normalize_history_message_artifacts(
    session_id: str,
    session_dir: Path,
    message: dict[str, Any],
    session_mode: str = "specialized",
) -> dict[str, Any]:
    normalized = dict(message)
    content = str(normalized.get("content") or "")
    artifacts_by_id = {
        artifact.get("id"): artifact
        for artifact in normalized.get("artifacts", [])
        if isinstance(artifact, dict) and artifact.get("id")
    }

    def rewrite_segment(segment: str) -> str:
        def replace(match: re.Match[str]) -> str:
            parsed = _parse_markdown_destination(match.group(3))
            if not parsed:
                return match.group(0)
            destination, suffix = parsed
            materialized = _artifact_from_destination(session_id, session_dir, destination, session_mode)
            if not materialized:
                return match.group(0)
            artifact, url = materialized
            artifacts_by_id[artifact["id"]] = artifact
            marker = match.group(1) if artifact["kind"] == "image" else ""
            return f"{marker}[{match.group(2)}]({url}{suffix})"

        return MARKDOWN_REF_RE.sub(replace, segment)

    if content:
        normalized["content"] = "".join(
            segment if protected else rewrite_segment(segment)
            for protected, segment in _split_markdown_protected_segments(content)
        )
    normalized["artifacts"] = list(artifacts_by_id.values())
    return normalized


def _history_path(session_id: str, thread_key: str, session_mode: str = "specialized") -> Path:
    _validate_thread_key(thread_key)
    return _session_dir(session_id, session_mode=session_mode) / f"chat-history-{thread_key}.json"


def _thread_cache_path(session_id: str, session_mode: str = "specialized") -> Path:
    return _session_dir(session_id, session_mode=session_mode) / "codex-threads.json"


def _analysis_task_exists_for_run(session_id: str, run_id: str, session_mode: str = "specialized") -> bool:
    if session_mode != "specialized" or not run_id:
        return False
    tasks_dir = _session_dir(session_id, session_mode=session_mode) / "analysis-tasks"
    if not tasks_dir.exists():
        return False
    for path in tasks_dir.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and payload.get("runId") == run_id:
            return True
    return False


def _sse_event(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _message_id_value(message: dict[str, Any]) -> int:
    try:
        return int(message.get("id", 0))
    except (TypeError, ValueError):
        return 0


def _next_message_id(messages: list[Any]) -> int:
    return (
        max(
            (
                _message_id_value(message)
                for message in messages
                if isinstance(message, dict)
            ),
            default=0,
        )
        + 1
    )


def _next_activity_id(messages: list[Any]) -> int:
    max_id = 0
    for message in messages:
        if not isinstance(message, dict):
            continue
        for activity in message.get("activity", []):
            if not isinstance(activity, dict):
                continue
            try:
                max_id = max(max_id, int(activity.get("id", 0)))
            except (TypeError, ValueError):
                continue
        for part in message.get("parts", []):
            if not isinstance(part, dict) or part.get("type") != TIMELINE_ACTIVITY_SEQUENCE:
                continue
            for activity in part.get("activities", []):
                if not isinstance(activity, dict):
                    continue
                try:
                    max_id = max(max_id, int(activity.get("id", 0)))
                except (TypeError, ValueError):
                    continue
    return max_id + 1


def _next_part_id(messages: list[Any]) -> int:
    total_parts = 0
    for message in messages:
        if isinstance(message, dict) and isinstance(message.get("parts"), list):
            total_parts += len(message["parts"])
    return total_parts + 1


def _sanitize_attachment_metadata(body: dict[str, Any]) -> list[dict[str, Any]]:
    source = body.get("attachmentMetadata")
    if not isinstance(source, list):
        source = body.get("attachments") if isinstance(body.get("attachments"), list) else []
    attachments: list[dict[str, Any]] = []
    for index, attachment in enumerate(source):
        if not isinstance(attachment, dict):
            continue
        name = str(attachment.get("name") or f"attachment-{index + 1}")
        attachment_type = str(attachment.get("type") or "")
        attachments.append(
            {
                "id": attachment.get("id", index + 1),
                "name": name,
                "type": attachment_type,
            }
        )
    return attachments


def _sanitize_analysis_run(body: dict[str, Any], session_mode: str) -> dict[str, Any] | None:
    if session_mode != "specialized":
        return None
    source = body.get("analysisRun")
    if not isinstance(source, dict):
        return None
    run_id = str(source.get("runId") or "").strip()
    if not run_id or not ANALYSIS_RUN_ID_RE.fullmatch(run_id):
        return None
    sanitized: dict[str, Any] = {
        "runId": run_id,
        "mode": str(source.get("mode") or ""),
        "presetKind": str(source.get("presetKind") or ""),
        "status": str(source.get("status") or ""),
        "startedAt": str(source.get("startedAt") or ""),
    }
    start_anchor = source.get("startAnchor")
    if isinstance(start_anchor, dict):
        sanitized["startAnchor"] = start_anchor
    return sanitized


def _normalize_activity(activity: Any, fallback_id: int) -> dict[str, Any]:
    if isinstance(activity, str):
        return {
            "id": fallback_id,
            "text": activity,
            "title": activity,
            "detail": "",
            "output": "",
            "level": "detail",
            "category": "legacy",
            "status": "",
            "eventId": "",
            "ephemeral": False,
        }

    payload = activity if isinstance(activity, dict) else {}
    title = str(payload.get("title") or payload.get("text") or payload.get("command") or payload.get("type") or "Activity")
    level = str(payload.get("level") or "detail")
    return {
        "id": payload.get("id") or fallback_id,
        "text": str(payload.get("text") or title),
        "title": title,
        "detail": str(payload.get("detail") or ""),
        "output": str(payload.get("output") or ""),
        "level": level if level in ACTIVITY_LEVELS else "detail",
        "category": str(payload.get("category") or payload.get("type") or "event"),
        "status": str(payload.get("status") or ""),
        "eventId": str(payload.get("eventId") or ""),
        "ephemeral": bool(payload.get("ephemeral")),
    }


def _artifact_key(artifact: Any) -> str:
    if not isinstance(artifact, dict):
        return ""
    return str(artifact.get("id") or artifact.get("path") or artifact.get("title") or artifact.get("name") or "")


def _activity_key(activity: dict[str, Any]) -> str:
    event_id = str(activity.get("eventId") or "")
    if not event_id:
        return ""
    return f"{event_id}:{activity.get('category') or ''}"


def _append_markdown_part(parts: list[dict[str, Any]], part_id: str, text: str) -> None:
    if not text:
        return
    if parts and parts[-1].get("type") == TIMELINE_MARKDOWN:
        parts[-1]["text"] = f"{parts[-1].get('text', '')}\n\n{text}" if parts[-1].get("text") else text
        return
    parts.append({"id": part_id, "type": TIMELINE_MARKDOWN, "text": text})


def _append_artifact_part(parts: list[dict[str, Any]], part_id: str, artifact: dict[str, Any]) -> None:
    key = _artifact_key(artifact)
    if not key:
        return
    for part in parts:
        if part.get("type") == TIMELINE_ARTIFACT and _artifact_key(part.get("artifact")) == key:
            existing = part.get("artifact") if isinstance(part.get("artifact"), dict) else {}
            part["artifact"] = {**existing, **artifact}
            return
    parts.append({"id": part_id, "type": TIMELINE_ARTIFACT, "artifact": dict(artifact)})


def _append_activity_to_timeline(parts: list[dict[str, Any]], sequence_id: str, activity: dict[str, Any]) -> None:
    if not activity or activity.get("ephemeral"):
        return

    key = _activity_key(activity)
    if key:
        for part in parts:
            if part.get("type") != TIMELINE_ACTIVITY_SEQUENCE or not isinstance(part.get("activities"), list):
                continue
            for index, existing_activity in enumerate(part["activities"]):
                if isinstance(existing_activity, dict) and _activity_key(existing_activity) == key:
                    part["activities"][index] = {**existing_activity, **activity, "id": existing_activity.get("id")}
                    return

    sequence = parts[-1] if parts else None
    if not isinstance(sequence, dict) or sequence.get("type") != TIMELINE_ACTIVITY_SEQUENCE:
        sequence = {"id": sequence_id, "type": TIMELINE_ACTIVITY_SEQUENCE, "activities": [], "open": False}
        parts.append(sequence)
    sequence["activities"].append(activity)


def _append_unique_artifact(artifacts: list[dict[str, Any]], artifact: dict[str, Any]) -> None:
    key = _artifact_key(artifact)
    if not key:
        return
    for index, existing_artifact in enumerate(artifacts):
        if _artifact_key(existing_artifact) == key:
            artifacts[index] = {**existing_artifact, **artifact}
            return
    artifacts.append(dict(artifact))


def _format_usage(usage: Any) -> str:
    if not isinstance(usage, dict):
        return ""
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    reasoning_tokens = int(usage.get("reasoning_output_tokens") or 0)
    return f"{input_tokens} input, {output_tokens} output, {reasoning_tokens} reasoning tokens"


def _history_payload(
    session_id: str,
    thread_key: str,
    session_mode: str,
    messages: list[Any],
) -> dict[str, Any]:
    return {
        "sessionId": session_id,
        "sessionMode": session_mode,
        "threadKey": thread_key,
        "lastUpdatedAt": _now_iso(),
        "messages": messages,
    }


def _write_history_payload(
    session_id: str,
    thread_key: str,
    session_mode: str,
    messages: list[Any],
) -> None:
    _atomic_write_json(
        _history_path(session_id, thread_key, session_mode=session_mode),
        _history_payload(session_id, thread_key, session_mode, messages),
    )


def _start_stream_history_turn(
    session_id: str,
    thread_key: str,
    session_mode: str,
    body: dict[str, Any],
    hidden_message: str,
) -> tuple[list[Any], dict[str, Any], dict[str, int]]:
    history = _read_json(_history_path(session_id, thread_key, session_mode=session_mode), {"messages": []})
    messages = history.get("messages") if isinstance(history.get("messages"), list) else []
    messages = list(messages)
    now = _now_iso()
    next_message_id = _next_message_id(messages)
    user_message = {
        "id": next_message_id,
        "role": "user",
        "content": str(body.get("displayMessage") or hidden_message),
        "attachments": _sanitize_attachment_metadata(body),
        "activity": [],
        "artifacts": [],
        "parts": [],
        "presetKind": str(body.get("presetKind") or ""),
        "activityOpen": False,
        "threadId": "",
        "createdAt": now,
    }
    analysis_run = _sanitize_analysis_run(body, session_mode)
    if analysis_run:
        user_message["analysisRun"] = analysis_run
    assistant_message = {
        "id": next_message_id + 1,
        "role": "assistant",
        "content": "",
        "attachments": [],
        "activity": [],
        "artifacts": [],
        "parts": [],
        "presetKind": "",
        "activityOpen": False,
        "threadId": "",
        "createdAt": now,
        "turnState": "streaming",
    }
    messages.extend([user_message, assistant_message])
    counters = {
        "activity": _next_activity_id(messages),
        "part": _next_part_id(messages),
    }
    _write_history_payload(session_id, thread_key, session_mode, messages)
    return messages, assistant_message, counters


def _append_history_markdown(assistant_message: dict[str, Any], counters: dict[str, int], text: str) -> None:
    if not text:
        return
    assistant_message["content"] = (
        f"{assistant_message.get('content', '')}\n\n{text}" if assistant_message.get("content") else text
    )
    _append_markdown_part(
        assistant_message.setdefault("parts", []),
        f"part-{counters['part']}",
        text,
    )
    counters["part"] += 1


def _append_history_activity(
    assistant_message: dict[str, Any],
    counters: dict[str, int],
    activity: Any,
) -> None:
    normalized = _normalize_activity(activity, counters["activity"])
    if normalized.get("ephemeral"):
        return
    counters["activity"] += 1
    activities = assistant_message.setdefault("activity", [])
    existing_index = -1
    if normalized.get("eventId"):
        for index, existing_activity in enumerate(activities):
            if (
                isinstance(existing_activity, dict)
                and existing_activity.get("eventId") == normalized.get("eventId")
                and existing_activity.get("category") == normalized.get("category")
            ):
                existing_index = index
                break
    if existing_index != -1:
        normalized = {**activities[existing_index], **normalized, "id": activities[existing_index].get("id")}
        activities[existing_index] = normalized
    else:
        activities.append(normalized)
    _append_activity_to_timeline(assistant_message.setdefault("parts", []), f"part-{counters['part']}", normalized)
    counters["part"] += 1


def _apply_chat_event_to_history(
    event: dict[str, Any],
    assistant_message: dict[str, Any],
    counters: dict[str, int],
) -> str | None:
    event_type = event.get("type")
    if event_type == "agent_message":
        _append_history_markdown(assistant_message, counters, str(event.get("text") or ""))
    elif event_type == "reasoning":
        return None
    elif event_type in {"status", "command", "file_change", "web_search", "todo_list", "mcp_tool_call"}:
        _append_history_activity(assistant_message, counters, event)
    elif event_type == "artifact" and isinstance(event.get("artifact"), dict):
        artifact = event["artifact"]
        _append_unique_artifact(assistant_message.setdefault("artifacts", []), artifact)
        _append_artifact_part(assistant_message.setdefault("parts", []), f"part-{counters['part']}", artifact)
        counters["part"] += 1
    elif event_type == "error":
        _append_history_activity(
            assistant_message,
            counters,
            {
                "level": "error",
                "category": "session",
                "title": event.get("title") or "Codex error",
                "detail": event.get("error") or "",
            },
        )
    elif event_type == "thread":
        assistant_message["threadId"] = event.get("threadId") or assistant_message.get("threadId", "")
        _append_history_activity(assistant_message, counters, event)
    elif event_type == "usage":
        _append_history_activity(
            assistant_message,
            counters,
            {
                "level": "debug",
                "category": "session",
                "title": "Token usage",
                "detail": _format_usage(event.get("usage")),
            },
        )
    elif event_type == "stopped":
        _append_history_activity(assistant_message, counters, event)
        if not assistant_message.get("content"):
            _append_history_markdown(assistant_message, counters, "Stopped before completion.")
        assistant_message["turnState"] = "stopped"
        return "stopped"
    elif event_type == "done":
        assistant_message["threadId"] = event.get("threadId") or assistant_message.get("threadId", "")
        _append_history_activity(
            assistant_message,
            counters,
            {
                "level": "detail",
                "category": "session",
                "title": "Turn complete",
                "detail": "Codex finished this turn.",
            },
        )
        assistant_message["turnState"] = "completed"
        return "completed"
    return None


def _mark_history_turn_interrupted(
    assistant_message: dict[str, Any],
    counters: dict[str, int],
    reason: str,
    state: str = "interrupted",
) -> None:
    if assistant_message.get("turnState") in {"completed", "stopped", "failed"}:
        return
    assistant_message["turnState"] = state
    _append_history_activity(
        assistant_message,
        counters,
        {
            "level": "error" if state == "failed" else "highlight",
            "category": "session",
            "title": "Turn interrupted" if state == "interrupted" else "Turn ended with error",
            "detail": reason,
        },
    )


def _sse_payload_from_lines(lines: list[str]) -> dict[str, Any] | None:
    data = "\n".join(line[5:].lstrip() for line in lines if line.startswith("data:"))
    if not data:
        return None
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _stream_codex_response(
    session_id: str,
    payload: dict[str, Any],
    *,
    history_messages: list[Any],
    assistant_message: dict[str, Any],
    history_counters: dict[str, int],
    thread_key: str,
    session_mode: str,
    analysis_run: dict[str, Any] | None,
) -> Iterator[str]:
    url = f"{CODEX_BRIDGE_URL.rstrip('/')}/chat/{session_id}/message"
    pending_event_lines: list[str] = []
    terminal_state: str | None = None
    saw_error = False
    client_disconnected = False

    def persist() -> None:
        _write_history_payload(session_id, thread_key, session_mode, history_messages)

    def apply_and_persist(event: dict[str, Any]) -> None:
        nonlocal terminal_state, saw_error
        if event.get("type") == "error":
            saw_error = True
        state = _apply_chat_event_to_history(event, assistant_message, history_counters)
        if state:
            terminal_state = state
        persist()

    try:
        with requests.post(url, json=payload, stream=True, timeout=(3, None)) as response:
            response.encoding = "utf-8"
            if response.status_code != 200:
                detail = response.text.strip() or response.reason
                event = {
                    "type": "error",
                    "error": f"Codex bridge returned HTTP {response.status_code}: {detail}",
                }
                apply_and_persist(event)
                assistant_message["turnState"] = "failed"
                persist()
                yield _sse_event(event)
                return

            for line in response.iter_lines(chunk_size=1, decode_unicode=True):
                if line == "":
                    event = _sse_payload_from_lines(pending_event_lines)
                    if event:
                        apply_and_persist(event)
                    pending_event_lines = []
                else:
                    pending_event_lines.append(line)
                yield f"{line}\n"
    except requests.ConnectionError:
        event = {
            "type": "error",
            "error": "Codex bridge is not running. Start it with `bun run codex-bridge` in front/.",
        }
        apply_and_persist(event)
        assistant_message["turnState"] = "failed"
        persist()
        yield _sse_event(event)
    except requests.Timeout:
        event = {"type": "error", "error": "Timed out while connecting to the Codex bridge."}
        apply_and_persist(event)
        assistant_message["turnState"] = "failed"
        persist()
        yield _sse_event(event)
    except requests.RequestException as exc:
        event = {"type": "error", "error": f"Codex bridge request failed: {exc}"}
        apply_and_persist(event)
        assistant_message["turnState"] = "failed"
        persist()
        yield _sse_event(event)
    except GeneratorExit:
        client_disconnected = True
        raise
    finally:
        if pending_event_lines:
            event = _sse_payload_from_lines(pending_event_lines)
            if event:
                apply_and_persist(event)
        if terminal_state is None:
            if client_disconnected:
                _mark_history_turn_interrupted(
                    assistant_message,
                    history_counters,
                    "Browser disconnected before the Codex turn completed.",
                )
            elif saw_error:
                _mark_history_turn_interrupted(
                    assistant_message,
                    history_counters,
                    "The Codex stream ended after an error event.",
                    state="failed",
                )
            else:
                _mark_history_turn_interrupted(
                    assistant_message,
                    history_counters,
                    "The Codex stream ended before a completion event.",
                )
        persist()
        background_task_preset = analysis_run and analysis_run.get("presetKind") in {"full_analysis", "update_analysis"}
        background_task_started = bool(
            background_task_preset
            and _analysis_task_exists_for_run(session_id, str(analysis_run.get("runId") or ""), session_mode)
        )
        if analysis_run and analysis_run.get("runId") and not background_task_started:
            run_status = str(assistant_message.get("turnState") or "")
            if run_status not in {"completed", "stopped", "failed", "interrupted"}:
                run_status = "failed" if saw_error else "interrupted"
            try:
                finish_analysis_run(
                    session_id,
                    str(analysis_run["runId"]),
                    run_status,
                    session_mode=session_mode,
                )
            except Exception as exc:
                logger.warning("Failed to finalize analysis run %s: %s", analysis_run["runId"], exc)


def _stop_codex_turn(session_id: str, thread_key: str, session_mode: str = "specialized") -> dict[str, Any]:
    url = f"{CODEX_BRIDGE_URL.rstrip('/')}/chat/{session_id}/threads/{thread_key}/stop"
    try:
        response = requests.post(url, json={"sessionMode": session_mode}, timeout=5)
    except requests.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="Codex bridge is not running. Start it with `bun run codex-bridge` in front/.",
        )
    except requests.Timeout:
        raise HTTPException(status_code=504, detail="Timed out while stopping the Codex turn.")
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Codex bridge stop request failed: {exc}")

    if not response.ok:
        detail = response.text.strip() or response.reason
        raise HTTPException(status_code=response.status_code, detail=detail)
    return response.json()


def _send_chat_message(session_id: str, body: dict[str, Any], session_mode: str = "specialized") -> StreamingResponse:
    _validate_session_id(session_id)
    session_mode = _validate_session_mode(session_mode)

    message = str(body.get("message") or "").strip()
    attachments = body.get("attachments") if isinstance(body.get("attachments"), list) else []
    if not message and not attachments:
        raise HTTPException(status_code=400, detail="message or image attachment is required")

    thread_key = str(body.get("threadKey") or "trace-analysis")
    _validate_thread_key(thread_key)
    workspace_role = _validate_mode_workspace_role(str(body.get("workspaceRole") or "human"), session_mode=session_mode)

    payload = {
        "message": message,
        "threadKey": thread_key,
        "attachments": attachments,
        "includeCurrentTrace": body.get("includeCurrentTrace", True),
        "includeCurrentViews": body.get("includeCurrentViews", True),
        "workspaceRole": workspace_role,
        "sessionMode": session_mode,
    }
    analysis_run = _sanitize_analysis_run(body, session_mode)
    if analysis_run:
        payload["analysisRun"] = analysis_run
    history_messages, assistant_message, history_counters = _start_stream_history_turn(
        session_id,
        thread_key,
        session_mode,
        body,
        message,
    )
    return StreamingResponse(
        _stream_codex_response(
            session_id,
            payload,
            history_messages=history_messages,
            assistant_message=assistant_message,
            history_counters=history_counters,
            thread_key=thread_key,
            session_mode=session_mode,
            analysis_run=analysis_run,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _get_chat_history(session_id: str, threadKey: str = "trace-analysis", session_mode: str = "specialized") -> dict[str, Any]:
    session_dir = _session_dir(session_id, session_mode=session_mode)
    history = _read_json(_history_path(session_id, threadKey, session_mode=session_mode), {"messages": []})
    messages = [
        _normalize_history_message_artifacts(session_id, session_dir, message, session_mode=session_mode)
        if isinstance(message, dict)
        else message
        for message in history.get("messages", [])
    ]
    return {
        "sessionId": session_id,
        "sessionMode": session_mode,
        "threadKey": threadKey,
        "messages": messages,
        "lastUpdatedAt": history.get("lastUpdatedAt"),
    }


def _save_chat_history(session_id: str, body: dict[str, Any], session_mode: str = "specialized") -> dict[str, Any]:
    thread_key = str(body.get("threadKey") or "trace-analysis")
    messages = body.get("messages")
    if not isinstance(messages, list):
        raise HTTPException(status_code=400, detail="messages must be an array")

    now = _now_iso()
    payload = {
        "sessionId": session_id,
        "sessionMode": session_mode,
        "threadKey": thread_key,
        "lastUpdatedAt": now,
        "messages": messages,
    }
    _atomic_write_json(_history_path(session_id, thread_key, session_mode=session_mode), payload)
    return {"sessionId": session_id, "sessionMode": session_mode, "threadKey": thread_key, "lastUpdatedAt": now}


def _clear_chat_thread(session_id: str, thread_key: str, session_mode: str = "specialized") -> dict[str, Any]:
    _validate_thread_key(thread_key)
    history_path = _history_path(session_id, thread_key, session_mode=session_mode)
    if history_path.exists():
        history_path.unlink()

    thread_cache_path = _thread_cache_path(session_id, session_mode=session_mode)
    thread_cache = _read_json(thread_cache_path, {})
    removed_thread = thread_cache.pop(thread_key, None)
    if thread_cache:
        _atomic_write_json(thread_cache_path, thread_cache)
    elif thread_cache_path.exists():
        thread_cache_path.unlink()

    return {
        "sessionId": session_id,
        "sessionMode": session_mode,
        "threadKey": thread_key,
        "removedThread": bool(removed_thread),
    }


def _stop_chat_thread(session_id: str, thread_key: str, session_mode: str = "specialized") -> dict[str, Any]:
    _validate_session_id(session_id)
    _validate_thread_key(thread_key)
    return _stop_codex_turn(session_id, thread_key, session_mode=session_mode)


@router.post("/{session_id}/message")
def send_chat_message(session_id: str, body: dict[str, Any]) -> StreamingResponse:
    return _send_chat_message(session_id, body, session_mode="specialized")


@baseline_router.post("/{session_id}/message")
def send_baseline_chat_message(session_id: str, body: dict[str, Any]) -> StreamingResponse:
    return _send_chat_message(session_id, body, session_mode="baseline")


@router.get("/{session_id}/history")
def get_chat_history(session_id: str, threadKey: str = "trace-analysis") -> dict[str, Any]:
    return _get_chat_history(session_id, threadKey=threadKey, session_mode="specialized")


@baseline_router.get("/{session_id}/history")
def get_baseline_chat_history(session_id: str, threadKey: str = "trace-analysis") -> dict[str, Any]:
    return _get_chat_history(session_id, threadKey=threadKey, session_mode="baseline")


@router.put("/{session_id}/history")
def save_chat_history(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return _save_chat_history(session_id, body, session_mode="specialized")


@baseline_router.put("/{session_id}/history")
def save_baseline_chat_history(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return _save_chat_history(session_id, body, session_mode="baseline")


@router.delete("/{session_id}/threads/{thread_key}")
def clear_chat_thread(session_id: str, thread_key: str) -> dict[str, Any]:
    return _clear_chat_thread(session_id, thread_key, session_mode="specialized")


@baseline_router.delete("/{session_id}/threads/{thread_key}")
def clear_baseline_chat_thread(session_id: str, thread_key: str) -> dict[str, Any]:
    return _clear_chat_thread(session_id, thread_key, session_mode="baseline")


@router.post("/{session_id}/threads/{thread_key}/stop")
def stop_chat_thread(session_id: str, thread_key: str) -> dict[str, Any]:
    return _stop_chat_thread(session_id, thread_key, session_mode="specialized")


@baseline_router.post("/{session_id}/threads/{thread_key}/stop")
def stop_baseline_chat_thread(session_id: str, thread_key: str) -> dict[str, Any]:
    return _stop_chat_thread(session_id, thread_key, session_mode="baseline")


@router.get("/health")
def chat_health() -> dict[str, Any]:
    try:
        response = requests.get(f"{CODEX_BRIDGE_URL.rstrip('/')}/health", timeout=2)
    except requests.RequestException as exc:
        return {"ok": False, "bridgeUrl": CODEX_BRIDGE_URL, "error": str(exc)}
    return {
        "ok": response.ok,
        "bridgeUrl": CODEX_BRIDGE_URL,
        "statusCode": response.status_code,
    }


@baseline_router.get("/health")
def baseline_chat_health() -> dict[str, Any]:
    return chat_health()
