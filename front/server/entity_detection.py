
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

# --- Configuration ---
# Define path to the transfer CSV file
# Using absolute path resolution based on project structure
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSFER_CSV_PATH = os.path.join(BASE_DIR, "public", "ACT_transfer_before_2024-11-10.csv")
TRANSFER_STATS_PATH = os.path.join(BASE_DIR, "public", "transfer_network_stats.csv")

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

<<<<<<< Updated upstream
=======
class LinkRequest(BaseModel):
    """
    Request body for link analysis.
    """
    target_users: Optional[List[str]] = Field(None, description="List of user IDs to check.")
    time_range: Optional[Dict[str, str]] = Field(None, description="Start and end time.")
    threshold: int = Field(1, description="Minimum transactions.")

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

>>>>>>> Stashed changes
# --- Logic Implementation ---

def apply_detection_logic(user_data: Dict, rules: List[DetectionRule]) -> List[DetectedEntity]:
    # Placeholder for user-specific rules (like threshold)
    # This function processes ONE user at a time
    detected = []
    
    for rule in rules:
        if not rule.enabled:
            continue
            
        if rule.rule_type == "threshold":
            limit = rule.parameters.get("limit", 1000)
            metric = rule.parameters.get("metric", "balance")
            # Check if user exceeds limit...
            # mock result
            user_val = user_data.get("value", 0)
            if user_val > limit:
                detected.append(DetectedEntity(
                    entity_id=user_data.get("id", "unknown"),
                    confidence=0.95,
                    reason=f"Exceeded {metric} threshold limit of {limit}",
                    details={"actual_value": user_val}
                ))
                
    return detected

def process_transfer_network_rule(target_users: Optional[List[str]], time_range: Optional[Dict[str, str]], threshold: int) -> List[DetectedEntity]:
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
        # Since we have aggregated stats, precise time filtering is harder.
        # Approximation: Check if the pair's interaction period overlaps with the query range.
        # Strict Mode: Only count pairs where ALL transactions fall within range? No, we don't have individual timestamps.
        # Loose Mode: Check if [first, last] overlaps with [start, end].
        # Better: If time range is provided, we might need to fall back to raw data OR accept approximation.
        # User asked to use "stats" to check, implying we accept the limitation or assume stats are sufficient.
        # Let's filter pairs that have ANY activity within the range.
        
        if time_range:
            start_time = time_range.get("start")
            end_time = time_range.get("end")
            
            if start_time:
                # Keep pairs where last transaction is after start time
                df = df[df['last_transaction'] >= start_time]
            if end_time:
                # Keep pairs where first transaction is before end time
                df = df[df['first_transaction'] <= end_time]
        
        # 3. Filter by Target Users
        if target_users:
            target_set = set(target_users)
            # Both sender and receiver must be in the target list (closed world assumption for entity detection)
            # Or at least one? Usually entity detection looks for connections WITHIN a group.
            df = df[df['from_owner'].isin(target_set) & df['to_owner'].isin(target_set)]
        
        if df.empty:
            return []

        # 4. Build Graph from Stats
        G = nx.Graph()
        
        # Since stats are already grouped by (from, to), we just need to sum up weights if there are multiple entries (unlikely if unique pairs)
        # The stats file has directed pairs (from, to). We want an undirected graph.
        
        for _, row in df.iterrows():
            u, v = row['from_owner'], row['to_owner']
            count = row['transaction_count']
            
            if G.has_edge(u, v):
                G[u][v]['weight'] += count
            else:
                G.add_edge(u, v, weight=count)
        
        # 5. Apply Threshold and Find Components
        # Remove edges with weight <= threshold
        edges_to_remove = [(u, v) for u, v, d in G.edges(data=True) if d['weight'] <= threshold]
        G.remove_edges_from(edges_to_remove)
        
        # Find connected components
        components = list(nx.connected_components(G))
        
        detected_entities = []
        for i, comp in enumerate(components):
            if len(comp) > 1:
                members = list(comp)
                subgraph = G.subgraph(comp)
                total_txs = sum(d['weight'] for u, v, d in subgraph.edges(data=True))
                
                detected_entities.append(DetectedEntity(
                    entity_id=f"entity_group_{i}_{int(time.time())}",
                    confidence=0.8 + (0.02 * min(10, total_txs)),
                    reason=f"Network detection (stats): {len(members)} addresses connected via {int(total_txs)} transactions (threshold > {threshold})",
                    details={
                        "members": members,
                        "total_transactions": int(total_txs),
                        "member_count": len(members)
                    }
                ))
        
        return detected_entities

    except Exception as e:
        print(f"Error in transfer network detection (stats): {e}")
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
        other_rules = [r for r in request.rules if r.rule_type != "transfer-network" and r.enabled]
        
        # 1. Process Transfer Network Rules (Batch process)
        for rule in transfer_network_rules:
            threshold = rule.parameters.get("threshold", 5)
            # Use request.target_users if available, otherwise maybe use all users (careful!)
            # For this specific rule, we need a list of addresses to check interactions between.
            # If target_users is None, we might check ALL interactions in the CSV (computationally expensive but possible).
            # Let's assume target_users is provided or we default to top active ones (but here we just pass what we have)
            
            # If target_users is None, we might want to scan the whole file. 
            # For safety, let's proceed with request.target_users. If None, it means "all in file".
            
            network_entities = process_transfer_network_rule(
                request.target_users, 
                request.time_range, 
                threshold
            )
            all_detected.extend(network_entities)

        # 2. Process Per-User Rules (Threshold, etc.)
        # Mock data for demonstration (as before) if target_users provided, else mock some
        if request.target_users:
            mock_user_data = [{"id": uid, "value": hash(uid) % 2000} for uid in request.target_users]
        else:
            mock_user_data = [
                {"id": "user_A", "value": 500},
                {"id": "user_B", "value": 1500}, 
                {"id": "user_C", "value": 200}
            ]
            
        for user in mock_user_data:
            results = apply_detection_logic(user, other_rules)
            all_detected.extend(results)
            
        execution_time = time.time() - start_time
        
        # 3. Return Results
        return DetectionResponse(
            status="success",
            processed_count=len(request.target_users) if request.target_users else len(mock_user_data), # Approximation
            detected_entities=all_detected,
            metadata={
                "execution_time_seconds": execution_time,
                "rules_applied": len(request.rules)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rules/templates")
async def get_rule_templates():
    """
    Return available rule templates to help frontend build the UI.
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
<<<<<<< Updated upstream
=======

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
    try:
        links = process_transfer_network_links(
            request.target_users, 
            request.time_range, 
            request.threshold
        )
        return {"links": links}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
>>>>>>> Stashed changes
