"""
In-process screenshot state management.
Replaces the standalone virtual_browser FastAPI service (port 8001).
"""

import logging
from typing import Any, Dict, Optional

from screenshot import take_screenshot

logger = logging.getLogger(__name__)

# Persistent visualization state (mirrors virtual_browser/app.py)
visualization_state: Dict[str, Any] = {
    "snapshotResponse": None,
    "detectionResponse": None,
    "manipulationResponse": None,
    "entityDetectionConfig": None,
    "linkDetectionConfig": None,
}

# Cached latest screenshot
latest_screenshot: Optional[bytes] = None


async def update_and_screenshot(data: dict, width: int = 1200, height: int = 800) -> Optional[bytes]:
    """Merge incoming fields into persistent state and take a screenshot.

    Returns PNG bytes, or None if snapshotResponse is not yet available.
    """
    global latest_screenshot

    # Merge incoming fields (skip None values)
    for key, value in data.items():
        if key in visualization_state and value is not None:
            visualization_state[key] = value

    # Must have snapshot data to render
    if visualization_state["snapshotResponse"] is None:
        logger.warning("Cannot render: snapshotResponse not yet available")
        return None

    # Build render payload from non-None state
    render_payload = {k: v for k, v in visualization_state.items() if v is not None}

    png_bytes = await take_screenshot(render_payload, width, height)
    latest_screenshot = png_bytes
    return png_bytes


def get_latest_screenshot() -> Optional[bytes]:
    return latest_screenshot


def reset_state():
    global latest_screenshot
    for key in visualization_state:
        visualization_state[key] = None
    latest_screenshot = None


def get_state_summary() -> dict:
    return {
        key: (type(value).__name__ if value is not None else None)
        for key, value in visualization_state.items()
    }
