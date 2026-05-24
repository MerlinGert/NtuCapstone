from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TOOL_VERSION = "__MANISCOPE_TOOL_VERSION__"
SESSION_ID = "__MANISCOPE_SESSION_ID__"
BRIDGE_URL = os.environ.get("MANISCOPE_CODEX_BRIDGE_URL", "http://127.0.0.1:8787")
BACKEND_URL = os.environ.get("MANISCOPE_BACKEND_URL", "http://127.0.0.1:8099")
SESSION_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = SESSION_DIR / "artifacts"


def health(timeout_seconds: float = 30) -> dict[str, Any]:
    return _get_json(_bridge_path("/health"), timeout_seconds=timeout_seconds)


def get_token_distribution_args(
    *,
    width: int = 1008,
    height: int = 610,
    scale_factor: float | None = None,
    show_links: bool | None = None,
    timeout_seconds: float = 120,
) -> dict[str, Any]:
    args = _current_args(
        "token-distribution",
        {"width": width, "height": height},
        timeout_seconds=timeout_seconds,
    )
    if scale_factor is not None:
        args["scale_factor"] = scale_factor
    if show_links is not None:
        args["show_links"] = show_links
    return args


def render_token_distribution(
    *,
    snapshot_data: dict[str, Any],
    entity_detection_results: dict[str, Any] | list[Any],
    link_detection_results: dict[str, Any] | list[Any],
    manipulation_detection_results: dict[str, Any] | list[Any],
    scale_factor: float = 0.4,
    show_links: bool = True,
    width: int = 1008,
    height: int = 610,
    artifact_name: str | None = None,
    quality: str = "full",
    include_raw_data: bool = False,
    timeout_seconds: float = 180,
) -> dict[str, Any]:
    args = {
        "snapshotData": snapshot_data,
        "entityDetectionResults": entity_detection_results,
        "linkDetectionResults": link_detection_results,
        "manipulationDetectionResults": manipulation_detection_results,
        "scaleFactor": scale_factor,
        "showLinks": show_links,
        "width": width,
        "height": height,
    }
    return _render(
        "token-distribution",
        args,
        artifact_name=artifact_name,
        quality=quality,
        include_raw_data=include_raw_data,
        timeout_seconds=timeout_seconds,
    )


def get_kline_args(
    *,
    width: int = 1500,
    height: int = 850,
    visible_time_window: list[str] | None = None,
    card_alignment: str = "scroll_offsets",
    card_focus_time: str | None = None,
    timeout_seconds: float = 120,
) -> dict[str, Any]:
    args = _current_args(
        "kline",
        {
            "width": width,
            "height": height,
            "visibleTimeWindow": visible_time_window,
            "cardAlignment": card_alignment,
            "cardFocusTime": card_focus_time,
        },
        timeout_seconds=timeout_seconds,
    )
    args["visible_time_window"] = visible_time_window
    args["card_alignment"] = card_alignment
    args["card_focus_time"] = card_focus_time
    return args


def render_kline_chart(
    *,
    current_coin: str,
    ohlc_data: dict[str, Any],
    manipulation_results: list[Any],
    sync_target_time_window: list[str] | None,
    is_sequential_time: bool,
    current_granularity: str,
    zoom_transform: dict[str, Any] | None = None,
    top_cards_scroll_left: int = 0,
    bottom_cards_scroll_left: int = 0,
    visible_time_window: list[str] | None = None,
    card_alignment: str = "scroll_offsets",
    card_focus_time: str | None = None,
    width: int = 1500,
    height: int = 850,
    artifact_name: str | None = None,
    quality: str = "full",
    include_raw_data: bool = False,
    timeout_seconds: float = 180,
) -> dict[str, Any]:
    args = {
        "currentCoin": current_coin,
        "ohlcData": ohlc_data,
        "manipulationResults": manipulation_results,
        "syncTargetTimeWindow": sync_target_time_window,
        "isSequentialTime": is_sequential_time,
        "currentGranularity": current_granularity,
        "zoomTransform": zoom_transform,
        "topCardsScrollLeft": top_cards_scroll_left,
        "bottomCardsScrollLeft": bottom_cards_scroll_left,
        "visibleTimeWindow": visible_time_window,
        "cardAlignment": card_alignment,
        "cardFocusTime": card_focus_time,
        "width": width,
        "height": height,
    }
    return _render(
        "kline",
        args,
        artifact_name=artifact_name,
        quality=quality,
        include_raw_data=include_raw_data,
        timeout_seconds=timeout_seconds,
    )


def fetch_behavior_sequences(
    users: list[str],
    *,
    coin: str = "ACT",
    timeout_seconds: float = 120,
) -> dict[str, Any]:
    return _post_json(
        _bridge_path("/behavior-details/fetch-sequences"),
        {"users": users, "coin": coin},
        timeout_seconds=timeout_seconds,
    )


def get_behavior_details_args(
    *,
    width: int = 1500,
    height: int = 520,
    visible_time_window: list[str] | None = None,
    max_events_per_user: int = 1500,
    timeout_seconds: float = 120,
) -> dict[str, Any]:
    args = _current_args(
        "behavior-details",
        {
            "width": width,
            "height": height,
            "visibleTimeWindow": visible_time_window,
            "maxEventsPerUser": max_events_per_user,
        },
        timeout_seconds=timeout_seconds,
    )
    args["visible_time_window"] = visible_time_window
    args["max_events_per_user"] = max_events_per_user
    return args


def render_behavior_details(
    *,
    selected_user: str | None,
    selected_users_list: list[str],
    behavior_data: dict[str, Any],
    entity_info: dict[str, Any] | None,
    snapshot_time: str,
    manipulation_results: list[Any],
    sync_target_time_window: list[str] | None,
    show_related_users: bool = False,
    use_sequential_time: bool = False,
    show_manipulation_boxes: bool = True,
    visible_time_window: list[str] | None = None,
    max_events_per_user: int = 1500,
    width: int = 1500,
    height: int = 520,
    artifact_name: str | None = None,
    strict: bool = True,
    allow_empty: bool = False,
    quality: str = "full",
    include_raw_data: bool = False,
    timeout_seconds: float = 180,
) -> dict[str, Any]:
    args = {
        "selectedUser": selected_user,
        "selectedUsersList": selected_users_list,
        "behaviorData": behavior_data,
        "entityInfo": entity_info,
        "snapshotTime": snapshot_time,
        "manipulationResults": manipulation_results,
        "syncTargetTimeWindow": sync_target_time_window,
        "showRelatedUsers": show_related_users,
        "useSequentialTime": use_sequential_time,
        "showManipulationBoxes": show_manipulation_boxes,
        "visibleTimeWindow": visible_time_window,
        "maxEventsPerUser": max_events_per_user,
        "width": width,
        "height": height,
    }
    return _render(
        "behavior-details",
        args,
        artifact_name=artifact_name,
        quality=quality,
        include_raw_data=include_raw_data,
        strict=strict,
        allow_empty=allow_empty,
        timeout_seconds=timeout_seconds,
    )


def artifact_path(name: str) -> Path:
    base = ARTIFACTS_DIR.resolve()
    target = (base / name).resolve()
    try:
        target.relative_to(base)
    except ValueError as error:
        raise ValueError(f"Artifact path escapes the session artifacts directory: {name}") from error
    return target


def _bridge_path(path: str) -> str:
    return f"/api/agent-browser/{SESSION_ID}{path}"


def _current_args(
    view_slug: str,
    options: dict[str, Any],
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    response = _post_json(
        _bridge_path(f"/{view_slug}/current-args"),
        {"options": _drop_none(options)},
        timeout_seconds=timeout_seconds,
    )
    return _snake_top_level(response.get("args") or {})


def _render(
    view_slug: str,
    args: dict[str, Any],
    *,
    artifact_name: str | None,
    quality: str,
    include_raw_data: bool,
    timeout_seconds: float,
    strict: bool | None = None,
    allow_empty: bool | None = None,
) -> dict[str, Any]:
    options = {
        "quality": quality,
        "includeRawData": include_raw_data,
        "strict": strict,
        "allowEmpty": allow_empty,
    }
    response = _post_json(
        _bridge_path(f"/{view_slug}/render"),
        {
            "args": args,
            "options": _drop_none(options),
            "artifactName": artifact_name,
        },
        timeout_seconds=timeout_seconds,
    )
    return _snake_top_level(response)


def _get_json(path: str, *, timeout_seconds: float) -> dict[str, Any]:
    return _request_json("GET", path, None, timeout_seconds=timeout_seconds)


def _post_json(path: str, payload: dict[str, Any], *, timeout_seconds: float) -> dict[str, Any]:
    return _request_json("POST", path, payload, timeout_seconds=timeout_seconds)


def _request_json(
    method: str,
    path: str,
    payload: dict[str, Any] | None,
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    url = BRIDGE_URL.rstrip("/") + path
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            text = response.read().decode("utf-8")
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(_format_bridge_error(error.code, detail)) from error
    except URLError as error:
        raise RuntimeError(f"Cannot reach ManiScope Codex bridge at {BRIDGE_URL}: {error.reason}") from error

    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Codex bridge returned invalid JSON from {url}: {text[:500]}") from error


def _format_bridge_error(status_code: int, detail: str) -> str:
    try:
        parsed = json.loads(detail)
    except json.JSONDecodeError:
        parsed = {}
    message = parsed.get("error") or parsed.get("detail") or detail or "unknown error"
    return f"Codex bridge returned HTTP {status_code}: {message}"


def _drop_none(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None}


def _snake_top_level(value: dict[str, Any]) -> dict[str, Any]:
    return {_camel_to_snake(key): item for key, item in value.items()}


def _camel_to_snake(value: str) -> str:
    chars: list[str] = []
    for index, char in enumerate(value):
        if char.isupper() and index > 0:
            chars.append("_")
        chars.append(char.lower())
    return "".join(chars)
