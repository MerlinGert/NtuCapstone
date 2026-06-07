import copy
import json
import logging
import os
import threading
from collections import OrderedDict
from itertools import combinations
from typing import Any, Dict, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ACCOUNT_LABELS_PATH = os.path.join(BASE_DIR, "public", "data", "simplified_owner_labels.json")
# SORTED_TRANSFERS_PATH = os.path.join(BASE_DIR, "public", "data", "sorted_transfers.csv")
# USER_RELATIONS_PATH = os.path.join(BASE_DIR, "public", "data", "user_relations.json")

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
    coin: str = "ACT"


def get_data_dir(coin: str) -> str:
    if coin == "PNUT":
        return os.path.join(BASE_DIR, "public", "data2")
    return os.path.join(BASE_DIR, "public", "data")


DETECTION_RESULT_CACHE_MAX_SIZE = 64
MANISCOPE_USE_OPTIMIZED_DETECTION = "MANISCOPE_USE_OPTIMIZED_DETECTION"

_cache_lock = threading.RLock()
_csv_file_cache: Dict[str, pd.DataFrame] = {}
_json_file_cache: Dict[str, Any] = {}
_detection_result_cache: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
_optimized_detection_result_cache: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
_prepared_transfer_cache: Dict[str, pd.DataFrame] = {}
_prepared_user_relations_cache: Dict[str, Dict[str, Any]] = {}
_prepared_user_actions_cache: Dict[str, Dict[str, list]] = {}


def _load_csv_file(path: str) -> Optional[pd.DataFrame]:
    """Load a static CSV once per process and return a defensive copy."""
    with _cache_lock:
        cached = _csv_file_cache.get(path)
        if cached is not None:
            return cached.copy()

    if not os.path.exists(path):
        logger.warning(f"CSV file not found at {path}")
        return None

    try:
        df = pd.read_csv(path)
    except Exception as e:
        logger.error(f"Error loading CSV file {path}: {e}")
        return None

    with _cache_lock:
        cached = _csv_file_cache.setdefault(path, df)
        return cached.copy()


def _load_json_file(path: str, default=None):
    """Load a static JSON file once per process."""
    with _cache_lock:
        if path in _json_file_cache:
            return _json_file_cache[path]

    if not os.path.exists(path):
        logger.warning(f"JSON file not found at {path}")
        return default

    try:
        with open(path, "r") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON file {path}: {e}")
        return default

    with _cache_lock:
        return _json_file_cache.setdefault(path, data)


def _make_detection_cache_key(
    target_users: Dict[str, float],
    related_users: Dict[str, float],
    entity_detection_config: Dict[str, Any],
    link_detection_config: Dict[str, Any],
    snapshot_time: Optional[str],
    detect_entity: bool,
    detect_link: bool,
    coin: str,
) -> str:
    payload = {
        "coin": coin,
        "snapshot_time": snapshot_time,
        "detect_entity": detect_entity,
        "detect_link": detect_link,
        "target_users": target_users,
        "related_users": related_users,
        "entity_detection_config": entity_detection_config,
        "link_detection_config": link_detection_config,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _get_detection_result_from_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    with _cache_lock:
        cached = _detection_result_cache.get(cache_key)
        if cached is None:
            return None
        _detection_result_cache.move_to_end(cache_key)
        return copy.deepcopy(cached)


def _set_detection_result_cache(cache_key: str, result: Dict[str, Any]) -> None:
    with _cache_lock:
        _detection_result_cache[cache_key] = copy.deepcopy(result)
        _detection_result_cache.move_to_end(cache_key)
        while len(_detection_result_cache) > DETECTION_RESULT_CACHE_MAX_SIZE:
            _detection_result_cache.popitem(last=False)


def _env_enabled(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def clear_optimized_detection_caches() -> None:
    """Clear optimized detection caches for equivalence tests and benchmarks."""
    with _cache_lock:
        _optimized_detection_result_cache.clear()
        _prepared_transfer_cache.clear()
        _prepared_user_relations_cache.clear()
        _prepared_user_actions_cache.clear()


def _get_optimized_detection_result_from_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    with _cache_lock:
        cached = _optimized_detection_result_cache.get(cache_key)
        if cached is None:
            return None
        _optimized_detection_result_cache.move_to_end(cache_key)
        return copy.deepcopy(cached)


def _set_optimized_detection_result_cache(cache_key: str, result: Dict[str, Any]) -> None:
    with _cache_lock:
        _optimized_detection_result_cache[cache_key] = copy.deepcopy(result)
        _optimized_detection_result_cache.move_to_end(cache_key)
        while len(_optimized_detection_result_cache) > DETECTION_RESULT_CACHE_MAX_SIZE:
            _optimized_detection_result_cache.popitem(last=False)


@router.post("/run")
async def run_detection(request: DetectionRequest):
    try:
        detector = (
            process_detection_optimized
            if _env_enabled(MANISCOPE_USE_OPTIMIZED_DETECTION, default=True)
            else process_detection
        )
        results = detector(
            request.target_users,
            request.related_users,
            request.entity_detection_config,
            request.link_detection_config,
            request.snapshot_time,
            request.detect_entity,
            request.detect_link,
            request.coin,
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
    detect_link: bool = True,
    coin: str = "ACT",
) -> Dict[str, Any]:
    cache_key = _make_detection_cache_key(
        target_users,
        related_users,
        entity_detection_config,
        link_detection_config,
        snapshot_time,
        detect_entity,
        detect_link,
        coin,
    )
    cached = _get_detection_result_from_cache(cache_key)
    if cached is not None:
        logger.info("Detection result cache hit.")
        return cached

    result = _process_detection_uncached(
        target_users,
        related_users,
        entity_detection_config,
        link_detection_config,
        snapshot_time,
        detect_entity,
        detect_link,
        coin,
    )
    _set_detection_result_cache(cache_key, result)
    return result


def process_detection_optimized(
    target_users: Dict[str, float],
    related_users: Dict[str, float],
    entity_detection_config: Dict[str, Any],
    link_detection_config: Dict[str, Any],
    snapshot_time: Optional[str] = None,
    detect_entity: bool = True,
    detect_link: bool = True,
    coin: str = "ACT",
) -> Dict[str, Any]:
    cache_key = "optimized:" + _make_detection_cache_key(
        target_users,
        related_users,
        entity_detection_config,
        link_detection_config,
        snapshot_time,
        detect_entity,
        detect_link,
        coin,
    )
    cached = _get_optimized_detection_result_from_cache(cache_key)
    if cached is not None:
        logger.info("Optimized detection result cache hit.")
        return cached

    result = _process_detection_uncached_optimized(
        target_users,
        related_users,
        entity_detection_config,
        link_detection_config,
        snapshot_time,
        detect_entity,
        detect_link,
        coin,
    )
    _set_optimized_detection_result_cache(cache_key, result)
    return result


def _relation_key(u, v) -> str:
    return "-".join(sorted([str(u), str(v)]))


def _merge_relations_optimized(base_relations, new_relations):
    for k, reasons in new_relations.items():
        if k not in base_relations:
            base_relations[k] = []
        base_relations[k].extend(reasons)
    return base_relations


def _network_rule_enabled(config: Dict[str, Any], rule_name: str) -> bool:
    return bool(
        config.get("enable_network_based", False)
        and config.get("transfer_network_based_params", {}).get(rule_name, False)
    )


def _load_prepared_transfers(coin: str) -> Optional[pd.DataFrame]:
    with _cache_lock:
        cached = _prepared_transfer_cache.get(coin)
        if cached is not None:
            return cached

    transfers_path = os.path.join(get_data_dir(coin), "sorted_transfers.csv")
    df = _load_csv_file(transfers_path)
    if df is None:
        return None

    prepared = df.copy()
    if "timestamp" in prepared.columns:
        prepared["timestamp_dt"] = pd.to_datetime(prepared["timestamp"], errors="coerce")
    if "amount" in prepared.columns:
        prepared["amount_numeric"] = pd.to_numeric(prepared["amount"], errors="coerce").fillna(0.0)
    else:
        prepared["amount_numeric"] = 0.0

    with _cache_lock:
        return _prepared_transfer_cache.setdefault(coin, prepared)


def _filter_transfers_to_snapshot(
    transfers: Optional[pd.DataFrame], snapshot_time: Optional[str]
) -> Optional[pd.DataFrame]:
    if transfers is None:
        return None
    if not snapshot_time or "timestamp_dt" not in transfers.columns:
        return transfers
    try:
        snap_dt = pd.to_datetime(snapshot_time)
    except Exception as e:
        logger.warning(f"Time filtering failed: {e}")
        return transfers
    return transfers[transfers["timestamp_dt"] <= snap_dt]


def _direct_transfer_stats_vectorized(
    transfers: pd.DataFrame,
    target_user_set: set,
    related_user_set: set,
):
    empty_stats = {}
    if transfers is None or transfers.empty:
        return empty_stats, empty_stats
    if "from_owner" not in transfers.columns or "to_owner" not in transfers.columns:
        return empty_stats, empty_stats

    owners = transfers[["from_owner", "to_owner", "amount_numeric"]].dropna(
        subset=["from_owner", "to_owner"]
    )
    if owners.empty:
        return empty_stats, empty_stats

    from_owner = owners["from_owner"].astype(str)
    to_owner = owners["to_owner"].astype(str)
    from_target = from_owner.isin(target_user_set)
    to_target = to_owner.isin(target_user_set)
    from_related = from_owner.isin(related_user_set)
    to_related = to_owner.isin(related_user_set)

    tt_mask = from_target & to_target
    tr_mask = (from_target & to_related) | (from_related & to_target)

    def grouped_stats(mask):
        subset = owners.loc[mask, ["amount_numeric"]].copy()
        if subset.empty:
            return {}
        left = from_owner[mask]
        right = to_owner[mask]
        subset["pair_key"] = left.where(left <= right, right) + "-" + right.where(
            left <= right, left
        )
        grouped = subset.groupby("pair_key", sort=False)["amount_numeric"].agg(["count", "sum"])
        return {
            key: {"count": int(row["count"]), "volume": float(row["sum"])}
            for key, row in grouped.iterrows()
        }

    return grouped_stats(tt_mask), grouped_stats(tr_mask)


def _check_direct_transfer_criteria(count, volume, config):
    net_params = config.get("transfer_network_based_params", {})
    if not config.get("enable_network_based", False) or not net_params.get(
        "enable_direct_transfer", False
    ):
        return False, None

    direct_params = net_params.get("direct_transfer_params", {})
    min_count = direct_params.get("min_tx_count", 0)
    min_volume = direct_params.get("min_tx_volume", 0)
    enable_count = direct_params.get("enable_min_count", True)
    enable_volume = direct_params.get("enable_min_volume", True)

    reason_desc = []
    count_passed = True
    if enable_count:
        if count < min_count:
            count_passed = False
        else:
            reason_desc.append(f"count >= {min_count} ({count})")

    volume_passed = True
    if enable_volume:
        if volume < min_volume:
            volume_passed = False
        else:
            reason_desc.append(f"volume >= {min_volume} ({volume:.2f})")

    if count_passed and volume_passed:
        return True, ", ".join(reason_desc)
    return False, None


def _direct_stats_to_relations_optimized(stats_map, config):
    res = {}
    for key, stats in stats_map.items():
        passed, desc = _check_direct_transfer_criteria(
            stats["count"], stats["volume"], config
        )
        if passed:
            res[key] = [
                {
                    "type": "direct_transfer",
                    "count": stats["count"],
                    "volume": stats["volume"],
                    "description": f"Direct transfer: {desc}",
                }
            ]
    return res


def _load_prepared_user_relations(coin: str) -> Dict[str, Any]:
    with _cache_lock:
        cached = _prepared_user_relations_cache.get(coin)
        if cached is not None:
            return cached

    relations_path = os.path.join(get_data_dir(coin), "user_relations.json")
    raw_relations = _load_json_file(relations_path, {}) or {}

    prepared = {"senders": {}, "recipients": {}}
    for relation_kind in ("senders", "recipients"):
        for user, records in raw_relations.get(relation_kind, {}).items():
            parsed_records = []
            for record in records:
                try:
                    parsed_records.append(
                        {
                            "timestamp": pd.to_datetime(record["timestamp"]),
                            "address": record["address"],
                        }
                    )
                except (ValueError, TypeError, KeyError):
                    pass
            prepared[relation_kind][user] = parsed_records

    with _cache_lock:
        return _prepared_user_relations_cache.setdefault(coin, prepared)


def _valid_relation_addresses(records, snap_dt):
    if not snap_dt:
        return [record["address"] for record in records]
    valid = []
    for record in records:
        if record["timestamp"] <= snap_dt:
            valid.append(record["address"])
        else:
            break
    return valid


def _collect_prepared_network_relations(
    target_user_set: set,
    related_user_set: set,
    entity_detection_config: Dict[str, Any],
    link_detection_config: Dict[str, Any],
    snapshot_time: Optional[str],
    detect_entity: bool,
    detect_link: bool,
    coin: str,
):
    target_relations_for_entity = {}
    target_relations_for_links = {}
    target_related_relations_for_entity = {}
    target_related_relations_for_links = {}

    need_direct_transfer = (
        detect_entity and _network_rule_enabled(entity_detection_config, "enable_direct_transfer")
    ) or (
        detect_link and _network_rule_enabled(link_detection_config, "enable_direct_transfer")
    )
    need_funding_relationship = (
        detect_entity
        and _network_rule_enabled(entity_detection_config, "enable_funding_relationship")
    ) or (
        detect_link and _network_rule_enabled(link_detection_config, "enable_funding_relationship")
    )
    need_same_sender = (
        detect_entity and _network_rule_enabled(entity_detection_config, "enable_same_sender")
    ) or (detect_link and _network_rule_enabled(link_detection_config, "enable_same_sender"))
    need_same_recipient = (
        detect_entity and _network_rule_enabled(entity_detection_config, "enable_same_recipient")
    ) or (
        detect_link and _network_rule_enabled(link_detection_config, "enable_same_recipient")
    )

    if need_direct_transfer:
        transfers = _filter_transfers_to_snapshot(_load_prepared_transfers(coin), snapshot_time)
        tt_stats, tr_stats = _direct_transfer_stats_vectorized(
            transfers, target_user_set, related_user_set
        )
        if detect_entity and _network_rule_enabled(
            entity_detection_config, "enable_direct_transfer"
        ):
            _merge_relations_optimized(
                target_relations_for_entity,
                _direct_stats_to_relations_optimized(tt_stats, entity_detection_config),
            )
            _merge_relations_optimized(
                target_related_relations_for_entity,
                _direct_stats_to_relations_optimized(tr_stats, entity_detection_config),
            )
        if detect_link and _network_rule_enabled(link_detection_config, "enable_direct_transfer"):
            _merge_relations_optimized(
                target_relations_for_links,
                _direct_stats_to_relations_optimized(tt_stats, link_detection_config),
            )
            _merge_relations_optimized(
                target_related_relations_for_links,
                _direct_stats_to_relations_optimized(tr_stats, link_detection_config),
            )

    if need_funding_relationship or need_same_sender or need_same_recipient:
        all_tracked_users = target_user_set.union(related_user_set)
        prepared_relations = _load_prepared_user_relations(coin)
        snap_dt = None
        if snapshot_time:
            try:
                snap_dt = pd.to_datetime(snapshot_time)
            except (ValueError, TypeError):
                snap_dt = None

        funding_senders = {}
        recipients = {}
        for user in all_tracked_users:
            sender_records = prepared_relations.get("senders", {}).get(user, [])
            valid_senders = _valid_relation_addresses(sender_records, snap_dt)
            if valid_senders:
                funding_senders[user] = valid_senders

            recipient_records = prepared_relations.get("recipients", {}).get(user, [])
            valid_recipients = _valid_relation_addresses(recipient_records, snap_dt)
            if valid_recipients:
                recipients[user] = valid_recipients

        funding_tt = {}
        funding_tr = {}
        same_sender_tt = {}
        same_sender_tr = {}

        if need_funding_relationship:
            for user in target_user_set:
                if user not in funding_senders:
                    continue
                sender = funding_senders[user][0]
                if sender in target_user_set:
                    funding_tt.setdefault(_relation_key(user, sender), []).append(
                        {
                            "type": "funding",
                            "description": f"Direct funded by {sender}",
                            "direction": f"{sender}->{user}",
                        }
                    )
                elif sender in related_user_set:
                    funding_tr.setdefault(_relation_key(user, sender), []).append(
                        {
                            "type": "funding",
                            "description": f"Direct funded by {sender}",
                            "direction": f"{sender}->{user}",
                        }
                    )

            first_sender_to_users = {}
            for user, senders in funding_senders.items():
                if senders:
                    first_sender_to_users.setdefault(senders[0], []).append(user)

            for sender, users in first_sender_to_users.items():
                for u1, u2 in combinations(sorted(set(users)), 2):
                    u1_t = u1 in target_user_set
                    u2_t = u2 in target_user_set
                    u1_r = u1 in related_user_set
                    u2_r = u2 in related_user_set
                    if u1_t and u2_t:
                        funding_tt.setdefault(_relation_key(u1, u2), []).append(
                            {
                                "type": "co_funded",
                                "description": f"Co-funded by {sender}",
                                "sender": sender,
                            }
                        )
                    elif (u1_t and u2_r) or (u1_r and u2_t):
                        funding_tr.setdefault(_relation_key(u1, u2), []).append(
                            {
                                "type": "co_funded",
                                "description": f"Co-funded by {sender}",
                                "sender": sender,
                            }
                        )

        if need_same_sender:
            sender_to_users = {}
            for user, senders in funding_senders.items():
                for sender in senders:
                    sender_to_users.setdefault(sender, []).append(user)
            for sender, users in sender_to_users.items():
                for u1, u2 in combinations(sorted(set(users)), 2):
                    u1_t = u1 in target_user_set
                    u2_t = u2 in target_user_set
                    u1_r = u1 in related_user_set
                    u2_r = u2 in related_user_set
                    if u1_t and u2_t:
                        same_sender_tt.setdefault(_relation_key(u1, u2), []).append(
                            {
                                "type": "same_sender",
                                "description": f"Same sender: {sender}",
                                "sender": sender,
                            }
                        )
                    elif (u1_t and u2_r) or (u1_r and u2_t):
                        same_sender_tr.setdefault(_relation_key(u1, u2), []).append(
                            {
                                "type": "same_sender",
                                "description": f"Same sender: {sender}",
                                "sender": sender,
                            }
                        )

        if need_same_recipient:
            recipient_to_users = {}
            for user, recipient_list in recipients.items():
                for recipient in recipient_list:
                    recipient_to_users.setdefault(recipient, []).append(user)
            for recipient, users in recipient_to_users.items():
                for u1, u2 in combinations(sorted(set(users)), 2):
                    u1_t = u1 in target_user_set
                    u2_t = u2 in target_user_set
                    u1_r = u1 in related_user_set
                    u2_r = u2 in related_user_set
                    if u1_t and u2_t:
                        same_sender_tt.setdefault(_relation_key(u1, u2), []).append(
                            {
                                "type": "same_recipient",
                                "description": f"Same recipient: {recipient}",
                                "recipient": recipient,
                            }
                        )
                    elif (u1_t and u2_r) or (u1_r and u2_t):
                        same_sender_tr.setdefault(_relation_key(u1, u2), []).append(
                            {
                                "type": "same_recipient",
                                "description": f"Same recipient: {recipient}",
                                "recipient": recipient,
                            }
                        )

        if detect_entity:
            params = entity_detection_config.get("transfer_network_based_params", {})
            if params.get("enable_funding_relationship", False):
                _merge_relations_optimized(target_relations_for_entity, funding_tt)
                _merge_relations_optimized(target_related_relations_for_entity, funding_tr)
            if params.get("enable_same_sender", False) or params.get(
                "enable_same_recipient", False
            ):
                _merge_relations_optimized(target_relations_for_entity, same_sender_tt)
                _merge_relations_optimized(target_related_relations_for_entity, same_sender_tr)

        if detect_link:
            params = link_detection_config.get("transfer_network_based_params", {})
            if params.get("enable_funding_relationship", False):
                _merge_relations_optimized(target_relations_for_links, funding_tt)
                _merge_relations_optimized(target_related_relations_for_links, funding_tr)
            if params.get("enable_same_sender", False) or params.get(
                "enable_same_recipient", False
            ):
                _merge_relations_optimized(target_relations_for_links, same_sender_tt)
                _merge_relations_optimized(target_related_relations_for_links, same_sender_tr)

    return {
        "target_relations_for_entity": target_relations_for_entity,
        "target_relations_for_links": target_relations_for_links,
        "target_related_relations_for_entity": target_related_relations_for_entity,
        "target_related_relations_for_links": target_related_relations_for_links,
    }


def _load_prepared_user_actions(coin: str, users=None) -> Dict[str, list]:
    user_actions_path = os.path.join(get_data_dir(coin), "user_actions.json")
    raw_actions = _load_json_file(user_actions_path, {}) or {}

    with _cache_lock:
        prepared_for_coin = _prepared_user_actions_cache.setdefault(coin, {})

    requested_users = list(users) if users is not None else list(raw_actions.keys())
    for user in requested_users:
        with _cache_lock:
            if user in prepared_for_coin:
                continue
        actions = raw_actions.get(user)
        if actions is None:
            continue
        parsed = []
        for item in actions:
            try:
                parsed.append({**item, "_ts": pd.to_datetime(item["timestamp"]).timestamp()})
            except (ValueError, TypeError, KeyError):
                pass
        with _cache_lock:
            prepared_for_coin[user] = parsed

    with _cache_lock:
        return {
            user: prepared_for_coin[user]
            for user in requested_users
            if user in prepared_for_coin
        }


def _merge_detection_results_optimized(base_map, new_results, rel_type="trading_action_sequence"):
    for key, result in new_results.items():
        if key not in base_map:
            base_map[key] = []
        base_map[key].append(
            {
                "type": rel_type,
                "score": result["score"],
                "description": f"Found matching sequence ({rel_type}): {result['actions_summary']}...",
                "details": result,
            }
        )


def _build_detection_response_from_relations(
    target_relations_for_entity,
    target_relations_for_links,
    target_related_relations_for_entity,
    target_related_relations_for_links,
) -> Dict[str, Any]:
    adj = {}

    def add_edge(u, v, rel_info):
        if u not in adj:
            adj[u] = []
        if v not in adj:
            adj[v] = []
        adj[u].append((v, rel_info))
        adj[v].append((u, rel_info))

    for key, relations in target_relations_for_entity.items():
        parts = key.split("-")
        if len(parts) >= 2:
            add_edge(parts[0], parts[1], relations)

    for key, relations in target_related_relations_for_entity.items():
        parts = key.split("-")
        if len(parts) >= 2:
            add_edge(parts[0], parts[1], relations)

    visited = set()
    entities = []
    for user in adj:
        if user in visited:
            continue
        component_users = {user}
        queue = [user]
        visited.add(user)
        while queue:
            curr = queue.pop(0)
            for neighbor, _rels in adj.get(curr, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    component_users.add(neighbor)
                    queue.append(neighbor)

        comp_rels = []
        processed_keys = set()
        for key, value in target_relations_for_entity.items():
            if key in processed_keys:
                continue
            parts = key.split("-")
            if len(parts) >= 2 and parts[0] in component_users and parts[1] in component_users:
                comp_rels.extend(value)
                processed_keys.add(key)
        for key, value in target_related_relations_for_entity.items():
            if key in processed_keys:
                continue
            parts = key.split("-")
            if len(parts) >= 2 and parts[0] in component_users and parts[1] in component_users:
                comp_rels.extend(value)
                processed_keys.add(key)

        entities.append({"users": list(component_users), "relations": comp_rels})

    return {
        "entity_results": entities,
        "relations": {
            "target_relations_for_entity": target_relations_for_entity,
            "target_relations_for_links": target_relations_for_links,
            "target_related_relations_for_entity": target_related_relations_for_entity,
            "target_related_relations_for_links": target_related_relations_for_links,
        },
    }


def _process_detection_uncached_optimized(
    target_users: Dict[str, float],
    related_users: Dict[str, float],
    entity_detection_config: Dict[str, Any],
    link_detection_config: Dict[str, Any],
    snapshot_time: Optional[str] = None,
    detect_entity: bool = True,
    detect_link: bool = True,
    coin: str = "ACT",
) -> Dict[str, Any]:
    logger.info(
        f"Starting optimized detection process (Entity: {detect_entity}, Link: {detect_link})..."
    )

    target_relations_for_entity = {}
    target_relations_for_links = {}
    target_related_relations_for_entity = {}
    target_related_relations_for_links = {}

    need_network_detection = (
        detect_entity and entity_detection_config.get("enable_network_based", False)
    ) or (detect_link and link_detection_config.get("enable_network_based", False))
    need_similarity_detection = (
        detect_entity and entity_detection_config.get("enable_similarity_based", False)
    ) or (detect_link and link_detection_config.get("enable_similarity_based", False))

    if need_network_detection:
        relation_maps = _collect_prepared_network_relations(
            set(target_users.keys()),
            set(related_users.keys()),
            entity_detection_config,
            link_detection_config,
            snapshot_time,
            detect_entity,
            detect_link,
            coin,
        )
        target_relations_for_entity = relation_maps["target_relations_for_entity"]
        target_relations_for_links = relation_maps["target_relations_for_links"]
        target_related_relations_for_entity = relation_maps[
            "target_related_relations_for_entity"
        ]
        target_related_relations_for_links = relation_maps[
            "target_related_relations_for_links"
        ]
    else:
        logger.info("Network-based detection not enabled. Skipping transfer data loading.")

    if need_similarity_detection:
        entity_similarity_params = entity_detection_config.get("similarity_based_params", {})
        link_similarity_params = link_detection_config.get("similarity_based_params", {})
        need_action_sequence = (
            detect_entity
            and entity_detection_config.get("enable_similarity_based", False)
            and entity_similarity_params.get("enable_trading_action_sequence", False)
        ) or (
            detect_link
            and link_detection_config.get("enable_similarity_based", False)
            and link_similarity_params.get("enable_trading_action_sequence", False)
        )
        need_balance_sequence = (
            detect_entity
            and entity_detection_config.get("enable_similarity_based", False)
            and entity_similarity_params.get("enable_balance_sequence", False)
        ) or (
            detect_link
            and link_detection_config.get("enable_similarity_based", False)
            and link_similarity_params.get("enable_balance_sequence", False)
        )
        need_earning_sequence = (
            detect_entity
            and entity_detection_config.get("enable_similarity_based", False)
            and entity_similarity_params.get("enable_earning_sequence", False)
        ) or (
            detect_link
            and link_detection_config.get("enable_similarity_based", False)
            and link_similarity_params.get("enable_earning_sequence", False)
        )

        if need_action_sequence:
            user_actions = _load_prepared_user_actions(
                coin, list(target_users.keys()) + list(related_users.keys())
            )
            if user_actions:
                target_seqs = {u: user_actions[u] for u in target_users if u in user_actions}
                related_seqs = {u: user_actions[u] for u in related_users if u in user_actions}

                if detect_entity and entity_detection_config.get("enable_similarity_based", False):
                    params = entity_detection_config.get("similarity_based_params", {})
                    if params.get("enable_trading_action_sequence", False):
                        matches = detect_trading_action_sequence_optimized(
                            target_seqs, related_seqs, params
                        )
                        _merge_detection_results_optimized(
                            target_relations_for_entity, matches["tt"]
                        )
                        _merge_detection_results_optimized(
                            target_related_relations_for_entity, matches["tr"]
                        )

                if detect_link and link_detection_config.get("enable_similarity_based", False):
                    params = link_detection_config.get("similarity_based_params", {})
                    if params.get("enable_trading_action_sequence", False):
                        matches = detect_trading_action_sequence_optimized(
                            target_seqs, related_seqs, params
                        )
                        _merge_detection_results_optimized(
                            target_relations_for_links, matches["tt"]
                        )
                        _merge_detection_results_optimized(
                            target_related_relations_for_links, matches["tr"]
                        )

        if need_balance_sequence:
            if detect_entity and entity_detection_config.get("enable_similarity_based", False):
                params = entity_detection_config.get("similarity_based_params", {})
                if params.get("enable_balance_sequence", False):
                    matches = detect_balance_sequence_optimized(
                        list(target_users.keys()),
                        list(related_users.keys()),
                        params,
                        snapshot_time,
                        coin,
                    )
                    _merge_detection_results_optimized(
                        target_relations_for_entity, matches["tt"], "balance_sequence"
                    )
                    _merge_detection_results_optimized(
                        target_related_relations_for_entity, matches["tr"], "balance_sequence"
                    )

            if detect_link and link_detection_config.get("enable_similarity_based", False):
                params = link_detection_config.get("similarity_based_params", {})
                if params.get("enable_balance_sequence", False):
                    matches = detect_balance_sequence_optimized(
                        list(target_users.keys()),
                        list(related_users.keys()),
                        params,
                        snapshot_time,
                        coin,
                    )
                    _merge_detection_results_optimized(
                        target_relations_for_links, matches["tt"], "balance_sequence"
                    )
                    _merge_detection_results_optimized(
                        target_related_relations_for_links, matches["tr"], "balance_sequence"
                    )

        if need_earning_sequence:
            if detect_entity and entity_detection_config.get("enable_similarity_based", False):
                params = entity_detection_config.get("similarity_based_params", {})
                if params.get("enable_earning_sequence", False):
                    matches = detect_earning_sequence_optimized(
                        list(target_users.keys()),
                        list(related_users.keys()),
                        params,
                        snapshot_time,
                        coin,
                    )
                    _merge_detection_results_optimized(
                        target_relations_for_entity, matches["tt"], "earning_sequence"
                    )
                    _merge_detection_results_optimized(
                        target_related_relations_for_entity, matches["tr"], "earning_sequence"
                    )

            if detect_link and link_detection_config.get("enable_similarity_based", False):
                params = link_detection_config.get("similarity_based_params", {})
                if params.get("enable_earning_sequence", False):
                    matches = detect_earning_sequence_optimized(
                        list(target_users.keys()),
                        list(related_users.keys()),
                        params,
                        snapshot_time,
                        coin,
                    )
                    _merge_detection_results_optimized(
                        target_relations_for_links, matches["tt"], "earning_sequence"
                    )
                    _merge_detection_results_optimized(
                        target_related_relations_for_links, matches["tr"], "earning_sequence"
                    )

    logger.info("Optimized detection process completed.")
    return _build_detection_response_from_relations(
        target_relations_for_entity,
        target_relations_for_links,
        target_related_relations_for_entity,
        target_related_relations_for_links,
    )


def _process_detection_uncached(
    target_users: Dict[str, float],
    related_users: Dict[str, float],
    entity_detection_config: Dict[str, Any],
    link_detection_config: Dict[str, Any],
    snapshot_time: Optional[str] = None,
    detect_entity: bool = True,
    detect_link: bool = True,
    coin: str = "ACT",
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
        detect_entity and entity_detection_config.get("enable_network_based", False)
    ) or (detect_link and link_detection_config.get("enable_network_based", False))

    need_similarity_detection = (
        detect_entity and entity_detection_config.get("enable_similarity_based", False)
    ) or (detect_link and link_detection_config.get("enable_similarity_based", False))

    # Load Transfer Data
    if need_network_detection:
        try:
            df_transfers = None
            sorted_transfers_path = os.path.join(get_data_dir(coin), "sorted_transfers.csv")
            if os.path.exists(sorted_transfers_path):
                # 0. Load Pre-sorted Data
                df_transfers = _load_csv_file(sorted_transfers_path)

                # preprocess_data.py: timestamp, from_owner, from_owner_label, to_owner, to_owner_label, amount
                # existing: block_time, from_owner, to_owner, amount_display

                if df_transfers is not None and snapshot_time and "timestamp" in df_transfers.columns:
                    try:
                        snap_dt = pd.to_datetime(snapshot_time)
                        df_transfers["timestamp_dt"] = pd.to_datetime(
                            df_transfers["timestamp"], errors="coerce"
                        )
                        df_transfers = df_transfers[df_transfers["timestamp_dt"] <= snap_dt]
                        # Already sorted by time
                    except Exception as e:
                        logger.warning(f"Time filtering failed: {e}")
            else:
                logger.warning(f"Transfer CSV not found at {sorted_transfers_path}")

            # Check if direct transfer is needed
            need_direct_transfer = (
                detect_entity
                and entity_detection_config.get("transfer_network_based_params", {}).get(
                    "enable_direct_transfer", False
                )
            ) or (
                detect_link
                and link_detection_config.get("transfer_network_based_params", {}).get(
                    "enable_direct_transfer", False
                )
            )

            need_funding_relationship = (
                detect_entity
                and entity_detection_config.get("transfer_network_based_params", {}).get(
                    "enable_funding_relationship", False
                )
            ) or (
                detect_link
                and link_detection_config.get("transfer_network_based_params", {}).get(
                    "enable_funding_relationship", False
                )
            )

            need_same_sender = (
                detect_entity
                and entity_detection_config.get("transfer_network_based_params", {}).get(
                    "enable_same_sender", False
                )
            ) or (
                detect_link
                and link_detection_config.get("transfer_network_based_params", {}).get(
                    "enable_same_sender", False
                )
            )

            need_same_recipient = (
                detect_entity
                and entity_detection_config.get("transfer_network_based_params", {}).get(
                    "enable_same_recipient", False
                )
            ) or (
                detect_link
                and link_detection_config.get("transfer_network_based_params", {}).get(
                    "enable_same_recipient", False
                )
            )

            # Pre-calculate sets for faster lookup
            target_user_set = set(target_users.keys())
            related_user_set = set(related_users.keys())

            # Helper to generate key: "addr1-addr2" (sorted)
            def get_key(u, v):
                return "-".join(sorted([str(u), str(v)]))

            # 1. Direct Transfer
            if need_direct_transfer and df_transfers is not None:
                # Temporary storage for aggregation
                # key -> {'count': 0, 'volume': 0.0}
                tt_stats = {}  # Target-Target
                tr_stats = {}  # Target-Related (or Related-Target)

                for _, row in df_transfers.iterrows():
                    u = row.get("from_owner")
                    v = row.get("to_owner")

                    if pd.isna(u) or pd.isna(v):
                        continue

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
                            vol = float(row.get("amount", 0) or 0)
                        except (TypeError, ValueError):
                            vol = 0.0

                        k = get_key(u, v)

                        stats_map = tt_stats if is_tt else tr_stats
                        if k not in stats_map:
                            stats_map[k] = {"count": 0, "volume": 0.0}

                        stats_map[k]["count"] += 1
                        stats_map[k]["volume"] += vol

                # Helper to check if a relation meets criteria
                def check_criteria(count, volume, config):
                    net_params = config.get("transfer_network_based_params", {})
                    if not config.get("enable_network_based", False) or not net_params.get(
                        "enable_direct_transfer", False
                    ):
                        return False, None

                    direct_params = net_params.get("direct_transfer_params", {})
                    min_count = direct_params.get("min_tx_count", 0)
                    min_volume = direct_params.get("min_tx_volume", 0)
                    enable_count = direct_params.get("enable_min_count", True)
                    enable_volume = direct_params.get("enable_min_volume", True)

                    reason_desc = []

                    # Logic:
                    # If enabled, criteria MUST be met.
                    count_passed = True
                    if enable_count:
                        if count < min_count:
                            count_passed = False
                        else:
                            reason_desc.append(f"count >= {min_count} ({count})")

                    volume_passed = True
                    if enable_volume:
                        if volume < min_volume:
                            volume_passed = False
                        else:
                            reason_desc.append(f"volume >= {min_volume} ({volume:.2f})")

                    if count_passed and volume_passed:
                        return True, ", ".join(reason_desc)

                    return False, None

                # Convert stats to the required list-of-reasons format based on config
                def stats_to_relations(stats_map, config):
                    res = {}
                    for k, v in stats_map.items():
                        passed, desc = check_criteria(v["count"], v["volume"], config)
                        if passed:
                            res[k] = [
                                {
                                    "type": "direct_transfer",
                                    "count": v["count"],
                                    "volume": v["volume"],
                                    "description": f"Direct transfer: {desc}",
                                }
                            ]
                    return res

                # 1. target_relations_for_entity
                if (
                    detect_entity
                    and entity_detection_config.get("enable_network_based", False)
                    and entity_detection_config.get("transfer_network_based_params", {}).get(
                        "enable_direct_transfer", False
                    )
                ):
                    new_tt_entity = stats_to_relations(tt_stats, entity_detection_config)
                    merge_relations(target_relations_for_entity, new_tt_entity)

                # 2. target_relations_for_links
                if (
                    detect_link
                    and link_detection_config.get("enable_network_based", False)
                    and link_detection_config.get("transfer_network_based_params", {}).get(
                        "enable_direct_transfer", False
                    )
                ):
                    new_tt_link = stats_to_relations(tt_stats, link_detection_config)
                    merge_relations(target_relations_for_links, new_tt_link)

                # 3. target_related_relations_for_entity
                if (
                    detect_entity
                    and entity_detection_config.get("enable_network_based", False)
                    and entity_detection_config.get("transfer_network_based_params", {}).get(
                        "enable_direct_transfer", False
                    )
                ):
                    new_tr_entity = stats_to_relations(tr_stats, entity_detection_config)
                    merge_relations(target_related_relations_for_entity, new_tr_entity)

                # 4. target_related_relations_for_links
                if (
                    detect_link
                    and link_detection_config.get("enable_network_based", False)
                    and link_detection_config.get("transfer_network_based_params", {}).get(
                        "enable_direct_transfer", False
                    )
                ):
                    new_tr_link = stats_to_relations(tr_stats, link_detection_config)
                    merge_relations(target_related_relations_for_links, new_tr_link)

            # 2. Funding / Same Sender / Recipient
            if need_funding_relationship or need_same_sender or need_same_recipient:
                all_tracked_users = target_user_set.union(related_user_set)

                funding_senders = {}
                recipients = {}

                USER_RELATIONS_PATH = os.path.join(get_data_dir(coin), "user_relations.json")
                user_relations = _load_json_file(USER_RELATIONS_PATH, {})
                if user_relations:
                    try:
                        json_senders = user_relations.get("senders", {})
                        json_recipients = user_relations.get("recipients", {})

                        snap_dt = None
                        if snapshot_time:
                            try:
                                snap_dt = pd.to_datetime(snapshot_time)
                            except (ValueError, TypeError):
                                pass

                        for u in all_tracked_users:
                            # Get Senders
                            if u in json_senders:
                                u_senders = json_senders[u]
                                if snap_dt:
                                    valid_s = []
                                    for r in u_senders:
                                        try:
                                            if pd.to_datetime(r["timestamp"]) <= snap_dt:
                                                valid_s.append(r["address"])
                                            else:
                                                break  # Sorted by time
                                        except (ValueError, TypeError, KeyError):
                                            pass
                                    if valid_s:
                                        funding_senders[u] = valid_s
                                else:
                                    funding_senders[u] = [r["address"] for r in u_senders]

                            # Get Recipients
                            if u in json_recipients:
                                u_recipients = json_recipients[u]
                                if snap_dt:
                                    valid_r = []
                                    for r in u_recipients:
                                        try:
                                            if pd.to_datetime(r["timestamp"]) <= snap_dt:
                                                valid_r.append(r["address"])
                                            else:
                                                break
                                        except (ValueError, TypeError, KeyError):
                                            pass
                                    if valid_r:
                                        recipients[u] = valid_r
                                else:
                                    recipients[u] = [r["address"] for r in u_recipients]

                    except Exception as e:
                        logger.error(f"Error processing user relations: {e}")
                else:
                    logger.warning(f"User relations file not found at {USER_RELATIONS_PATH}")

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
                            s = funding_senders[u][0]  # First sender

                            if s in target_user_set:
                                k = get_key(u, s)
                                if k not in funding_tt:
                                    funding_tt[k] = []
                                funding_tt[k].append(
                                    {
                                        "type": "funding",
                                        "description": f"Direct funded by {s}",
                                        "direction": f"{s}->{u}",
                                    }
                                )
                            elif s in related_user_set:
                                k = get_key(u, s)
                                if k not in funding_tr:
                                    funding_tr[k] = []
                                funding_tr[k].append(
                                    {
                                        "type": "funding",
                                        "description": f"Direct funded by {s}",
                                        "direction": f"{s}->{u}",
                                    }
                                )

                    # B. Co-funded (Same First Sender)
                    first_sender_to_users = {}
                    for u, senders in funding_senders.items():
                        if not senders:
                            continue
                        s = senders[0]
                        if s not in first_sender_to_users:
                            first_sender_to_users[s] = []
                        first_sender_to_users[s].append(u)

                    for s, users in first_sender_to_users.items():
                        if len(users) < 2:
                            continue
                        users = sorted(list(set(users)))

                        for i in range(len(users)):
                            for j in range(i + 1, len(users)):
                                u1, u2 = users[i], users[j]

                                u1_t = u1 in target_user_set
                                u2_t = u2 in target_user_set
                                u1_r = u1 in related_user_set
                                u2_r = u2 in related_user_set

                                if u1_t and u2_t:
                                    k = get_key(u1, u2)
                                    if k not in funding_tt:
                                        funding_tt[k] = []
                                    funding_tt[k].append(
                                        {
                                            "type": "co_funded",
                                            "description": f"Co-funded by {s}",
                                            "sender": s,
                                        }
                                    )
                                elif (u1_t and u2_r) or (u1_r and u2_t):
                                    k = get_key(u1, u2)
                                    if k not in funding_tr:
                                        funding_tr[k] = []
                                    funding_tr[k].append(
                                        {
                                            "type": "co_funded",
                                            "description": f"Co-funded by {s}",
                                            "sender": s,
                                        }
                                    )

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
                        if len(users) < 2:
                            continue
                        users = sorted(list(set(users)))

                        for i in range(len(users)):
                            for j in range(i + 1, len(users)):
                                u1, u2 = users[i], users[j]

                                u1_t = u1 in target_user_set
                                u2_t = u2 in target_user_set
                                u1_r = u1 in related_user_set
                                u2_r = u2 in related_user_set

                                if u1_t and u2_t:
                                    k = get_key(u1, u2)
                                    if k not in same_sender_tt:
                                        same_sender_tt[k] = []
                                    same_sender_tt[k].append(
                                        {
                                            "type": "same_sender",
                                            "description": f"Same sender: {s}",
                                            "sender": s,
                                        }
                                    )
                                elif (u1_t and u2_r) or (u1_r and u2_t):
                                    k = get_key(u1, u2)
                                    if k not in same_sender_tr:
                                        same_sender_tr[k] = []
                                    same_sender_tr[k].append(
                                        {
                                            "type": "same_sender",
                                            "description": f"Same sender: {s}",
                                            "sender": s,
                                        }
                                    )

                # 3. Same Recipient
                if need_same_recipient:
                    recipient_to_users = {}
                    for u, recips in recipients.items():
                        for r in recips:
                            if r not in recipient_to_users:
                                recipient_to_users[r] = []
                            recipient_to_users[r].append(u)

                    for r, users in recipient_to_users.items():
                        if len(users) < 2:
                            continue
                        users = sorted(list(set(users)))

                        for i in range(len(users)):
                            for j in range(i + 1, len(users)):
                                u1, u2 = users[i], users[j]

                                u1_t = u1 in target_user_set
                                u2_t = u2 in target_user_set
                                u1_r = u1 in related_user_set
                                u2_r = u2 in related_user_set

                                if u1_t and u2_t:
                                    k = get_key(u1, u2)
                                    # Use same_sender dicts for simplicity or create new ones?
                                    # reusing merging logic below
                                    if k not in same_sender_tt:
                                        same_sender_tt[k] = []  # reusing key space
                                    same_sender_tt[k].append(
                                        {
                                            "type": "same_recipient",
                                            "description": f"Same recipient: {r}",
                                            "recipient": r,
                                        }
                                    )
                                elif (u1_t and u2_r) or (u1_r and u2_t):
                                    k = get_key(u1, u2)
                                    if k not in same_sender_tr:
                                        same_sender_tr[k] = []
                                    same_sender_tr[k].append(
                                        {
                                            "type": "same_recipient",
                                            "description": f"Same recipient: {r}",
                                            "recipient": r,
                                        }
                                    )

                # Merge Funding Results
                if detect_entity:
                    if entity_detection_config.get("transfer_network_based_params", {}).get(
                        "enable_funding_relationship", False
                    ):
                        merge_relations(target_relations_for_entity, funding_tt)
                        merge_relations(target_related_relations_for_entity, funding_tr)
                    if entity_detection_config.get("transfer_network_based_params", {}).get(
                        "enable_same_sender", False
                    ) or entity_detection_config.get("transfer_network_based_params", {}).get(
                        "enable_same_recipient", False
                    ):
                        merge_relations(target_relations_for_entity, same_sender_tt)
                        merge_relations(target_related_relations_for_entity, same_sender_tr)

                if detect_link:
                    if link_detection_config.get("transfer_network_based_params", {}).get(
                        "enable_funding_relationship", False
                    ):
                        merge_relations(target_relations_for_links, funding_tt)
                        merge_relations(target_related_relations_for_links, funding_tr)
                    if link_detection_config.get("transfer_network_based_params", {}).get(
                        "enable_same_sender", False
                    ) or link_detection_config.get("transfer_network_based_params", {}).get(
                        "enable_same_recipient", False
                    ):
                        merge_relations(target_relations_for_links, same_sender_tt)
                        merge_relations(target_related_relations_for_links, same_sender_tr)

        except Exception as e:
            logger.error(f"Error loading data: {e}")
    else:
        logger.info("Network-based detection not enabled. Skipping transfer data loading.")

    # similarity based detection
    if need_similarity_detection:
        entity_similarity_params = entity_detection_config.get("similarity_based_params", {})
        link_similarity_params = link_detection_config.get("similarity_based_params", {})
        need_action_sequence = (
            detect_entity
            and entity_detection_config.get("enable_similarity_based", False)
            and entity_similarity_params.get("enable_trading_action_sequence", False)
        ) or (
            detect_link
            and link_detection_config.get("enable_similarity_based", False)
            and link_similarity_params.get("enable_trading_action_sequence", False)
        )
        need_balance_sequence = (
            detect_entity
            and entity_detection_config.get("enable_similarity_based", False)
            and entity_similarity_params.get("enable_balance_sequence", False)
        ) or (
            detect_link
            and link_detection_config.get("enable_similarity_based", False)
            and link_similarity_params.get("enable_balance_sequence", False)
        )
        need_earning_sequence = (
            detect_entity
            and entity_detection_config.get("enable_similarity_based", False)
            and entity_similarity_params.get("enable_earning_sequence", False)
        ) or (
            detect_link
            and link_detection_config.get("enable_similarity_based", False)
            and link_similarity_params.get("enable_earning_sequence", False)
        )

        USER_ACTIONS_PATH = os.path.join(get_data_dir(coin), "user_actions.json")

        # Helper to merge detection results
        def merge_detection_results(base_map, new_results, rel_type="trading_action_sequence"):
            for k, res in new_results.items():
                if k not in base_map:
                    base_map[k] = []
                base_map[k].append(
                    {
                        "type": rel_type,
                        "score": res["score"],
                        "description": f"Found matching sequence ({rel_type}): {res['actions_summary']}...",
                        "details": res,
                    }
                )

        if need_action_sequence:
            # Load user actions
            user_actions = _load_json_file(USER_ACTIONS_PATH, {})

            if user_actions:
                # Filter for relevant users
                target_seqs = {u: user_actions[u] for u in target_users if u in user_actions}
                related_seqs = {u: user_actions[u] for u in related_users if u in user_actions}

                # 1. Entity Detection
                if detect_entity and entity_detection_config.get("enable_similarity_based", False):
                    params = entity_detection_config.get("similarity_based_params", {})
                    if params.get("enable_trading_action_sequence", False):
                        matches = detect_trading_action_sequence(target_seqs, related_seqs, params)
                        merge_detection_results(target_relations_for_entity, matches["tt"])
                        merge_detection_results(target_related_relations_for_entity, matches["tr"])

                # 2. Link Detection
                if detect_link and link_detection_config.get("enable_similarity_based", False):
                    params = link_detection_config.get("similarity_based_params", {})
                    if params.get("enable_trading_action_sequence", False):
                        matches = detect_trading_action_sequence(target_seqs, related_seqs, params)
                        merge_detection_results(target_relations_for_links, matches["tt"])
                        merge_detection_results(target_related_relations_for_links, matches["tr"])

        if need_balance_sequence:
            # 1. Entity Detection
            if detect_entity and entity_detection_config.get("enable_similarity_based", False):
                params = entity_detection_config.get("similarity_based_params", {})
                if params.get("enable_balance_sequence", False):
                    matches = detect_balance_sequence(
                        list(target_users.keys()),
                        list(related_users.keys()),
                        params,
                        snapshot_time,
                        coin,
                    )
                    merge_detection_results(
                        target_relations_for_entity, matches["tt"], "balance_sequence"
                    )
                    merge_detection_results(
                        target_related_relations_for_entity, matches["tr"], "balance_sequence"
                    )

            # 2. Link Detection
            if detect_link and link_detection_config.get("enable_similarity_based", False):
                params = link_detection_config.get("similarity_based_params", {})
                if params.get("enable_balance_sequence", False):
                    matches = detect_balance_sequence(
                        list(target_users.keys()),
                        list(related_users.keys()),
                        params,
                        snapshot_time,
                        coin,
                    )
                    merge_detection_results(
                        target_relations_for_links, matches["tt"], "balance_sequence"
                    )
                    merge_detection_results(
                        target_related_relations_for_links, matches["tr"], "balance_sequence"
                    )

        if need_earning_sequence:
            # 1. Entity Detection
            if detect_entity and entity_detection_config.get("enable_similarity_based", False):
                params = entity_detection_config.get("similarity_based_params", {})
                if params.get("enable_earning_sequence", False):
                    matches = detect_earning_sequence(
                        list(target_users.keys()),
                        list(related_users.keys()),
                        params,
                        snapshot_time,
                        coin,
                    )
                    merge_detection_results(
                        target_relations_for_entity, matches["tt"], "earning_sequence"
                    )
                    merge_detection_results(
                        target_related_relations_for_entity, matches["tr"], "earning_sequence"
                    )

            # 2. Link Detection
            if detect_link and link_detection_config.get("enable_similarity_based", False):
                params = link_detection_config.get("similarity_based_params", {})
                if params.get("enable_earning_sequence", False):
                    matches = detect_earning_sequence(
                        list(target_users.keys()),
                        list(related_users.keys()),
                        params,
                        snapshot_time,
                        coin,
                    )
                    merge_detection_results(
                        target_relations_for_links, matches["tt"], "earning_sequence"
                    )
                    merge_detection_results(
                        target_related_relations_for_links, matches["tr"], "earning_sequence"
                    )

    logger.info("Detection process completed.")

    response = {}

    # Form entities based on relations
    # We only care about entity detection relations for this part
    # target_relations_for_entity (TT) and target_related_relations_for_entity (TR)

    # Use Union-Find or BFS/DFS to find connected components
    adj = {}

    # Helper to add edge
    def add_edge(u, v, rel_info):
        if u not in adj:
            adj[u] = []
        if v not in adj:
            adj[v] = []
        adj[u].append((v, rel_info))
        adj[v].append((u, rel_info))

    # Process TT relations
    for key, relations in target_relations_for_entity.items():
        # key is "u1-u2"
        parts = key.split("-")
        if len(parts) >= 2:
            u1, u2 = parts[0], parts[1]
            # Pass all relations between these two users
            add_edge(u1, u2, relations)

    # Process TR relations
    for key, relations in target_related_relations_for_entity.items():
        # key is "u1-u2"
        parts = key.split("-")
        if len(parts) >= 2:
            u1, u2 = parts[0], parts[1]
            add_edge(u1, u2, relations)

    # Find connected components
    visited = set()
    entities = []

    for user in adj:
        if user not in visited:
            # Start a new component
            component_users = set()

            queue = [user]
            visited.add(user)
            component_users.add(user)

            while queue:
                curr = queue.pop(0)

                if curr in adj:
                    for neighbor, rels in adj[curr]:
                        # Check if neighbor visited
                        if neighbor not in visited:
                            visited.add(neighbor)
                            component_users.add(neighbor)
                            queue.append(neighbor)

            # Re-traverse to collect unique edges for this component
            comp_rels = []

            # Use a set to avoid duplicates if we process keys
            processed_keys = set()

            # Check TT map
            for k, v in target_relations_for_entity.items():
                if k in processed_keys:
                    continue
                parts = k.split("-")
                if len(parts) >= 2:
                    u1, u2 = parts[0], parts[1]
                    if u1 in component_users and u2 in component_users:
                        comp_rels.extend(v)
                        processed_keys.add(k)

            # Check TR map
            for k, v in target_related_relations_for_entity.items():
                if k in processed_keys:
                    continue
                parts = k.split("-")
                if len(parts) >= 2:
                    u1, u2 = parts[0], parts[1]
                    if u1 in component_users and u2 in component_users:
                        comp_rels.extend(v)
                        processed_keys.add(k)

            entities.append({"users": list(component_users), "relations": comp_rels})

    response["entity_results"] = entities

    # DEBUG: Return intermediate relations for frontend inspection
    response["relations"] = {
        "target_relations_for_entity": target_relations_for_entity,
        "target_relations_for_links": target_relations_for_links,
        "target_related_relations_for_entity": target_related_relations_for_entity,
        "target_related_relations_for_links": target_related_relations_for_links,
    }

    return response


def detect_trading_action_sequence(target_users_sequences, related_users_sequences, params):
    # Extract actual parameters, handling potential nesting
    config = params.get("trading_action_sequence_params", params)

    type = config.get("type", "action_only")
    min_seq_length = config.get("min_seq_length", 5)
    max_time_diff = config.get("max_time_diff", 2)
    amount_similarity = config.get("amount_similarity", 0.7)
    price_similarity = config.get("price_similarity", 0.7)

    def compare_actions(a1, a2):
        # Action type must match
        act1 = a1.get("action_type", a1.get("action"))
        act2 = a2.get("action_type", a2.get("action"))
        if act1 != act2:
            return False

        if type == "action_only":
            return True

        try:
            amt1 = float(a1.get("amount", 0))
            amt2 = float(a2.get("amount", 0))

            # Check amount
            if "amount" in type:
                if max(amt1, amt2) == 0:
                    sim = 1.0 if amt1 == amt2 else 0.0
                else:
                    sim = 1.0 - abs(amt1 - amt2) / max(amt1, amt2)
                if sim < amount_similarity:
                    return False

            # Check price
            if "price" in type:
                p1 = float(a1.get("price", 0))
                p2 = float(a2.get("price", 0))
                if max(p1, p2) == 0:
                    sim = 1.0 if p1 == p2 else 0.0
                else:
                    sim = 1.0 - abs(p1 - p2) / max(p1, p2)
                if sim < price_similarity:
                    return False

            return True
        except Exception:
            return False

    # Helper to parse timestamps
    def parse_seq(seq):
        parsed = []
        for item in seq:
            try:
                # Parse timestamp to epoch seconds for easy comparison
                ts = pd.to_datetime(item["timestamp"]).timestamp()
                parsed.append({**item, "_ts": ts})
            except (ValueError, TypeError, KeyError):
                pass
        return parsed

    # Pre-parse sequences
    t_parsed = {u: parse_seq(s) for u, s in target_users_sequences.items()}
    r_parsed = {u: parse_seq(s) for u, s in related_users_sequences.items()}

    results = {"tt": {}, "tr": {}}

    def get_key(u, v):
        return "-".join(sorted([str(u), str(v)]))

    def find_match(u1, u2, s1, s2):
        n1 = len(s1)
        n2 = len(s2)
        if n1 == 0 or n2 == 0:
            return None

        # 1. Collect all valid matches (action match + time constraint)
        # We use a sliding window for efficiency
        matches = []  # List of (i, j)

        start_j = 0
        end_j = 0

        for i in range(n1):
            u = s1[i]
            t = u["_ts"]

            # Adjust window [t - max, t + max]
            # s2[j] sorted by time

            # Move start_j to first valid
            while start_j < n2 and s2[start_j]["_ts"] < t - max_time_diff:
                start_j += 1

            # Move end_j to first invalid after window
            while end_j < n2 and s2[end_j]["_ts"] <= t + max_time_diff:
                end_j += 1

            if start_j >= n2:
                break  # No more matches possible

            for j in range(start_j, end_j):
                if compare_actions(u, s2[j]):
                    matches.append((i, j))

        if not matches:
            return None

        # 2. Find Longest Increasing Subsequence (LIS) on j
        # Sort by i ascending, then j descending (to avoid picking multiple j for same i)
        matches.sort(key=lambda x: (x[0], -x[1]))

        # LIS algorithm with path reconstruction
        # tails[k] stores the smallest tail of all increasing subsequences of length k+1 in `matches_j`
        # To reconstruct, we need to track predecessors.
        # standard O(N log N) LIS usually just gives length.
        # For reconstruction, we can use the P array approach.

        tails = []  # stores indices into `matches`
        parent = [-1] * len(matches)  # parent[k] = index of predecessor of matches[k] in the LIS

        for k in range(len(matches)):
            j_val = matches[k][1]

            # We perform LIS on the j values
            # Binary search in tails based on matches[tail_idx][1]
            # We want to find insertion point for j_val

            # Custom bisect to handle the indirection
            left, right = 0, len(tails)
            while left < right:
                mid = (left + right) // 2
                if matches[tails[mid]][1] < j_val:
                    left = mid + 1
                else:
                    right = mid

            if left == len(tails):
                tails.append(k)
            else:
                tails[left] = k

            if left > 0:
                parent[k] = tails[left - 1]

        length = len(tails)

        if length < min_seq_length:
            return None

        # Reconstruct path
        path_indices = []
        curr = tails[-1]
        while curr != -1:
            path_indices.append(curr)
            curr = parent[curr]
        path_indices.reverse()

        final_matches = [matches[k] for k in path_indices]

        # Create result object
        first_m = final_matches[0]
        # last_m = final_matches[-1]

        # Extract actions for summary
        actions_str = ",".join(
            [str(s1[i].get("action_type", s1[i].get("action"))) for i, j in final_matches[:5]]
        )
        if length > 5:
            actions_str += "..."

        return {
            "u1": u1,
            "u2": u2,
            "start_time_1": s1[first_m[0]]["timestamp"],
            "start_time_2": s2[first_m[1]]["timestamp"],
            "length": length,
            "actions_summary": actions_str,
            "score": length,
        }

    # TT Matches (Target-Target)
    target_users = list(t_parsed.keys())
    for i in range(len(target_users)):
        for j in range(i + 1, len(target_users)):
            u1, u2 = target_users[i], target_users[j]
            match = find_match(u1, u2, t_parsed[u1], t_parsed[u2])
            if match:
                k = get_key(u1, u2)
                results["tt"][k] = match

    # TR Matches (Target-Related)
    related_users = list(r_parsed.keys())
    for u1 in target_users:
        for u2 in related_users:
            if u1 == u2:
                continue
            match = find_match(u1, u2, t_parsed[u1], r_parsed[u2])
            if match:
                k = get_key(u1, u2)
                results["tr"][k] = match

    logger.info(f"Found {len(results['tt'])} TT matches and {len(results['tr'])} TR matches")

    return results


def detect_trading_action_sequence_optimized(
    target_users_sequences, related_users_sequences, params
):
    config = params.get("trading_action_sequence_params", params)

    sequence_type = config.get("type", "action_only")
    min_seq_length = config.get("min_seq_length", 5)
    max_time_diff = config.get("max_time_diff", 2)
    amount_similarity = config.get("amount_similarity", 0.7)
    price_similarity = config.get("price_similarity", 0.7)

    def compare_actions(a1, a2):
        act1 = a1.get("action_type", a1.get("action"))
        act2 = a2.get("action_type", a2.get("action"))
        if act1 != act2:
            return False
        if sequence_type == "action_only":
            return True
        try:
            amt1 = float(a1.get("amount", 0))
            amt2 = float(a2.get("amount", 0))
            if "amount" in sequence_type:
                if max(amt1, amt2) == 0:
                    sim = 1.0 if amt1 == amt2 else 0.0
                else:
                    sim = 1.0 - abs(amt1 - amt2) / max(amt1, amt2)
                if sim < amount_similarity:
                    return False

            p1 = float(a1.get("price", 0))
            p2 = float(a2.get("price", 0))
            if "price" in sequence_type:
                if max(p1, p2) == 0:
                    sim = 1.0 if p1 == p2 else 0.0
                else:
                    sim = 1.0 - abs(p1 - p2) / max(p1, p2)
                if sim < price_similarity:
                    return False
            return True
        except Exception:
            return False

    def parse_seq(seq):
        parsed = []
        for item in seq:
            if "_ts" in item:
                parsed.append(item)
                continue
            try:
                parsed.append({**item, "_ts": pd.to_datetime(item["timestamp"]).timestamp()})
            except (ValueError, TypeError, KeyError):
                pass
        return parsed

    t_parsed = {u: parse_seq(s) for u, s in target_users_sequences.items()}
    r_parsed = {u: parse_seq(s) for u, s in related_users_sequences.items()}
    results = {"tt": {}, "tr": {}}

    def find_match(u1, u2, s1, s2):
        n1 = len(s1)
        n2 = len(s2)
        if n1 == 0 or n2 == 0:
            return None

        matches = []
        start_j = 0
        end_j = 0
        for i, action in enumerate(s1):
            ts = action["_ts"]
            while start_j < n2 and s2[start_j]["_ts"] < ts - max_time_diff:
                start_j += 1
            while end_j < n2 and s2[end_j]["_ts"] <= ts + max_time_diff:
                end_j += 1
            if start_j >= n2:
                break
            for j in range(start_j, end_j):
                if compare_actions(action, s2[j]):
                    matches.append((i, j))

        if not matches:
            return None

        matches.sort(key=lambda x: (x[0], -x[1]))
        tails = []
        parent = [-1] * len(matches)

        for k, match in enumerate(matches):
            j_val = match[1]
            left, right = 0, len(tails)
            while left < right:
                mid = (left + right) // 2
                if matches[tails[mid]][1] < j_val:
                    left = mid + 1
                else:
                    right = mid
            if left == len(tails):
                tails.append(k)
            else:
                tails[left] = k
            if left > 0:
                parent[k] = tails[left - 1]

        length = len(tails)
        if length < min_seq_length:
            return None

        path_indices = []
        curr = tails[-1]
        while curr != -1:
            path_indices.append(curr)
            curr = parent[curr]
        path_indices.reverse()
        final_matches = [matches[k] for k in path_indices]
        first_m = final_matches[0]
        actions_str = ",".join(
            [
                str(s1[i].get("action_type", s1[i].get("action")))
                for i, _j in final_matches[:5]
            ]
        )
        if length > 5:
            actions_str += "..."

        return {
            "u1": u1,
            "u2": u2,
            "start_time_1": s1[first_m[0]]["timestamp"],
            "start_time_2": s2[first_m[1]]["timestamp"],
            "length": length,
            "actions_summary": actions_str,
            "score": length,
        }

    target_users = list(t_parsed.keys())
    for i in range(len(target_users)):
        for j in range(i + 1, len(target_users)):
            u1, u2 = target_users[i], target_users[j]
            match = find_match(u1, u2, t_parsed[u1], t_parsed[u2])
            if match:
                results["tt"][_relation_key(u1, u2)] = match

    related_users = list(r_parsed.keys())
    for u1 in target_users:
        for u2 in related_users:
            if u1 == u2:
                continue
            match = find_match(u1, u2, t_parsed[u1], r_parsed[u2])
            if match:
                results["tr"][_relation_key(u1, u2)] = match

    logger.info(
        f"Found {len(results['tt'])} optimized TT matches and {len(results['tr'])} optimized TR matches"
    )
    return results


def calculate_sequence_correlation(seq1, seq2, freq_str, value_col="balance", snapshot_time=None):
    if not seq1 or not seq2:
        return 0.0

    try:
        df1 = pd.DataFrame(seq1)
        # Convert to datetime and remove timezone info (make naive) to avoid mismatch errors
        df1["timestamp"] = pd.to_datetime(df1["timestamp"])
        if df1["timestamp"].dt.tz is not None:
            df1["timestamp"] = df1["timestamp"].dt.tz_localize(None)
        df1.set_index("timestamp", inplace=True)

        df2 = pd.DataFrame(seq2)
        df2["timestamp"] = pd.to_datetime(df2["timestamp"])
        if df2["timestamp"].dt.tz is not None:
            df2["timestamp"] = df2["timestamp"].dt.tz_localize(None)
        df2.set_index("timestamp", inplace=True)

        # Map frequency for pandas
        pd_freq = freq_str
        if freq_str == "1min":
            pd_freq = "1min"

        # Resample and forward fill to get dense series
        if value_col not in df1.columns or value_col not in df2.columns:
            return 0.0

        # Determine fill method based on value type
        # For 'balance', we forward fill (balance persists until changed)
        # For 'earning', we fill with 0 (no earning in gaps)
        fill_method = "ffill" if value_col == "balance" else "zero"

        if fill_method == "ffill":
            s1 = df1[value_col].resample(pd_freq).ffill()
            s2 = df2[value_col].resample(pd_freq).ffill()
        else:
            s1 = df1[value_col].resample(pd_freq).sum().fillna(0)
            s2 = df2[value_col].resample(pd_freq).sum().fillna(0)

        # Align to common index (intersection or union?)
        # Update: align start time to the later one (max of min_ts) to avoid zero-filling the prefix
        # This handles "no balance at front" case by aligning with the shorter history.
        if s1.empty or s2.empty:
            return 0.0

        min_ts = max(s1.index.min(), s2.index.min())
        max_ts = max(s1.index.max(), s2.index.max())

        # If snapshot_time is provided, clip max_ts
        if snapshot_time:
            snap_dt = pd.to_datetime(snapshot_time)
            if snap_dt.tzinfo is not None:
                snap_dt = snap_dt.tz_localize(None)
            max_ts = min(max_ts, snap_dt)

        if min_ts > max_ts:
            return 0.0

        common_idx = pd.date_range(start=min_ts, end=max_ts, freq=pd_freq)

        if fill_method == "ffill":
            s1 = s1.reindex(common_idx).ffill().fillna(0)
            s2 = s2.reindex(common_idx).ffill().fillna(0)
        else:
            s1 = s1.reindex(common_idx).fillna(0)
            s2 = s2.reindex(common_idx).fillna(0)

        # Use percentage change (rate of change) instead of absolute balance
        # Add a small epsilon to avoid division by zero
        epsilon = 1e-8

        if value_col == "balance":
            # For balance, use rate of change (log returns or pct change)
            s1_processed = s1.diff() / (s1.shift(1).abs() + epsilon)
            s2_processed = s2.diff() / (s2.shift(1).abs() + epsilon)
        else:
            # For earning, use the raw values directly (or standardized)
            # Earnings are already "flow" variables, unlike balance which is "stock"
            # But if we want to detect similar patterns of earnings, direct correlation is better
            s1_processed = s1
            s2_processed = s2

        # Drop the first NaN value caused by diff() (only for balance)
        if value_col == "balance":
            s1_processed = s1_processed.dropna()
            s2_processed = s2_processed.dropna()

        # Handle length < 2 (cannot compute correlation)
        if len(s1_processed) < 2:
            return 0.0

        # Calculate correlation
        # Handle cases where standard deviation is zero (constant balance change)
        if s1_processed.std() == 0 or s2_processed.std() == 0:
            # If both are constant, are they both 0 or non-zero?
            # A simple fallback: if they are both exactly 0 std dev, we might say correlation is 0 or undefined.
            # Let's return 0.0 to avoid warnings and false positives.
            return 0.0

        corr = s1_processed.corr(s2_processed)
        # logger.info(f"Loading balance {corr}")

        if pd.isna(corr):
            return 0.0
        return float(corr)
    except Exception as e:
        logger.error(f"Error calculating correlation: {e}", exc_info=True)
        return 0.0


def detect_balance_sequence(
    target_users_list, related_users_list, params, snapshot_time=None, coin="ACT"
):
    # Extract params
    config = params.get("balance_sequence_params", params)
    granularity = config.get("balance_granularity", "1d").lower()
    threshold = config.get("balance_similarity_threshold", 0.7)

    # Select file based on granularity
    granularity_map = {"1min": "1min", "1h": "1h", "1d": "1d"}
    suffix = granularity_map.get(granularity, "1d")
    filename = f"user_balance_{suffix}.json"
    filepath = os.path.join(get_data_dir(coin), filename)

    logger.info(f"Loading balance data from {filename} for granularity {granularity}")

    all_balances = _load_json_file(filepath)
    if not all_balances:
        return {"tt": {}, "tr": {}}

    # Filter relevant users
    target_seqs = {u: all_balances[u] for u in target_users_list if u in all_balances}
    related_seqs = {u: all_balances[u] for u in related_users_list if u in all_balances}

    results = {"tt": {}, "tr": {}}

    def get_key(u, v):
        return "-".join(sorted([str(u), str(v)]))

    # TT Matches
    t_users = list(target_seqs.keys())
    for i in range(len(t_users)):
        for j in range(i + 1, len(t_users)):
            u1, u2 = t_users[i], t_users[j]
            corr = calculate_sequence_correlation(
                target_seqs[u1], target_seqs[u2], granularity, "balance", snapshot_time
            )
            if corr >= threshold:
                k = get_key(u1, u2)
                results["tt"][k] = {
                    "u1": u1,
                    "u2": u2,
                    "score": corr,
                    "length": 0,  # Not applicable
                    "actions_summary": f"Balance correlation: {corr:.2f}",
                    "details": {"correlation": corr, "granularity": granularity},
                }

    # TR Matches
    r_users = list(related_seqs.keys())
    for u1 in t_users:
        for u2 in r_users:
            if u1 == u2:
                continue
            corr = calculate_sequence_correlation(
                target_seqs[u1], related_seqs[u2], granularity, "balance", snapshot_time
            )
            if corr >= threshold:
                k = get_key(u1, u2)
                results["tr"][k] = {
                    "u1": u1,
                    "u2": u2,
                    "score": corr,
                    "length": 0,
                    "actions_summary": f"Balance correlation: {corr:.2f}",
                    "details": {"correlation": corr, "granularity": granularity},
                }

    logger.info(
        f"Found {len(results['tt'])} TT balance matches and {len(results['tr'])} TR balance matches"
    )
    return results


def detect_earning_sequence(
    target_users_list, related_users_list, params, snapshot_time=None, coin="ACT"
):
    # Extract params
    config = params.get("earning_sequence_params", params)
    granularity = config.get("earning_granularity", "1d").lower()
    threshold = config.get("earning_similarity_threshold", 0.7)

    # Select file based on granularity
    granularity_map = {"1min": "1min", "1h": "1h", "1d": "1d"}
    suffix = granularity_map.get(granularity, "1d")
    filename = f"user_earnings_{suffix}.json"
    filepath = os.path.join(get_data_dir(coin), filename)

    logger.info(f"Loading earning data from {filename} for granularity {granularity}")

    all_earnings = _load_json_file(filepath)
    if not all_earnings:
        return {"tt": {}, "tr": {}}

    # Filter relevant users
    target_seqs = {u: all_earnings[u] for u in target_users_list if u in all_earnings}
    related_seqs = {u: all_earnings[u] for u in related_users_list if u in all_earnings}

    results = {"tt": {}, "tr": {}}

    def get_key(u, v):
        return "-".join(sorted([str(u), str(v)]))

    # TT Matches
    t_users = list(target_seqs.keys())
    for i in range(len(t_users)):
        for j in range(i + 1, len(t_users)):
            u1, u2 = t_users[i], t_users[j]
            corr = calculate_sequence_correlation(
                target_seqs[u1], target_seqs[u2], granularity, "earning", snapshot_time
            )
            if corr >= threshold:
                k = get_key(u1, u2)
                results["tt"][k] = {
                    "u1": u1,
                    "u2": u2,
                    "score": corr,
                    "length": 0,  # Not applicable
                    "actions_summary": f"Earning correlation: {corr:.2f}",
                    "details": {"correlation": corr, "granularity": granularity},
                }

    # TR Matches
    r_users = list(related_seqs.keys())
    for u1 in t_users:
        for u2 in r_users:
            if u1 == u2:
                continue
            corr = calculate_sequence_correlation(
                target_seqs[u1], related_seqs[u2], granularity, "earning", snapshot_time
            )
            if corr >= threshold:
                k = get_key(u1, u2)
                results["tr"][k] = {
                    "u1": u1,
                    "u2": u2,
                    "score": corr,
                    "length": 0,
                    "actions_summary": f"Earning correlation: {corr:.2f}",
                    "details": {"correlation": corr, "granularity": granularity},
                }

    logger.info(
        f"Found {len(results['tt'])} TT earning matches and {len(results['tr'])} TR earning matches"
    )
    return results


def detect_balance_sequence_optimized(
    target_users_list, related_users_list, params, snapshot_time=None, coin="ACT"
):
    return detect_balance_sequence(target_users_list, related_users_list, params, snapshot_time, coin)


def detect_earning_sequence_optimized(
    target_users_list, related_users_list, params, snapshot_time=None, coin="ACT"
):
    return detect_earning_sequence(target_users_list, related_users_list, params, snapshot_time, coin)
