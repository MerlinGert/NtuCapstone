import os
import sys

import behavior_detection
import chat_session_service
import codex_chat_service
import detection_service
import entity_detection
import fraudulent_activity_detection
import manipulation_detect
import manipulation_detection
import manipulation_detection_service
import snapshot_service
import user_behavior_service
import uvicorn
from fastapi import FastAPI

# Add data_processing directory to path to import scripts if needed
# BASE_DIR is the 'server' directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DATA_PROCESSING_DIR is the sibling directory 'data_processing'
DATA_PROCESSING_DIR = os.path.join(os.path.dirname(BASE_DIR), "data_processing")
sys.path.append(DATA_PROCESSING_DIR)

app = FastAPI()

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
app.include_router(chat_session_service.router)
app.include_router(codex_chat_service.router)


@app.get("/")
def read_root():
    return {"message": "CryptoVis Backend is running!"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
