import os
import pandas as pd
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from datetime import datetime

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import token_config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/manipulation_service",
    tags=["manipulation_service"],
    responses={404: {"description": "Not found"}},
)

# Request Model
class ManipulationRequest(BaseModel):
    target_users: Dict[str, float]  # user_id -> balance/score
    related_users: Dict[str, float] # user_id -> balance/score
    entity_results: List[Dict[str, Any]] # List of entities detected
    manipulation_config: Dict[str, Any] # Configuration for detection methods
    token: str = "ACT"

# Response Model (Unified Result)
class ManipulationResult(BaseModel):
    suspicious_users: List[str]
    manipulation_time: List[str] # [start_time, end_time] or specific timestamps
    participants: List[str]
    features: Dict[str, Any]
    transactions: List[Dict[str, Any]]
    detection_method: str

class UnifiedResponse(BaseModel):
    results: List[ManipulationResult]

# Global DataFrame cache (token-keyed)
_trades_cache = {}

def load_trading_data(token: str = "ACT"):
    global _trades_cache
    if token not in _trades_cache:
        trades_path = token_config.get_data_path(token, "sorted_trades.csv")
        if os.path.exists(trades_path):
            logger.info(f"Loading trading data from {trades_path}")
            try:
                _trades_cache[token] = pd.read_csv(trades_path)
                if 'timestamp' in _trades_cache[token].columns:
                     _trades_cache[token]['timestamp'] = pd.to_datetime(_trades_cache[token]['timestamp'])
            except Exception as e:
                logger.error(f"Failed to load trading data: {e}")
                _trades_cache[token] = pd.DataFrame()
        else:
            logger.warning(f"Trading data file not found at {trades_path}")
            _trades_cache[token] = pd.DataFrame()
    return _trades_cache[token]

# --- Detection Methods (Placeholders) ---
def detect_round_trip_for_user(participant_id: str, user_trades: pd.DataFrame, max_time_diff_min: float, max_position_diff: float, max_earning_usd: float) -> List[ManipulationResult]:
    """
    Detect round trips for a single participant's trade sequence. 
    A participant could be a single user or a combined entity.
    """
    results = []
    n_trades = len(user_trades)
    
    if n_trades < 2:
        return results
        
    i = 0
    while i < n_trades:
        start_trade = user_trades.iloc[i]
        start_time = start_trade['timestamp']
        
        current_position = 0.0
        current_earning_usd = 0.0
        sequence_trades = []
        
        # First, add the starting trade to the sequence
        sequence_trades.append(start_trade)
        amount = float(start_trade.get('amount', 0))
        amount_usd = float(start_trade.get('amount_usd', 0))
        action = start_trade.get('action_type', 'buy').lower()
        
        if action == 'buy':
            current_position += amount
            current_earning_usd -= amount_usd
        elif action == 'sell':
            current_position -= amount
            current_earning_usd += amount_usd
        
        found_round_trip = False
        
        # Iterate to find subsequent trades within the time window
        for j in range(i + 1, n_trades):
            current_trade = user_trades.iloc[j]
            time_diff = (current_trade['timestamp'] - start_time).total_seconds() / 60.0
            
            # If we exceed max_time_diff, stop adding to this sequence
            if time_diff > max_time_diff_min:
                break
                
            sequence_trades.append(current_trade)
            
            # Calculate position and earning change based on action_type
            amount = float(current_trade.get('amount', 0))
            amount_usd = float(current_trade.get('amount_usd', 0))
            action = current_trade.get('action_type', 'buy').lower()
            
            if action == 'buy':
                current_position += amount
                current_earning_usd -= amount_usd # Spent USD
            elif action == 'sell':
                current_position -= amount
                current_earning_usd += amount_usd # Gained USD
            
            # We need at least 2 trades to form a round trip
            if len(sequence_trades) >= 2:
                # Check if there is at least one buy and one sell in the sequence
                actions_in_seq = set(t.get('action_type', 'buy').lower() for t in sequence_trades)
                if 'buy' in actions_in_seq and 'sell' in actions_in_seq:
                    if abs(current_position) <= max_position_diff and current_earning_usd <= max_earning_usd:
                        trade_records = sequence_trades.copy()
                        transactions = []
                        involved_users = set()
                        for t in trade_records:
                            t_dict = t.to_dict()
                            if 'timestamp' in t_dict:
                                t_dict['timestamp'] = t_dict['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                            if 'trader' in t_dict:
                                involved_users.add(t_dict['trader'])
                            transactions.append(t_dict)
                        results.append(
                            ManipulationResult(
                                suspicious_users=[participant_id],
                                manipulation_time=[
                                    trade_records[0]['timestamp'].strftime("%Y-%m-%d %H:%M:%S"),
                                    trade_records[-1]['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                                ],
                                participants=list(involved_users),
                                features={
                                    "net_position_change": abs(current_position),
                                    "earning_usd": current_earning_usd,
                                    "trade_count": len(trade_records),
                                    "time_diff_min": time_diff
                                },
                                transactions=transactions,
                                detection_method="round_trip"
                            )
                        )
                        found_round_trip = True
                        i = j + 1
                        break
                    
        if not found_round_trip:
            i += 1
            
    return results

def detect_round_trip(df: pd.DataFrame, users: List[str], config: Dict[str, Any], entity_results: List[Dict[str, Any]] = None) -> List[ManipulationResult]:
    """
    Round Trip detection logic.
    Finds a group of continuous trades within max_time_diff (minutes) where the net position change
    is less than max_position_diff and the earning is less than max_earning (usd).
    If enable_entity_based is true, it aggregates trades of users within the same entity.
    """
    max_time_diff_min = config.get("max_time_diff", 10)
    max_position_diff = config.get("max_position_diff", 10)
    max_earning_usd = config.get("max_earning", 1)
    enable_entity_based = config.get("enable_entity_based", False)
    logger.info(f"Round Trip Detection Config: max_time_diff={max_time_diff_min}, max_position_diff={max_position_diff}, max_earning={max_earning_usd}, enable_entity_based={enable_entity_based}")

    results = []
    processed_users = set()
    
    # 1. Process Individual Users (Check individual first)
    logger.info("Starting individual round trip detection...")
    for user in users:
        # Get trades for this user, sorted by time
        user_trades = df[df['trader'] == user].sort_values(by='timestamp')
        if not user_trades.empty:
            user_results = detect_round_trip_for_user(
                participant_id=user, 
                user_trades=user_trades, 
                max_time_diff_min=max_time_diff_min, 
                max_position_diff=max_position_diff, 
                max_earning_usd=max_earning_usd
            )
            results.extend(user_results)
            
    # 2. Process Entities (Then check entities)
    if enable_entity_based and entity_results:
        logger.info(f"Processing {len(entity_results)} entities for round trip detection")
        for idx, entity in enumerate(entity_results):
            entity_users = entity.get("users", [])
            if not entity_users:
                continue
                
            # Filter users that are in our target list (now expanded to include entity users)
            # Use all users in the entity for detection
            valid_entity_users = entity_users
            if not valid_entity_users:
                continue
                
            # Aggregate trades for the entire entity
            entity_trades = df[df['trader'].isin(valid_entity_users)].sort_values(by='timestamp')
            
            if not entity_trades.empty:
                participant_id = f"Entity_{idx}"
                logger.info(f"Detecting round trip for entity {participant_id} with {len(entity_trades)} trades (sorted by time)")
                entity_results_list = detect_round_trip_for_user(
                    participant_id=participant_id, 
                    user_trades=entity_trades, 
                    max_time_diff_min=max_time_diff_min, 
                    max_position_diff=max_position_diff, 
                    max_earning_usd=max_earning_usd
                )
                
                # Post-process entity results
                for res in entity_results_list:
                    # If entity check finds all trades from same person, classify as individual evidence
                    if len(res.participants) == 1:
                        single_user = res.participants[0]
                        res.suspicious_users = [single_user]
                        # We can optionally mark the method to indicate it was found via entity scan
                        res.detection_method = "round_trip_entity_single"
                    else:
                        # It's a cross-user round trip
                        res.suspicious_users = res.participants
                        res.detection_method = "round_trip_entity_group"
                        
                results.extend(entity_results_list)

    # 3. Deduplicate and Merge
    # We want to merge historical round trips for each user.
    # Since we might detect the same sequence in both individual and entity checks (if entity = single user),
    # we need to remove duplicates.
    
    unique_results = []
    seen_signatures = set()
    
    for res in results:
        # Create a unique signature for the round trip event
        # (start_time, end_time, sorted_participants_tuple, trade_count)
        start = res.manipulation_time[0]
        end = res.manipulation_time[1]
        parts = tuple(sorted(res.participants))
        count = res.features.get('trade_count', 0)
        
        sig = (start, end, parts, count)
        
        if sig not in seen_signatures:
            seen_signatures.add(sig)
            unique_results.append(res)
            
    logger.info(f"Total unique round trips found: {len(unique_results)}")
    return unique_results


def detect_same_direction_for_user(participant_id: str, user_trades: pd.DataFrame, max_time_diff_min: float, min_seq_length: int, max_diff_direction: int) -> List[ManipulationResult]:
    """
    Detect continuous same-direction trades for a single participant.
    """
    results = []
    n_trades = len(user_trades)
    
    if n_trades < min_seq_length:
        return results
        
    i = 0
    while i <= n_trades - min_seq_length:
        start_trade = user_trades.iloc[i]
        target_direction = start_trade.get('action_type', 'buy').lower()
        
        sequence_trades = [start_trade]
        ignored_count = 0
        last_trade_time = start_trade['timestamp']
        
        for j in range(i + 1, n_trades):
            current_trade = user_trades.iloc[j]
            current_time = current_trade['timestamp']
            current_direction = current_trade.get('action_type', 'buy').lower()
            
            # Check time difference between adjacent trades
            time_diff = (current_time - last_trade_time).total_seconds() / 60.0
            if time_diff > max_time_diff_min:
                break # Sequence broken due to time gap
                
            if current_direction == target_direction:
                sequence_trades.append(current_trade)
                last_trade_time = current_time
            else:
                # Different direction
                if ignored_count < max_diff_direction:
                    ignored_count += 1
                    sequence_trades.append(current_trade) # Include the ignored trade in sequence to show full picture
                    last_trade_time = current_time
                else:
                    break # Sequence broken due to too many different directions
                    
        # Check if the valid same-direction sequence is long enough
        # We only count trades that match the target direction towards the min_seq_length
        same_direction_count = sum(1 for t in sequence_trades if t.get('action_type', 'buy').lower() == target_direction)
        
        if same_direction_count >= min_seq_length:
            transactions = []
            involved_users = set()
            for t in sequence_trades:
                t_dict = t.to_dict()
                if 'timestamp' in t_dict:
                    t_dict['timestamp'] = t_dict['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                if 'trader' in t_dict:
                    involved_users.add(t_dict['trader'])
                transactions.append(t_dict)
                
            results.append(
                ManipulationResult(
                    suspicious_users=[participant_id],
                    manipulation_time=[
                        sequence_trades[0]['timestamp'].strftime("%Y-%m-%d %H:%M:%S"), 
                        sequence_trades[-1]['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                    ],
                    participants=list(involved_users),
                    features={
                        "direction": target_direction,
                        "trade_count": len(sequence_trades),
                        "same_direction_count": same_direction_count,
                        "ignored_different_direction_count": ignored_count,
                        "duration_min": (sequence_trades[-1]['timestamp'] - sequence_trades[0]['timestamp']).total_seconds() / 60.0
                    },
                    transactions=transactions,
                    detection_method="same_direction"
                )
            )
            # Jump past this sequence to avoid overlapping
            i = i + len(sequence_trades)
        else:
            i += 1
            
    return results

def detect_same_direction(df: pd.DataFrame, users: List[str], config: Dict[str, Any], entity_results: List[Dict[str, Any]] = None) -> List[ManipulationResult]:
    """
    Same Direction detection logic.
    Finds continuous trades in the same direction with constraints on time gaps and max allowed opposite trades.
    """
    max_time_diff_min = config.get("max_time_diff", 2)
    min_seq_length = config.get("min_seq_length", 3)
    max_diff_direction = config.get("max_diff_direction", 0)
    enable_entity_based = config.get("enable_entity_based", False)
    
    logger.info(f"Same Direction Config: max_time={max_time_diff_min}, min_seq={min_seq_length}, max_diff_dir={max_diff_direction}, entity_based={enable_entity_based}")

    results = []
    
    # 1. Process Individual Users
    logger.info("Starting individual same direction detection...")
    for user in users:
        user_trades = df[df['trader'] == user].sort_values(by='timestamp')
        if not user_trades.empty:
            user_results = detect_same_direction_for_user(
                participant_id=user,
                user_trades=user_trades,
                max_time_diff_min=max_time_diff_min,
                min_seq_length=min_seq_length,
                max_diff_direction=max_diff_direction
            )
            results.extend(user_results)
            
    # 2. Process Entities
    if enable_entity_based and entity_results:
        logger.info(f"Processing {len(entity_results)} entities for same direction detection")
        for idx, entity in enumerate(entity_results):
            entity_users = entity.get("users", [])
            if not entity_users:
                continue
                
            valid_entity_users = entity_users
            entity_trades = df[df['trader'].isin(valid_entity_users)].sort_values(by='timestamp')
            
            if not entity_trades.empty:
                participant_id = f"Entity_{idx}"
                entity_results_list = detect_same_direction_for_user(
                    participant_id=participant_id,
                    user_trades=entity_trades,
                    max_time_diff_min=max_time_diff_min,
                    min_seq_length=min_seq_length,
                    max_diff_direction=max_diff_direction
                )
                
                # Post-process entity results
                for res in entity_results_list:
                    if len(res.participants) == 1:
                        res.suspicious_users = [res.participants[0]]
                        res.detection_method = "same_direction_entity_single"
                    else:
                        res.suspicious_users = res.participants
                        res.detection_method = "same_direction_entity_group"
                        
                results.extend(entity_results_list)

    # 3. Deduplicate
    unique_results = []
    seen_signatures = set()
    
    for res in results:
        start = res.manipulation_time[0]
        end = res.manipulation_time[1]
        parts = tuple(sorted(res.participants))
        count = res.features.get('trade_count', 0)
        direction = res.features.get('direction', '')
        
        sig = (start, end, parts, count, direction)
        
        if sig not in seen_signatures:
            seen_signatures.add(sig)
            unique_results.append(res)
            
    logger.info(f"Total unique same direction sequences found: {len(unique_results)}")
    return unique_results


@router.post("/detect", response_model=UnifiedResponse)
async def detect_manipulation(request: ManipulationRequest):
    try:
        # 1. Load Data
        df = load_trading_data(request.token)
        if df.empty:
            logger.warning("Trading data is empty")
            return UnifiedResponse(results=[])
        
        # 2. Prepare Target Users
        # Combine target and related users
        all_target_users = set(request.target_users.keys())
        all_target_users.update(request.related_users.keys())
        
        # Also include users from entity results to ensure we have their data
        if request.entity_results:
            for entity in request.entity_results:
                if 'users' in entity:
                    all_target_users.update(entity['users'])
        
        target_user_list = list(all_target_users)
        
        # Filter DataFrame for relevant users (optimization)
        # Using 'trader' column based on CSV inspection
        if 'trader' in df.columns:
             filtered_df = df[df['trader'].isin(target_user_list)].copy()
        else:
             logger.warning("'trader' column not found in trading data")
             filtered_df = df.copy()
        
        # 3. Dispatch to Detection Methods
        unified_results = []

        # Determine methods to run from config, or default to all if not specified
        methods_to_run = []
        if request.manipulation_config.get("enable_round_trip_detection", False):
            methods_to_run.append("round_trip")
        if request.manipulation_config.get("enable_same_direction_detection", False):
             methods_to_run.append("same_direction")
             
        # Map frontend names to internal names if necessary
        # The frontend seems to use "round_trip_params", let's adjust the dictionary
        
        if "round_trip" in methods_to_run:
            logger.info("Running detection method: round_trip")
            method_config = request.manipulation_config.get("round_trip_params", {})
            # Ensure enable_entity_based is correctly set from the method config or default to False
            if "enable_entity_based" not in method_config:
                method_config["enable_entity_based"] = request.manipulation_config.get("enable_entity_based", False)
            
            results = detect_round_trip(filtered_df, target_user_list, method_config, request.entity_results)
            
            # Convert dicts to Pydantic models if they aren't already
            validated_results = []
            for res in results:
                if isinstance(res, dict):
                     validated_results.append(ManipulationResult(**res))
                elif isinstance(res, ManipulationResult):
                     validated_results.append(res)
            unified_results.extend(validated_results)

        if "same_direction" in methods_to_run:
            logger.info("Running detection method: same_direction")
            method_config = request.manipulation_config.get("same_direction_params", {})
            if "enable_entity_based" not in method_config:
                method_config["enable_entity_based"] = request.manipulation_config.get("enable_entity_based", False)
            
            results = detect_same_direction(filtered_df, target_user_list, method_config, request.entity_results)
            
            validated_results = []
            for res in results:
                if isinstance(res, dict):
                     validated_results.append(ManipulationResult(**res))
                elif isinstance(res, ManipulationResult):
                     validated_results.append(res)
            unified_results.extend(validated_results)

            
        return UnifiedResponse(results=unified_results)

    except Exception as e:
        logger.error(f"Error in manipulation detection service: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
