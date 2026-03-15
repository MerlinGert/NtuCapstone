
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import time
import pandas as pd
import networkx as nx
import os
import behavior_detection
from behavior_detection import (
    process_rule3, process_rule4, process_rule5, edges_to_groups,
    TradingSequenceParams, BalanceSequenceParams, EarningSequenceParams
)

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
    reason: List[str]
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

def build_transfer_network_graph(target_users: Optional[List[str]], time_range: Optional[Dict[str, str]], threshold: int, check_funding_source: bool = False, volume_threshold: float = 0, check_same_sender: bool = False, check_same_recipient: bool = False, enable_tx_count: bool = True, enable_tx_volume: bool = True) -> nx.Graph:
    """
    Builds a NetworkX graph based on transfer network rules.
    """
    if not os.path.exists(TRANSFER_STATS_PATH):
        print(f"Warning: Transfer stats file not found at {TRANSFER_STATS_PATH}. Please run precompute_transfer_stats.py first.")
        return nx.Graph()

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
            tx_count = row['transaction_count']
            # Get volume, default to 0 if column missing
            volume = row.get('total_volume', 0)
            
            # Check thresholds (OR logic: either high frequency OR high volume)
            is_high_frequency = enable_tx_count and tx_count >= threshold
            is_high_volume = enable_tx_volume and volume_threshold > 0 and volume >= volume_threshold
            
            if is_high_frequency or is_high_volume:
                u, v = row['from_owner'], row['to_owner']
                
                reasons = []
                if is_high_frequency:
                    reasons.append(f"High frequency transfers ({tx_count} txs)")
                if is_high_volume:
                    reasons.append(f"High volume transfers ({volume:.2f} tokens)")
                
                if G.has_edge(u, v):
                    G[u][v]['transfer_count'] = G[u][v].get('transfer_count', 0) + tx_count
                    
                    # Merge reasons
                    current_reasons = G[u][v].get('reasons', [])
                    if isinstance(current_reasons, list):
                        # Avoid duplicates
                        for r in reasons:
                            if r not in current_reasons:
                                current_reasons.append(r)
                        G[u][v]['reasons'] = current_reasons
                else:
                    G.add_edge(u, v, transfer_count=tx_count, reasons=reasons)

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

            # Add edges for direct funding (parent-child)
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

        # --- Same Sender Logic ---
        if check_same_sender and target_users:
            # Check if target users received transfers from the SAME sender within the time range
            # 1. Filter: to_owner in target_users
            target_set = set(target_users)
            df_recv = df[df['to_owner'].isin(target_set)]
            
            # 2. Filter blacklist (senders)
            blacklist = get_blacklist_addresses()
            if blacklist:
                df_recv = df_recv[~df_recv['from_owner'].isin(blacklist)]
            
            # 3. Group by sender
            # sender -> list of recipients (who are in target_users)
            sender_groups = df_recv.groupby('from_owner')['to_owner'].apply(list).to_dict()
            
            for sender, recipients in sender_groups.items():
                # Remove duplicates (if one user received multiple txs from same sender)
                unique_recipients = list(set(recipients))
                
                if len(unique_recipients) > 1:
                    reason_str = f"Same sender ({sender})"
                    
                    # Link all recipients
                    # Similar to funding source: connect first one to others
                    hub = unique_recipients[0]
                    for i in range(1, len(unique_recipients)):
                        peer = unique_recipients[i]
                        if G.has_edge(hub, peer):
                            reasons = G[hub][peer].get('reasons', [])
                            if isinstance(reasons, list):
                                # Check duplicate reason
                                already_exists = any(r.startswith(f"Same sender ({sender})") for r in reasons)
                                if not already_exists:
                                    reasons.append(reason_str)
                                    G[hub][peer]['reasons'] = reasons
                        else:
                            G.add_edge(hub, peer, reasons=[reason_str])

        # --- Same Recipient Logic ---
        if check_same_recipient and target_users:
            # Check if target users sent transfers to the SAME recipient within the time range
            # 1. Filter: from_owner in target_users
            target_set = set(target_users)
            df_sent = df[df['from_owner'].isin(target_set)]
            
            # 2. Filter blacklist (recipients)
            blacklist = get_blacklist_addresses()
            if blacklist:
                df_sent = df_sent[~df_sent['to_owner'].isin(blacklist)]
                
            # 3. Group by recipient
            # recipient -> list of senders (who are in target_users)
            recipient_groups = df_sent.groupby('to_owner')['from_owner'].apply(list).to_dict()
            
            for recipient, senders in recipient_groups.items():
                unique_senders = list(set(senders))
                
                if len(unique_senders) > 1:
                    reason_str = f"Same recipient ({recipient})"
                    
                    # Link all senders
                    hub = unique_senders[0]
                    for i in range(1, len(unique_senders)):
                        peer = unique_senders[i]
                        if G.has_edge(hub, peer):
                            reasons = G[hub][peer].get('reasons', [])
                            if isinstance(reasons, list):
                                already_exists = any(r.startswith(f"Same recipient ({recipient})") for r in reasons)
                                if not already_exists:
                                    reasons.append(reason_str)
                                    G[hub][peer]['reasons'] = reasons
                        else:
                            G.add_edge(hub, peer, reasons=[reason_str])
        
        return G

    except Exception as e:
        print(f"Error in transfer network graph build: {e}")
        import traceback
        traceback.print_exc()
        return nx.Graph()


def process_transfer_network_rule(target_users: Optional[List[str]], time_range: Optional[Dict[str, str]], threshold: int, check_funding_source: bool = False, volume_threshold: float = 0, check_same_sender: bool = False, check_same_recipient: bool = False, enable_tx_count: bool = True, enable_tx_volume: bool = True) -> List[DetectedEntity]:
    """
    Implements transfer-network-based entity detection using pre-aggregated statistics.
    """
    try:
        G = build_transfer_network_graph(target_users, time_range, threshold, check_funding_source, volume_threshold, check_same_sender, check_same_recipient, enable_tx_count, enable_tx_volume)

        # Find connected components and return detected entities
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
                
                # Format reasons
                final_reasons = sorted(list(reasons_set)) if reasons_set else ["Connected via network analysis"]
                
                detected_entities.append(DetectedEntity(
                    entity_id=f"entity_group_{i}_{int(time.time())}",
                    confidence=0.8, # Simplified confidence
                    reason=final_reasons,
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


def build_entity_graph(request: DetectionRequest) -> nx.Graph:
    """
    Builds the master graph based on all enabled rules in the request.
    """
    start_time = time.time()
    
    # Main graph for merging
    G_master = nx.Graph()
    
    # Separate rules
    transfer_network_rules = [r for r in request.rules if r.rule_type == "transfer-network" and r.enabled]
    behavior_similarity_rules = [r for r in request.rules if r.rule_type == "behavior-similarity" and r.enabled]
    
    # 1. Process Transfer Network Rules
    for rule in transfer_network_rules:
        threshold = rule.parameters.get("threshold", 5)
        check_funding_source = rule.parameters.get("check_funding_source", False)
        volume_threshold = rule.parameters.get("volume_threshold", 0)
        check_same_sender = rule.parameters.get("check_same_sender", False)
        check_same_recipient = rule.parameters.get("check_same_recipient", False)
        enable_tx_count = rule.parameters.get("enable_tx_count", True)
        enable_tx_volume = rule.parameters.get("enable_tx_volume", True)
        
        G_rule = build_transfer_network_graph(
            request.target_users, 
            request.time_range, 
            threshold,
            check_funding_source,
            volume_threshold,
            check_same_sender,
            check_same_recipient,
            enable_tx_count,
            enable_tx_volume
        )
        
        # Merge into G_master
        for u, v, d in G_rule.edges(data=True):
            if G_master.has_edge(u, v):
                # Merge attributes
                G_master[u][v]['transfer_count'] = G_master[u][v].get('transfer_count', 0) + d.get('transfer_count', 0)
                # Merge reasons
                master_reasons = G_master[u][v].get('reasons', [])
                new_reasons = d.get('reasons', [])
                for r in new_reasons:
                    if r not in master_reasons:
                        master_reasons.append(r)
                G_master[u][v]['reasons'] = master_reasons
            else:
                G_master.add_edge(u, v, **d)

    # 2. Process Behavior Similarity Rules
    current_edges = []
    for rule in behavior_similarity_rules:
        # Extract params
        params = rule.parameters
        time_window = params.get("time_window", 1.0)
        enable_rule3 = params.get("enable_rule3", True)
        enable_rule4 = params.get("enable_rule4", True)
        enable_rule5 = params.get("enable_rule5", True)
        
        # Extract sub-params
        rule3_params = params.get("rule3_params", {})
        rule4_params = params.get("rule4_params", {})
        rule5_params = params.get("rule5_params", {})
        
        # Rule 3
        if enable_rule3:
            p3_args = {"enable": True, "time_window": time_window}
            p3_args.update(rule3_params)
            try:
                p3 = TradingSequenceParams(**p3_args)
                current_edges.extend(process_rule3(request.target_users, request.time_range, p3))
            except Exception as e:
                print(f"Error in Rule3: {e}")
        
        # Rule 4
        if enable_rule4:
            p4_args = {"enable": True, "time_window": time_window}
            p4_args.update(rule4_params)
            try:
                p4 = BalanceSequenceParams(**p4_args)
                current_edges.extend(process_rule4(request.target_users, request.time_range, p4))
            except Exception as e:
                print(f"Error in Rule4: {e}")
                
        # Rule 5
        if enable_rule5:
            p5_args = {"enable": True, "time_window": time_window}
            p5_args.update(rule5_params)
            try:
                p5 = EarningSequenceParams(**p5_args)
                current_edges.extend(process_rule5(request.target_users, request.time_range, p5))
            except Exception as e:
                print(f"Error in Rule5: {e}")
                
    # Merge behavior edges into G_master
    for edge in current_edges:
        u, v = edge.source, edge.target
        sim = edge.similarity
        rule_name = edge.rule
        details = edge.details
        
        reason_str = f"Behavior Similarity ({rule_name}, sim={sim})"
        
        if G_master.has_edge(u, v):
            master_reasons = G_master[u][v].get('reasons', [])
            if reason_str not in master_reasons:
                master_reasons.append(reason_str)
            G_master[u][v]['reasons'] = master_reasons
            
            # Merge details
            master_details = G_master[u][v].get('behavior_details', [])
            master_details.append(details)
            G_master[u][v]['behavior_details'] = master_details
        else:
            G_master.add_edge(u, v, reasons=[reason_str], behavior_details=[details])
            
    return G_master

@router.post("/detect", response_model=DetectionResponse)
async def detect_entities(request: DetectionRequest):
    """
    Run entity detection based on provided rules and parameters.
    """
    try:
        start_time = time.time()
        
        # Build the graph
        G_master = build_entity_graph(request)
        
        # Target set for strict filtering
        target_set = set(request.target_users) if request.target_users else None

        # 3. Find Components (Merged Entities)
        # Remove self-loops to ensure no single-node entities from self-edges
        G_master.remove_edges_from(nx.selfloop_edges(G_master))
        
        components = list(nx.connected_components(G_master))
        all_detected = []
        
        for i, comp in enumerate(components):
            # Strict filtering:
            # 1. Must have > 1 members
            # 2. All members must be in target_users (if provided)
            
            members = list(comp)
            if target_set:
                members = [m for m in members if m in target_set]
            
            if len(members) > 1:
                subgraph = G_master.subgraph(members)
                
                reasons_set = set()
                total_txs = 0
                behavior_details_list = []
                
                for u, v, d in subgraph.edges(data=True):
                    total_txs += d.get('transfer_count', 0)
                    for r in d.get('reasons', []):
                        reasons_set.add(r)
                    if 'behavior_details' in d:
                        behavior_details_list.extend(d['behavior_details'])
                
                final_reasons = sorted(list(reasons_set)) if reasons_set else ["Connected via network analysis"]
                
                all_detected.append(DetectedEntity(
                    entity_id=f"merged_entity_{i}_{int(time.time())}",
                    confidence=0.8,
                    reason=final_reasons,
                    details={
                        "members": members,
                        "total_transactions": int(total_txs),
                        "member_count": len(members),
                        "behavior_details": behavior_details_list
                    }
                ))

        execution_time = time.time() - start_time
        
        # Return Results
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
        print(f"Error in detect_entities: {e}")
        import traceback
        traceback.print_exc()
        return DetectionResponse(
            status="error",
            processed_count=0,
            detected_entities=[],
            metadata={
                "error": str(e),
                "execution_time_seconds": time.time() - start_time if 'start_time' in locals() else 0,
            }
        )

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
async def get_links(request: DetectionRequest):
    """
    Get links (edges) based on detection rules (Network + Behavior).
    """
    try:
        # Build the graph using the same logic as entity detection
        G = build_entity_graph(request)
        
        # Filter edges to ensure both source and target are in target_users
        # This is to strictly follow the requirement: "Only calculate edges between the filtered nodes"
        valid_users = set(request.target_users) if request.target_users else None
        
        links = []
        for u, v, d in G.edges(data=True):
            # Strict filtering
            if valid_users:
                if u not in valid_users or v not in valid_users:
                    continue
            
            # Calculate a weight for visualization
            # Default to transfer_count, or 1 if it's purely behavior-based
            weight = d.get('transfer_count', 0)
            if weight == 0:
                weight = 1
                
            links.append({
                "source": u,
                "target": v,
                "weight": weight,
                "reasons": d.get('reasons', []),
                "details": d
            })
            
        return {"links": links}
    except Exception as e:
        print(f"Error in get_links: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
