"""
Screenshot integration module.
Directly calls the in-process screenshot service instead of HTTP to port 8001.
"""

import logging

logger = logging.getLogger(__name__)


async def notify_screenshot(data: dict):
    """Update visualization state and take a screenshot.
    Silently ignores errors to avoid blocking the caller."""
    try:
        from screenshot_service import update_and_screenshot
        await update_and_screenshot(data)
        logger.info("Screenshot updated successfully")
    except Exception as e:
        logger.debug(f"Screenshot update failed: {e}")
