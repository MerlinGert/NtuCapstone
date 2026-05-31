import json
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

from session_tool_service import ensure_baseline_session_tools, ensure_session_tools

router = APIRouter(prefix="/api/chat", tags=["chat"])
baseline_router = APIRouter(prefix="/api/base/chat", tags=["base-chat"])

SESSION_ID_RE = re.compile(r"^[0-9a-f]{5}$")
THREAD_KEY_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
WORKSPACE_ROLES = {"human", "agent"}
SESSION_MODES = {"specialized", "baseline"}
ARTIFACT_SUFFIXES = {".json", ".md", ".png", ".jpg", ".jpeg", ".webp"}
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


def _sse_event(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _stream_codex_response(session_id: str, payload: dict[str, Any]) -> Iterator[str]:
    url = f"{CODEX_BRIDGE_URL.rstrip('/')}/chat/{session_id}/message"
    try:
        with requests.post(url, json=payload, stream=True, timeout=(3, None)) as response:
            response.encoding = "utf-8"
            if response.status_code != 200:
                detail = response.text.strip() or response.reason
                yield _sse_event(
                    {
                        "type": "error",
                        "error": f"Codex bridge returned HTTP {response.status_code}: {detail}",
                    }
                )
                return

            for line in response.iter_lines(chunk_size=1, decode_unicode=True):
                yield f"{line}\n"
    except requests.ConnectionError:
        yield _sse_event(
            {
                "type": "error",
                "error": "Codex bridge is not running. Start it with `bun run codex-bridge` in front/.",
            }
        )
    except requests.Timeout:
        yield _sse_event({"type": "error", "error": "Timed out while connecting to the Codex bridge."})
    except requests.RequestException as exc:
        yield _sse_event({"type": "error", "error": f"Codex bridge request failed: {exc}"})


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
    return StreamingResponse(
        _stream_codex_response(session_id, payload),
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
