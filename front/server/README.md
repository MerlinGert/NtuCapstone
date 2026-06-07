# CryptoVis Backend

This is a FastAPI backend for processing data and serving API requests.

## Setup

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    Or use uv:
    ```bash
    uv sync
    ```

## Running the Server

Run the server from `front/server`:

```bash
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8099
```

The API will be available at `http://127.0.0.1:8099`.
Frontend requests to `/api/*` will be proxied to this server.

## Detection Acceleration

The active detection endpoints use optimized implementations by default while
keeping the original algorithms available for A/B checks:

- `/api/detection/run`: entity and link detection.
- `/api/manipulation_service/detect`: manipulation detection.

Set these environment flags to `0` to force the original paths:

```bash
MANISCOPE_USE_OPTIMIZED_DETECTION=0
MANISCOPE_USE_OPTIMIZED_MANIPULATION=0
```

Run the side-by-side correctness tests:

```bash
uv run python -m unittest tests/test_detection_algorithm_equivalence.py
```

Regenerate the committed synthetic golden fixture matrix:

```bash
uv run python scripts/generate_detection_fixtures.py
```

Manual raw-data fixture snapshots are also available, but PNUT relation-heavy
cases read large raw files and may take much longer:

```bash
uv run python scripts/generate_detection_fixtures.py --source real
uv run python scripts/generate_detection_fixtures.py --source real --full
```

Run the benchmark harness:

```bash
uv run python scripts/benchmark_detection.py --iterations 1 --compact
uv run python scripts/benchmark_detection.py --iterations 20
uv run python scripts/benchmark_detection.py --iterations 20 --json artifacts/detection-benchmark.json
```

## Structure

- `main.py`: The FastAPI application entry point.
- `requirements.txt`: Python dependencies.
- `../data_processing/`: Data processing scripts (available in python path).
