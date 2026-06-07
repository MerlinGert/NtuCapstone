import asyncio
import copy
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from snapshot_service import SnapshotRequest, process_snapshot


SNAPSHOT_TIME = "2024-11-09 23:00:00 UTC"


@dataclass(frozen=True)
class DetectionScenario:
    name: str
    coin: str
    target_users: Dict[str, float]
    related_users: Dict[str, float]
    entity_detection_config: Dict[str, Any]
    link_detection_config: Dict[str, Any]
    snapshot_time: str
    detect_entity: bool = True
    detect_link: bool = True


@dataclass(frozen=True)
class ManipulationScenario:
    name: str
    coin: str
    target_users: Dict[str, float]
    related_users: Dict[str, float]
    entity_results: List[Dict[str, Any]]
    manipulation_config: Dict[str, Any]


def _copy(value):
    return copy.deepcopy(value)


def _base_network_params():
    return {
        "enable_direct_transfer": False,
        "direct_transfer_params": {
            "enable_min_count": True,
            "min_tx_count": 3,
            "enable_min_volume": False,
            "min_tx_volume": 100_000,
        },
        "enable_funding_relationship": False,
        "enable_same_sender": False,
        "enable_same_recipient": False,
    }


def _base_similarity_params():
    return {
        "enable_trading_action_sequence": False,
        "trading_action_sequence_params": {
            "type": "action_only",
            "min_seq_length": 3,
            "max_time_diff": 120,
            "amount_similarity": 0.7,
            "price_similarity": 0.7,
        },
        "enable_balance_sequence": False,
        "balance_sequence_params": {
            "balance_granularity": "1h",
            "balance_similarity_threshold": 0.6,
        },
        "enable_earning_sequence": False,
        "earning_sequence_params": {
            "earning_granularity": "1h",
            "earning_similarity_threshold": 0.6,
        },
    }


def _empty_detection_config():
    return {
        "enable_network_based": False,
        "transfer_network_based_params": _base_network_params(),
        "enable_similarity_based": False,
        "similarity_based_params": _base_similarity_params(),
        "enable_manipulation_based": False,
        "manipulation_based_params": {"max_time_diff": 2},
    }


def default_ui_detection_configs():
    entity = _empty_detection_config()
    entity["enable_network_based"] = False
    entity["transfer_network_based_params"]["enable_direct_transfer"] = True
    entity["transfer_network_based_params"]["direct_transfer_params"].update(
        {"enable_min_count": True, "min_tx_count": 3, "enable_min_volume": False}
    )
    entity["transfer_network_based_params"]["enable_funding_relationship"] = True
    entity["enable_similarity_based"] = True
    entity["similarity_based_params"]["enable_balance_sequence"] = True
    entity["similarity_based_params"]["balance_sequence_params"].update(
        {"balance_granularity": "1h", "balance_similarity_threshold": 0.6}
    )

    link = _empty_detection_config()
    link["enable_network_based"] = False
    link["transfer_network_based_params"]["enable_direct_transfer"] = True
    link["transfer_network_based_params"]["direct_transfer_params"].update(
        {"enable_min_count": True, "min_tx_count": 1, "enable_min_volume": False}
    )
    link["enable_similarity_based"] = True
    link["similarity_based_params"]["enable_trading_action_sequence"] = True
    link["similarity_based_params"]["trading_action_sequence_params"].update(
        {"type": "action_only", "min_seq_length": 3, "max_time_diff": 120}
    )
    link["enable_manipulation_based"] = True
    return entity, link


def default_manipulation_config():
    return {
        "enable_round_trip_detection": True,
        "round_trip_params": {
            "max_time_diff": 120,
            "max_position_diff": 100,
            "max_earning": 1000,
            "enable_entity_based": True,
        },
        "enable_same_direction_detection": True,
        "same_direction_params": {
            "max_time_diff": 10,
            "min_seq_length": 5,
            "max_diff_direction": 0,
            "enable_entity_based": True,
        },
        "enable_entity_based": True,
    }


def _ordered_without_others(users: Dict[str, float], limit: int | None = None):
    filtered = [(user, balance) for user, balance in users.items() if user != "Others"]
    if limit is not None:
        filtered = filtered[:limit]
    return dict(filtered)


def snapshot_users(coin: str, *, compact: bool = False):
    request = SnapshotRequest(
        time=SNAPSHOT_TIME,
        threshold=0.3,
        related_user_threshold=0.2,
        coin=coin,
    )
    try:
        response = asyncio.run(process_snapshot(request))
    except Exception:
        response = asyncio.run(
            process_snapshot(
                SnapshotRequest(
                    time=None,
                    threshold=request.threshold,
                    related_user_threshold=request.related_user_threshold,
                    coin=coin,
                )
            )
        )
    target_limit = 10 if compact else None
    related_limit = 8 if compact else None
    return {
        "snapshot_time": response["time"],
        "target_users": _ordered_without_others(response["balances"]["users"], target_limit),
        "related_users": _ordered_without_others(
            response["balances"]["related_users"], related_limit
        ),
    }


def _scenario_detection_config(name: str):
    entity, link = _empty_detection_config(), _empty_detection_config()

    if name == "default-ui":
        return default_ui_detection_configs()

    if name == "network-direct-count":
        for config in (entity, link):
            config["enable_network_based"] = True
            config["transfer_network_based_params"]["enable_direct_transfer"] = True
            config["transfer_network_based_params"]["direct_transfer_params"].update(
                {"enable_min_count": True, "min_tx_count": 2, "enable_min_volume": False}
            )
        return entity, link

    if name == "network-direct-volume":
        for config in (entity, link):
            config["enable_network_based"] = True
            config["transfer_network_based_params"]["enable_direct_transfer"] = True
            config["transfer_network_based_params"]["direct_transfer_params"].update(
                {"enable_min_count": False, "enable_min_volume": True, "min_tx_volume": 250_000}
            )
        return entity, link

    if name == "network-funding":
        for config in (entity, link):
            config["enable_network_based"] = True
            config["transfer_network_based_params"]["enable_funding_relationship"] = True
        return entity, link

    if name == "network-sender-recipient":
        for config in (entity, link):
            config["enable_network_based"] = True
            config["transfer_network_based_params"]["enable_same_sender"] = True
            config["transfer_network_based_params"]["enable_same_recipient"] = True
        return entity, link

    if name == "similarity-action-only":
        for config in (entity, link):
            config["enable_similarity_based"] = True
            config["similarity_based_params"]["enable_trading_action_sequence"] = True
            config["similarity_based_params"]["trading_action_sequence_params"].update(
                {"type": "action_only", "min_seq_length": 3, "max_time_diff": 120}
            )
        return entity, link

    if name == "similarity-action-amount-price":
        for config in (entity, link):
            config["enable_similarity_based"] = True
            config["similarity_based_params"]["enable_trading_action_sequence"] = True
            config["similarity_based_params"]["trading_action_sequence_params"].update(
                {
                    "type": "action_amount_price",
                    "min_seq_length": 3,
                    "max_time_diff": 120,
                    "amount_similarity": 0.55,
                    "price_similarity": 0.55,
                }
            )
        return entity, link

    if name.startswith("similarity-balance-"):
        granularity = name.removeprefix("similarity-balance-")
        for config in (entity, link):
            config["enable_similarity_based"] = True
            config["similarity_based_params"]["enable_balance_sequence"] = True
            config["similarity_based_params"]["balance_sequence_params"].update(
                {
                    "balance_granularity": granularity,
                    "balance_similarity_threshold": 0.55,
                }
            )
        return entity, link

    if name.startswith("similarity-earning-"):
        granularity = name.removeprefix("similarity-earning-")
        for config in (entity, link):
            config["enable_similarity_based"] = True
            config["similarity_based_params"]["enable_earning_sequence"] = True
            config["similarity_based_params"]["earning_sequence_params"].update(
                {
                    "earning_granularity": granularity,
                    "earning_similarity_threshold": 0.55,
                }
            )
        return entity, link

    if name == "combined-network-similarity":
        entity, link = default_ui_detection_configs()
        for config in (entity, link):
            config["enable_network_based"] = True
            config["transfer_network_based_params"]["enable_direct_transfer"] = True
            config["transfer_network_based_params"]["enable_funding_relationship"] = True
            config["enable_similarity_based"] = True
            config["similarity_based_params"]["enable_trading_action_sequence"] = True
            config["similarity_based_params"]["enable_balance_sequence"] = True
        return entity, link

    raise ValueError(f"Unknown detection scenario: {name}")


def detection_scenario_names() -> Iterable[tuple[str, str]]:
    scenarios = [
        ("default-ui", "ACT"),
        ("default-ui", "PNUT"),
        ("network-direct-count", "ACT"),
        ("network-direct-count", "PNUT"),
        ("network-direct-volume", "ACT"),
        ("network-funding", "ACT"),
        ("network-funding", "PNUT"),
        ("network-sender-recipient", "ACT"),
        ("similarity-action-only", "ACT"),
        ("similarity-action-only", "PNUT"),
        ("similarity-action-amount-price", "ACT"),
        ("similarity-balance-1min", "ACT"),
        ("similarity-balance-1h", "ACT"),
        ("similarity-balance-1d", "ACT"),
        ("similarity-earning-1h", "ACT"),
        ("similarity-earning-1d", "ACT"),
        ("combined-network-similarity", "ACT"),
        ("combined-network-similarity", "PNUT"),
    ]
    return scenarios


def build_detection_scenarios(*, compact: bool = False) -> List[DetectionScenario]:
    snapshots = {}
    scenarios = []
    for name, coin in detection_scenario_names():
        snapshots.setdefault(coin, snapshot_users(coin, compact=compact))
        snapshot = snapshots[coin]
        entity_config, link_config = _scenario_detection_config(name)
        scenarios.append(
            DetectionScenario(
                name=f"{coin.lower()}-{name}",
                coin=coin,
                target_users=_copy(snapshot["target_users"]),
                related_users=_copy(snapshot["related_users"]),
                entity_detection_config=entity_config,
                link_detection_config=link_config,
                snapshot_time=snapshot["snapshot_time"],
            )
        )
    return scenarios


def _entity_groups_from_users(users: Dict[str, float]) -> List[Dict[str, Any]]:
    ordered = [user for user in users if user != "Others"]
    if len(ordered) < 3:
        return []
    return [
        {"users": ordered[:3], "relations": [{"type": "fixture_entity"}]},
        {"users": ordered[3:6], "relations": [{"type": "fixture_entity"}]},
    ]


def _manipulation_scenario_config(name: str):
    config = default_manipulation_config()
    if name == "manipulation-round-trip-only":
        config["enable_same_direction_detection"] = False
    elif name == "manipulation-same-direction-only":
        config["enable_round_trip_detection"] = False
    elif name == "manipulation-entity-off":
        config["enable_entity_based"] = False
        config["round_trip_params"]["enable_entity_based"] = False
        config["same_direction_params"]["enable_entity_based"] = False
    elif name == "manipulation-strict-thresholds":
        config["round_trip_params"].update(
            {"max_time_diff": 30, "max_position_diff": 10, "max_earning": 100}
        )
        config["same_direction_params"].update(
            {"max_time_diff": 2, "min_seq_length": 8, "max_diff_direction": 0}
        )
    elif name == "manipulation-loose-thresholds":
        config["round_trip_params"].update(
            {"max_time_diff": 240, "max_position_diff": 1000, "max_earning": 5000}
        )
        config["same_direction_params"].update(
            {"max_time_diff": 30, "min_seq_length": 3, "max_diff_direction": 1}
        )
    elif name != "manipulation-default":
        raise ValueError(f"Unknown manipulation scenario: {name}")
    return config


def manipulation_scenario_names() -> Iterable[tuple[str, str]]:
    return [
        ("manipulation-default", "ACT"),
        ("manipulation-default", "PNUT"),
        ("manipulation-round-trip-only", "ACT"),
        ("manipulation-round-trip-only", "PNUT"),
        ("manipulation-same-direction-only", "ACT"),
        ("manipulation-same-direction-only", "PNUT"),
        ("manipulation-entity-off", "ACT"),
        ("manipulation-strict-thresholds", "ACT"),
        ("manipulation-loose-thresholds", "ACT"),
    ]


def build_manipulation_scenarios(*, compact: bool = False) -> List[ManipulationScenario]:
    snapshots = {}
    scenarios = []
    for name, coin in manipulation_scenario_names():
        snapshots.setdefault(coin, snapshot_users(coin, compact=compact))
        snapshot = snapshots[coin]
        target_users = _copy(snapshot["target_users"])
        scenarios.append(
            ManipulationScenario(
                name=f"{coin.lower()}-{name}",
                coin=coin,
                target_users=target_users,
                related_users=_copy(snapshot["related_users"]),
                entity_results=_entity_groups_from_users(target_users),
                manipulation_config=_manipulation_scenario_config(name),
            )
        )
    return scenarios
