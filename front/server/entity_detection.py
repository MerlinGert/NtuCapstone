
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import time
import pandas as pd
import networkx as nx
import os
from similarity_detection import (
    rule3_similar_trading_sequence,
    rule4_similar_balance_sequence,
    rule5_similar_earning_sequence,
)
import similarity_detection

# Create a router instance
router = APIRouter(
    prefix="/api/entity",
    tags=["entity_detection"],
    responses={404: {"description": "Not found"}},
)

import json

# --- Configuration ---
# Define path to the transfer CSV file
# Using absolute path resolution based on project structure
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSFER_CSV_PATH = os.path.join(BASE_DIR, "public", "ACT_transfer_before_2024-11-10.csv")
TRANSFER_STATS_PATH = os.path.join(BASE_DIR, "public", "transfer_network_stats.csv")
EXCHANGE_WALLETS_PATH = os.path.join(BASE_DIR, "public", "exchange_wallets_list.json")
ACCOUNT_LABELS_PATH = os.path.join(BASE_DIR, "public", "processed", "transfers", "account_labels.json")

def get_blacklist_addresses() -> set:
    """
    Returns a set of addresses to exclude from funding source checks (Exchanges + Contracts).
    """
    blacklist = set()
    
    # 2. Load Account Labels (Contracts & Exchanges)
    if os.path.exists(ACCOUNT_LABELS_PATH):
        try:
            with open(ACCOUNT_LABELS_PATH, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for entry in data:
                        # Exclude contract/exchange addresses AND their owners if labeled as such
                        if entry.get("label") in ["contract", "exchange"]:
                            if "address" in entry:
                                blacklist.add(entry["address"])
                            if "owner" in entry:
                                blacklist.add(entry["owner"])
        except Exception as e:
            print(f"Error loading account labels: {e}")
            
    return blacklist

# --- Data Models ---

class DetectionRule(BaseModel):
    """
    Defines a single rule for entity detection.
    """
    rule_type: str = Field(..., description="Type of rule (e.g., 'threshold', 'pattern', 'frequency')")
    parameters: Dict[str, Any] = Field(..., description="Parameters specific to the rule type")
    enabled: bool = True

class DetectionRequest(BaseModel):
    """
    Request body for entity detection.
    """
    target_users: Optional[List[str]] = Field(None, description="List of user IDs to check. If None, check all.")
    time_range: Optional[Dict[str, str]] = Field(None, description="Start and end time for analysis")
    rules: List[DetectionRule] = Field(..., description="List of detection rules to apply")

class DetectedEntity(BaseModel):
    """
    Represents a detected entity or anomaly.
    """
    entity_id: str
    confidence: float
    reason: str
    details: Dict[str, Any]

class DetectionResponse(BaseModel):
    """
    Response body containing detection results.
    """
    status: str
    processed_count: int
    detected_entities: List[DetectedEntity]
    metadata: Dict[str, Any]

class LinkRequest(BaseModel):
    """
    Request body for link analysis.
    """
    target_users: Optional[List[str]] = Field(None, description="List of user IDs to check.")
    time_range: Optional[Dict[str, str]] = Field(None, description="Start and end time.")
    threshold: int = Field(1, description="Minimum transactions.")
k-line

class LinkResponse(BaseModel):
    """
    Response body containing link analysis results.
    """
    links: List[Dict[str, Any]]

class SimilarityRequest(BaseModel):
    """
    Request body for similarity-based detection.
    """
    target_users: Optional[List[str]] = Field(None, description="List of user IDs to check.")
    time_range: Optional[Dict[str, str]] = Field(None, description="Start and end time.")
    rule_type: str = Field(..., description="Rule type: 'similar_trading_sequence' | 'similar_balance_sequence' | 'similar_earning_sequence'")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Rule-specific parameters")

class SimilarityResponse(BaseModel):
    """
    Response body for similarity detection results.
    """
    status: str
    rule_type: str
    pair_count: int
    pairs: List[Dict[str, Any]]
    metadata: Dict[str, Any]

Stashed changes
# --- Logic Implementation ---
=======
main

class LinkResponse(BaseModel):
    """
    Response body containing link analysis results.
    """
    links: List[Dict[str, Any]]

# --- Logic Implementation ---

def process_transfer_network_rule(target_users: Optional[List[str]], time_range: Optional[Dict[str, str]], threshold: int, check_funding_source: bool = False) -> List[DetectedEntity]:
    """
    Implements transfer-network-based entity detection using pre-aggregated statistics.
    """
    if not os.path.exists(TRANSFER_STATS_PATH):
        print(f"Warning: Transfer stats file not found at {TRANSFER_STATS_PATH}. Please run precompute_transfer_stats.py first.")
        return []

    try:
        # 1. Load Pre-aggregated Stats
        # Columns: from_owner, to_owner, transaction_count, first_transaction, last_transaction
        df = pd.read_csv(TRANSFER_STATS_PATH)
        
        # 2. Filter by Time Range (if provided)
        if time_range:
            start_time = time_range.get("start")
            end_time = time_range.get("end")
            
            if start_time:
                df = df[df['last_transaction'] >= start_time]
            if end_time:
                df = df[df['first_transaction'] <= end_time]
        
        # 3. Build Graph
        G = nx.Graph()
        
        # --- Transfer Threshold Logic ---
        # Filter for connections within target_users (if provided)
        df_transfer = df.copy()
        if target_users:
            target_set = set(target_users)
            df_transfer = df_transfer[df_transfer['from_owner'].isin(target_set) & df_transfer['to_owner'].isin(target_set)]
        
        for _, row in df_transfer.iterrows():
            if row['transaction_count'] > threshold:
                u, v = row['from_owner'], row['to_owner']
                if G.has_edge(u, v):
                    G[u][v]['transfer_count'] = G[u][v].get('transfer_count', 0) + row['transaction_count']
                else:
                    G.add_edge(u, v, transfer_count=row['transaction_count'], reasons=["High frequency transfers"])

        # --- Same Funding Source Logic ---
        if check_funding_source and target_users:
            # We need to find the "first" incoming transaction for each target user
            # We look at the ENTIRE dataset (df) where to_owner is in target_users
            # We do NOT restrict from_owner to target_users here, because the funding source might be external
            
            funding_map = {} # user -> funding_source
            
            # Filter rows where receiver is a target user
            df_funding = df[df['to_owner'].isin(set(target_users))].sort_values('first_transaction')
            
            # Load blacklist
            blacklist = get_blacklist_addresses()
            
            # Filter out blacklisted sources
            if blacklist:
                df_funding = df_funding[~df_funding['from_owner'].isin(blacklist)]

            # Group by receiver and take the first one
            # drop_duplicates(subset=['to_owner'], keep='first') works because we sorted by time
            first_txs = df_funding.drop_duplicates(subset=['to_owner'], keep='first')
            
            for _, row in first_txs.iterrows():
                funding_map[row['to_owner']] = row['from_owner']
            
            # Group users by funding source
            source_groups = {}
            for user, source in funding_map.items():
                if source not in source_groups:
                    source_groups[source] = []
                source_groups[source].append(user)
            
            # 1. Add edges for co-funded groups (siblings)
            for source, users in source_groups.items():
                if len(users) > 1:
                    reason_str = f"Same funding source ({source})"
                    
                    # Connect everyone to the first one
                    hub = users[0]
                    for i in range(1, len(users)):
                        peer = users[i]
                        if G.has_edge(hub, peer):
                            if "Same funding source" not in str(G[hub][peer].get('reasons', [])):
                                reasons = G[hub][peer].get('reasons', [])
                                if isinstance(reasons, list):
                                    reasons.append(reason_str)
                                else:
                                    # Handle legacy or string case
                                    reasons = [reasons, reason_str]
                                G[hub][peer]['reasons'] = reasons
                        else:
                            G.add_edge(hub, peer, reasons=[reason_str])

            # 2. Add edges for direct funding (parent-child)
            # If the funding source itself is one of the target users, connect them.
            target_set = set(target_users)
            for user, source in funding_map.items():
                if source in target_set:
                    # 'source' funded 'user', and both are in target list
                    reason_str = f"Direct funding ({source} -> {user})"
                    
                    if G.has_edge(source, user):
                         reasons = G[source][user].get('reasons', [])
                         # Avoid duplicate reasons roughly
                         if not any("Direct funding" in r for r in reasons):
                             if isinstance(reasons, list):
                                 reasons.append(reason_str)
                             else:
                                 reasons = [reasons, reason_str]
                             G[source][user]['reasons'] = reasons
                    else:
                        G.add_edge(source, user, reasons=[reason_str])

        # 4. Find Components
        components = list(nx.connected_components(G))
        
        detected_entities = []
        for i, comp in enumerate(components):
            if len(comp) > 1:
                members = list(comp)
                subgraph = G.subgraph(comp)
                
                # Collect reasons
                reasons_set = set()
                total_txs = 0
                
                for u, v, d in subgraph.edges(data=True):
                    total_txs += d.get('transfer_count', 0)
                    edge_reasons = d.get('reasons', [])
                    for r in edge_reasons:
                        reasons_set.add(r)
                
                # Format reasons point by point
                formatted_reasons = []
                for idx, r in enumerate(sorted(reasons_set), 1):
                    formatted_reasons.append(f"{idx}. {r}")
                
                reason_text = "\n".join(formatted_reasons) if formatted_reasons else "Connected via network analysis"
                
                detected_entities.append(DetectedEntity(
                    entity_id=f"entity_group_{i}_{int(time.time())}",
                    confidence=0.8, # Simplified confidence
                    reason=reason_text,
                    details={
                        "members": members,
                        "total_transactions": int(total_txs),
                        "member_count": len(members),
                        "raw_reasons": list(reasons_set)
                    }
                ))
        
        return detected_entities

    except Exception as e:
        print(f"Error in transfer network detection (stats): {e}")
        import traceback
        traceback.print_exc()
        return []

# --- Endpoints ---

@router.post("/detect", response_model=DetectionResponse)
async def detect_entities(request: DetectionRequest):
    """
    Run entity detection based on provided rules and parameters.
    """
    try:
        start_time = time.time()
        
        all_detected = []
        
        # Separate rules
        transfer_network_rules = [r for r in request.rules if r.rule_type == "transfer-network" and r.enabled]
        
        # 1. Process Transfer Network Rules (Batch process)
        for rule in transfer_network_rules:
            threshold = rule.parameters.get("threshold", 5)
            check_funding_source = rule.parameters.get("check_funding_source", False)
            # Use request.target_users if available
            
            network_entities = process_transfer_network_rule(
                request.target_users, 
                request.time_range, 
                threshold,
                check_funding_source
            )
            all_detected.extend(network_entities)

        execution_time = time.time() - start_time
        
        # 2. Return Results
        return DetectionResponse(
            status="success",
            processed_count=len(request.target_users) if request.target_users else 0,
            detected_entities=all_detected,
            metadata={
                "execution_time_seconds": execution_time,
                "rules_applied": len(request.rules)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def process_transfer_network_links(target_users: Optional[List[str]], time_range: Optional[Dict[str, str]], threshold: int) -> List[Dict[str, Any]]:
    if not os.path.exists(TRANSFER_STATS_PATH):
        return []

    try:
        # Load Pre-aggregated Stats
        df = pd.read_csv(TRANSFER_STATS_PATH)
        
        # Filter by Time Range
        if time_range:
            start_time = time_range.get("start")
            end_time = time_range.get("end")
            
            if start_time:
                df = df[df['last_transaction'] >= start_time]
            if end_time:
                df = df[df['first_transaction'] <= end_time]
        
        # Filter by Target Users
        if target_users:
            target_set = set(target_users)
            df = df[df['from_owner'].isin(target_set) & df['to_owner'].isin(target_set)]
        
        if df.empty:
            return []

        # Group by pair (undirected) and sum weights
        G = nx.Graph()
        for _, row in df.iterrows():
            u, v = row['from_owner'], row['to_owner']
            count = row['transaction_count']
            
            if G.has_edge(u, v):
                G[u][v]['weight'] += count
            else:
                G.add_edge(u, v, weight=count)
        
        links = []
        for u, v, d in G.edges(data=True):
            if d['weight'] >= threshold:
                links.append({
                    "source": u,
                    "target": v,
                    "weight": d['weight']
                })
        
        return links

    except Exception as e:
        print(f"Error in transfer network links: {e}")
        return []

@router.post("/links", response_model=LinkResponse)
async def get_links(request: LinkRequest):
    """
    Get links (edges) based on transfer network rules.
    """
    return {
        "templates": [
            {
                "type": "threshold",
                "description": "Detects users exceeding a specific value",
                "default_params": {"metric": "balance", "limit": 1000, "operator": ">"}
            },
            {
                "type": "frequency",
                "description": "Detects high frequency transactions",
                "default_params": {"window_seconds": 60, "max_count": 10}
            },
            {
                "type": "pattern",
                "description": "Detects specific interaction patterns (e.g., wash trading)",
                "default_params": {"pattern_type": "cycle", "min_depth": 3}
            },
            {
                "type": "similar_trading_sequence",
                "description": "Detects addresses with similar buy/sell action sequences",
                "default_params": {
                    "direction_mode": "same_side_only",
                    "sequence_representation": "action_only",
                    "min_contiguous_length": 3,
                    "amount_similarity": 0.8,
                    "price_similarity": 0.8,
                }
            },
            {
                "type": "similar_balance_sequence",
                "description": "Detects addresses with similar balance curves (Pearson correlation)",
                "default_params": {
                    "balance_axis": "time_grid",
                    "tx_step": 5,
                    "time_bin": "1h",
                    "similarity": 0.8,
                    "topk_neighbors": 5,
                }
            },
            {
                "type": "similar_earning_sequence",
                "description": "Detects addresses with similar earning/equity curves",
                "default_params": {
                    "earning_axis": "time_grid",
                    "tx_step": 5,
                    "time_bin": "1h",
                    "similarity": 0.8,
                    "topk_neighbors": 5,
                }
            },
        ]
    }
    try:
        links = process_transfer_network_links(
            request.target_users, 
            request.time_range, 
            request.threshold
        )
        return {"links": links}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 k-line

@router.post("/similarity", response_model=SimilarityResponse)
async def detect_similarity(request: SimilarityRequest):
    """
    Run behavior-similarity-based entity detection.
    Supports: similar_trading_sequence, similar_balance_sequence, similar_earning_sequence
    """
    try:
        start_time_t = time.time()
        params = request.parameters

        if request.rule_type == "similar_trading_sequence":
            pairs = rule3_similar_trading_sequence(
                target_users=request.target_users,
                time_window=request.time_range,
                direction_mode=params.get("direction_mode", "same_side_only"),
                sequence_representation=params.get("sequence_representation", "action_only"),
                min_contiguous_length=params.get("min_contiguous_length", 3),
                amount_similarity=params.get("amount_similarity", 0.8),
                price_similarity=params.get("price_similarity", 0.8),
            )
        elif request.rule_type == "similar_balance_sequence":
            pairs = rule4_similar_balance_sequence(
                target_users=request.target_users,
                time_window=request.time_range,
                balance_axis=params.get("balance_axis", "time_grid"),
                tx_step=params.get("tx_step", 5),
                time_bin=params.get("time_bin", "1h"),
                similarity=params.get("similarity", 0.8),
                topk_neighbors=params.get("topk_neighbors", 5),
            )
        elif request.rule_type == "similar_earning_sequence":
            pairs = rule5_similar_earning_sequence(
                target_users=request.target_users,
                time_window=request.time_range,
                earning_axis=params.get("earning_axis", "time_grid"),
                tx_step=params.get("tx_step", 5),
                time_bin=params.get("time_bin", "1h"),
                similarity=params.get("similarity", 0.8),
                topk_neighbors=params.get("topk_neighbors", 5),
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown rule_type: {request.rule_type}")

        execution_time = time.time() - start_time_t

        return SimilarityResponse(
            status="success",
            rule_type=request.rule_type,
            pair_count=len(pairs),
            pairs=pairs,
            metadata={
                "execution_time_seconds": round(execution_time, 3),
                "parameters": params,
                "note": (
                    f"User cap: auto={similarity_detection.MAX_USERS_RULE3_AUTO}, "
                    f"explicit={similarity_detection.MAX_USERS_RULE3}; "
                    f"seq_cap={similarity_detection.MAX_SEQ_LEN_RULE3}; "
                    f"pair_cap={similarity_detection.MAX_CANDIDATE_PAIRS} "
                    f"(numpy LCCS active for action_only)"
                ) if request.rule_type == "similar_trading_sequence" else None,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 Stashed changes
=======
 main
