import os
from typing import Dict, List, Any, Optional, Set
import pandas as pd
import networkx as nx
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSFER_CSV_PATH = os.path.join(BASE_DIR, "public", "ACT_transfer_before_2024-11-10.csv")
TRADING_CSV_PATH = os.path.join(BASE_DIR, "public", "ACT_24_11_10.csv")
ACCOUNT_LABELS_PATH = os.path.join(BASE_DIR, "public", "processed", "transfers", "owner_labels.json")

router = APIRouter(
    prefix="/api/detection",
    tags=["detection"],
    responses={404: {"description": "Not found"}},
)

class DetectionRequest(BaseModel):
    target_users: Dict[str, float]
    related_users: Dict[str, float]
    entity_detection_config: Dict[str, Any]
    link_detection_config: Dict[str, Any]
    snapshot_time: str = None
    detect_entity: bool = True
    detect_link: bool = True

@router.post("/run")
async def run_detection(request: DetectionRequest):
    try:
        results = process_detection(
            request.target_users,
            request.related_users,
            request.entity_detection_config,
            request.link_detection_config,
            request.snapshot_time,
            request.detect_entity,
            request.detect_link
        )
        return results
    except Exception as e:
        logger.error(f"Error in detection process: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def process_detection(
    target_users: Dict[str, float],
    related_users: Dict[str, float],
    entity_detection_config: Dict[str, Any],
    link_detection_config: Dict[str, Any],
    snapshot_time: Optional[str] = None,
    detect_entity: bool = True,
    detect_link: bool = True
) -> Dict[str, Any]:
    """
    Main entry point for processing both entity and link detection.
    
    Args:
        target_users: Dictionary of target users and their balances
        related_users: Dictionary of related users and their balances
        entity_detection_config: Configuration for entity detection
        link_detection_config: Configuration for link detection
        snapshot_time: Optional snapshot time to filter data
        detect_entity: Whether to perform entity detection
        detect_link: Whether to perform link detection
        
    Returns:
        Dictionary containing detection results
    """
    logger.info(f"Starting detection process (Entity: {detect_entity}, Link: {detect_link})...")
    
    # 0. Load Data
    # Initialize relation dictionaries
    target_relations_for_entity = {}
    target_relations_for_links = {}
    target_related_relations_for_entity = {}
    target_related_relations_for_links = {}

    # Helper to merge relations
    def merge_relations(base_relations, new_relations):
        for k, reasons in new_relations.items():
            if k not in base_relations:
                base_relations[k] = []
            base_relations[k].extend(reasons)
        return base_relations

    
    # Check if network-based detection is enabled in either configuration
    need_network_detection = (
        (detect_entity and entity_detection_config.get("enable_network_based", False)) or
        (detect_link and link_detection_config.get("enable_network_based", False))
    )

    need_similarity_detection = (
        (detect_entity and entity_detection_config.get("enable_similarity_based", False)) or
        (detect_link and link_detection_config.get("enable_similarity_based", False))
    )

    # Load Transfer Data
    if need_network_detection:
        try:
            if os.path.exists(TRANSFER_CSV_PATH):
                # 0. Load and Pre-filter Data Once
                df_transfers = pd.read_csv(TRANSFER_CSV_PATH)
                if snapshot_time and 'block_time' in df_transfers.columns:
                    try:
                        snap_dt = pd.to_datetime(snapshot_time)
                        df_transfers['block_time_dt'] = pd.to_datetime(df_transfers['block_time'], errors='coerce')
                        df_transfers = df_transfers[df_transfers['block_time_dt'] <= snap_dt]
                        # Sort by time once for all subsequent uses
                        df_transfers = df_transfers.sort_values(by='block_time_dt')
                    except Exception as e:
                        logger.warning(f"Time filtering failed: {e}")
                else:
                    # Sort by string time if datetime conversion failed or not needed, though less reliable
                    if 'block_time' in df_transfers.columns:
                        df_transfers = df_transfers.sort_values(by='block_time')

                # Check if direct transfer is needed
                need_direct_transfer = (
                    (detect_entity and entity_detection_config.get("transfer_network_based_params", {}).get("enable_direct_transfer", False)) or
                    (detect_link and link_detection_config.get("transfer_network_based_params", {}).get("enable_direct_transfer", False))
                )

                need_funding_relationship = (
                    (detect_entity and entity_detection_config.get("transfer_network_based_params", {}).get("enable_funding_relationship", False)) or
                    (detect_link and link_detection_config.get("transfer_network_based_params", {}).get("enable_funding_relationship", False))
                )

                need_same_sender = (
                    (detect_entity and entity_detection_config.get("transfer_network_based_params", {}).get("enable_same_sender", False)) or
                    (detect_link and link_detection_config.get("transfer_network_based_params", {}).get("enable_same_sender", False))
                )

                need_same_recipient = (
                    (detect_entity and entity_detection_config.get("transfer_network_based_params", {}).get("enable_same_recipient", False)) or
                    (detect_link and link_detection_config.get("transfer_network_based_params", {}).get("enable_same_recipient", False))
                )

                if need_direct_transfer:
                    # Filter and populate dictionaries
                    target_user_set = set(target_users.keys())
                    related_user_set = set(related_users.keys())
                    
                    # Helper to generate key: "addr1-addr2" (sorted)
                    def get_key(u, v):
                        return "-".join(sorted([str(u), str(v)]))

                    # Temporary storage for aggregation
                    # key -> {'count': 0, 'volume': 0.0}
                    tt_stats = {} # Target-Target
                    tr_stats = {} # Target-Related (or Related-Target)

                    for _, row in df_transfers.iterrows():
                        u = row.get('from_owner')
                        v = row.get('to_owner')
                        
                        if pd.isna(u) or pd.isna(v): continue
                        
                        u, v = str(u), str(v)
                        
                        # Determine relationship type
                        u_in_t = u in target_user_set
                        v_in_t = v in target_user_set
                        u_in_r = u in related_user_set
                        v_in_r = v in related_user_set
                        
                        is_tt = u_in_t and v_in_t
                        is_tr = (u_in_t and v_in_r) or (u_in_r and v_in_t)
                        
                        if is_tt or is_tr:
                            try:
                                vol = float(row.get('amount_display', 0) or 0)
                            except:
                                vol = 0.0
                            
                            k = get_key(u, v)
                            
                            stats_map = tt_stats if is_tt else tr_stats
                            if k not in stats_map:
                                stats_map[k] = {'count': 0, 'volume': 0.0}
                            
                            stats_map[k]['count'] += 1
                            stats_map[k]['volume'] += vol

                    # Helper to check if a relation meets criteria
                    def check_criteria(count, volume, config):
                        net_params = config.get("transfer_network_based_params", {})
                        if not config.get("enable_network_based", False) or not net_params.get("enable_direct_transfer", False):
                            return False, None
                        
                        direct_params = net_params.get("direct_transfer_params", {})
                        min_count = direct_params.get("min_tx_count", 0)
                        min_volume = direct_params.get("min_tx_volume", 0)
                        enable_count = direct_params.get("enable_min_count", True)
                        enable_volume = direct_params.get("enable_min_volume", True)
                        
                        passed = False
                        reason_desc = []
                        
                        # Logic: 
                        # If enabled, criteria MUST be met.
                        count_passed = True
                        if enable_count:
                             if count < min_count: count_passed = False
                             else: reason_desc.append(f"count >= {min_count} ({count})")
                        
                        volume_passed = True
                        if enable_volume:
                             if volume < min_volume: volume_passed = False
                             else: reason_desc.append(f"volume >= {min_volume} ({volume:.2f})")
                        
                        # If neither is enabled, we assume pass (or fail? Usually pass if just logging, but here implies detection criteria)
                        # If both disabled, maybe it means "detect all direct transfers"? Or "detect none"?
                        # Assuming at least one should be enabled to be meaningful filter.
                        # If both False, count_passed=True, volume_passed=True -> returns True.
                        
                        if count_passed and volume_passed:
                            return True, ", ".join(reason_desc)
                            
                        return False, None

                    # Convert stats to the required list-of-reasons format based on config
                    def stats_to_relations(stats_map, config):
                        res = {}
                        for k, v in stats_map.items():
                            passed, desc = check_criteria(v['count'], v['volume'], config)
                            if passed:
                                res[k] = [{
                                    "type": "direct_transfer",
                                    "count": v['count'],
                                    "volume": v['volume'],
                                    "description": f"Direct transfer: {desc}"
                                }]
                        return res


                    # 1. target_relations_for_entity
                    if detect_entity and entity_detection_config.get("enable_network_based", False) and entity_detection_config.get("transfer_network_based_params", {}).get("enable_direct_transfer", False):
                        new_tt_entity = stats_to_relations(tt_stats, entity_detection_config)
                        merge_relations(target_relations_for_entity, new_tt_entity)
                    
                    # 2. target_relations_for_links
                    if detect_link and link_detection_config.get("enable_network_based", False) and link_detection_config.get("transfer_network_based_params", {}).get("enable_direct_transfer", False):
                        new_tt_link = stats_to_relations(tt_stats, link_detection_config)
                        merge_relations(target_relations_for_links, new_tt_link)
                    
                    # 3. target_related_relations_for_entity
                    if detect_entity and entity_detection_config.get("enable_network_based", False) and entity_detection_config.get("transfer_network_based_params", {}).get("enable_direct_transfer", False):
                        new_tr_entity = stats_to_relations(tr_stats, entity_detection_config)
                        merge_relations(target_related_relations_for_entity, new_tr_entity)

                    
                    # 4. target_related_relations_for_links
                    if detect_link and link_detection_config.get("enable_network_based", False) and link_detection_config.get("transfer_network_based_params", {}).get("enable_direct_transfer", False):
                        new_tr_link = stats_to_relations(tr_stats, link_detection_config)
                        merge_relations(target_related_relations_for_links, new_tr_link)
                    
                if need_funding_relationship or need_same_sender or need_same_recipient:
                    if 'target_user_set' not in locals():
                        target_user_set = set(target_users.keys())
                        related_user_set = set(related_users.keys())

                    address_to_label = {}
                    if os.path.exists(ACCOUNT_LABELS_PATH):
                        import json
                        with open(ACCOUNT_LABELS_PATH, 'r') as f:
                            try:
                                labels_list = json.load(f)
                                for item in labels_list:
                                    if "owner_address" in item and "label" in item:
                                        address_to_label[item["owner_address"]] = item["label"]
                            except Exception as e:
                                logger.error(f"Error loading account labels: {e}")
                    
                    all_tracked_users = target_user_set.union(related_user_set)
                    
                    # Use the pre-loaded and sorted df_transfers
                    df_sorted = df_transfers
                        
                    funding_senders = {user: [] for user in all_tracked_users}
                    recipients = {user: [] for user in all_tracked_users}
                    
                    for _, row in df_sorted.iterrows():
                        u = row.get('from_owner')
                        v = row.get('to_owner')
                        
                        if pd.isna(u) or pd.isna(v): continue
                        u, v = str(u), str(v)
                        
                        u_label = address_to_label.get(u, "")
                        v_label = address_to_label.get(v, "")
                        
                        if v in all_tracked_users:
                            if u_label not in ["contract", "exchange"]:
                                if u not in funding_senders[v]:
                                    funding_senders[v].append(u)
                                
                        if u in all_tracked_users:
                            if v_label not in ["contract", "exchange"]:
                                if v not in recipients[u]:
                                    recipients[u].append(v)

                    # Filter empty lists
                    funding_senders = {k: v for k, v in funding_senders.items() if v}
                    recipients = {k: v for k, v in recipients.items() if v}

                    # Prepare temporary result containers
                    funding_tt = {}
                    funding_tr = {}
                    same_sender_tt = {}
                    same_sender_tr = {}

                    # 1. Funding Relationship (Direct Funded & Co-funded)
                    if need_funding_relationship:
                        # A. Direct Funded
                        for u in target_user_set:
                            if u in funding_senders:
                                s = funding_senders[u][0] # First sender
                                
                                if s in target_user_set:
                                    k = get_key(u, s)
                                    if k not in funding_tt: funding_tt[k] = []
                                    funding_tt[k].append({
                                        "type": "funding",
                                        "description": f"Direct funded by {s}",
                                        "direction": f"{s}->{u}"
                                    })
                                elif s in related_user_set:
                                    k = get_key(u, s)
                                    if k not in funding_tr: funding_tr[k] = []
                                    funding_tr[k].append({
                                        "type": "funding",
                                        "description": f"Direct funded by {s}",
                                        "direction": f"{s}->{u}"
                                    })
                        
                        # B. Co-funded (Same First Sender)
                        first_sender_to_users = {}
                        for u, senders in funding_senders.items():
                            if not senders: continue
                            s = senders[0]
                            if s not in first_sender_to_users: first_sender_to_users[s] = []
                            first_sender_to_users[s].append(u)
                        
                        for s, users in first_sender_to_users.items():
                            if len(users) < 2: continue
                            users = sorted(list(set(users)))
                            
                            for i in range(len(users)):
                                for j in range(i+1, len(users)):
                                    u1, u2 = users[i], users[j]
                                    
                                    u1_t = u1 in target_user_set
                                    u2_t = u2 in target_user_set
                                    u1_r = u1 in related_user_set
                                    u2_r = u2 in related_user_set
                                    
                                    if u1_t and u2_t:
                                        k = get_key(u1, u2)
                                        if k not in funding_tt: funding_tt[k] = []
                                        funding_tt[k].append({
                                            "type": "co_funded",
                                            "description": f"Co-funded by {s}",
                                            "sender": s
                                        })
                                    elif (u1_t and u2_r) or (u1_r and u2_t):
                                        k = get_key(u1, u2)
                                        if k not in funding_tr: funding_tr[k] = []
                                        funding_tr[k].append({
                                            "type": "co_funded",
                                            "description": f"Co-funded by {s}",
                                            "sender": s
                                        })

                    # 2. Same Sender (Any Common Sender)
                    if need_same_sender:
                        # Inverted index: sender -> list of users
                        sender_to_users = {}
                        for u, senders in funding_senders.items():
                            for s in senders:
                                if s not in sender_to_users:
                                    sender_to_users[s] = []
                                sender_to_users[s].append(u)
                        
                        for s, users in sender_to_users.items():
                            if len(users) < 2: continue
                            users = sorted(list(set(users)))
                            
                            for i in range(len(users)):
                                for j in range(i+1, len(users)):
                                    u1, u2 = users[i], users[j]
                                    
                                    u1_t = u1 in target_user_set
                                    u2_t = u2 in target_user_set
                                    u1_r = u1 in related_user_set
                                    u2_r = u2 in related_user_set
                                    
                                    if u1_t and u2_t:
                                        k = get_key(u1, u2)
                                        if k not in same_sender_tt: same_sender_tt[k] = []
                                        same_sender_tt[k].append({
                                            "type": "same_sender",
                                            "description": f"Common sender {s}",
                                            "sender": s
                                        })
                                    elif (u1_t and u2_r) or (u1_r and u2_t):
                                        k = get_key(u1, u2)
                                        if k not in same_sender_tr: same_sender_tr[k] = []
                                        same_sender_tr[k].append({
                                            "type": "same_sender",
                                            "description": f"Common sender {s}",
                                            "sender": s
                                        })

                    # 3. Same Recipient (Any Common Recipient)
                    if need_same_recipient:
                        same_recipient_tt = {}
                        same_recipient_tr = {}
                        
                        # Inverted index: recipient -> list of users
                        recipient_to_users = {}
                        for u, user_recipients in recipients.items():
                            for r in user_recipients:
                                if r not in recipient_to_users:
                                    recipient_to_users[r] = []
                                recipient_to_users[r].append(u)
                        
                        for r, users in recipient_to_users.items():
                            if len(users) < 2: continue
                            users = sorted(list(set(users)))
                            
                            for i in range(len(users)):
                                for j in range(i+1, len(users)):
                                    u1, u2 = users[i], users[j]
                                    
                                    u1_t = u1 in target_user_set
                                    u2_t = u2 in target_user_set
                                    u1_r = u1 in related_user_set
                                    u2_r = u2 in related_user_set
                                    
                                    if u1_t and u2_t:
                                        k = get_key(u1, u2)
                                        if k not in same_recipient_tt: same_recipient_tt[k] = []
                                        same_recipient_tt[k].append({
                                            "type": "same_recipient",
                                            "description": f"Common recipient {r}",
                                            "recipient": r
                                        })
                                    elif (u1_t and u2_r) or (u1_r and u2_t):
                                        k = get_key(u1, u2)
                                        if k not in same_recipient_tr: same_recipient_tr[k] = []
                                        same_recipient_tr[k].append({
                                            "type": "same_recipient",
                                            "description": f"Common recipient {r}",
                                            "recipient": r
                                        })

                    # Merge into Entity Detection results
                    if detect_entity and entity_detection_config.get("enable_network_based", False):
                        params = entity_detection_config.get("transfer_network_based_params", {})
                        if params.get("enable_funding_relationship", False):
                            merge_relations(target_relations_for_entity, funding_tt)
                            merge_relations(target_related_relations_for_entity, funding_tr)
                        if params.get("enable_same_sender", False):
                            merge_relations(target_relations_for_entity, same_sender_tt)
                            merge_relations(target_related_relations_for_entity, same_sender_tr)
                        if params.get("enable_same_recipient", False):
                            merge_relations(target_relations_for_entity, same_recipient_tt)
                            merge_relations(target_related_relations_for_entity, same_recipient_tr)

                    # Merge into Link Detection results
                    if detect_link and link_detection_config.get("enable_network_based", False):
                        params = link_detection_config.get("transfer_network_based_params", {})
                        if params.get("enable_funding_relationship", False):
                            merge_relations(target_relations_for_links, funding_tt)
                            merge_relations(target_related_relations_for_links, funding_tr)
                        if params.get("enable_same_sender", False):
                            merge_relations(target_relations_for_links, same_sender_tt)
                            merge_relations(target_related_relations_for_links, same_sender_tr)
                        if params.get("enable_same_recipient", False):
                            merge_relations(target_relations_for_links, same_recipient_tt)
                            merge_relations(target_related_relations_for_links, same_recipient_tr)

                
            else:
                logger.warning(f"Transfer CSV not found at {TRANSFER_CSV_PATH}")
    
        except Exception as e:
            logger.error(f"Error loading data: {e}")
    else:
        logger.info("Network-based detection not enabled. Skipping transfer data loading.")


    
    logger.info("Detection process completed.")
    
    response = {}


    # DEBUG: Return intermediate relations for frontend inspection
    response["current_results"] = {
        "target_relations_for_entity": target_relations_for_entity,
        "target_relations_for_links": target_relations_for_links,
        "target_related_relations_for_entity": target_related_relations_for_entity,
        "target_related_relations_for_links": target_related_relations_for_links,
        "funding_senders": funding_senders,
        "recipients": recipients,
    }
        
    return response


