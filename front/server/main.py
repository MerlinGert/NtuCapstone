
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
import os
import uvicorn
import entity_detection
import snapshot_service
import manipulation_detect
import behavior_detection
import manipulation_detection
import fraudulent_activity_detection
import detection_service
import manipulation_detection_service
import user_behavior_service

# Add data_processing directory to path to import scripts if needed
# BASE_DIR is the 'server' directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DATA_PROCESSING_DIR is the sibling directory 'data_processing'
DATA_PROCESSING_DIR = os.path.join(os.path.dirname(BASE_DIR), 'data_processing')
sys.path.append(DATA_PROCESSING_DIR)

import token_config
# Ezio
# Add virtual_browser directory so screenshot.py can be imported directly
VIRTUAL_BROWSER_DIR = os.path.join(os.path.dirname(BASE_DIR), 'virtual_browser')
sys.path.insert(0, VIRTUAL_BROWSER_DIR)

from screenshot import init_browser, close_browser

app = FastAPI()

# ezio
@app.on_event("startup")
async def startup_browser():
    """Launch headless browser once when server starts."""
    await init_browser()

# ezio
@app.on_event("shutdown")
async def shutdown_browser():
    """Clean up browser resources when server stops."""
    await close_browser()


# Include routers
app.include_router(entity_detection.router)
app.include_router(snapshot_service.router)
app.include_router(manipulation_detect.router)
app.include_router(behavior_detection.router)
app.include_router(manipulation_detection.router)
app.include_router(fraudulent_activity_detection.router)
app.include_router(detection_service.router)
app.include_router(manipulation_detection_service.router)
app.include_router(user_behavior_service.router)

@app.get("/")
def read_root():
    return {"message": "CryptoVis Backend is running!"}

@app.get("/api/tokens")
def get_available_tokens():
    return {"tokens": token_config.get_available_tokens(), "default": token_config.DEFAULT_TOKEN}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
