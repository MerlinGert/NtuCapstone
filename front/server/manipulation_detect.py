
import bisect
import pandas as pd
import numpy as np
import os
import json
import networkx as nx
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

router = APIRouter(
    prefix="/api/manipulation",
    tags=["manipulation"],
    responses={404: {"description": "Not found"}},
)

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "public", "ACT-24-11-10.csv")
TRANSFER_FILE = os.path.join(BASE_DIR, "public", "ACT_transfer_before_2024-11-10.csv")
RESULTS_DIR = os.path.join(BASE_DIR, "public", "wash_trading_results")

# Ensure results directory exists
if not os.path.exists(RESULTS_DIR):
    os.makedirs(RESULTS_DIR)

class ManipulationRequest(BaseModel):
    threshold: float = 10.0  # Default difference threshold for self-trading
    limit_traders: Optional[List[str]] = None  # Optional list of trader IDs to check
    check_entity_based: bool = False
    time_window: int = 60
    entities: Optional[List[List[str]]] = None

class SuspiciousTrader(BaseModel):
    trader_id: str
    total_bought: float
    total_sold: float
    diff: float
    transaction_count: int
    reasons: List[str] = []
    # Can add more structured info here if needed

class ManipulationResponse(BaseModel):
    suspicious_traders: List[SuspiciousTrader]
    count: int
    saved_file: Optional[str] = None

class WashTradingRequest(BaseModel):
    min_scc_size: int = 2
    net_threshold: float = 10.0

class WashTradingResponse(BaseModel):
    sccs: List[Dict[str, Any]]
    count: int
    saved_file: Optional[str] = None

@router.post("/detect", response_model=ManipulationResponse)
async def detect_manipulation(request: ManipulationRequest):
    print(f"Starting manipulation detection with params: threshold={request.threshold}, window={request.time_window}min, check_entity={request.check_entity_based}")
    
    if not os.path.exists(DATA_FILE):
        raise HTTPException(status_code=500, detail=f"Data file not found at {DATA_FILE}")
    
    try:
        # Read columns needed for both individual and entity detection
        # We always need block_time for entity detection if enabled, but let's read it anyway to be safe/consistent
        # Actually, reading block_time is only expensive if we parse it.
        usecols = ['trader_id', 'token_bought_symbol', 'token_sold_symbol', 'token_bought_amount', 'token_sold_amount', 'block_time']
        df = pd.read_csv(DATA_FILE, usecols=usecols)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading data file: {str(e)}")
    
    # 1. Filter by trader_id if limit provided
    if request.limit_traders:
        allowed_traders = set(request.limit_traders)
        df = df[df['trader_id'].isin(allowed_traders)]
    
    if df.empty:
        return ManipulationResponse(suspicious_traders=[], count=0)

    # 2. Pre-process amounts
    df['token_bought_amount'] = pd.to_numeric(df['token_bought_amount'], errors='coerce').fillna(0)
    df['token_sold_amount'] = pd.to_numeric(df['token_sold_amount'], errors='coerce').fillna(0)

    # 3. Identify ACT transactions
    # We create helper columns for ACT amounts
    df['bought_act'] = np.where(df['token_bought_symbol'] == 'ACT', df['token_bought_amount'], 0)
    df['sold_act'] = np.where(df['token_sold_symbol'] == 'ACT', df['token_sold_amount'], 0)
    
    # Ensure time is parsed for time-window detection
    try:
        df['block_time'] = pd.to_datetime(df['block_time'])
    except Exception as e:
        print(f"Time parsing error: {e}")
        # If time parsing fails, we can't do time-based detection properly
        return ManipulationResponse(suspicious_traders=[], count=0)

    suspicious_map: Dict[str, SuspiciousTrader] = {}

    # Calculate Global Stats for reporting (total bought/sold over all time)
    individual_stats = df.groupby('trader_id').agg({
        'bought_act': 'sum',
        'sold_act': 'sum',
        'token_bought_amount': 'count'
    }).rename(columns={'token_bought_amount': 'tx_count'})
    individual_stats['diff'] = (individual_stats['bought_act'] - individual_stats['sold_act']).abs()

    # --- Phase A: Individual Self-Trading Detection (Rolling Window) ---
    # Sort by time for rolling
    df_sorted = df.sort_values('block_time')
    
    # We use groupby().rolling() to detect windows for EACH trader
    # set_index('block_time') is required for time-based rolling
    # groupby('trader_id') ensures we roll within each trader's history
    
    indexer = df_sorted.set_index('block_time').groupby('trader_id')[['bought_act', 'sold_act']]
    rolling_ind = indexer.rolling(f"{request.time_window}min").sum()
    
    rolling_ind['diff'] = (rolling_ind['bought_act'] - rolling_ind['sold_act']).abs()
    rolling_ind['total'] = rolling_ind['bought_act'] + rolling_ind['sold_act']
    
    # Filter for suspicious windows
    matches_ind = rolling_ind[
        (rolling_ind['diff'] <= request.threshold) & 
        (rolling_ind['total'] > 0) & 
        (rolling_ind['bought_act'] > 0) & 
        (rolling_ind['sold_act'] > 0)
    ]
    
    if not matches_ind.empty:
        # Reset index to access trader_id and block_time
        # The index is (trader_id, block_time)
        matches_flat = matches_ind.reset_index()
        
        # Group by trader_id to find top windows for each detected trader
        for trader_id, group in matches_flat.groupby('trader_id'):
            tid = str(trader_id)
            
            # Get global stats for this trader
            global_bought = 0.0
            global_sold = 0.0
            global_diff = 0.0
            global_count = 0
            if tid in individual_stats.index:
                row = individual_stats.loc[tid]
                global_bought = float(row['bought_act'])
                global_sold = float(row['sold_act'])
                global_diff = float(row['diff'])
                global_count = int(row['tx_count'])
            
            # Pick top 3 windows by volume
            top_windows = group.sort_values('total', ascending=False).head(3)
            
            reasons = []
            for _, w_row in top_windows.iterrows():
                end_time = w_row['block_time']
                start_time = end_time - pd.Timedelta(minutes=request.time_window)
                w_bought = w_row['bought_act']
                w_sold = w_row['sold_act']
                w_diff = w_row['diff']
                
                r_str = (
                    f"Individual Self-Trading: "
                    f"Window {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}, "
                    f"Bought {w_bought:.2f}, Sold {w_sold:.2f}, Diff {w_diff:.2f}"
                )
                reasons.append(r_str)
                print(f"[DETECTED] {tid}: {r_str}")

            suspicious_map[tid] = SuspiciousTrader(
                trader_id=tid,
                total_bought=global_bought,
                total_sold=global_sold,
                diff=global_diff,
                transaction_count=global_count,
                reasons=reasons
            )

    # --- Phase B: Entity-Based Self-Trading Detection (Rolling Window) ---
    if request.check_entity_based and request.entities:
        # We can reuse df_sorted (already sorted by time)
        # But we need to index by block_time again if we didn't save it
        # Actually df_sorted is just sorted, index is original.
        
        # Prepare for entity rolling
        df_time_indexed = df_sorted.set_index('block_time')

        for i, entity_members in enumerate(request.entities):
            member_set = set(entity_members)
            mask = df_time_indexed['trader_id'].isin(member_set)
            
            if not mask.any():
                continue

            sub_df = df_time_indexed[mask]
            
            # Resample/Rolling
            window = f"{request.time_window}min"
            
            # Aggregate ACT volume for the WHOLE entity in the rolling window
            # We need to sum up all members' trades in the window
            # rolling() on dataframe sums columns.
            rolling = sub_df[['bought_act', 'sold_act']].rolling(window).sum()
            
            # Calculate diff and filter
            rolling['diff'] = (rolling['bought_act'] - rolling['sold_act']).abs()
            rolling['total'] = rolling['bought_act'] + rolling['sold_act']
            
            matches = rolling[
                (rolling['diff'] <= request.threshold) & 
                (rolling['total'] > 0) &
                (rolling['bought_act'] > 0) &
                (rolling['sold_act'] > 0)
            ]
            
            if not matches.empty:
                # Found suspicious window(s)
                # Let's pick the top 3 by volume to keep it concise but informative.
                sorted_matches = matches.sort_values('total', ascending=False).head(3)
                
                for idx, best_match in sorted_matches.iterrows():
                    end_time = idx
                    start_time = end_time - pd.Timedelta(minutes=request.time_window)
                    
                    reason_str = (
                        f"Entity Self-Trading (Group #{i+1}): "
                        f"Window {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}, "
                        f"Bought {best_match['bought_act']:.2f}, Sold {best_match['sold_act']:.2f}, "
                        f"Diff {best_match['diff']:.2f}"
                    )
                    print(f"[DETECTED] Entity Group #{i+1} Members {entity_members}: {reason_str}")
                    
                    # Tag all members
                    for member in entity_members:
                        if member in suspicious_map:
                            if reason_str not in suspicious_map[member].reasons:
                                suspicious_map[member].reasons.append(reason_str)
                        else:
                            # New suspect - populate with individual stats
                            ind_bought = 0.0
                            ind_sold = 0.0
                            ind_diff = 0.0
                            ind_count = 0
                            
                            if member in individual_stats.index:
                                row = individual_stats.loc[member]
                                ind_bought = float(row['bought_act'])
                                ind_sold = float(row['sold_act'])
                                ind_diff = float(row['diff'])
                                ind_count = int(row['tx_count'])
                            
                            suspicious_map[member] = SuspiciousTrader(
                                trader_id=member,
                                total_bought=ind_bought,
                                total_sold=ind_sold,
                                diff=ind_diff,
                                transaction_count=ind_count,
                                reasons=[reason_str]
                            )

    # Convert map to list
    results = list(suspicious_map.values())
    print(f"Detection completed. Found {len(results)} suspicious traders.")
    
    return ManipulationResponse(suspicious_traders=results, count=len(results))
