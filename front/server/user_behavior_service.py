import json
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter(
    prefix="/api/user_behavior",
    tags=["user_behavior"]
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "public", "data", "user_behavior_sequences.json")

# In-memory cache
_user_behavior_cache = None

def get_user_behavior_data():
    global _user_behavior_cache
    if _user_behavior_cache is None:
        if not os.path.exists(DATA_PATH):
            raise FileNotFoundError(f"Data file not found at {DATA_PATH}")
        with open(DATA_PATH, 'r') as f:
            _user_behavior_cache = json.load(f)
    return _user_behavior_cache

class UserBehaviorRequest(BaseModel):
    users: List[str]

@router.post("/sequences")
def get_sequences(request: UserBehaviorRequest):
    try:
        data = get_user_behavior_data()
        result = {}
        for user in request.users:
            if user in data:
                result[user] = data[user]
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
