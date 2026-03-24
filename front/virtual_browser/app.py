import io

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
from pydantic import BaseModel
from typing import Any, Dict, Optional

from screenshot import take_screenshot, init_browser, close_browser

app = FastAPI(title="Virtual Browser Service")


@app.on_event("startup")
async def startup_event():
    """Launch headless browser once when server starts."""
    await init_browser()


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up browser resources when server stops."""
    await close_browser()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Persistent visualization state (like CryptoVis.vue's data())
visualization_state: Dict[str, Any] = {
    "snapshotResponse": None,
    "detectionResponse": None,
    "manipulationResponse": None,
    "entityDetectionConfig": None,  # None → render.html uses defaults
    "linkDetectionConfig": None,
}

# Cached latest screenshot from /update
latest_screenshot: Optional[bytes] = None


class ScreenshotRequest(BaseModel):
    snapshotResponse: dict
    detectionResponse: Optional[dict] = None
    manipulationResponse: Optional[dict] = None
    entityDetectionConfig: Optional[dict] = None
    linkDetectionConfig: Optional[dict] = None
    width: int = 1200
    height: int = 800


class UpdateRequest(BaseModel):
    snapshotResponse: Optional[dict] = None
    detectionResponse: Optional[dict] = None
    manipulationResponse: Optional[dict] = None
    entityDetectionConfig: Optional[dict] = None
    linkDetectionConfig: Optional[dict] = None
    width: int = 1200
    height: int = 800


@app.get("/render")
async def render_page():
    """Serve the standalone D3 visualization page."""
    html_path = Path(__file__).parent / "render.html"
    return FileResponse(html_path, media_type="text/html")


@app.post("/screenshot")
async def create_screenshot(request: ScreenshotRequest):
    """Accept full visualization data, render in headless browser, return PNG.
    Does NOT affect persistent state."""
    render_data = request.dict(exclude={"width", "height"})
    png_bytes = await take_screenshot(render_data, request.width, request.height)
    return StreamingResponse(
        io.BytesIO(png_bytes),
        media_type="image/png",
        headers={"Content-Disposition": "attachment; filename=token_distribution.png"},
    )


@app.post("/update")
async def update_and_screenshot(request: UpdateRequest):
    """Incrementally update visualization state and return a new screenshot.
    Only provided fields are updated; others keep their previous values."""
    global latest_screenshot

    # Merge incoming fields into persistent state
    update_data = request.dict(exclude={"width", "height"}, exclude_none=True)
    for key, value in update_data.items():
        visualization_state[key] = value

    # Must have at least snapshot data to render
    if visualization_state["snapshotResponse"] is None:
        raise HTTPException(
            status_code=400,
            detail="Cannot render: snapshotResponse is required. Send it first.",
        )

    # Build render data from current state
    render_payload = {k: v for k, v in visualization_state.items() if v is not None}

    png_bytes = await take_screenshot(render_payload, request.width, request.height)
    latest_screenshot = png_bytes
    return StreamingResponse(
        io.BytesIO(png_bytes),
        media_type="image/png",
        headers={"Content-Disposition": "attachment; filename=token_distribution.png"},
    )


@app.get("/latest-screenshot")
async def get_latest_screenshot():
    """Return the most recently cached screenshot without re-rendering."""
    if latest_screenshot is None:
        raise HTTPException(status_code=404, detail="No screenshot available yet")
    return StreamingResponse(
        io.BytesIO(latest_screenshot),
        media_type="image/png",
        headers={"Content-Disposition": "attachment; filename=latest_screenshot.png"},
    )


@app.post("/reset")
async def reset_state():
    """Clear all persistent state and cached screenshot."""
    global latest_screenshot
    for key in visualization_state:
        visualization_state[key] = None
    latest_screenshot = None
    return {"status": "ok", "message": "State cleared"}


@app.get("/state")
async def get_state():
    """Return current state summary (for debugging)."""
    return {
        key: (type(value).__name__ if value is not None else None)
        for key, value in visualization_state.items()
    }


@app.get("/screenshot/test")
async def test_screenshot():
    """Test endpoint: uses /update incrementally with sample data."""
    global latest_screenshot

    # Step 1: Set snapshot
    visualization_state["snapshotResponse"] = {
        "time": "2024-11-09 23:00:00 UTC",
        "balances": {
            "users": {
                "UserA_0x1234abcd": 50000000,
                "UserB_0x5678efgh": 30000000,
                "UserC_0x9abc1234": 20000000,
                "UserD_0xdef05678": 15000000,
                "UserE_0x1111aaaa": 10000000,
                "UserF_0x2222bbbb": 8000000,
                "UserG_0x3333cccc": 5000000,
                "UserH_0x4444dddd": 3000000,
                "UserI_0x5555eeee": 2000000,
                "UserJ_0x6666ffff": 1000000,
                "Others": 100000000,
            },
            "related_users": {
                "RelatedA_0xaaaa1111": 500000,
                "RelatedB_0xbbbb2222": 300000,
            },
        },
    }

    # Step 2: Set detection
    visualization_state["detectionResponse"] = {
        "entity_results": [
            {
                "users": ["UserA_0x1234abcd", "UserB_0x5678efgh", "UserC_0x9abc1234"],
                "relations": ["Same funding source", "Coordinated timing"],
            },
            {
                "users": ["UserE_0x1111aaaa", "UserF_0x2222bbbb"],
                "relations": ["Round-trip transfers"],
            },
        ],
        "relations": {
            "target_relations_for_links": {
                "UserA_0x1234abcd-UserD_0xdef05678": [
                    {"type": "direct_transfer", "description": "Transfer 1M tokens"},
                ],
                "UserG_0x3333cccc-UserH_0x4444dddd": [
                    {"type": "trading_sequence", "description": "Sequential trades"},
                ],
            },
            "target_related_relations_for_links": {
                "UserB_0x5678efgh-RelatedA_0xaaaa1111": [
                    {"type": "funding", "description": "Funding link"},
                ],
            },
            "target_relations_for_entity": {
                "UserA_0x1234abcd-UserB_0x5678efgh": [
                    {"type": "balance_similarity", "description": "Same funding source"},
                ],
                "UserB_0x5678efgh-UserC_0x9abc1234": [
                    {"type": "balance_similarity", "description": "Coordinated timing"},
                ],
                "UserE_0x1111aaaa-UserF_0x2222bbbb": [
                    {"type": "direct_transfer", "description": "Round-trip transfers"},
                ],
            },
            "target_related_relations_for_entity": {
                "UserE_0x1111aaaa-RelatedB_0xbbbb2222": [
                    {"type": "entity_relation", "description": "Entity relation"},
                ],
            },
        },
    }

    # Step 3: Set manipulation
    visualization_state["manipulationResponse"] = {
        "results": [
            {
                "detection_method": "round_trip",
                "participants": ["UserA_0x1234abcd", "UserE_0x1111aaaa"],
                "manipulation_time": ["2024-11-09 10:30:45", "2024-11-09 10:35:12"],
            },
            {
                "detection_method": "same_direction",
                "participants": ["UserG_0x3333cccc"],
                "manipulation_time": ["2024-11-09 11:00:00", "2024-11-09 11:15:00"],
            },
        ],
    }

    # Render with all data (configs use defaults via render.html)
    render_payload = {k: v for k, v in visualization_state.items() if v is not None}
    png_bytes = await take_screenshot(render_payload, 1200, 800)
    latest_screenshot = png_bytes
    return StreamingResponse(
        io.BytesIO(png_bytes),
        media_type="image/png",
        headers={"Content-Disposition": "attachment; filename=test_screenshot.png"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
