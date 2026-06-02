from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


TOOL_VERSION = "__MANISCOPE_TOOL_VERSION__"
SESSION_ID = "__MANISCOPE_SESSION_ID__"
SESSION_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = SESSION_DIR / "artifacts"

_VIEW_ALIASES = {
    "token_distribution": ("token_distribution", "tokenDistribution"),
    "kline_chart": ("candlestick_chart", "kline_chart", "klineChart"),
    "behavior_details": ("behavior_details", "behaviorDetails"),
}


def artifact_path(name: str) -> Path:
    if not name or Path(name).name != name:
        raise ValueError("artifact name must be a simple filename")
    target = (ARTIFACTS_DIR / name).resolve()
    artifacts_root = ARTIFACTS_DIR.resolve()
    try:
        target.relative_to(artifacts_root)
    except ValueError as exc:
        raise ValueError("artifact path escapes the session artifacts directory") from exc
    return target


def capture_current_token_distribution() -> dict:
    return _capture_view("token_distribution")


def capture_current_kline_chart() -> dict:
    return _capture_view("kline_chart")


def capture_current_behavior_details() -> dict:
    return _capture_view("behavior_details")


def capture_current_views() -> dict:
    return {
        "token_distribution": capture_current_token_distribution(),
        "kline_chart": capture_current_kline_chart(),
        "behavior_details": capture_current_behavior_details(),
    }


def _read_current_state() -> dict:
    state_path = SESSION_DIR / "current-state.json"
    if not state_path.exists():
        raise RuntimeError(f"current-state.json is missing for session {SESSION_ID}")
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("current-state.json is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("current-state.json must contain an object")
    return payload


def _capture_view(view_name: str) -> dict:
    state = _read_current_state()
    screenshots = state.get("majorViewScreenshots")
    if not isinstance(screenshots, dict):
        raise RuntimeError("current-state.json does not contain majorViewScreenshots")

    source_relative = _find_view_screenshot(screenshots, _VIEW_ALIASES[view_name])
    source_path = _resolve_session_file(source_relative)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    extension = source_path.suffix.lower() if source_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} else ".png"
    output_name = f"baseline-current-{view_name}-{timestamp}{extension}"
    target_path = artifact_path(output_name)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
    return {
        "session_id": SESSION_ID,
        "view_name": view_name,
        "artifact_name": output_name,
        "artifact_path": str(target_path),
        "artifact_url": f"/api/base/sessions/{SESSION_ID}/artifacts/{output_name}",
        "source_image_path": str(source_path),
        "source_image_relative_path": source_relative,
    }


def _find_view_screenshot(screenshots: dict, aliases: tuple[str, ...]) -> str:
    for key in aliases:
        value = screenshots.get(key)
        if isinstance(value, str) and value:
            return value
    available = ", ".join(sorted(str(key) for key in screenshots.keys()))
    raise RuntimeError(f"no synced screenshot found for {aliases[0]}; available keys: {available}")


def _resolve_session_file(relative_path: str) -> Path:
    if not relative_path or "\x00" in relative_path:
        raise RuntimeError("invalid screenshot path in current-state.json")
    requested = Path(relative_path)
    if requested.is_absolute():
        raise RuntimeError("screenshot path must be session-relative")
    path = (SESSION_DIR / requested).resolve()
    session_root = SESSION_DIR.resolve()
    try:
        path.relative_to(session_root)
    except ValueError as exc:
        raise RuntimeError("screenshot path escapes the session directory") from exc
    if not path.exists() or not path.is_file():
        raise RuntimeError(f"synced screenshot does not exist: {relative_path}")
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise RuntimeError(f"unsupported screenshot type: {path.suffix}")
    return path
