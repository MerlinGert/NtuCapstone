from networkx import read_multiline_adjlist
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

import pandas as pd

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOTS_FILE = os.path.join(BASE_DIR, "public", "processed", "transfers", "hourly_balance_snapshots.json")
TRANSFER_STATS_PATH = os.path.join(BASE_DIR, "public", "transfer_network_stats.csv")

# Global Cache
SNAPSHOTS_DATA = None
TRANSFER_STATS_DF = None

def load_transfer_stats():
    global TRANSFER_STATS_DF
    if TRANSFER_STATS_DF is None:
        if os.path.exists(TRANSFER_STATS_PATH):
             print(f"Loading transfer stats from {TRANSFER_STATS_PATH}...")
             try:
                 TRANSFER_STATS_DF = pd.read_csv(TRANSFER_STATS_PATH)
                 print(f"Loaded transfer stats with {len(TRANSFER_STATS_DF)} rows.")
             except Exception as e:
                 print(f"Error loading transfer stats: {e}")
                 TRANSFER_STATS_DF = pd.DataFrame()
        else:
            print(f"Warning: Transfer stats file not found at {TRANSFER_STATS_PATH}")
            TRANSFER_STATS_DF = pd.DataFrame()
    return TRANSFER_STATS_DF

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
    related_user_threshold: float = 0.2 # Threshold factor for related users (relative to min processed balance)

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
    # e.g., Threshold 0.5 means we want top users holding 50% of TOTAL USER BALANCE
    target_supply = total_users * request.threshold
    
    # Sort Users
    sorted_users = sorted(users.items(), key=lambda item: item[1], reverse=True)
    
    processed_users = {}
    related_users = {}
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
    
    # Identify Related Users
    # Find users who have transfers with processed_users (excluding "Others")
    # AND are in sorted_users (so they have a balance)
    # AND are NOT already in processed_users
    
    processed_user_set = set(processed_users.keys())
    if "Others" in processed_user_set:
        processed_user_set.remove("Others")
        
    df = load_transfer_stats()
    
    if not df.empty and processed_user_set:
        # Filter transfers involving processed users
        # AND first_transaction <= snapshot_time
        snapshot_time = target_snapshot.get("time")
        
        mask = (df['from_owner'].isin(processed_user_set) | df['to_owner'].isin(processed_user_set))
        if snapshot_time:
             mask = mask & (df['first_transaction'] <= snapshot_time)
             
        related_df = df[mask]
        
        # Collect all related owners
        potential_related = set(related_df['from_owner'].unique()) | set(related_df['to_owner'].unique())
        
        # Filter: Must be in sorted_users (have balance) AND not in processed_users
        all_users_with_balance = set(users.keys())
        
        final_related_users = potential_related.intersection(all_users_with_balance) - processed_user_set
        
        # Determine minimum balance threshold from processed users
        processed_balances = [users[u] for u in processed_user_set if u in users]
        min_processed_balance = min(processed_balances) if processed_balances else 0
        balance_threshold = min_processed_balance * request.related_user_threshold
        
        print(f"Filtering related users: min_processed_balance={min_processed_balance}, factor={request.related_user_threshold}, threshold={balance_threshold}")
        
        filtered_count = 0
        for user in final_related_users:
            balance = users.get(user, 0)
            if balance >= balance_threshold:
                related_users[user] = balance
            else:
                filtered_count += 1
            
        print(f"Identified {len(related_users)} related users (filtered {filtered_count} due to low balance).")

    # Construct Response matching processed_latest_snapshot format
    all_times = [s.get("time") for s in data]
    response = {
        "time": target_snapshot.get("time"),
        "all_times": all_times,
        "statistics": {
            "threshold_percentage": request.threshold * 100,
            "total_supply": total_supply,
            "users": {
                "count": len(users),
                "processed_count": user_count,
                "total_balance": total_users,
                "top_users_balance": current_sum,
                "top_users_percentage": (current_sum / total_users) * 100 if total_users > 0 else 0,
                "others_balance": others_balance,
                "others_percentage": (others_balance / total_users) * 100 if total_users > 0 else 0,
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
            "users": processed_users,
            "related_users": related_users
        }
    }
    
    return response
