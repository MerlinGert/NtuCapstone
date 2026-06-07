import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd


SERVER_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SERVER_DIR / "scripts"
sys.path.insert(0, str(SERVER_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

import detection_service  # noqa: E402
import manipulation_detection_service  # noqa: E402
from detection_fixture_data import (  # noqa: E402
    ENTITY_RESULTS,
    MANIPULATION_USERS,
    RELATED_USERS,
    SNAPSHOT_TIME,
    TARGET_USERS,
    create_detection_data_dir,
    create_manipulation_trades,
)
from detection_output_normalizer import normalize_detection_output  # noqa: E402
from detection_scenarios import (  # noqa: E402
    _manipulation_scenario_config,
    _scenario_detection_config,
    detection_scenario_names,
    manipulation_scenario_names,
)


def _model_dump_list(results):
    dumped = []
    for result in results:
        if hasattr(result, "model_dump"):
            dumped.append(result.model_dump())
        else:
            dumped.append(result.dict())
    return dumped


class DetectionAlgorithmEquivalenceTests(unittest.TestCase):
    def test_committed_fixture_matrix_is_complete(self):
        fixture_dir = SERVER_DIR / "tests" / "fixtures" / "detection"
        expected = {
            f"{coin.lower()}-{scenario_name}.json"
            for scenario_name, coin in detection_scenario_names()
        }
        expected.update(
            f"{coin.lower()}-{scenario_name}.json"
            for scenario_name, coin in manipulation_scenario_names()
        )

        actual = {path.name for path in fixture_dir.glob("*.json")}
        self.assertEqual(expected, actual)
        for path in fixture_dir.glob("*.json"):
            with self.subTest(path=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn("scenario", payload)
                self.assertIn("normalizedOutput", payload)

    def test_detection_config_matrix_matches_original_on_fixture_data(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            data_dir = Path(tmp_dir)
            create_detection_data_dir(data_dir)
            with patch.object(detection_service, "get_data_dir", return_value=str(data_dir)):
                for scenario_name, _coin in detection_scenario_names():
                    with self.subTest(scenario=scenario_name):
                        entity_config, link_config = _scenario_detection_config(scenario_name)
                        original = detection_service._process_detection_uncached(
                            copy.deepcopy(TARGET_USERS),
                            copy.deepcopy(RELATED_USERS),
                            entity_config,
                            link_config,
                            SNAPSHOT_TIME,
                            True,
                            True,
                            "ACT",
                        )
                        detection_service.clear_optimized_detection_caches()
                        optimized = detection_service._process_detection_uncached_optimized(
                            copy.deepcopy(TARGET_USERS),
                            copy.deepcopy(RELATED_USERS),
                            entity_config,
                            link_config,
                            SNAPSHOT_TIME,
                            True,
                            True,
                            "ACT",
                        )
                        self.assertEqual(
                            normalize_detection_output(original),
                            normalize_detection_output(optimized),
                        )

    def test_manipulation_config_matrix_matches_original_on_fixture_data(self):
        trades = create_manipulation_trades()
        users = MANIPULATION_USERS
        entity_results = ENTITY_RESULTS
        trades_by_user = {
            str(user): user_df.sort_values(by="timestamp").copy()
            for user, user_df in trades.groupby("trader", sort=False)
        }

        for scenario_name, _coin in manipulation_scenario_names():
            with self.subTest(scenario=scenario_name):
                config = _manipulation_scenario_config(scenario_name)
                original_results = []
                if config.get("enable_round_trip_detection", False):
                    round_trip_config = copy.deepcopy(config["round_trip_params"])
                    original_results.extend(
                        manipulation_detection_service.detect_round_trip(
                            trades, users, round_trip_config, entity_results
                        )
                    )
                if config.get("enable_same_direction_detection", False):
                    same_direction_config = copy.deepcopy(config["same_direction_params"])
                    original_results.extend(
                        manipulation_detection_service.detect_same_direction(
                            trades, users, same_direction_config, entity_results
                        )
                    )

                optimized_results = []
                if config.get("enable_round_trip_detection", False):
                    optimized_results.extend(
                        manipulation_detection_service.detect_round_trip_optimized(
                            trades,
                            users,
                            copy.deepcopy(config["round_trip_params"]),
                            entity_results,
                            trades_by_user=trades_by_user,
                        )
                    )
                if config.get("enable_same_direction_detection", False):
                    optimized_results.extend(
                        manipulation_detection_service.detect_same_direction_optimized(
                            trades,
                            users,
                            copy.deepcopy(config["same_direction_params"]),
                            entity_results,
                            trades_by_user=trades_by_user,
                        )
                    )

                self.assertEqual(
                    normalize_detection_output(_model_dump_list(original_results)),
                    normalize_detection_output(_model_dump_list(optimized_results)),
                )

    def test_optimized_detection_cache_returns_defensive_copy(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            data_dir = Path(tmp_dir)
            create_detection_data_dir(data_dir)
            with patch.object(detection_service, "get_data_dir", return_value=str(data_dir)):
                entity_config, link_config = _scenario_detection_config("network-direct-count")
                detection_service.clear_optimized_detection_caches()
                first = detection_service.process_detection_optimized(
                    copy.deepcopy(TARGET_USERS),
                    copy.deepcopy(RELATED_USERS),
                    entity_config,
                    link_config,
                    SNAPSHOT_TIME,
                    True,
                    True,
                    "ACT",
                )
                expected = normalize_detection_output(first)
                first["relations"]["target_relations_for_entity"].clear()
                second = detection_service.process_detection_optimized(
                    copy.deepcopy(TARGET_USERS),
                    copy.deepcopy(RELATED_USERS),
                    entity_config,
                    link_config,
                    SNAPSHOT_TIME,
                    True,
                    True,
                    "ACT",
                )
                self.assertEqual(expected, normalize_detection_output(second))

    def test_detection_endpoint_dispatch_can_use_original_path(self):
        request = detection_service.DetectionRequest(
            target_users=copy.deepcopy(TARGET_USERS),
            related_users=copy.deepcopy(RELATED_USERS),
            entity_detection_config=_scenario_detection_config("network-direct-count")[0],
            link_detection_config=_scenario_detection_config("network-direct-count")[1],
            snapshot_time=SNAPSHOT_TIME,
            detect_entity=True,
            detect_link=True,
            coin="ACT",
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            data_dir = Path(tmp_dir)
            create_detection_data_dir(data_dir)
            with patch.object(detection_service, "get_data_dir", return_value=str(data_dir)):
                with patch.dict(
                    os.environ,
                    {detection_service.MANISCOPE_USE_OPTIMIZED_DETECTION: "0"},
                ):
                    import asyncio

                    result = asyncio.run(detection_service.run_detection(request))
                original = detection_service._process_detection_uncached(
                    request.target_users,
                    request.related_users,
                    request.entity_detection_config,
                    request.link_detection_config,
                    request.snapshot_time,
                    request.detect_entity,
                    request.detect_link,
                    request.coin,
                )
                self.assertEqual(
                    normalize_detection_output(original),
                    normalize_detection_output(result),
                )

    def test_manipulation_endpoint_dispatch_can_use_original_path(self):
        request = manipulation_detection_service.ManipulationRequest(
            target_users={"A": 1},
            related_users={},
            entity_results=[],
            manipulation_config={"enable_round_trip_detection": False},
            coin="ACT",
        )
        with patch.object(
            manipulation_detection_service,
            "load_trading_data",
            return_value=pd.DataFrame(columns=["trader", "timestamp"]),
        ):
            with patch.dict(
                os.environ,
                {manipulation_detection_service.MANISCOPE_USE_OPTIMIZED_MANIPULATION: "0"},
            ):
                import asyncio

                result = asyncio.run(manipulation_detection_service.detect_manipulation(request))
                self.assertEqual(result.results, [])


if __name__ == "__main__":
    unittest.main()
