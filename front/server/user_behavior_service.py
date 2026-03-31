import json
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import token_config

router = APIRouter(
    prefix="/api/user_behavior",
    tags=["user_behavior"]
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Token-keyed in-memory cache
_user_behavior_cache = {}

def get_user_behavior_data(token: str = "ACT"):
    if token not in _user_behavior_cache:
        data_path = token_config.get_data_path(token, "user_behavior_sequences.json")
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Data file not found at {data_path}")
        with open(data_path, 'r') as f:
            _user_behavior_cache[token] = json.load(f)
    return _user_behavior_cache[token]

class UserBehaviorRequest(BaseModel):
    users: List[str]
    token: str = "ACT"

@router.post("/sequences")
def get_sequences(request: UserBehaviorRequest):
    try:
        data = get_user_behavior_data(request.token)
        result = {}
        for user in request.users:
            if user in data:
                result[user] = data[user]
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
