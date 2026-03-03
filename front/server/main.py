
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import sys
import os
import json
import uvicorn
import entity_detection
import snapshot_service

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

class AnalyzeRequest(BaseModel):
    user_id: str
    params: dict = {}

@app.get("/")
def read_root():
    return {"message": "CryptoVis Backend is running!"}

@app.post("/api/analyze")
def analyze_user(request: AnalyzeRequest):
    """
    Example endpoint to process user data.
    You can call your data processing scripts here.
    """
    try:
        user_id = request.user_id
        # Example: Just echo back for now, or load processed data
        # In a real scenario, you might call:
        # result = process_user_behavior.analyze(user_id, request.params)
        
        # Simulating processing...
        result = {
            "user_id": user_id,
            "status": "processed",
            "analysis": {
                "score": 0.85,
                "segments": ["active", "trader"],
                "summary": f"Analysis for user {user_id} complete based on params {request.params}"
            }
        }
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
