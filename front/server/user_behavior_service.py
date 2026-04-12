import json
import os
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/user_behavior", tags=["user_behavior"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# In-memory cache: dict[coin] -> data
_user_behavior_cache = {}


def get_data_dir(coin: str):
    if coin == "PNUT":
        return os.path.join(BASE_DIR, "public", "data2")
    return os.path.join(BASE_DIR, "public", "data")


def get_user_behavior_data(coin: str):
    global _user_behavior_cache
    if coin not in _user_behavior_cache:
        data_path = os.path.join(get_data_dir(coin), "user_behavior_sequences.json")
        if not os.path.exists(data_path):
            print(f"Warning: Data file not found at {data_path}")
            _user_behavior_cache[coin] = {}
        else:
            try:
                with open(data_path, "r") as f:
                    _user_behavior_cache[coin] = json.load(f)
            except Exception as e:
                print(f"Error loading user behavior sequences for {coin}: {e}")
                _user_behavior_cache[coin] = {}
    return _user_behavior_cache[coin]


class UserBehaviorRequest(BaseModel):
    users: List[str]
    coin: str = "ACT"


@router.post("/sequences")
def get_sequences(request: UserBehaviorRequest):
    try:
        data = get_user_behavior_data(request.coin)
        result = {}
        for user in request.users:
            if user in data:
                result[user] = data[user]
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
