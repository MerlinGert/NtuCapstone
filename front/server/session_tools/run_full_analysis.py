#!/usr/bin/env python3
"""Start, inspect, or stop a ManiScope full-analysis background task."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TOOL_VERSION = "__MANISCOPE_TOOL_VERSION__"
SESSION_ID = "__MANISCOPE_SESSION_ID__"
MODE = "full"
DEFAULT_BACKEND_URL = "http://127.0.0.1:8099"


def _backend_url() -> str:
    return os.environ.get("MANISCOPE_BACKEND_URL", DEFAULT_BACKEND_URL).rstrip("/")


def _request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"{_backend_url()}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Cannot reach ManiScope backend at {_backend_url()}: {exc.reason}") from exc
    return json.loads(body) if body else {}


def _latest_task(tasks: list[dict[str, Any]], *, running_only: bool = False) -> dict[str, Any] | None:
    candidates = [task for task in tasks if task.get("mode") == MODE]
    if running_only:
        candidates = [
            task
            for task in candidates
            if task.get("status") in {"starting", "running", "stopping"}
        ]
    return candidates[0] if candidates else None


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def start(args: argparse.Namespace) -> int:
    body: dict[str, Any] = {}
    if args.run_id:
        body["runId"] = args.run_id
    if args.task_id:
        body["taskId"] = args.task_id
    payload = _request("POST", f"/api/sessions/{SESSION_ID}/analysis-tasks/full/start", body)
    _print(payload)
    return 0


def status(args: argparse.Namespace) -> int:
    if args.task_id:
        payload = _request("GET", f"/api/sessions/{SESSION_ID}/analysis-tasks/{args.task_id}")
        _print(payload)
        return 0
    payload = _request("GET", f"/api/sessions/{SESSION_ID}/analysis-tasks")
    latest = _latest_task(payload.get("tasks") or [])
    if latest is None:
        print("No full-analysis task found.", file=sys.stderr)
        return 1
    _print(latest)
    return 0


def stop(args: argparse.Namespace) -> int:
    task_id = args.task_id
    if not task_id:
        payload = _request("GET", f"/api/sessions/{SESSION_ID}/analysis-tasks")
        latest = _latest_task(payload.get("tasks") or [], running_only=True)
        if latest is None:
            print("No running full-analysis task found.", file=sys.stderr)
            return 1
        task_id = latest["taskId"]
    payload = _request("POST", f"/api/sessions/{SESSION_ID}/analysis-tasks/{task_id}/stop", {})
    _print(payload)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--run-id")
    start_parser.add_argument("--task-id")
    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--task-id")
    stop_parser = subparsers.add_parser("stop")
    stop_parser.add_argument("--task-id")
    args = parser.parse_args(argv)
    try:
        if args.command == "start":
            return start(args)
        if args.command == "status":
            return status(args)
        if args.command == "stop":
            return stop(args)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
