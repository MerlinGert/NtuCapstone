
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

# Add data_processing directory to path to import scripts if needed
# BASE_DIR is the 'server' directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DATA_PROCESSING_DIR is the sibling directory 'data_processing'
DATA_PROCESSING_DIR = os.path.join(os.path.dirname(BASE_DIR), 'data_processing')
sys.path.append(DATA_PROCESSING_DIR)

app = FastAPI()

# Include routers
app.include_router(entity_detection.router)
app.include_router(snapshot_service.router)
app.include_router(manipulation_detect.router)
app.include_router(behavior_detection.router)
app.include_router(manipulation_detection.router)
app.include_router(fraudulent_activity_detection.router)

@app.get("/")
def read_root():
    return {"message": "CryptoVis Backend is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
