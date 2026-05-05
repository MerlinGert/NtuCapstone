import base64
import copy
import json
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote_to_bytes

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse


router = APIRouter(prefix="/api/sessions", tags=["sessions"])

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
CHAT_ROOT = REPO_ROOT / ".maniscope-chat"
SESSIONS_DIR = CHAT_ROOT / "sessions"
SESSION_ID_RE = re.compile(r"^[0-9a-f]{5}$")
EXPORT_VERSION = "1.0"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_session_id(session_id: str) -> None:
    if not SESSION_ID_RE.fullmatch(session_id):
        raise HTTPException(status_code=400, detail="Session ID must be 5 lowercase hex characters")


def _session_dir(session_id: str) -> Path:
    _validate_session_id(session_id)
    return SESSIONS_DIR / session_id


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in {path.name}")


def _empty_live_session(session_id: str, coin: str | None = None) -> dict[str, Any]:
    return {
        "exportVersion": EXPORT_VERSION,
        "exportFormat": "live-session",
        "sessionId": session_id,
        "exportedAt": None,
        "lastUpdatedAt": None,
        "coin": coin,
        "includesSnapshots": True,
        "imageDirectory": "images",
        "imageCount": 0,
        "config": {
            "snapshotCategories": None,
            "snapshotQuality": None,
        },
        "annotationSeqId": 0,
        "userActionSequence": [],
        "annotationRecords": [],
    }


def _create_meta(session_id: str, coin: str | None = None, restored: bool = False) -> dict[str, Any]:
    now = _now_iso()
    return {
        "sessionId": session_id,
        "coin": coin,
        "createdAt": now,
        "lastUpdatedAt": now,
        "restoredFromExisting": restored,
    }


def _ensure_session(session_id: str, coin: str | None = None) -> tuple[Path, dict[str, Any], bool]:
    session_dir = _session_dir(session_id)
    existed = session_dir.exists()
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "images").mkdir(exist_ok=True)
    (session_dir / "artifacts").mkdir(exist_ok=True)

    meta_path = session_dir / "session-meta.json"
    meta = _read_json(meta_path)
    if meta is None:
        meta = _create_meta(session_id, coin=coin, restored=existed)
        _atomic_write_json(meta_path, meta)
    return session_dir, meta, existed


def _decode_png_data_url(data_url: str) -> bytes | None:
    if not isinstance(data_url, str) or not data_url.startswith("data:image/png"):
        return None
    try:
        header, payload = data_url.split(",", 1)
    except ValueError:
        return None
    if ";base64" in header:
        return base64.b64decode(payload)
    return unquote_to_bytes(payload)


def _safe_name_part(value: Any) -> str:
    text = str(value or "unknown").lower()
    cleaned = re.sub(r"[^a-z0-9_-]+", "-", text).strip("-")
    return cleaned or "unknown"


def _write_data_url_image(session_dir: Path, relative_path: str, data_url: str) -> str | None:
    png_bytes = _decode_png_data_url(data_url)
    if png_bytes is None:
        return None
    image_path = session_dir / relative_path
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(png_bytes)
    return relative_path


def _process_action_images(session_dir: Path, actions: list[Any]) -> int:
    image_count = 0
    for action_index, action in enumerate(actions):
        if not isinstance(action, dict):
            continue
        for field in ("sourceSnapshot", "targetSnapshot"):
            snapshots = action.get(field)
            if not isinstance(snapshots, list):
                continue
            for snapshot_index, snapshot in enumerate(snapshots):
                if not isinstance(snapshot, dict):
                    continue
                data_url = snapshot.pop("dataUrl", None)
                if data_url:
                    view_name = snapshot.get("viewName") or action.get("sourceView" if field == "sourceSnapshot" else "targetView")
                    file_name = "-".join(
                        [
                            "action",
                            str(action_index + 1).zfill(4),
                            "source" if field == "sourceSnapshot" else "target",
                            _safe_name_part(view_name),
                            str(snapshot_index + 1).zfill(2),
                        ]
                    )
                    image_path = _write_data_url_image(session_dir, f"images/{file_name}.png", data_url)
                    if image_path:
                        snapshot["imagePath"] = image_path
                if snapshot.get("imagePath"):
                    image_count += 1
    return image_count


def _process_annotation_images(session_dir: Path, annotations: list[Any]) -> int:
    image_count = 0
    for annotation_index, annotation in enumerate(annotations):
        if not isinstance(annotation, dict):
            continue
        data_url = annotation.pop("sketchDataUrl", None)
        if data_url:
            annotation_id = annotation.get("id", annotation_index + 1)
            source_view = annotation.get("sourceView", "unknown")
            image_path = _write_data_url_image(
                session_dir,
                f"images/annotation-{str(annotation_id).zfill(4)}-{_safe_name_part(source_view)}.png",
                data_url,
            )
            if image_path:
                annotation["sketchImagePath"] = image_path
        if annotation.get("sketchImagePath"):
            image_count += 1
    return image_count


def _process_current_state_images(session_dir: Path, current_state: dict[str, Any]) -> int:
    image_count = 0
    screenshots = current_state.get("majorViewScreenshots")
    if not isinstance(screenshots, dict):
        return image_count
    processed: dict[str, str] = {}
    for view_name, value in screenshots.items():
        if isinstance(value, str) and value.startswith("data:image/png"):
            image_path = _write_data_url_image(
                session_dir,
                f"images/current-{_safe_name_part(view_name)}.png",
                value,
            )
            if image_path:
                processed[view_name] = image_path
                image_count += 1
        elif isinstance(value, str):
            processed[view_name] = value
            image_count += 1
    current_state["majorViewScreenshots"] = processed
    return image_count


def _data_url_for_image(session_dir: Path, image_path: str | None) -> str | None:
    if not image_path:
        return None
    path = (session_dir / image_path).resolve()
    try:
        path.relative_to(session_dir.resolve())
    except ValueError:
        return None
    if not path.exists():
        return None
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _hydrate_live_session_for_frontend(session_dir: Path, live_session: dict[str, Any]) -> dict[str, Any]:
    hydrated = copy.deepcopy(live_session)
    for action in hydrated.get("userActionSequence", []):
        if not isinstance(action, dict):
            continue
        for field in ("sourceSnapshot", "targetSnapshot"):
            snapshots = action.get(field)
            if not isinstance(snapshots, list):
                continue
            for snapshot in snapshots:
                if not isinstance(snapshot, dict):
                    continue
                data_url = _data_url_for_image(session_dir, snapshot.get("imagePath"))
                if data_url:
                    snapshot["dataUrl"] = data_url
    for annotation in hydrated.get("annotationRecords", []):
        if not isinstance(annotation, dict):
            continue
        data_url = _data_url_for_image(session_dir, annotation.get("sketchImagePath"))
        if data_url:
            annotation["sketchDataUrl"] = data_url
    return hydrated


@router.post("")
def create_session(body: dict[str, Any] | None = None) -> dict[str, Any]:
    coin = (body or {}).get("coin")
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    for _ in range(20):
        session_id = secrets.token_hex(3)[:5]
        session_dir = SESSIONS_DIR / session_id
        try:
            session_dir.mkdir(parents=True)
        except FileExistsError:
            continue
        (session_dir / "images").mkdir()
        (session_dir / "artifacts").mkdir()
        meta = _create_meta(session_id, coin=coin, restored=False)
        _atomic_write_json(session_dir / "session-meta.json", meta)
        return {"sessionId": session_id, "meta": meta}

    raise HTTPException(status_code=503, detail="Unable to allocate a unique session ID")


@router.get("/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    session_dir, meta, existed = _ensure_session(session_id)
    live_session = _read_json(session_dir / "live-session.json")
    current_state = _read_json(session_dir / "current-state.json")
    return {
        "sessionId": session_id,
        "meta": {**meta, "restoredFromExisting": existed},
        "liveSession": _hydrate_live_session_for_frontend(session_dir, live_session) if live_session else None,
        "currentState": current_state,
    }


@router.get("/{session_id}/artifacts/{artifact_name}")
def get_session_artifact(session_id: str, artifact_name: str) -> FileResponse:
    session_dir = _session_dir(session_id)
    artifact_path = (session_dir / "artifacts" / artifact_name).resolve()
    try:
        artifact_path.relative_to((session_dir / "artifacts").resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid artifact path")

    allowed_suffixes = {".md", ".png", ".jpg", ".jpeg", ".webp"}
    if artifact_path.suffix.lower() not in allowed_suffixes:
        raise HTTPException(status_code=400, detail="Unsupported artifact type")
    if not artifact_path.exists() or not artifact_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")

    return FileResponse(artifact_path)


@router.post("/{session_id}/sync")
def sync_session(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    session_dir, meta, _ = _ensure_session(session_id, coin=body.get("coin"))

    actions = copy.deepcopy(body.get("userActionSequence") or [])
    annotations = copy.deepcopy(body.get("annotationRecords") or [])
    current_state = copy.deepcopy(body.get("currentState") or {})

    if not isinstance(actions, list):
        raise HTTPException(status_code=400, detail="userActionSequence must be an array")
    if not isinstance(annotations, list):
        raise HTTPException(status_code=400, detail="annotationRecords must be an array")
    if not isinstance(current_state, dict):
        raise HTTPException(status_code=400, detail="currentState must be an object")

    image_count = 0
    image_count += _process_action_images(session_dir, actions)
    image_count += _process_annotation_images(session_dir, annotations)
    image_count += _process_current_state_images(session_dir, current_state)

    now = _now_iso()
    live_session = {
        "exportVersion": EXPORT_VERSION,
        "exportFormat": "live-session",
        "sessionId": session_id,
        "exportedAt": None,
        "lastUpdatedAt": now,
        "coin": body.get("coin"),
        "includesSnapshots": True,
        "imageDirectory": "images",
        "imageCount": image_count,
        "config": {
            "snapshotCategories": body.get("snapshotCategories"),
            "snapshotQuality": body.get("snapshotQuality"),
        },
        "annotationSeqId": body.get("annotationSeqId", 0),
        "userActionSequence": actions,
        "annotationRecords": annotations,
    }

    current_state["sessionId"] = session_id
    current_state["lastUpdatedAt"] = now

    meta.update(
        {
            "coin": body.get("coin"),
            "lastUpdatedAt": now,
        }
    )
    _atomic_write_json(session_dir / "live-session.json", live_session)
    _atomic_write_json(session_dir / "current-state.json", current_state)
    _atomic_write_json(session_dir / "session-meta.json", meta)

    return {
        "sessionId": session_id,
        "imageCount": image_count,
        "actionCount": len(actions),
        "annotationCount": len(annotations),
        "lastUpdatedAt": now,
    }
