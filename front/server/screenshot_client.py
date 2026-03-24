"""
Client for the Virtual Browser Screenshot Service (port 8001).
Each backend endpoint calls notify_screenshot() after computing its response.
The screenshot service maintains persistent state and re-renders incrementally.
"""

import asyncio
import json
import logging
import urllib.request

logger = logging.getLogger(__name__)

SCREENSHOT_SERVICE_URL = "http://localhost:8001/update"


def _sync_post(data: dict):
    """Synchronous POST to screenshot service (runs in thread pool)."""
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        SCREENSHOT_SERVICE_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    # Timeout is generous because Playwright rendering takes time
    urllib.request.urlopen(req, timeout=60)


async def notify_screenshot(data: dict):
    """Fire-and-forget: send data to screenshot service without blocking the API response.
    Silently ignores errors (service may not be running)."""
    try:
        await asyncio.to_thread(_sync_post, data)
        logger.info("Screenshot service updated successfully")
    except Exception as e:
        logger.debug(f"Screenshot service not available: {e}")
