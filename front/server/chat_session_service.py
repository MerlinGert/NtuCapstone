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

from session_git_service import SessionGitError, commit_trace_state, list_trace_versions
from session_tool_service import ensure_session_tools


router = APIRouter(prefix="/api/sessions", tags=["sessions"])

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
CHAT_ROOT = REPO_ROOT / ".maniscope-chat"
SESSIONS_DIR = CHAT_ROOT / "sessions"
SESSION_ID_RE = re.compile(r"^[0-9a-f]{5}$")
EXPORT_VERSION = "1.0"
WORKSPACE_ROLES = {"human", "agent"}
ANALYSIS_ARTIFACT_ROLES = {
    "userReasoningForest": {
        "label": "User Reasoning Forest",
        "patterns": ("user-reasoning-forest.json",),
    },
    "reasoningGraphPatch": {
        "label": "Reasoning Graph Patch",
        "patterns": (
            "reasoning-graph-patch.json",
            "reasoning-graph-patch-001.json",
            "reasoning-graph-patch-*.json",
        ),
    },
}
SERVABLE_SESSION_FILE_SUFFIXES = {".json", ".md", ".png", ".jpg", ".jpeg", ".webp"}
SERVABLE_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_session_id(session_id: str) -> None:
    if not SESSION_ID_RE.fullmatch(session_id):
        raise HTTPException(status_code=400, detail="Session ID must be 5 lowercase hex characters")


def _session_dir(session_id: str) -> Path:
    _validate_session_id(session_id)
    return SESSIONS_DIR / session_id


def _validate_workspace_role(role: str) -> None:
    if role not in WORKSPACE_ROLES:
        raise HTTPException(status_code=400, detail="Workspace role must be 'human' or 'agent'")


def _workspace_dir(session_dir: Path, role: str) -> Path:
    _validate_workspace_role(role)
    return session_dir / "workspaces" / role


def _workspace_state_path(session_dir: Path, role: str) -> Path:
    return _workspace_dir(session_dir, role) / "current-state.json"


def _ensure_workspace_dirs(session_dir: Path) -> None:
    for role in WORKSPACE_ROLES:
        _workspace_dir(session_dir, role).mkdir(parents=True, exist_ok=True)


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


def _analysis_artifact_info(session_id: str, path: Path, role: str, label: str, priority: int) -> dict[str, Any]:
    stat = path.stat()
    return {
        "role": role,
        "label": label,
        "name": path.name,
        "path": f"artifacts/{path.name}",
        "url": f"/api/sessions/{session_id}/artifacts/{path.name}",
        "size": stat.st_size,
        "modifiedAt": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"),
        "mtime": stat.st_mtime,
        "priority": priority,
    }


def _session_scoped_file_response(
    session_dir: Path,
    directory_name: str,
    relative_path: str,
    *,
    allowed_suffixes: set[str],
    invalid_detail: str,
    unsupported_detail: str,
    not_found_detail: str,
) -> FileResponse:
    if not relative_path or "\x00" in relative_path:
        raise HTTPException(status_code=400, detail=invalid_detail)

    requested_path = Path(relative_path)
    if requested_path.is_absolute():
        raise HTTPException(status_code=400, detail=invalid_detail)

    base_dir = (session_dir / directory_name).resolve()
    file_path = (base_dir / requested_path).resolve()
    try:
        file_path.relative_to(base_dir)
    except ValueError:
        raise HTTPException(status_code=400, detail=invalid_detail)

    if file_path.suffix.lower() not in allowed_suffixes:
        raise HTTPException(status_code=400, detail=unsupported_detail)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=not_found_detail)

    return FileResponse(file_path)


def _latest_artifact(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not items:
        return None
    return max(items, key=lambda item: (item["mtime"], item["name"]))


def _current_artifact(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not items:
        return None
    return sorted(items, key=lambda item: (item["priority"], -item["mtime"], item["name"]))[0]


def _analysis_artifact_manifest(session_id: str, session_dir: Path) -> dict[str, Any]:
    artifacts_dir = session_dir / "artifacts"
    current: dict[str, dict[str, Any] | None] = {}
    artifacts: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for role, spec in ANALYSIS_ARTIFACT_ROLES.items():
        role_items: list[dict[str, Any]] = []
        for priority, pattern in enumerate(spec["patterns"]):
            for path in artifacts_dir.glob(pattern):
                if not path.is_file() or path.suffix.lower() != ".json":
                    continue
                key = (role, path.name)
                if key in seen:
                    continue
                seen.add(key)
                item = _analysis_artifact_info(session_id, path, role, spec["label"], priority)
                role_items.append(item)
                artifacts.append(item)
        current[role] = _current_artifact(role_items)

    latest = _latest_artifact(artifacts)
    return {
        "sessionId": session_id,
        "artifactRoot": "artifacts",
        "current": current,
        "artifacts": sorted(artifacts, key=lambda item: (item["role"], item["name"])),
        "latestModifiedAt": latest["modifiedAt"] if latest else None,
    }


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
    _ensure_workspace_dirs(session_dir)

    meta_path = session_dir / "session-meta.json"
    meta = _read_json(meta_path)
    if meta is None:
        meta = _create_meta(session_id, coin=coin, restored=existed)
        _atomic_write_json(meta_path, meta)
        _commit_trace_history(
            session_dir=session_dir,
            event_type="session_init",
            session_id=session_id,
            action_count=0,
            annotation_count=0,
            image_count=0,
            updated_at=meta["createdAt"],
        )
    ensure_session_tools(session_dir, session_id)
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


def _process_current_state_images(
    session_dir: Path,
    current_state: dict[str, Any],
    prefix: str = "current",
) -> int:
    image_count = 0
    screenshots = current_state.get("majorViewScreenshots")
    if not isinstance(screenshots, dict):
        return image_count
    processed: dict[str, str] = {}
    for view_name, value in screenshots.items():
        if isinstance(value, str) and value.startswith("data:image/png"):
            image_path = _write_data_url_image(
                session_dir,
                f"images/{_safe_name_part(prefix)}-{_safe_name_part(view_name)}.png",
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


def _load_live_session(session_dir: Path, session_id: str, coin: str | None = None) -> dict[str, Any]:
    return _read_json(session_dir / "live-session.json") or _empty_live_session(session_id, coin=coin)


def _normalize_trace_lists(live_session: dict[str, Any]) -> tuple[list[Any], list[Any]]:
    actions = live_session.get("userActionSequence")
    annotations = live_session.get("annotationRecords")
    if not isinstance(actions, list):
        actions = []
        live_session["userActionSequence"] = actions
    if not isinstance(annotations, list):
        annotations = []
        live_session["annotationRecords"] = annotations
    return actions, annotations


def _event_context_from_body(body: dict[str, Any]) -> dict[str, Any]:
    return {
        "coin": body.get("coin"),
        "annotationSeqId": body.get("annotationSeqId"),
        "snapshotCategories": body.get("snapshotCategories"),
        "snapshotQuality": body.get("snapshotQuality"),
        "currentState": copy.deepcopy(body.get("currentState") or {}),
    }


def _apply_trace_context(
    live_session: dict[str, Any],
    current_state: dict[str, Any],
    context: dict[str, Any],
) -> None:
    if context.get("coin") is not None:
        live_session["coin"] = context["coin"]
        current_state["coin"] = context["coin"]
    if context.get("annotationSeqId") is not None:
        live_session["annotationSeqId"] = context["annotationSeqId"]

    config = live_session.setdefault("config", {})
    if context.get("snapshotCategories") is not None:
        config["snapshotCategories"] = context["snapshotCategories"]
    if context.get("snapshotQuality") is not None:
        config["snapshotQuality"] = context["snapshotQuality"]

    body_current_state = context.get("currentState")
    if isinstance(body_current_state, dict):
        current_state.update(body_current_state)


def _write_trace_state(
    session_id: str,
    session_dir: Path,
    meta: dict[str, Any],
    live_session: dict[str, Any],
    current_state: dict[str, Any] | None,
    event_type: str,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    actions, annotations = _normalize_trace_lists(live_session)
    image_count = 0
    image_count += _process_action_images(session_dir, actions)
    image_count += _process_annotation_images(session_dir, annotations)
    if current_state is not None:
        image_count += _process_current_state_images(session_dir, current_state)

    now = _now_iso()
    live_session.update(
        {
            "exportVersion": EXPORT_VERSION,
            "exportFormat": "live-session",
            "sessionId": session_id,
            "exportedAt": None,
            "lastUpdatedAt": now,
            "includesSnapshots": True,
            "imageDirectory": "images",
            "imageCount": image_count,
        }
    )
    live_session.setdefault("config", {})

    if current_state is None:
        current_state = _read_json(session_dir / "current-state.json") or {}
    current_state["sessionId"] = session_id
    current_state["lastUpdatedAt"] = now

    meta.update(
        {
            "coin": live_session.get("coin"),
            "lastUpdatedAt": now,
        }
    )
    _atomic_write_json(session_dir / "live-session.json", live_session)
    _atomic_write_json(session_dir / "current-state.json", current_state)
    _atomic_write_json(_workspace_state_path(session_dir, "human"), current_state)
    _atomic_write_json(session_dir / "session-meta.json", meta)
    git_result = _commit_trace_history(
        session_dir=session_dir,
        event_type=event_type,
        session_id=session_id,
        action_count=len(actions),
        annotation_count=len(annotations),
        image_count=image_count,
        updated_at=now,
        detail=detail,
    )

    return {
        "sessionId": session_id,
        "eventType": event_type,
        "imageCount": image_count,
        "actionCount": len(actions),
        "annotationCount": len(annotations),
        "lastUpdatedAt": now,
        "git": git_result,
    }


def _event_session_state(session_id: str, body: dict[str, Any]) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any]]:
    session_dir, meta, _ = _ensure_session(session_id, coin=body.get("coin"))
    live_session = _load_live_session(session_dir, session_id, coin=body.get("coin"))
    current_state = _read_json(session_dir / "current-state.json") or {}
    _apply_trace_context(live_session, current_state, _event_context_from_body(body))
    return session_dir, meta, live_session, current_state


def _commit_trace_history(
    session_dir: Path,
    event_type: str,
    session_id: str,
    action_count: int,
    annotation_count: int,
    image_count: int,
    updated_at: str,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        return commit_trace_state(
            session_dir=session_dir,
            event_type=event_type,
            session_id=session_id,
            action_count=action_count,
            annotation_count=annotation_count,
            image_count=image_count,
            updated_at=updated_at,
            detail=detail,
        )
    except SessionGitError as error:
        return {
            "committed": False,
            "error": str(error),
        }


def _action_detail(action: dict[str, Any], action_index: int | None = None) -> dict[str, Any]:
    detail = {
        "actionIndex": action_index,
        "actionType": action.get("actionType"),
        "sourceView": action.get("sourceView"),
        "targetView": action.get("targetView"),
    }
    return {key: value for key, value in detail.items() if value is not None}


def _annotation_detail(annotation: dict[str, Any] | None, annotation_id: int | None = None) -> dict[str, Any]:
    annotation = annotation or {}
    detail = {
        "annotationId": annotation_id if annotation_id is not None else annotation.get("id"),
        "sourceView": annotation.get("sourceView"),
    }
    return {key: value for key, value in detail.items() if value is not None}


def _workspace_payload(session_id: str, role: str) -> dict[str, Any]:
    _validate_workspace_role(role)
    session_dir, meta, existed = _ensure_session(session_id)
    live_session = _load_live_session(session_dir, session_id, coin=meta.get("coin"))
    current_state = _read_json(session_dir / "current-state.json")
    workspace_state = _read_json(_workspace_state_path(session_dir, role))
    if workspace_state is None and role == "human":
        workspace_state = current_state
    return {
        "sessionId": session_id,
        "workspaceRole": role,
        "meta": {**meta, "restoredFromExisting": existed},
        "liveSession": _hydrate_live_session_for_frontend(session_dir, live_session),
        "currentState": current_state,
        "workspaceState": workspace_state,
        "latestTraceTimestamp": (live_session or {}).get("lastUpdatedAt") or meta.get("lastUpdatedAt"),
        "latestWorkspaceTimestamp": (workspace_state or {}).get("lastUpdatedAt"),
    }


def _workspace_state_from_body(body: dict[str, Any]) -> dict[str, Any]:
    state = body.get("currentState") if isinstance(body, dict) and "currentState" in body else body
    if not isinstance(state, dict):
        raise HTTPException(status_code=400, detail="currentState must be an object")
    return copy.deepcopy(state)


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
        _ensure_workspace_dirs(session_dir)
        meta = _create_meta(session_id, coin=coin, restored=False)
        _atomic_write_json(session_dir / "session-meta.json", meta)
        git_result = _commit_trace_history(
            session_dir=session_dir,
            event_type="session_init",
            session_id=session_id,
            action_count=0,
            annotation_count=0,
            image_count=0,
            updated_at=meta["createdAt"],
        )
        ensure_session_tools(session_dir, session_id)
        return {"sessionId": session_id, "meta": meta, "git": git_result}

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


@router.get("/{session_id}/workspaces/{role}")
def get_session_workspace(session_id: str, role: str) -> dict[str, Any]:
    return _workspace_payload(session_id, role)


@router.put("/{session_id}/workspaces/{role}/state")
def put_session_workspace_state(session_id: str, role: str, body: dict[str, Any]) -> dict[str, Any]:
    _validate_workspace_role(role)
    session_dir, _, _ = _ensure_session(session_id)
    state = _workspace_state_from_body(body)
    now = _now_iso()
    _process_current_state_images(session_dir, state, prefix=f"{role}-current")
    state.update(
        {
            "sessionId": session_id,
            "workspaceRole": role,
            "lastUpdatedAt": now,
        }
    )
    _atomic_write_json(_workspace_state_path(session_dir, role), state)
    return {
        "sessionId": session_id,
        "workspaceRole": role,
        "lastUpdatedAt": now,
    }


@router.get("/{session_id}/artifacts/{artifact_path:path}")
def get_session_artifact(session_id: str, artifact_path: str) -> FileResponse:
    session_dir = _session_dir(session_id)
    return _session_scoped_file_response(
        session_dir,
        "artifacts",
        artifact_path,
        allowed_suffixes=SERVABLE_SESSION_FILE_SUFFIXES,
        invalid_detail="Invalid artifact path",
        unsupported_detail="Unsupported artifact type",
        not_found_detail="Artifact not found",
    )


@router.get("/{session_id}/images/{image_path:path}")
def get_session_image(session_id: str, image_path: str) -> FileResponse:
    session_dir = _session_dir(session_id)
    return _session_scoped_file_response(
        session_dir,
        "images",
        image_path,
        allowed_suffixes=SERVABLE_IMAGE_SUFFIXES,
        invalid_detail="Invalid image path",
        unsupported_detail="Unsupported image type",
        not_found_detail="Image not found",
    )


@router.get("/{session_id}/analysis-artifacts")
def get_analysis_artifact_manifest(session_id: str) -> dict[str, Any]:
    session_dir, _meta, _existed = _ensure_session(session_id)
    return _analysis_artifact_manifest(session_id, session_dir)


@router.get("/{session_id}/versions")
def get_session_versions(session_id: str, limit: int = 50) -> dict[str, Any]:
    session_dir = _session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        versions = list_trace_versions(session_dir, limit=limit)
    except SessionGitError as error:
        raise HTTPException(status_code=500, detail=str(error))
    return {
        "sessionId": session_id,
        "versions": versions,
    }


@router.post("/{session_id}/events/user-actions")
def append_user_action_event(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    action = copy.deepcopy(body.get("action"))
    if not isinstance(action, dict):
        raise HTTPException(status_code=400, detail="action must be an object")

    session_dir, meta, live_session, current_state = _event_session_state(session_id, body)
    actions, _ = _normalize_trace_lists(live_session)
    actions.append(action)
    return _write_trace_state(
        session_id,
        session_dir,
        meta,
        live_session,
        current_state,
        "user_action_append",
        _action_detail(action, len(actions) - 1),
    )


@router.put("/{session_id}/events/user-actions/{action_index}")
def upsert_user_action_event(session_id: str, action_index: int, body: dict[str, Any]) -> dict[str, Any]:
    if action_index < 0:
        raise HTTPException(status_code=400, detail="action_index must be non-negative")
    action = copy.deepcopy(body.get("action"))
    if not isinstance(action, dict):
        raise HTTPException(status_code=400, detail="action must be an object")

    session_dir, meta, live_session, current_state = _event_session_state(session_id, body)
    actions, _ = _normalize_trace_lists(live_session)
    if action_index < len(actions):
        actions[action_index] = action
    elif action_index == len(actions):
        actions.append(action)
    else:
        raise HTTPException(status_code=409, detail="action_index is beyond the current action sequence")
    return _write_trace_state(
        session_id,
        session_dir,
        meta,
        live_session,
        current_state,
        "user_action_upsert",
        _action_detail(action, action_index),
    )


@router.delete("/{session_id}/events/user-actions/{action_index}")
def delete_user_action_event(session_id: str, action_index: int, body: dict[str, Any] | None = None) -> dict[str, Any]:
    if action_index < 0:
        raise HTTPException(status_code=400, detail="action_index must be non-negative")

    body = body or {}
    session_dir, meta, live_session, current_state = _event_session_state(session_id, body)
    actions, _ = _normalize_trace_lists(live_session)
    if action_index >= len(actions):
        raise HTTPException(status_code=404, detail="action not found")
    action = actions.pop(action_index)
    return _write_trace_state(
        session_id,
        session_dir,
        meta,
        live_session,
        current_state,
        "user_action_delete",
        _action_detail(action if isinstance(action, dict) else {}, action_index),
    )


@router.post("/{session_id}/events/annotations")
def append_annotation_event(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    annotation = copy.deepcopy(body.get("annotation"))
    if not isinstance(annotation, dict):
        raise HTTPException(status_code=400, detail="annotation must be an object")

    session_dir, meta, live_session, current_state = _event_session_state(session_id, body)
    _, annotations = _normalize_trace_lists(live_session)
    annotations.append(annotation)
    return _write_trace_state(
        session_id,
        session_dir,
        meta,
        live_session,
        current_state,
        "annotation_append",
        _annotation_detail(annotation),
    )


@router.put("/{session_id}/events/annotations/{annotation_id}")
def upsert_annotation_event(session_id: str, annotation_id: int, body: dict[str, Any]) -> dict[str, Any]:
    annotation = copy.deepcopy(body.get("annotation"))
    if not isinstance(annotation, dict):
        raise HTTPException(status_code=400, detail="annotation must be an object")

    session_dir, meta, live_session, current_state = _event_session_state(session_id, body)
    _, annotations = _normalize_trace_lists(live_session)
    existing_index = next(
        (index for index, item in enumerate(annotations) if isinstance(item, dict) and item.get("id") == annotation_id),
        None,
    )
    if existing_index is None:
        annotations.append(annotation)
    else:
        annotations[existing_index] = annotation
    return _write_trace_state(
        session_id,
        session_dir,
        meta,
        live_session,
        current_state,
        "annotation_upsert",
        _annotation_detail(annotation, annotation_id),
    )


@router.delete("/{session_id}/events/annotations/{annotation_id}")
def delete_annotation_event(session_id: str, annotation_id: int, body: dict[str, Any] | None = None) -> dict[str, Any]:
    body = body or {}
    session_dir, meta, live_session, current_state = _event_session_state(session_id, body)
    _, annotations = _normalize_trace_lists(live_session)
    existing_index = next(
        (index for index, item in enumerate(annotations) if isinstance(item, dict) and item.get("id") == annotation_id),
        None,
    )
    if existing_index is None:
        raise HTTPException(status_code=404, detail="annotation not found")
    annotation = annotations.pop(existing_index)
    return _write_trace_state(
        session_id,
        session_dir,
        meta,
        live_session,
        current_state,
        "annotation_delete",
        _annotation_detail(annotation if isinstance(annotation, dict) else {}, annotation_id),
    )


@router.post("/{session_id}/events/reorder")
def reorder_trace_event(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    actions = copy.deepcopy(body.get("userActionSequence"))
    annotations = copy.deepcopy(body.get("annotationRecords"))
    if not isinstance(actions, list):
        raise HTTPException(status_code=400, detail="userActionSequence must be an array")
    if not isinstance(annotations, list):
        raise HTTPException(status_code=400, detail="annotationRecords must be an array")

    session_dir, meta, live_session, current_state = _event_session_state(session_id, body)
    live_session["userActionSequence"] = actions
    live_session["annotationRecords"] = annotations
    return _write_trace_state(
        session_id,
        session_dir,
        meta,
        live_session,
        current_state,
        "trace_reorder",
    )


@router.post("/{session_id}/events/settings")
def update_session_settings_event(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    session_dir, meta, live_session, current_state = _event_session_state(session_id, body)
    return _write_trace_state(
        session_id,
        session_dir,
        meta,
        live_session,
        current_state,
        "settings_update",
        {"coin": body.get("coin")},
    )


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

    live_session = {
        "exportVersion": EXPORT_VERSION,
        "exportFormat": "live-session",
        "sessionId": session_id,
        "exportedAt": None,
        "lastUpdatedAt": None,
        "coin": body.get("coin"),
        "includesSnapshots": True,
        "imageDirectory": "images",
        "imageCount": 0,
        "config": {
            "snapshotCategories": body.get("snapshotCategories"),
            "snapshotQuality": body.get("snapshotQuality"),
        },
        "annotationSeqId": body.get("annotationSeqId", 0),
        "userActionSequence": actions,
        "annotationRecords": annotations,
    }
    return _write_trace_state(
        session_id,
        session_dir,
        meta,
        live_session,
        current_state,
        "full_sync",
        {"coin": body.get("coin")},
    )
