import json
import os
import re
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])

SESSION_ID_RE = re.compile(r"^[0-9a-f]{5}$")
THREAD_KEY_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
CODEX_BRIDGE_URL = os.getenv("CODEX_BRIDGE_URL", "http://127.0.0.1:8787")
BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
SESSIONS_DIR = REPO_ROOT / ".maniscope-chat" / "sessions"


def _validate_session_id(session_id: str) -> None:
    if not SESSION_ID_RE.fullmatch(session_id):
        raise HTTPException(status_code=400, detail="Session ID must be 5 lowercase hex characters")


def _validate_thread_key(thread_key: str) -> None:
    if not THREAD_KEY_RE.fullmatch(thread_key):
        raise HTTPException(status_code=400, detail="Thread key must use letters, numbers, underscores, or hyphens")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _session_dir(session_id: str) -> Path:
    _validate_session_id(session_id)
    session_dir = SESSIONS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "images").mkdir(exist_ok=True)
    (session_dir / "artifacts").mkdir(exist_ok=True)
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


def _history_path(session_id: str, thread_key: str) -> Path:
    _validate_thread_key(thread_key)
    return _session_dir(session_id) / f"chat-history-{thread_key}.json"


def _thread_cache_path(session_id: str) -> Path:
    return _session_dir(session_id) / "codex-threads.json"


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


def _stop_codex_turn(session_id: str, thread_key: str) -> dict[str, Any]:
    url = f"{CODEX_BRIDGE_URL.rstrip('/')}/chat/{session_id}/threads/{thread_key}/stop"
    try:
        response = requests.post(url, json={}, timeout=5)
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


@router.post("/{session_id}/message")
def send_chat_message(session_id: str, body: dict[str, Any]) -> StreamingResponse:
    _validate_session_id(session_id)

    message = str(body.get("message") or "").strip()
    attachments = body.get("attachments") if isinstance(body.get("attachments"), list) else []
    if not message and not attachments:
        raise HTTPException(status_code=400, detail="message or image attachment is required")

    thread_key = str(body.get("threadKey") or "trace-analysis")
    _validate_thread_key(thread_key)

    payload = {
        "message": message,
        "threadKey": thread_key,
        "attachments": attachments,
        "includeCurrentTrace": body.get("includeCurrentTrace", True),
        "includeCurrentViews": body.get("includeCurrentViews", True),
    }
    return StreamingResponse(
        _stream_codex_response(session_id, payload),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{session_id}/history")
def get_chat_history(session_id: str, threadKey: str = "trace-analysis") -> dict[str, Any]:
    history = _read_json(_history_path(session_id, threadKey), {"messages": []})
    return {
        "sessionId": session_id,
        "threadKey": threadKey,
        "messages": history.get("messages", []),
        "lastUpdatedAt": history.get("lastUpdatedAt"),
    }


@router.put("/{session_id}/history")
def save_chat_history(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    thread_key = str(body.get("threadKey") or "trace-analysis")
    messages = body.get("messages")
    if not isinstance(messages, list):
        raise HTTPException(status_code=400, detail="messages must be an array")

    now = _now_iso()
    payload = {
        "sessionId": session_id,
        "threadKey": thread_key,
        "lastUpdatedAt": now,
        "messages": messages,
    }
    _atomic_write_json(_history_path(session_id, thread_key), payload)
    return {"sessionId": session_id, "threadKey": thread_key, "lastUpdatedAt": now}


@router.delete("/{session_id}/threads/{thread_key}")
def clear_chat_thread(session_id: str, thread_key: str) -> dict[str, Any]:
    _validate_thread_key(thread_key)
    history_path = _history_path(session_id, thread_key)
    if history_path.exists():
        history_path.unlink()

    thread_cache_path = _thread_cache_path(session_id)
    thread_cache = _read_json(thread_cache_path, {})
    removed_thread = thread_cache.pop(thread_key, None)
    if thread_cache:
        _atomic_write_json(thread_cache_path, thread_cache)
    elif thread_cache_path.exists():
        thread_cache_path.unlink()

    return {
        "sessionId": session_id,
        "threadKey": thread_key,
        "removedThread": bool(removed_thread),
    }


@router.post("/{session_id}/threads/{thread_key}/stop")
def stop_chat_thread(session_id: str, thread_key: str) -> dict[str, Any]:
    _validate_session_id(session_id)
    _validate_thread_key(thread_key)
    return _stop_codex_turn(session_id, thread_key)


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
