from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import os
import time

router = APIRouter(
    prefix="/api/snapshot",
    tags=["snapshot"],
    responses={404: {"description": "Not found"}},
)

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOTS_FILE = os.path.join(BASE_DIR, "public", "processed", "transfers", "hourly_balance_snapshots.json")

# Global Cache
SNAPSHOTS_DATA = None

def load_snapshots():
    global SNAPSHOTS_DATA
    if SNAPSHOTS_DATA is None:
        if not os.path.exists(SNAPSHOTS_FILE):
            print(f"Error: Snapshot file not found at {SNAPSHOTS_FILE}")
            return []
        print(f"Loading snapshots from {SNAPSHOTS_FILE}...")
        try:
            with open(SNAPSHOTS_FILE, 'r') as f:
                SNAPSHOTS_DATA = json.load(f)
            print(f"Loaded {len(SNAPSHOTS_DATA)} snapshots.")
        except Exception as e:
            print(f"Error loading snapshots: {e}")
            SNAPSHOTS_DATA = []
    return SNAPSHOTS_DATA

class SnapshotRequest(BaseModel):
    time: Optional[str] = None
    threshold: float = 0.5 # 0.0 to 1.0

@router.get("/times")
async def get_snapshot_times():
    data = load_snapshots()
    times = [s.get("time") for s in data]
    return {"times": times}

@router.post("/process")
async def process_snapshot(request: SnapshotRequest):
    data = load_snapshots()
    if not data:
        raise HTTPException(status_code=500, detail="Snapshot data not available")

    # Find snapshot
    target_snapshot = None
    if request.time:
        for s in data:
            if s.get("time") == request.time:
                target_snapshot = s
                break
    else:
        # Default to last one
        if data:
            target_snapshot = data[-1]
    
    if not target_snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found for given time")

    # Process Logic
    # Calculate Total Supply
    # Assume total supply is sum of all balances (users + contracts + exchanges)
    # Or maybe just users? Let's check the structure again.
    # The processed file had 'total_supply' in statistics.
    # We will sum everything up.
    
    balances = target_snapshot.get("balances", {})
    users = balances.get("users", {})
    contracts = balances.get("contracts", {})
    exchanges = balances.get("exchanges", {})
    
    total_users = sum(users.values())
    total_contracts = sum(contracts.values())
    total_exchanges = sum(exchanges.values())
    
    total_supply = total_users + total_contracts + total_exchanges
    
    # Target Active User Supply based on Threshold
    # e.g., Threshold 0.5 means we want top users holding 50% of TOTAL SUPPLY
    target_supply = total_supply * request.threshold
    
    # Sort Users
    sorted_users = sorted(users.items(), key=lambda item: item[1], reverse=True)
    
    processed_users = {}
    current_sum = 0
    user_count = 0
    
    for user, balance in sorted_users:
        processed_users[user] = balance
        current_sum += balance
        user_count += 1
        if current_sum >= target_supply:
            break
            
    # Calculate Others
    # Others = Total User Balance - Sum of Processed Users
    others_balance = total_users - current_sum
    processed_users["Others"] = others_balance
    
    # Construct Response matching processed_latest_snapshot format
    response = {
        "time": target_snapshot.get("time"),
        "statistics": {
            "threshold_percentage": request.threshold * 100,
            "total_supply": total_supply,
            "users": {
                "count": len(users),
                "processed_count": user_count,
                "total_balance": total_users,
                "top_users_balance": current_sum,
                "top_users_percentage": (current_sum / total_supply) * 100 if total_supply > 0 else 0,
                "others_balance": others_balance,
                "others_percentage": (others_balance / total_supply) * 100 if total_supply > 0 else 0,
                "percentage": (total_users / total_supply) * 100 if total_supply > 0 else 0
            },
            "contracts": {
                "count": len(contracts),
                "total_balance": total_contracts,
                "percentage": (total_contracts / total_supply) * 100 if total_supply > 0 else 0
            },
            "exchanges": {
                "count": len(exchanges),
                "total_balance": total_exchanges,
                "percentage": (total_exchanges / total_supply) * 100 if total_supply > 0 else 0
            }
        },
        "balances": {
            "users": processed_users
        }
    }
    
    return response
