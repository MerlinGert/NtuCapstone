import argparse
import copy
import json
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from detection_fixture_data import (
    ENTITY_RESULTS,
    RELATED_USERS,
    SNAPSHOT_TIME,
    TARGET_USERS,
    create_detection_data_dir,
    create_manipulation_trades,
)
from detection_output_normalizer import normalize_detection_output
from detection_scenarios import (
    DetectionScenario,
    ManipulationScenario,
    _manipulation_scenario_config,
    _scenario_detection_config,
    build_detection_scenarios,
    build_manipulation_scenarios,
    detection_scenario_names,
    manipulation_scenario_names,
)

import detection_service
import manipulation_detection_service


DEFAULT_OUTPUT_DIR = SERVER_DIR / "tests" / "fixtures" / "detection"


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _clear_generated_fixtures(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in output_dir.glob("*.json"):
        path.unlink()


def _original_manipulation_output(scenario):
    request = manipulation_detection_service.ManipulationRequest(
        target_users=scenario.target_users,
        related_users=scenario.related_users,
        entity_results=scenario.entity_results,
        manipulation_config=scenario.manipulation_config,
        coin=scenario.coin,
    )
    df = manipulation_detection_service.load_trading_data(request.coin)
    if df.empty:
        return {"results": []}

    target_user_list = manipulation_detection_service._collect_target_user_list(request)
    filtered_df = (
        df[df["trader"].isin(target_user_list)].copy() if "trader" in df.columns else df.copy()
    )
    results = []
    if request.manipulation_config.get("enable_round_trip_detection", False):
        method_config = copy.deepcopy(request.manipulation_config.get("round_trip_params", {}))
        method_config.setdefault(
            "enable_entity_based",
            request.manipulation_config.get("enable_entity_based", False),
        )
        results.extend(
            manipulation_detection_service.detect_round_trip(
                filtered_df, target_user_list, method_config, request.entity_results
            )
        )
    if request.manipulation_config.get("enable_same_direction_detection", False):
        method_config = copy.deepcopy(
            request.manipulation_config.get("same_direction_params", {})
        )
        method_config.setdefault(
            "enable_entity_based",
            request.manipulation_config.get("enable_entity_based", False),
        )
        results.extend(
            manipulation_detection_service.detect_same_direction(
                filtered_df, target_user_list, method_config, request.entity_results
            )
        )
    return {
        "results": [manipulation_detection_service._model_to_dict(result) for result in results]
    }


def _write_detection_fixture(output_dir: Path, scenario: DetectionScenario) -> None:
        result = detection_service.process_detection(
            scenario.target_users,
            scenario.related_users,
            scenario.entity_detection_config,
            scenario.link_detection_config,
            scenario.snapshot_time,
            scenario.detect_entity,
            scenario.detect_link,
            scenario.coin,
        )
        payload = {
            "scenario": asdict(scenario),
            "normalizedOutput": normalize_detection_output(result),
        }
        _write_json(output_dir / f"{scenario.name}.json", payload)


def _write_manipulation_fixture(output_dir: Path, scenario: ManipulationScenario) -> None:
        payload = {
            "scenario": asdict(scenario),
            "normalizedOutput": normalize_detection_output(_original_manipulation_output(scenario)),
        }
        _write_json(output_dir / f"{scenario.name}.json", payload)


def _synthetic_detection_scenarios():
    for name, coin in detection_scenario_names():
        entity_config, link_config = _scenario_detection_config(name)
        yield DetectionScenario(
            name=f"{coin.lower()}-{name}",
            coin=coin,
            target_users=copy.deepcopy(TARGET_USERS),
            related_users=copy.deepcopy(RELATED_USERS),
            entity_detection_config=entity_config,
            link_detection_config=link_config,
            snapshot_time=SNAPSHOT_TIME,
        )


def _synthetic_manipulation_scenarios():
    for name, coin in manipulation_scenario_names():
        yield ManipulationScenario(
            name=f"{coin.lower()}-{name}",
            coin=coin,
            target_users=copy.deepcopy(TARGET_USERS),
            related_users=copy.deepcopy(RELATED_USERS),
            entity_results=copy.deepcopy(ENTITY_RESULTS),
            manipulation_config=_manipulation_scenario_config(name),
        )


def generate_synthetic_fixtures(output_dir: Path) -> None:
    _clear_generated_fixtures(output_dir)
    with tempfile.TemporaryDirectory() as tmp_dir:
        data_dir = Path(tmp_dir)
        create_detection_data_dir(data_dir)
        trades = create_manipulation_trades()
        with patch.object(detection_service, "get_data_dir", return_value=str(data_dir)):
            for scenario in _synthetic_detection_scenarios():
                _write_detection_fixture(output_dir, scenario)
        with patch.object(manipulation_detection_service, "load_trading_data", return_value=trades):
            for scenario in _synthetic_manipulation_scenarios():
                _write_manipulation_fixture(output_dir, scenario)


def generate_real_fixtures(output_dir: Path, *, compact: bool) -> None:
    _clear_generated_fixtures(output_dir)
    for scenario in build_detection_scenarios(compact=compact):
        _write_detection_fixture(output_dir, scenario)

    for scenario in build_manipulation_scenarios(compact=compact):
        _write_manipulation_fixture(output_dir, scenario)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate normalized detection fixtures.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--source",
        choices=("synthetic", "real"),
        default="synthetic",
        help=(
            "Use fast synthetic data for committed fixtures, or raw ACT/PNUT data for "
            "long-running manual regeneration."
        ),
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="With --source real, use full snapshot user sets instead of compact raw-data inputs.",
    )
    args = parser.parse_args()

    if args.source == "synthetic":
        generate_synthetic_fixtures(args.output_dir)
    else:
        generate_real_fixtures(args.output_dir, compact=not args.full)


if __name__ == "__main__":
    main()
