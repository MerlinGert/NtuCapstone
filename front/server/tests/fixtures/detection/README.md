# Detection Correctness Fixtures

Use `front/server/scripts/generate_detection_fixtures.py` to regenerate normalized
golden outputs for the full detection configuration matrix. The default mode
uses deterministic synthetic data so committed fixtures stay fast and stable:

```bash
cd front/server
uv run python scripts/generate_detection_fixtures.py
```

For manual raw-data snapshots, use the real source mode. PNUT relation-heavy
scenarios load large files, so this is intentionally not the default:

```bash
uv run python scripts/generate_detection_fixtures.py --source real
uv run python scripts/generate_detection_fixtures.py --source real --full
```

The committed equivalence test compares the original and optimized functions
directly on the same synthetic data and verifies this fixture matrix is
complete, so normal test runs stay fast.
