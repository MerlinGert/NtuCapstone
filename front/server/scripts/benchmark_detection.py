import argparse
import json
import statistics
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Dict, List

import pandas as pd

SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

import detection_service
import manipulation_detection_service
from detection_scenarios import (
    DetectionScenario,
    ManipulationScenario,
    build_detection_scenarios,
    build_manipulation_scenarios,
)


def _clear_detection_file_caches() -> None:
    with detection_service._cache_lock:
        detection_service._csv_file_cache.clear()
        detection_service._json_file_cache.clear()
        detection_service._detection_result_cache.clear()
    detection_service.clear_optimized_detection_caches()


def _clear_detection_result_caches() -> None:
    with detection_service._cache_lock:
        detection_service._detection_result_cache.clear()
        detection_service._optimized_detection_result_cache.clear()


def _clear_manipulation_file_caches() -> None:
    manipulation_detection_service._trades_df.clear()
    manipulation_detection_service.clear_optimized_manipulation_caches()


def _clear_manipulation_result_caches() -> None:
    with manipulation_detection_service._manipulation_cache_lock:
        manipulation_detection_service._optimized_manipulation_result_cache.clear()


def _stats(samples: List[float]) -> Dict[str, float]:
    ordered = sorted(samples)
    p95_index = min(len(ordered) - 1, int(round((len(ordered) - 1) * 0.95)))
    return {
        "median": statistics.median(samples),
        "mean": statistics.mean(samples),
        "min": min(samples),
        "max": max(samples),
        "p95": ordered[p95_index],
    }


def _time_call(fn: Callable[[], object], iterations: int) -> List[float]:
    samples = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    return samples


def _run_detection_original_uncached(scenario: DetectionScenario):
    return detection_service._process_detection_uncached(
        scenario.target_users,
        scenario.related_users,
        scenario.entity_detection_config,
        scenario.link_detection_config,
        scenario.snapshot_time,
        scenario.detect_entity,
        scenario.detect_link,
        scenario.coin,
    )


def _run_detection_optimized_uncached(scenario: DetectionScenario):
    return detection_service._process_detection_uncached_optimized(
        scenario.target_users,
        scenario.related_users,
        scenario.entity_detection_config,
        scenario.link_detection_config,
        scenario.snapshot_time,
        scenario.detect_entity,
        scenario.detect_link,
        scenario.coin,
    )


def _run_detection_optimized_cached(scenario: DetectionScenario):
    return detection_service.process_detection_optimized(
        scenario.target_users,
        scenario.related_users,
        scenario.entity_detection_config,
        scenario.link_detection_config,
        scenario.snapshot_time,
        scenario.detect_entity,
        scenario.detect_link,
        scenario.coin,
    )


def _manipulation_original_response(scenario: ManipulationScenario):
    df = manipulation_detection_service.load_trading_data(scenario.coin)
    if df.empty:
        return {"results": []}
    users = manipulation_detection_service._collect_target_user_list(
        manipulation_detection_service.ManipulationRequest(
            target_users=scenario.target_users,
            related_users=scenario.related_users,
            entity_results=scenario.entity_results,
            manipulation_config=scenario.manipulation_config,
            coin=scenario.coin,
        )
    )
    filtered_df = df[df["trader"].isin(users)].copy() if "trader" in df.columns else df.copy()
    results = []
    if scenario.manipulation_config.get("enable_round_trip_detection", False):
        config = dict(scenario.manipulation_config.get("round_trip_params", {}))
        config.setdefault(
            "enable_entity_based",
            scenario.manipulation_config.get("enable_entity_based", False),
        )
        results.extend(
            manipulation_detection_service.detect_round_trip(
                filtered_df, users, config, scenario.entity_results
            )
        )
    if scenario.manipulation_config.get("enable_same_direction_detection", False):
        config = dict(scenario.manipulation_config.get("same_direction_params", {}))
        config.setdefault(
            "enable_entity_based",
            scenario.manipulation_config.get("enable_entity_based", False),
        )
        results.extend(
            manipulation_detection_service.detect_same_direction(
                filtered_df, users, config, scenario.entity_results
            )
        )
    return {"results": [manipulation_detection_service._model_to_dict(item) for item in results]}


def _manipulation_optimized_response(scenario: ManipulationScenario):
    request = manipulation_detection_service.ManipulationRequest(
        target_users=scenario.target_users,
        related_users=scenario.related_users,
        entity_results=scenario.entity_results,
        manipulation_config=scenario.manipulation_config,
        coin=scenario.coin,
    )
    response = manipulation_detection_service.detect_manipulation_optimized(request)
    return {"results": [manipulation_detection_service._model_to_dict(item) for item in response.results]}


def _select_detection_benchmarks(*, compact: bool) -> List[DetectionScenario]:
    scenarios = {
        scenario.name: scenario for scenario in build_detection_scenarios(compact=compact)
    }
    if compact:
        return [scenarios["act-default-ui"], scenarios["pnut-default-ui"]]
    return [
        scenarios["act-default-ui"],
        scenarios["pnut-default-ui"],
        scenarios["act-combined-network-similarity"],
        scenarios["act-similarity-action-amount-price"],
    ]


def _select_manipulation_benchmarks(*, compact: bool) -> List[ManipulationScenario]:
    scenarios = {
        scenario.name: scenario for scenario in build_manipulation_scenarios(compact=compact)
    }
    return [
        scenarios["act-manipulation-default"],
        scenarios["pnut-manipulation-default"],
    ]


def benchmark_detection_scenario(scenario: DetectionScenario, iterations: int) -> Dict:
    _clear_detection_file_caches()
    original_cold = _time_call(lambda: _run_detection_original_uncached(scenario), 1)
    _clear_detection_file_caches()
    optimized_cold = _time_call(lambda: _run_detection_optimized_uncached(scenario), 1)

    _clear_detection_result_caches()
    original_warm = _time_call(lambda: _run_detection_original_uncached(scenario), iterations)
    _clear_detection_result_caches()
    optimized_warm_uncached = _time_call(
        lambda: _run_detection_optimized_uncached(scenario), iterations
    )
    _clear_detection_result_caches()
    _run_detection_optimized_cached(scenario)
    optimized_cached = _time_call(lambda: _run_detection_optimized_cached(scenario), iterations)

    original_warm_stats = _stats(original_warm)
    optimized_warm_stats = _stats(optimized_warm_uncached)
    cached_stats = _stats(optimized_cached)
    return {
        "kind": "detection",
        "scenario": scenario.name,
        "request": asdict(scenario),
        "originalCold": _stats(original_cold),
        "optimizedCold": _stats(optimized_cold),
        "originalWarm": original_warm_stats,
        "optimizedWarmUncached": optimized_warm_stats,
        "optimizedCached": cached_stats,
        "speedups": {
            "warmUncachedMedian": original_warm_stats["median"]
            / optimized_warm_stats["median"]
            if optimized_warm_stats["median"]
            else None,
            "cachedMedian": optimized_warm_stats["median"] / cached_stats["median"]
            if cached_stats["median"]
            else None,
        },
    }


def benchmark_manipulation_scenario(scenario: ManipulationScenario, iterations: int) -> Dict:
    _clear_manipulation_file_caches()
    original_cold = _time_call(lambda: _manipulation_original_response(scenario), 1)
    _clear_manipulation_file_caches()
    optimized_cold = _time_call(lambda: _manipulation_optimized_response(scenario), 1)

    _clear_manipulation_result_caches()
    original_warm = _time_call(lambda: _manipulation_original_response(scenario), iterations)
    _clear_manipulation_result_caches()
    optimized_warm_uncached = _time_call(
        lambda: _manipulation_optimized_response(scenario), iterations
    )
    _clear_manipulation_result_caches()
    _manipulation_optimized_response(scenario)
    optimized_cached = _time_call(lambda: _manipulation_optimized_response(scenario), iterations)

    original_warm_stats = _stats(original_warm)
    optimized_warm_stats = _stats(optimized_warm_uncached)
    cached_stats = _stats(optimized_cached)
    return {
        "kind": "manipulation",
        "scenario": scenario.name,
        "request": asdict(scenario),
        "originalCold": _stats(original_cold),
        "optimizedCold": _stats(optimized_cold),
        "originalWarm": original_warm_stats,
        "optimizedWarmUncached": optimized_warm_stats,
        "optimizedCached": cached_stats,
        "speedups": {
            "warmUncachedMedian": original_warm_stats["median"]
            / optimized_warm_stats["median"]
            if optimized_warm_stats["median"]
            else None,
            "cachedMedian": optimized_warm_stats["median"] / cached_stats["median"]
            if cached_stats["median"]
            else None,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark ManiScope detection paths.")
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Use capped user sets and a smaller scenario set for quick harness validation.",
    )
    args = parser.parse_args()

    results = []
    for scenario in _select_detection_benchmarks(compact=args.compact):
        print(f"Benchmarking {scenario.name}...")
        results.append(benchmark_detection_scenario(scenario, args.iterations))
    for scenario in _select_manipulation_benchmarks(compact=args.compact):
        print(f"Benchmarking {scenario.name}...")
        results.append(benchmark_manipulation_scenario(scenario, args.iterations))

    payload = {"iterations": args.iterations, "compact": args.compact, "results": results}
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
