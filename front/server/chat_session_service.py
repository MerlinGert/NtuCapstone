import base64
import copy
import hashlib
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
from session_tool_service import ensure_baseline_session_tools, ensure_session_tools


router = APIRouter(prefix="/api/sessions", tags=["sessions"])
baseline_router = APIRouter(prefix="/api/base/sessions", tags=["base-sessions"])

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
CHAT_ROOT = REPO_ROOT / ".maniscope-chat"
SESSIONS_DIR = CHAT_ROOT / "sessions"
BASELINE_SESSIONS_DIR = CHAT_ROOT / "baseline-sessions"
SESSION_ID_RE = re.compile(r"^[0-9a-f]{5}$")
SESSION_MODES = {"specialized", "baseline"}
EXPORT_VERSION = "1.0"
WORKSPACE_ROLES = {"human", "agent"}
BASELINE_WORKSPACE_ROLES = {"human"}
ANALYSIS_EXPORT_SUFFIXES = {".json", ".md"}
REASONING_GRAPH_NAME = "reasoning-graph.json"
REASONING_GRAPH_PATCH_RE = re.compile(r"^reasoning-graph-patch(?:-.+)?\.json$")
LLM_ANALYSIS_EVALUATIONS_NAME = "llm-analysis-evaluations.json"
LLM_ANALYSIS_UI_STATE_NAME = "llm-analysis-ui-state.json"
ANALYSIS_RUNS_DIR_NAME = "analysis-runs"
SERVABLE_SESSION_FILE_SUFFIXES = {".json", ".md", ".png", ".jpg", ".jpeg", ".webp"}
SERVABLE_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
EVALUABLE_REASONING_NODE_KINDS = {"Hypothesis", "Finding"}
EVALUATION_ENTRY_KEYS = {
    "checked",
    "nodeKind",
    "updatedAt",
    "hypothesisAligned",
    "findingsSufficiency",
    "associatedHypothesisId",
    "associatedHypothesisLabel",
    "relevanceToHypothesis",
    "note",
}
ANALYSIS_UI_STATE_ENTRY_KEYS = {"nodeKind", "firstSeenAt", "runId"}
ANALYSIS_UI_STATE_RUN_KEYS = {"runId", "startedAt", "suppressNewBadges", "baselineVisibleNodeIds"}
ANALYSIS_RUN_MODES = {"full_analysis", "incremental_analysis", "manual_chat"}
ANALYSIS_RUN_STATUSES = {"running", "completed", "stopped", "failed", "interrupted"}
ANALYSIS_RUN_ID_RE = re.compile(r"^[a-zA-Z0-9_.-]{1,120}$")
ANALYSIS_EXPORT_FORMAT = "maniscope-llm-analysis-json"


HYPOTHESIS_ALIGNMENT_VALUES = {"yes", "no", "unsure"}
HYPOTHESIS_SUFFICIENCY_VALUES = {"yes", "no", "partially", "unsure"}
FINDING_RELEVANCE_VALUES = {"yes", "no", "unsure"}


def _normalize_optional_choice(
    value: Any,
    allowed_values: set[str],
    field_name: str,
    node_id: str,
) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    if text not in allowed_values:
        raise HTTPException(status_code=400, detail=f"Evaluation entry for {node_id} has invalid {field_name}")
    return text


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_session_id(session_id: str) -> None:
    if not SESSION_ID_RE.fullmatch(session_id):
        raise HTTPException(status_code=400, detail="Session ID must be 5 lowercase hex characters")


def _validate_session_mode(session_mode: str) -> str:
    if session_mode not in SESSION_MODES:
        raise HTTPException(status_code=400, detail="Session mode must be 'specialized' or 'baseline'")
    return session_mode


def _sessions_dir(session_mode: str = "specialized") -> Path:
    _validate_session_mode(session_mode)
    return BASELINE_SESSIONS_DIR if session_mode == "baseline" else SESSIONS_DIR


def _api_session_prefix(session_mode: str = "specialized") -> str:
    return "/api/base/sessions" if session_mode == "baseline" else "/api/sessions"


def _session_dir(session_id: str, session_mode: str = "specialized") -> Path:
    _validate_session_id(session_id)
    return _sessions_dir(session_mode) / session_id


def _workspace_roles(session_mode: str = "specialized") -> set[str]:
    return BASELINE_WORKSPACE_ROLES if session_mode == "baseline" else WORKSPACE_ROLES


def _validate_workspace_role(role: str, session_mode: str = "specialized") -> None:
    if role not in _workspace_roles(session_mode):
        if session_mode == "baseline":
            raise HTTPException(status_code=400, detail="Baseline sessions only support the human workspace")
        raise HTTPException(status_code=400, detail="Workspace role must be 'human' or 'agent'")


def _workspace_dir(session_dir: Path, role: str, session_mode: str = "specialized") -> Path:
    _validate_workspace_role(role, session_mode=session_mode)
    return session_dir / "workspaces" / role


def _workspace_state_path(session_dir: Path, role: str, session_mode: str = "specialized") -> Path:
    return _workspace_dir(session_dir, role, session_mode=session_mode) / "current-state.json"


def _ensure_workspace_dirs(session_dir: Path, session_mode: str = "specialized") -> None:
    for role in _workspace_roles(session_mode):
        _workspace_dir(session_dir, role, session_mode=session_mode).mkdir(parents=True, exist_ok=True)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    try:
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in {path.name}")


def _stable_trace_digest(live_session: dict[str, Any]) -> str:
    trace_payload = {
        "coin": live_session.get("coin"),
        "config": live_session.get("config") or {},
        "annotationSeqId": live_session.get("annotationSeqId"),
        "userActionSequence": live_session.get("userActionSequence") or [],
        "annotationRecords": live_session.get("annotationRecords") or [],
    }
    encoded = json.dumps(trace_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _last_action_id(actions: list[Any]) -> str | None:
    if not actions:
        return None
    action = actions[-1]
    if isinstance(action, dict):
        for key in ("id", "actionId", "seqId"):
            value = action.get(key)
            if value is not None:
                return str(value)
    return str(len(actions) - 1)


def _last_annotation_id(annotations: list[Any]) -> str | None:
    if not annotations:
        return None
    annotation = annotations[-1]
    if isinstance(annotation, dict) and annotation.get("id") is not None:
        return str(annotation["id"])
    return str(len(annotations) - 1)


def _trace_anchor(session_id: str, live_session: dict[str, Any]) -> dict[str, Any]:
    actions, annotations = _normalize_trace_lists(live_session)
    anchor: dict[str, Any] = {
        "sessionId": session_id,
        "traceRevision": int(live_session.get("traceRevision") or 0),
        "actionCount": len(actions),
        "annotationCount": len(annotations),
        "traceDigest": _stable_trace_digest(live_session),
    }
    last_action_id = _last_action_id(actions)
    last_annotation_id = _last_annotation_id(annotations)
    if last_action_id is not None:
        anchor["lastActionId"] = last_action_id
    if last_annotation_id is not None:
        anchor["lastAnnotationId"] = last_annotation_id
    return anchor


def _current_trace_anchor(session_id: str, session_dir: Path) -> dict[str, Any]:
    live_session = _read_json(session_dir / "live-session.json")
    if not isinstance(live_session, dict):
        live_session = _empty_live_session(session_id)
    anchor = live_session.get("traceAnchor")
    if isinstance(anchor, dict):
        return copy.deepcopy(anchor)
    return _trace_anchor(session_id, live_session)


def _analysis_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"run-{stamp}-{secrets.token_hex(4)}"


def _normalize_analysis_run_id(value: Any, *, required: bool = True) -> str:
    run_id = str(value or "").strip()
    if not run_id:
        if required:
            raise HTTPException(status_code=400, detail="runId is required")
        return ""
    if not ANALYSIS_RUN_ID_RE.fullmatch(run_id) or "/" in run_id or "\\" in run_id:
        raise HTTPException(status_code=400, detail="runId contains unsupported characters")
    return run_id


def _analysis_runs_dir(session_dir: Path) -> Path:
    path = session_dir / ANALYSIS_RUNS_DIR_NAME
    path.mkdir(exist_ok=True)
    return path


def _analysis_run_path(session_dir: Path, run_id: str) -> Path:
    safe_run_id = _normalize_analysis_run_id(run_id)
    return _analysis_runs_dir(session_dir) / f"{safe_run_id}.json"


def _analysis_run_mode_from_body(body: dict[str, Any]) -> str:
    mode = str(body.get("mode") or "").strip()
    if mode:
        if mode not in ANALYSIS_RUN_MODES:
            raise HTTPException(status_code=400, detail="analysis run mode is unsupported")
        return mode
    preset_kind = str(body.get("presetKind") or "").strip()
    if preset_kind == "full_analysis":
        return "full_analysis"
    if preset_kind == "update_analysis":
        return "incremental_analysis"
    return "manual_chat"


def _trace_advanced(start_anchor: dict[str, Any] | None, end_anchor: dict[str, Any] | None) -> bool:
    if not isinstance(start_anchor, dict) or not isinstance(end_anchor, dict):
        return False
    for key in ("traceRevision", "actionCount", "annotationCount"):
        try:
            if int(end_anchor.get(key) or 0) > int(start_anchor.get(key) or 0):
                return True
        except (TypeError, ValueError):
            continue
    return False


def _start_analysis_run(
    session_id: str,
    body: dict[str, Any],
    session_mode: str = "specialized",
) -> dict[str, Any]:
    if session_mode != "specialized":
        raise HTTPException(status_code=400, detail="Analysis runs are only supported for specialized sessions")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Analysis run payload must be a JSON object")
    session_dir, _meta, _existed = _ensure_session(session_id, session_mode=session_mode)
    requested_run_id = _normalize_analysis_run_id(body.get("runId"), required=False)
    run_id = requested_run_id or _analysis_run_id()
    run_path = _analysis_run_path(session_dir, run_id)
    if run_path.exists():
        raise HTTPException(status_code=409, detail="Analysis run already exists")
    now = _now_iso()
    payload = {
        "version": 1,
        "sessionId": session_id,
        "sessionMode": session_mode,
        "runId": run_id,
        "mode": _analysis_run_mode_from_body(body),
        "presetKind": str(body.get("presetKind") or ""),
        "status": "running",
        "startedAt": now,
        "completedAt": None,
        "startAnchor": _current_trace_anchor(session_id, session_dir),
        "endAnchor": None,
        "traceAdvanced": False,
    }
    _atomic_write_json(run_path, payload)
    return payload


def _finish_analysis_run(
    session_id: str,
    run_id: str,
    status: str,
    session_mode: str = "specialized",
) -> dict[str, Any] | None:
    if session_mode != "specialized":
        return None
    if status not in ANALYSIS_RUN_STATUSES:
        raise HTTPException(status_code=400, detail="Analysis run status is unsupported")
    session_dir, _meta, _existed = _ensure_session(session_id, session_mode=session_mode)
    run_path = _analysis_run_path(session_dir, run_id)
    if not run_path.exists():
        return None
    payload = _read_json(run_path)
    if not isinstance(payload, dict):
        return None
    if payload.get("status") in {"completed", "stopped", "failed", "interrupted"}:
        return payload
    end_anchor = _current_trace_anchor(session_id, session_dir)
    payload["status"] = status
    payload["completedAt"] = _now_iso()
    payload["endAnchor"] = end_anchor
    payload["traceAdvanced"] = _trace_advanced(payload.get("startAnchor"), end_anchor)
    _atomic_write_json(run_path, payload)
    return payload


def _analysis_artifact_info(
    session_id: str,
    path: Path,
    role: str,
    label: str,
    priority: int,
    session_mode: str = "specialized",
) -> dict[str, Any]:
    stat = path.stat()
    return {
        "role": role,
        "label": label,
        "name": path.name,
        "path": f"artifacts/{path.name}",
        "url": f"{_api_session_prefix(session_mode)}/{session_id}/artifacts/{path.name}",
        "size": stat.st_size,
        "modifiedAt": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"),
        "mtime": stat.st_mtime,
        "priority": priority,
    }


def _patch_sort_key(name: str) -> tuple[int, int, int, str]:
    if name == "reasoning-graph-patch.json":
        return (0, 0, 0, name)
    numbered = re.fullmatch(r"reasoning-graph-patch-(\d+)\.json", name)
    if numbered:
        return (1, int(numbered.group(1)), 0, name)
    if name == "reasoning-graph-patch-skeptical.json":
        return (2, 0, 0, name)
    incremental = re.fullmatch(r"reasoning-graph-patch-incremental-(\d+)-(\d+)\.json", name)
    if incremental:
        return (3, int(incremental.group(1)), int(incremental.group(2)), name)
    if REASONING_GRAPH_PATCH_RE.fullmatch(name):
        return (4, 0, 0, name)
    return (5, 0, 0, name)


def _json_run_id(path: Path) -> str | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    run_id = data.get("runId")
    return run_id if isinstance(run_id, str) and run_id.strip() else None


def _dedupe_patch_artifacts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_run_ids: set[str] = set()
    for item in sorted(items, key=lambda artifact: _patch_sort_key(artifact["name"])):
        run_id = item.get("runId")
        if isinstance(run_id, str) and run_id:
            if run_id in seen_run_ids:
                continue
            seen_run_ids.add(run_id)
        deduped.append(item)
    return deduped


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


def _analysis_artifact_manifest(session_id: str, session_dir: Path, session_mode: str = "specialized") -> dict[str, Any]:
    artifacts_dir = session_dir / "artifacts"
    artifacts: list[dict[str, Any]] = []
    exports: list[dict[str, Any]] = []

    reasoning_graph = None
    graph_path = artifacts_dir / REASONING_GRAPH_NAME
    if graph_path.is_file():
        reasoning_graph = _analysis_artifact_info(
            session_id,
            graph_path,
            "reasoningGraph",
            "Reasoning Graph",
            0,
            session_mode,
        )
        artifacts.append(reasoning_graph)

    patch_items: list[dict[str, Any]] = []
    for path in artifacts_dir.glob("reasoning-graph-patch*.json"):
        if not path.is_file() or not REASONING_GRAPH_PATCH_RE.fullmatch(path.name):
            continue
        item = _analysis_artifact_info(
            session_id,
            path,
            "reasoningGraphPatch",
            "Reasoning Graph Patch",
            _patch_sort_key(path.name)[0],
            session_mode,
        )
        run_id = _json_run_id(path)
        if run_id:
            item["runId"] = run_id
        patch_items.append(item)
    patches = _dedupe_patch_artifacts(patch_items)
    artifacts.extend(patches)

    source_names = {REASONING_GRAPH_NAME, *(item["name"] for item in patches)}
    for path in sorted(artifacts_dir.iterdir() if artifacts_dir.exists() else []):
        if not path.is_file() or path.suffix.lower() not in ANALYSIS_EXPORT_SUFFIXES:
            continue
        if path.name in source_names or REASONING_GRAPH_PATCH_RE.fullmatch(path.name):
            continue
        item = _analysis_artifact_info(session_id, path, "analysisExport", "Analysis Export", 0, session_mode)
        exports.append(item)
        artifacts.append(item)

    legacy_user_forest = next((item for item in exports if item["name"] == "user-reasoning-forest.json"), None)
    legacy_patch = patches[0] if patches else None
    latest = _latest_artifact(artifacts)
    return {
        "sessionId": session_id,
        "sessionMode": session_mode,
        "artifactRoot": "artifacts",
        "current": {
            "reasoningGraph": reasoning_graph,
            "patches": patches,
            "userReasoningForest": legacy_user_forest,
            "reasoningGraphPatch": legacy_patch,
        },
        "reasoningGraph": reasoning_graph,
        "patches": patches,
        "exports": exports,
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
        "traceRevision": 0,
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
        "studyInfo": {},
        "analysisMilestones": [],
        "chatbotLogs": [],
        "llmAnalysisTrace": [],
    }


def _create_meta(
    session_id: str,
    coin: str | None = None,
    restored: bool = False,
    session_mode: str = "specialized",
) -> dict[str, Any]:
    now = _now_iso()
    return {
        "sessionId": session_id,
        "sessionMode": session_mode,
        "coin": coin,
        "createdAt": now,
        "lastUpdatedAt": now,
        "restoredFromExisting": restored,
    }


def _effective_session_mode(meta: dict[str, Any] | None) -> str:
    if not meta:
        return "specialized"
    value = meta.get("sessionMode")
    return value if value in SESSION_MODES else "specialized"


def _ensure_session(
    session_id: str,
    coin: str | None = None,
    session_mode: str = "specialized",
) -> tuple[Path, dict[str, Any], bool]:
    session_mode = _validate_session_mode(session_mode)
    session_dir = _session_dir(session_id, session_mode=session_mode)
    existed = session_dir.exists()
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "images").mkdir(exist_ok=True)
    (session_dir / "artifacts").mkdir(exist_ok=True)
    _ensure_workspace_dirs(session_dir, session_mode=session_mode)

    meta_path = session_dir / "session-meta.json"
    meta = _read_json(meta_path)
    if meta is None:
        meta = _create_meta(session_id, coin=coin, restored=existed, session_mode=session_mode)
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
    elif _effective_session_mode(meta) != session_mode:
        raise HTTPException(status_code=409, detail="Session mode does not match requested API scope")

    meta.setdefault("sessionMode", session_mode)
    if session_mode == "baseline":
        ensure_baseline_session_tools(session_dir, session_id)
    else:
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


def _process_chatbot_log_images(session_dir: Path, chatbot_logs: list[Any]) -> int:
    image_count = 0
    for log_index, log in enumerate(chatbot_logs):
        if not isinstance(log, dict):
            continue
        attachments = log.get("promptAttachments")
        if not isinstance(attachments, list):
            continue
        for attachment_index, attachment in enumerate(attachments):
            if not isinstance(attachment, dict):
                continue
            data_url = attachment.pop("dataUrl", None)
            if data_url:
                file_name = "-".join(
                    [
                        "chat",
                        str(log_index + 1).zfill(4),
                        "prompt",
                        str(attachment_index + 1).zfill(2),
                        _safe_name_part(attachment.get("name") or "image"),
                    ]
                )
                image_path = _write_data_url_image(session_dir, f"images/{file_name}.png", data_url)
                if image_path:
                    attachment["imagePath"] = image_path
            if attachment.get("imagePath"):
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
    for log in hydrated.get("chatbotLogs", []):
        if not isinstance(log, dict):
            continue
        attachments = log.get("promptAttachments")
        if not isinstance(attachments, list):
            continue
        for attachment in attachments:
            if not isinstance(attachment, dict):
                continue
            data_url = _data_url_for_image(session_dir, attachment.get("imagePath"))
            if data_url:
                attachment["dataUrl"] = data_url
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
        "studyInfo": copy.deepcopy(body.get("studyInfo") or {}),
        "analysisMilestones": copy.deepcopy(body.get("analysisMilestones") or []),
        "chatbotLogs": copy.deepcopy(body.get("chatbotLogs") or []),
        "llmAnalysisTrace": copy.deepcopy(body.get("llmAnalysisTrace") or []),
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
    if isinstance(context.get("studyInfo"), dict):
        live_session["studyInfo"] = context["studyInfo"]
    if isinstance(context.get("analysisMilestones"), list):
        live_session["analysisMilestones"] = context["analysisMilestones"]
    if isinstance(context.get("chatbotLogs"), list):
        live_session["chatbotLogs"] = context["chatbotLogs"]
    if isinstance(context.get("llmAnalysisTrace"), list):
        live_session["llmAnalysisTrace"] = context["llmAnalysisTrace"]


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
    chatbot_logs = live_session.get("chatbotLogs")
    if isinstance(chatbot_logs, list):
        image_count += _process_chatbot_log_images(session_dir, chatbot_logs)
    if current_state is not None:
        image_count += _process_current_state_images(session_dir, current_state)

    now = _now_iso()
    trace_revision = int(live_session.get("traceRevision") or 0) + 1
    live_session.update(
        {
            "exportVersion": EXPORT_VERSION,
            "exportFormat": "live-session",
            "sessionId": session_id,
            "exportedAt": None,
            "lastUpdatedAt": now,
            "traceRevision": trace_revision,
            "includesSnapshots": True,
            "imageDirectory": "images",
            "imageCount": image_count,
        }
    )
    live_session.setdefault("config", {})
    live_session["traceAnchor"] = _trace_anchor(session_id, live_session)

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
        "traceAnchor": live_session["traceAnchor"],
        "git": git_result,
    }


def _event_session_state(
    session_id: str,
    body: dict[str, Any],
    session_mode: str = "specialized",
) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any]]:
    session_dir, meta, _ = _ensure_session(session_id, coin=body.get("coin"), session_mode=session_mode)
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


def _workspace_payload(session_id: str, role: str, session_mode: str = "specialized") -> dict[str, Any]:
    _validate_workspace_role(role, session_mode=session_mode)
    session_dir, meta, existed = _ensure_session(session_id, session_mode=session_mode)
    live_session = _load_live_session(session_dir, session_id, coin=meta.get("coin"))
    current_state = _read_json(session_dir / "current-state.json")
    workspace_state = _read_json(_workspace_state_path(session_dir, role, session_mode=session_mode))
    if workspace_state is None and role == "human":
        workspace_state = current_state
    return {
        "sessionId": session_id,
        "sessionMode": session_mode,
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


def _create_session(body: dict[str, Any] | None = None, session_mode: str = "specialized") -> dict[str, Any]:
    coin = (body or {}).get("coin")
    sessions_dir = _sessions_dir(session_mode)
    sessions_dir.mkdir(parents=True, exist_ok=True)

    for _ in range(20):
        session_id = secrets.token_hex(3)[:5]
        session_dir = sessions_dir / session_id
        try:
            session_dir.mkdir(parents=True)
        except FileExistsError:
            continue
        (session_dir / "images").mkdir()
        (session_dir / "artifacts").mkdir()
        _ensure_workspace_dirs(session_dir, session_mode=session_mode)
        meta = _create_meta(session_id, coin=coin, restored=False, session_mode=session_mode)
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
        if session_mode == "baseline":
            ensure_baseline_session_tools(session_dir, session_id)
        else:
            ensure_session_tools(session_dir, session_id)
        return {"sessionId": session_id, "sessionMode": session_mode, "meta": meta, "git": git_result}

    raise HTTPException(status_code=503, detail="Unable to allocate a unique session ID")


def _get_session(session_id: str, session_mode: str = "specialized") -> dict[str, Any]:
    session_dir, meta, existed = _ensure_session(session_id, session_mode=session_mode)
    live_session = _read_json(session_dir / "live-session.json")
    current_state = _read_json(session_dir / "current-state.json")
    return {
        "sessionId": session_id,
        "sessionMode": session_mode,
        "meta": {**meta, "restoredFromExisting": existed},
        "liveSession": _hydrate_live_session_for_frontend(session_dir, live_session) if live_session else None,
        "currentState": current_state,
    }


def _get_session_workspace(session_id: str, role: str, session_mode: str = "specialized") -> dict[str, Any]:
    return _workspace_payload(session_id, role, session_mode=session_mode)


def _put_session_workspace_state(
    session_id: str,
    role: str,
    body: dict[str, Any],
    session_mode: str = "specialized",
) -> dict[str, Any]:
    _validate_workspace_role(role, session_mode=session_mode)
    session_dir, _, _ = _ensure_session(session_id, session_mode=session_mode)
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
    _atomic_write_json(_workspace_state_path(session_dir, role, session_mode=session_mode), state)
    return {
        "sessionId": session_id,
        "sessionMode": session_mode,
        "workspaceRole": role,
        "lastUpdatedAt": now,
    }


def _get_session_artifact(session_id: str, artifact_path: str, session_mode: str = "specialized") -> FileResponse:
    session_dir = _session_dir(session_id, session_mode=session_mode)
    return _session_scoped_file_response(
        session_dir,
        "artifacts",
        artifact_path,
        allowed_suffixes=SERVABLE_SESSION_FILE_SUFFIXES,
        invalid_detail="Invalid artifact path",
        unsupported_detail="Unsupported artifact type",
        not_found_detail="Artifact not found",
    )


def _get_session_image(session_id: str, image_path: str, session_mode: str = "specialized") -> FileResponse:
    session_dir = _session_dir(session_id, session_mode=session_mode)
    return _session_scoped_file_response(
        session_dir,
        "images",
        image_path,
        allowed_suffixes=SERVABLE_IMAGE_SUFFIXES,
        invalid_detail="Invalid image path",
        unsupported_detail="Unsupported image type",
        not_found_detail="Image not found",
    )


def _get_analysis_artifact_manifest(session_id: str, session_mode: str = "specialized") -> dict[str, Any]:
    session_dir, _meta, _existed = _ensure_session(session_id, session_mode=session_mode)
    return _analysis_artifact_manifest(session_id, session_dir, session_mode=session_mode)


def _analysis_evaluations_path(session_dir: Path) -> Path:
    return session_dir / LLM_ANALYSIS_EVALUATIONS_NAME


def _analysis_ui_state_path(session_dir: Path) -> Path:
    return session_dir / LLM_ANALYSIS_UI_STATE_NAME


def _empty_analysis_evaluations(session_id: str, session_mode: str = "specialized") -> dict[str, Any]:
    return {
        "sessionId": session_id,
        "sessionMode": session_mode,
        "updatedAt": None,
        "evaluations": {},
    }


def _normalize_analysis_evaluations_payload(
    session_id: str,
    body: dict[str, Any],
    session_mode: str = "specialized",
) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Evaluation payload must be a JSON object")
    raw_evaluations = body.get("evaluations")
    if raw_evaluations is None:
        raw_evaluations = {}
    if not isinstance(raw_evaluations, dict):
        raise HTTPException(status_code=400, detail="evaluations must be an object keyed by canonical node ID")

    evaluations: dict[str, Any] = {}
    for raw_key, raw_entry in raw_evaluations.items():
        node_id = str(raw_key).strip()
        if not node_id:
            raise HTTPException(status_code=400, detail="Evaluation node IDs must be non-empty strings")
        if not isinstance(raw_entry, dict):
            raise HTTPException(status_code=400, detail=f"Evaluation entry for {node_id} must be an object")
        unsupported = sorted(set(raw_entry) - EVALUATION_ENTRY_KEYS)
        if unsupported:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported evaluation fields for {node_id}: {', '.join(unsupported)}",
            )
        node_kind = raw_entry.get("nodeKind")
        if node_kind is not None and node_kind not in EVALUABLE_REASONING_NODE_KINDS:
            raise HTTPException(status_code=400, detail=f"Evaluation entry for {node_id} has unsupported nodeKind")
        updated_at = raw_entry.get("updatedAt")
        if updated_at is not None and not isinstance(updated_at, str):
            raise HTTPException(status_code=400, detail=f"Evaluation entry for {node_id} has invalid updatedAt")
        checked = raw_entry.get("checked")
        if checked is not None and not isinstance(checked, bool):
            raise HTTPException(status_code=400, detail=f"Evaluation entry for {node_id} has invalid checked")
        normalized_entry: dict[str, Any] = {
            "checked": checked is True,
            "nodeKind": node_kind or "Finding",
            "updatedAt": updated_at,
        }

        hypothesis_aligned = _normalize_optional_choice(
            raw_entry.get("hypothesisAligned"),
            HYPOTHESIS_ALIGNMENT_VALUES,
            "hypothesisAligned",
            node_id,
        )
        if hypothesis_aligned:
            normalized_entry["hypothesisAligned"] = hypothesis_aligned

        findings_sufficiency = _normalize_optional_choice(
            raw_entry.get("findingsSufficiency"),
            HYPOTHESIS_SUFFICIENCY_VALUES,
            "findingsSufficiency",
            node_id,
        )
        if findings_sufficiency:
            normalized_entry["findingsSufficiency"] = findings_sufficiency

        relevance_to_hypothesis = _normalize_optional_choice(
            raw_entry.get("relevanceToHypothesis"),
            FINDING_RELEVANCE_VALUES,
            "relevanceToHypothesis",
            node_id,
        )
        if relevance_to_hypothesis:
            normalized_entry["relevanceToHypothesis"] = relevance_to_hypothesis

        if "associatedHypothesisId" in raw_entry:
            associated_hypothesis_id = raw_entry.get("associatedHypothesisId")
            if associated_hypothesis_id is not None:
                associated_hypothesis_id = str(associated_hypothesis_id).strip() or None
            normalized_entry["associatedHypothesisId"] = associated_hypothesis_id

        associated_hypothesis_label = _normalize_optional_text(raw_entry.get("associatedHypothesisLabel"))
        if associated_hypothesis_label:
            normalized_entry["associatedHypothesisLabel"] = associated_hypothesis_label

        note = _normalize_optional_text(raw_entry.get("note"))
        if note:
            normalized_entry["note"] = note

        evaluations[node_id] = normalized_entry

    return {
        "sessionId": session_id,
        "sessionMode": session_mode,
        "updatedAt": body.get("updatedAt") if isinstance(body.get("updatedAt"), str) else None,
        "evaluations": evaluations,
    }


def _get_analysis_evaluations(session_id: str, session_mode: str = "specialized") -> dict[str, Any]:
    session_dir, _meta, _existed = _ensure_session(session_id, session_mode=session_mode)
    payload = _read_json(_analysis_evaluations_path(session_dir))
    if payload is None:
        return _empty_analysis_evaluations(session_id, session_mode=session_mode)
    return _normalize_analysis_evaluations_payload(session_id, payload, session_mode=session_mode)


def _put_analysis_evaluations(
    session_id: str,
    body: dict[str, Any],
    session_mode: str = "specialized",
) -> dict[str, Any]:
    session_dir, _meta, _existed = _ensure_session(session_id, session_mode=session_mode)
    payload = _normalize_analysis_evaluations_payload(session_id, body, session_mode=session_mode)
    payload["updatedAt"] = _now_iso()
    _atomic_write_json(_analysis_evaluations_path(session_dir), payload)
    return payload


def _empty_analysis_ui_state(session_id: str, session_mode: str = "specialized") -> dict[str, Any]:
    return {
        "sessionId": session_id,
        "sessionMode": session_mode,
        "updatedAt": None,
        "activeRun": None,
        "newNodeIds": {},
    }


def _normalize_node_id_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise HTTPException(status_code=400, detail=f"{field_name} must be an array of node IDs")
    node_ids: list[str] = []
    for raw_id in value:
        node_id = str(raw_id).strip()
        if not node_id:
            raise HTTPException(status_code=400, detail=f"{field_name} contains an empty node ID")
        node_ids.append(node_id)
    return node_ids


def _normalize_analysis_ui_active_run(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise HTTPException(status_code=400, detail="activeRun must be an object or null")
    unsupported = sorted(set(value) - ANALYSIS_UI_STATE_RUN_KEYS)
    if unsupported:
        raise HTTPException(status_code=400, detail=f"Unsupported activeRun fields: {', '.join(unsupported)}")
    run_id = str(value.get("runId") or "").strip()
    if not run_id:
        raise HTTPException(status_code=400, detail="activeRun requires non-empty runId")
    started_at = value.get("startedAt")
    if started_at is not None and not isinstance(started_at, str):
        raise HTTPException(status_code=400, detail="activeRun.startedAt must be a string")
    suppress_new_badges = value.get("suppressNewBadges")
    if not isinstance(suppress_new_badges, bool):
        raise HTTPException(status_code=400, detail="activeRun.suppressNewBadges must be a boolean")
    return {
        "runId": run_id,
        "startedAt": started_at,
        "suppressNewBadges": suppress_new_badges,
        "baselineVisibleNodeIds": _normalize_node_id_list(
            value.get("baselineVisibleNodeIds"),
            "activeRun.baselineVisibleNodeIds",
        ),
    }


def _normalize_analysis_ui_state_payload(
    session_id: str,
    body: dict[str, Any],
    session_mode: str = "specialized",
) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Analysis UI state payload must be a JSON object")
    raw_new_node_ids = body.get("newNodeIds")
    if raw_new_node_ids is None:
        raw_new_node_ids = {}
    if not isinstance(raw_new_node_ids, dict):
        raise HTTPException(status_code=400, detail="newNodeIds must be an object keyed by canonical node ID")

    new_node_ids: dict[str, Any] = {}
    for raw_key, raw_entry in raw_new_node_ids.items():
        node_id = str(raw_key).strip()
        if not node_id:
            raise HTTPException(status_code=400, detail="New-badge node IDs must be non-empty strings")
        if not isinstance(raw_entry, dict):
            raise HTTPException(status_code=400, detail=f"New-badge entry for {node_id} must be an object")
        unsupported = sorted(set(raw_entry) - ANALYSIS_UI_STATE_ENTRY_KEYS)
        if unsupported:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported new-badge fields for {node_id}: {', '.join(unsupported)}",
            )
        node_kind = raw_entry.get("nodeKind")
        if node_kind not in EVALUABLE_REASONING_NODE_KINDS:
            raise HTTPException(status_code=400, detail=f"New-badge entry for {node_id} has unsupported nodeKind")
        first_seen_at = raw_entry.get("firstSeenAt")
        if first_seen_at is not None and not isinstance(first_seen_at, str):
            raise HTTPException(status_code=400, detail=f"New-badge entry for {node_id} has invalid firstSeenAt")
        run_id = raw_entry.get("runId")
        if run_id is not None:
            run_id = str(run_id).strip()
            if not run_id:
                raise HTTPException(status_code=400, detail=f"New-badge entry for {node_id} has invalid runId")
        new_node_ids[node_id] = {
            "nodeKind": node_kind,
            "firstSeenAt": first_seen_at,
            "runId": run_id,
        }

    updated_at = body.get("updatedAt")
    if updated_at is not None and not isinstance(updated_at, str):
        raise HTTPException(status_code=400, detail="updatedAt must be a string")
    return {
        "sessionId": session_id,
        "sessionMode": session_mode,
        "updatedAt": updated_at,
        "activeRun": _normalize_analysis_ui_active_run(body.get("activeRun")),
        "newNodeIds": new_node_ids,
    }


def _get_analysis_ui_state(session_id: str, session_mode: str = "specialized") -> dict[str, Any]:
    session_dir, _meta, _existed = _ensure_session(session_id, session_mode=session_mode)
    payload = _read_json(_analysis_ui_state_path(session_dir))
    if payload is None:
        return _empty_analysis_ui_state(session_id, session_mode=session_mode)
    return _normalize_analysis_ui_state_payload(session_id, payload, session_mode=session_mode)


def _put_analysis_ui_state(
    session_id: str,
    body: dict[str, Any],
    session_mode: str = "specialized",
) -> dict[str, Any]:
    session_dir, _meta, _existed = _ensure_session(session_id, session_mode=session_mode)
    payload = _normalize_analysis_ui_state_payload(session_id, body, session_mode=session_mode)
    payload["updatedAt"] = _now_iso()
    _atomic_write_json(_analysis_ui_state_path(session_dir), payload)
    return payload


def _start_analysis_ui_state_run(
    session_id: str,
    body: dict[str, Any],
    session_mode: str = "specialized",
) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Run-start payload must be a JSON object")
    session_dir, _meta, _existed = _ensure_session(session_id, session_mode=session_mode)
    run_id = str(body.get("runId") or "").strip()
    if not run_id:
        raise HTTPException(status_code=400, detail="runId is required")
    suppress_new_badges = body.get("suppressNewBadges", False)
    if not isinstance(suppress_new_badges, bool):
        raise HTTPException(status_code=400, detail="suppressNewBadges must be a boolean")
    now = _now_iso()
    payload = {
        "sessionId": session_id,
        "sessionMode": session_mode,
        "updatedAt": now,
        "activeRun": {
            "runId": run_id,
            "startedAt": now,
            "suppressNewBadges": suppress_new_badges,
            "baselineVisibleNodeIds": _normalize_node_id_list(
                body.get("baselineVisibleNodeIds"),
                "baselineVisibleNodeIds",
            ),
        },
        "newNodeIds": {},
    }
    _atomic_write_json(_analysis_ui_state_path(session_dir), payload)
    return payload


def _analysis_export_file_name(session_id: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    return f"maniscope-llm-analysis-{_safe_name_part(session_id)}-{stamp}.json"


def _write_analysis_export(session_id: str, body: dict[str, Any], session_mode: str = "specialized") -> dict[str, Any]:
    session_dir, _meta, _existed = _ensure_session(session_id, session_mode=session_mode)
    payload = body.get("payload") if isinstance(body, dict) and isinstance(body.get("payload"), dict) else body
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Analysis export payload must be a JSON object")
    if payload.get("exportFormat") != ANALYSIS_EXPORT_FORMAT:
        raise HTTPException(status_code=400, detail="Analysis export payload has unsupported exportFormat")
    file_path = session_dir / "artifacts" / _analysis_export_file_name(session_id)
    _atomic_write_json(file_path, payload)
    artifact = _analysis_artifact_info(
        session_id,
        file_path,
        "analysisExport",
        "Analysis Export",
        0,
        session_mode=session_mode,
    )
    return {
        "sessionId": session_id,
        "sessionMode": session_mode,
        "artifact": artifact,
        "name": artifact["name"],
        "path": artifact["path"],
        "url": artifact["url"],
        "modifiedAt": artifact["modifiedAt"],
    }


def _get_session_versions(session_id: str, limit: int = 50, session_mode: str = "specialized") -> dict[str, Any]:
    session_dir = _session_dir(session_id, session_mode=session_mode)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        versions = list_trace_versions(session_dir, limit=limit)
    except SessionGitError as error:
        raise HTTPException(status_code=500, detail=str(error))
    return {
        "sessionId": session_id,
        "sessionMode": session_mode,
        "versions": versions,
    }


def _append_user_action_event(session_id: str, body: dict[str, Any], session_mode: str = "specialized") -> dict[str, Any]:
    action = copy.deepcopy(body.get("action"))
    if not isinstance(action, dict):
        raise HTTPException(status_code=400, detail="action must be an object")

    session_dir, meta, live_session, current_state = _event_session_state(session_id, body, session_mode=session_mode)
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


def _upsert_user_action_event(
    session_id: str,
    action_index: int,
    body: dict[str, Any],
    session_mode: str = "specialized",
) -> dict[str, Any]:
    if action_index < 0:
        raise HTTPException(status_code=400, detail="action_index must be non-negative")
    action = copy.deepcopy(body.get("action"))
    if not isinstance(action, dict):
        raise HTTPException(status_code=400, detail="action must be an object")

    session_dir, meta, live_session, current_state = _event_session_state(session_id, body, session_mode=session_mode)
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


def _delete_user_action_event(
    session_id: str,
    action_index: int,
    body: dict[str, Any] | None = None,
    session_mode: str = "specialized",
) -> dict[str, Any]:
    if action_index < 0:
        raise HTTPException(status_code=400, detail="action_index must be non-negative")

    body = body or {}
    session_dir, meta, live_session, current_state = _event_session_state(session_id, body, session_mode=session_mode)
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


def _append_annotation_event(session_id: str, body: dict[str, Any], session_mode: str = "specialized") -> dict[str, Any]:
    annotation = copy.deepcopy(body.get("annotation"))
    if not isinstance(annotation, dict):
        raise HTTPException(status_code=400, detail="annotation must be an object")

    session_dir, meta, live_session, current_state = _event_session_state(session_id, body, session_mode=session_mode)
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


def _upsert_annotation_event(
    session_id: str,
    annotation_id: int,
    body: dict[str, Any],
    session_mode: str = "specialized",
) -> dict[str, Any]:
    annotation = copy.deepcopy(body.get("annotation"))
    if not isinstance(annotation, dict):
        raise HTTPException(status_code=400, detail="annotation must be an object")

    session_dir, meta, live_session, current_state = _event_session_state(session_id, body, session_mode=session_mode)
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


def _delete_annotation_event(
    session_id: str,
    annotation_id: int,
    body: dict[str, Any] | None = None,
    session_mode: str = "specialized",
) -> dict[str, Any]:
    body = body or {}
    session_dir, meta, live_session, current_state = _event_session_state(session_id, body, session_mode=session_mode)
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


def _reorder_trace_event(session_id: str, body: dict[str, Any], session_mode: str = "specialized") -> dict[str, Any]:
    actions = copy.deepcopy(body.get("userActionSequence"))
    annotations = copy.deepcopy(body.get("annotationRecords"))
    if not isinstance(actions, list):
        raise HTTPException(status_code=400, detail="userActionSequence must be an array")
    if not isinstance(annotations, list):
        raise HTTPException(status_code=400, detail="annotationRecords must be an array")

    session_dir, meta, live_session, current_state = _event_session_state(session_id, body, session_mode=session_mode)
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


def _update_session_settings_event(session_id: str, body: dict[str, Any], session_mode: str = "specialized") -> dict[str, Any]:
    session_dir, meta, live_session, current_state = _event_session_state(session_id, body, session_mode=session_mode)
    return _write_trace_state(
        session_id,
        session_dir,
        meta,
        live_session,
        current_state,
        "settings_update",
        {"coin": body.get("coin")},
    )


def _sync_session(session_id: str, body: dict[str, Any], session_mode: str = "specialized") -> dict[str, Any]:
    session_dir, meta, _ = _ensure_session(session_id, coin=body.get("coin"), session_mode=session_mode)
    existing_live_session = _load_live_session(session_dir, session_id, coin=body.get("coin"))

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
        "traceRevision": existing_live_session.get("traceRevision", 0),
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
        "studyInfo": copy.deepcopy(body.get("studyInfo") or {}),
        "analysisMilestones": copy.deepcopy(body.get("analysisMilestones") or []),
        "chatbotLogs": copy.deepcopy(body.get("chatbotLogs") or []),
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


@router.post("")
def create_session(body: dict[str, Any] | None = None) -> dict[str, Any]:
    return _create_session(body, session_mode="specialized")


@baseline_router.post("")
def create_baseline_session(body: dict[str, Any] | None = None) -> dict[str, Any]:
    return _create_session(body, session_mode="baseline")


@router.get("/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    return _get_session(session_id, session_mode="specialized")


@baseline_router.get("/{session_id}")
def get_baseline_session(session_id: str) -> dict[str, Any]:
    return _get_session(session_id, session_mode="baseline")


@router.get("/{session_id}/workspaces/{role}")
def get_session_workspace(session_id: str, role: str) -> dict[str, Any]:
    return _get_session_workspace(session_id, role, session_mode="specialized")


@baseline_router.get("/{session_id}/workspaces/{role}")
def get_baseline_session_workspace(session_id: str, role: str) -> dict[str, Any]:
    return _get_session_workspace(session_id, role, session_mode="baseline")


@router.put("/{session_id}/workspaces/{role}/state")
def put_session_workspace_state(session_id: str, role: str, body: dict[str, Any]) -> dict[str, Any]:
    return _put_session_workspace_state(session_id, role, body, session_mode="specialized")


@baseline_router.put("/{session_id}/workspaces/{role}/state")
def put_baseline_session_workspace_state(session_id: str, role: str, body: dict[str, Any]) -> dict[str, Any]:
    return _put_session_workspace_state(session_id, role, body, session_mode="baseline")


@router.get("/{session_id}/artifacts/{artifact_path:path}")
def get_session_artifact(session_id: str, artifact_path: str) -> FileResponse:
    return _get_session_artifact(session_id, artifact_path, session_mode="specialized")


@baseline_router.get("/{session_id}/artifacts/{artifact_path:path}")
def get_baseline_session_artifact(session_id: str, artifact_path: str) -> FileResponse:
    return _get_session_artifact(session_id, artifact_path, session_mode="baseline")


@router.get("/{session_id}/images/{image_path:path}")
def get_session_image(session_id: str, image_path: str) -> FileResponse:
    return _get_session_image(session_id, image_path, session_mode="specialized")


@baseline_router.get("/{session_id}/images/{image_path:path}")
def get_baseline_session_image(session_id: str, image_path: str) -> FileResponse:
    return _get_session_image(session_id, image_path, session_mode="baseline")


@router.get("/{session_id}/analysis-artifacts")
def get_analysis_artifact_manifest(session_id: str) -> dict[str, Any]:
    return _get_analysis_artifact_manifest(session_id, session_mode="specialized")


@baseline_router.get("/{session_id}/analysis-artifacts")
def get_baseline_analysis_artifact_manifest(session_id: str) -> dict[str, Any]:
    return _get_analysis_artifact_manifest(session_id, session_mode="baseline")


@router.get("/{session_id}/analysis-evaluations")
def get_analysis_evaluations(session_id: str) -> dict[str, Any]:
    return _get_analysis_evaluations(session_id, session_mode="specialized")


@router.put("/{session_id}/analysis-evaluations")
def put_analysis_evaluations(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return _put_analysis_evaluations(session_id, body, session_mode="specialized")


@router.get("/{session_id}/analysis-ui-state")
def get_analysis_ui_state(session_id: str) -> dict[str, Any]:
    return _get_analysis_ui_state(session_id, session_mode="specialized")


@router.put("/{session_id}/analysis-ui-state")
def put_analysis_ui_state(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return _put_analysis_ui_state(session_id, body, session_mode="specialized")


@router.post("/{session_id}/analysis-ui-state/run-start")
def start_analysis_ui_state_run(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return _start_analysis_ui_state_run(session_id, body, session_mode="specialized")


@router.post("/{session_id}/analysis-runs/start")
def start_analysis_run(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return _start_analysis_run(session_id, body, session_mode="specialized")


def finish_analysis_run(
    session_id: str,
    run_id: str,
    status: str,
    session_mode: str = "specialized",
) -> dict[str, Any] | None:
    return _finish_analysis_run(session_id, run_id, status, session_mode=session_mode)


@router.post("/{session_id}/analysis-export")
def write_analysis_export(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return _write_analysis_export(session_id, body, session_mode="specialized")


@router.get("/{session_id}/versions")
def get_session_versions(session_id: str, limit: int = 50) -> dict[str, Any]:
    return _get_session_versions(session_id, limit=limit, session_mode="specialized")


@baseline_router.get("/{session_id}/versions")
def get_baseline_session_versions(session_id: str, limit: int = 50) -> dict[str, Any]:
    return _get_session_versions(session_id, limit=limit, session_mode="baseline")


@router.post("/{session_id}/events/user-actions")
def append_user_action_event(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return _append_user_action_event(session_id, body, session_mode="specialized")


@baseline_router.post("/{session_id}/events/user-actions")
def append_baseline_user_action_event(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return _append_user_action_event(session_id, body, session_mode="baseline")


@router.put("/{session_id}/events/user-actions/{action_index}")
def upsert_user_action_event(session_id: str, action_index: int, body: dict[str, Any]) -> dict[str, Any]:
    return _upsert_user_action_event(session_id, action_index, body, session_mode="specialized")


@baseline_router.put("/{session_id}/events/user-actions/{action_index}")
def upsert_baseline_user_action_event(session_id: str, action_index: int, body: dict[str, Any]) -> dict[str, Any]:
    return _upsert_user_action_event(session_id, action_index, body, session_mode="baseline")


@router.delete("/{session_id}/events/user-actions/{action_index}")
def delete_user_action_event(session_id: str, action_index: int, body: dict[str, Any] | None = None) -> dict[str, Any]:
    return _delete_user_action_event(session_id, action_index, body, session_mode="specialized")


@baseline_router.delete("/{session_id}/events/user-actions/{action_index}")
def delete_baseline_user_action_event(
    session_id: str,
    action_index: int,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _delete_user_action_event(session_id, action_index, body, session_mode="baseline")


@router.post("/{session_id}/events/annotations")
def append_annotation_event(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return _append_annotation_event(session_id, body, session_mode="specialized")


@baseline_router.post("/{session_id}/events/annotations")
def append_baseline_annotation_event(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return _append_annotation_event(session_id, body, session_mode="baseline")


@router.put("/{session_id}/events/annotations/{annotation_id}")
def upsert_annotation_event(session_id: str, annotation_id: int, body: dict[str, Any]) -> dict[str, Any]:
    return _upsert_annotation_event(session_id, annotation_id, body, session_mode="specialized")


@baseline_router.put("/{session_id}/events/annotations/{annotation_id}")
def upsert_baseline_annotation_event(session_id: str, annotation_id: int, body: dict[str, Any]) -> dict[str, Any]:
    return _upsert_annotation_event(session_id, annotation_id, body, session_mode="baseline")


@router.delete("/{session_id}/events/annotations/{annotation_id}")
def delete_annotation_event(session_id: str, annotation_id: int, body: dict[str, Any] | None = None) -> dict[str, Any]:
    return _delete_annotation_event(session_id, annotation_id, body, session_mode="specialized")


@baseline_router.delete("/{session_id}/events/annotations/{annotation_id}")
def delete_baseline_annotation_event(
    session_id: str,
    annotation_id: int,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _delete_annotation_event(session_id, annotation_id, body, session_mode="baseline")


@router.post("/{session_id}/events/reorder")
def reorder_trace_event(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return _reorder_trace_event(session_id, body, session_mode="specialized")


@baseline_router.post("/{session_id}/events/reorder")
def reorder_baseline_trace_event(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return _reorder_trace_event(session_id, body, session_mode="baseline")


@router.post("/{session_id}/events/settings")
def update_session_settings_event(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return _update_session_settings_event(session_id, body, session_mode="specialized")


@baseline_router.post("/{session_id}/events/settings")
def update_baseline_session_settings_event(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return _update_session_settings_event(session_id, body, session_mode="baseline")


@router.post("/{session_id}/sync")
def sync_session(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return _sync_session(session_id, body, session_mode="specialized")


@baseline_router.post("/{session_id}/sync")
def sync_baseline_session(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return _sync_session(session_id, body, session_mode="baseline")
