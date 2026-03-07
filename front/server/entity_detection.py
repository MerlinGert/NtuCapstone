
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import time
import pandas as pd
import networkx as nx
import os

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

# --- Logic Implementation ---

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
        
        # 1. Process Transfer Network Rules (Batch process)
        for rule in transfer_network_rules:
            threshold = rule.parameters.get("threshold", 5)
            # Use request.target_users if available
            
            network_entities = process_transfer_network_rule(
                request.target_users, 
                request.time_range, 
                threshold
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
    try:
        links = process_transfer_network_links(
            request.target_users, 
            request.time_range, 
            request.threshold
        )
        return {"links": links}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
