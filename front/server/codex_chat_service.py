import json
import os
import re
from collections.abc import Iterator
from typing import Any

import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse


router = APIRouter(prefix="/api/chat", tags=["chat"])

SESSION_ID_RE = re.compile(r"^[0-9a-f]{5}$")
CODEX_BRIDGE_URL = os.getenv("CODEX_BRIDGE_URL", "http://127.0.0.1:8787")


def _validate_session_id(session_id: str) -> None:
    if not SESSION_ID_RE.fullmatch(session_id):
        raise HTTPException(status_code=400, detail="Session ID must be 5 lowercase hex characters")


def _sse_event(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _stream_codex_response(session_id: str, payload: dict[str, Any]) -> Iterator[str]:
    url = f"{CODEX_BRIDGE_URL.rstrip('/')}/chat/{session_id}/message"
    try:
        with requests.post(url, json=payload, stream=True, timeout=(3, None)) as response:
            if response.status_code != 200:
                detail = response.text.strip() or response.reason
                yield _sse_event(
                    {
                        "type": "error",
                        "error": f"Codex bridge returned HTTP {response.status_code}: {detail}",
                    }
                )
                return

            for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                if chunk:
                    yield chunk
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


@router.post("/{session_id}/message")
def send_chat_message(session_id: str, body: dict[str, Any]) -> StreamingResponse:
    _validate_session_id(session_id)

    message = str(body.get("message") or "").strip()
    attachments = body.get("attachments") if isinstance(body.get("attachments"), list) else []
    if not message and not attachments:
        raise HTTPException(status_code=400, detail="message or image attachment is required")

    payload = {
        "message": message,
        "threadKey": str(body.get("threadKey") or "trace-analysis"),
        "attachments": attachments,
    }
    return StreamingResponse(
        _stream_codex_response(session_id, payload),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


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
