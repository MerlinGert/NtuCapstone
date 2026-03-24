from pathlib import Path
from playwright.async_api import async_playwright

# Load render.html via file:// so it works before the HTTP server is ready
_RENDER_HTML = Path(__file__).parent / "render.html"

# Module-level singleton: browser and page are reused across screenshots
_playwright_instance = None
_browser = None
_page = None


async def init_browser(width: int = 1200, height: int = 800):
    """Launch browser once and pre-load the render page (D3 etc.)."""
    global _playwright_instance, _browser, _page
    _playwright_instance = await async_playwright().start()
    _browser = await _playwright_instance.chromium.launch(headless=True)
    _page = await _browser.new_page(viewport={"width": width, "height": height})
    # Pre-load render.html via file:// so D3 is cached in memory
    await _page.goto(f"file://{_RENDER_HTML.resolve()}", wait_until="networkidle")


async def take_screenshot(render_data: dict, width: int = 1200, height: int = 800) -> bytes:
    """
    Inject data into the already-loaded page via JS and capture a screenshot.
    No browser restart, no page navigation, no network fetch for render data.
    """
    global _page

    if _page is None:
        # Fallback: if init_browser wasn't called, do a cold start
        await init_browser(width, height)

    # Reset settled flag and render with new data
    await _page.evaluate("window.__SIMULATION_SETTLED = false")
    await _page.evaluate("data => window.renderWithData(data)", render_data)

    # Wait for D3 force simulation to finish
    await _page.wait_for_function(
        "window.__SIMULATION_SETTLED === true",
        timeout=15000,
    )

    # Brief delay for final SVG render
    await _page.wait_for_timeout(50)

    return await _page.screenshot(full_page=False)


async def close_browser():
    """Clean up browser resources on shutdown."""
    global _playwright_instance, _browser, _page
    if _browser:
        await _browser.close()
    if _playwright_instance:
        await _playwright_instance.stop()
    _playwright_instance = None
    _browser = None
    _page = None
