from pathlib import Path

import pandas as pd


SNAPSHOT_TIME = "2024-01-01 00:03:00 UTC"
TARGET_USERS = {"A": 100.0, "B": 90.0, "C": 80.0}
RELATED_USERS = {"X": 70.0, "Y": 60.0}
MANIPULATION_USERS = ["A", "B", "X"]
ENTITY_RESULTS = [{"users": ["A", "B"], "relations": [{"type": "fixture"}]}]


def write_json(path: Path, payload: str) -> None:
    path.write_text(payload, encoding="utf-8")


def create_detection_data_dir(root: Path) -> None:
    pd.DataFrame(
        [
            {
                "timestamp": "2024-01-01 00:00:00 UTC",
                "from_owner": "A",
                "to_owner": "B",
                "amount": 10,
            },
            {
                "timestamp": "2024-01-01 00:01:00 UTC",
                "from_owner": "A",
                "to_owner": "B",
                "amount": 20,
            },
            {
                "timestamp": "2024-01-01 00:02:00 UTC",
                "from_owner": "B",
                "to_owner": "A",
                "amount": 30,
            },
            {
                "timestamp": "2024-01-01 00:01:30 UTC",
                "from_owner": "A",
                "to_owner": "X",
                "amount": 300_000,
            },
            {
                "timestamp": "2024-01-01 00:02:30 UTC",
                "from_owner": "X",
                "to_owner": "A",
                "amount": 350_000,
            },
            {
                "timestamp": "2024-01-02 00:00:00 UTC",
                "from_owner": "C",
                "to_owner": "Y",
                "amount": 999_000,
            },
        ]
    ).to_csv(root / "sorted_transfers.csv", index=False)

    write_json(
        root / "user_relations.json",
        """
{
  "senders": {
    "A": [{"timestamp": "2024-01-01 00:00:00 UTC", "address": "S1"}],
    "B": [{"timestamp": "2024-01-01 00:00:30 UTC", "address": "S1"}],
    "C": [{"timestamp": "2024-01-01 00:01:00 UTC", "address": "X"}],
    "X": [{"timestamp": "2024-01-01 00:01:30 UTC", "address": "S1"}],
    "Y": [{"timestamp": "2024-01-02 00:00:00 UTC", "address": "S2"}]
  },
  "recipients": {
    "A": [{"timestamp": "2024-01-01 00:00:00 UTC", "address": "R1"}],
    "B": [{"timestamp": "2024-01-01 00:00:30 UTC", "address": "R1"}],
    "C": [{"timestamp": "2024-01-01 00:01:00 UTC", "address": "R2"}],
    "X": [{"timestamp": "2024-01-01 00:01:30 UTC", "address": "R1"}]
  }
}
""".strip(),
    )

    write_json(
        root / "user_actions.json",
        """
{
  "A": [
    {"timestamp": "2024-01-01 00:00:00 UTC", "action_type": "buy", "amount": 100, "price": 1.0},
    {"timestamp": "2024-01-01 00:01:00 UTC", "action_type": "sell", "amount": 95, "price": 1.01},
    {"timestamp": "2024-01-01 00:02:00 UTC", "action_type": "buy", "amount": 105, "price": 1.0}
  ],
  "B": [
    {"timestamp": "2024-01-01 00:00:30 UTC", "action_type": "buy", "amount": 101, "price": 1.0},
    {"timestamp": "2024-01-01 00:01:30 UTC", "action_type": "sell", "amount": 96, "price": 1.01},
    {"timestamp": "2024-01-01 00:02:30 UTC", "action_type": "buy", "amount": 106, "price": 1.0}
  ],
  "C": [
    {"timestamp": "2024-01-01 00:00:00 UTC", "action_type": "sell", "amount": 200, "price": 2.0}
  ],
  "X": [
    {"timestamp": "2024-01-01 00:00:20 UTC", "action_type": "buy", "amount": 100, "price": 1.0},
    {"timestamp": "2024-01-01 00:01:20 UTC", "action_type": "sell", "amount": 94, "price": 1.01},
    {"timestamp": "2024-01-01 00:02:20 UTC", "action_type": "buy", "amount": 104, "price": 1.0}
  ],
  "Y": [
    {"timestamp": "2024-01-01 00:00:00 UTC", "action_type": "buy", "amount": 10, "price": 5.0}
  ]
}
""".strip(),
    )

    balance_payload = """
{
  "A": [{"timestamp": "2024-01-01 00:00:00", "balance": 100}, {"timestamp": "2024-01-01 01:00:00", "balance": 110}, {"timestamp": "2024-01-01 02:00:00", "balance": 120}],
  "B": [{"timestamp": "2024-01-01 00:00:00", "balance": 200}, {"timestamp": "2024-01-01 01:00:00", "balance": 220}, {"timestamp": "2024-01-01 02:00:00", "balance": 240}],
  "C": [{"timestamp": "2024-01-01 00:00:00", "balance": 300}, {"timestamp": "2024-01-01 01:00:00", "balance": 290}, {"timestamp": "2024-01-01 02:00:00", "balance": 280}],
  "X": [{"timestamp": "2024-01-01 00:00:00", "balance": 400}, {"timestamp": "2024-01-01 01:00:00", "balance": 440}, {"timestamp": "2024-01-01 02:00:00", "balance": 480}]
}
""".strip()
    earning_payload = """
{
  "A": [{"timestamp": "2024-01-01 00:00:00", "earning": 1}, {"timestamp": "2024-01-01 01:00:00", "earning": 2}, {"timestamp": "2024-01-01 02:00:00", "earning": 3}],
  "B": [{"timestamp": "2024-01-01 00:00:00", "earning": 2}, {"timestamp": "2024-01-01 01:00:00", "earning": 4}, {"timestamp": "2024-01-01 02:00:00", "earning": 6}],
  "C": [{"timestamp": "2024-01-01 00:00:00", "earning": 3}, {"timestamp": "2024-01-01 01:00:00", "earning": 2}, {"timestamp": "2024-01-01 02:00:00", "earning": 1}],
  "X": [{"timestamp": "2024-01-01 00:00:00", "earning": 1}, {"timestamp": "2024-01-01 01:00:00", "earning": 2}, {"timestamp": "2024-01-01 02:00:00", "earning": 3}]
}
""".strip()
    for suffix in ("1min", "1h", "1d"):
        write_json(root / f"user_balance_{suffix}.json", balance_payload)
        write_json(root / f"user_earnings_{suffix}.json", earning_payload)


def create_manipulation_trades() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "timestamp": pd.Timestamp("2024-01-01 00:00:00"),
                "trader": "A",
                "action_type": "buy",
                "amount": 100,
                "amount_usd": 100,
            },
            {
                "timestamp": pd.Timestamp("2024-01-01 00:01:00"),
                "trader": "A",
                "action_type": "sell",
                "amount": 100,
                "amount_usd": 101,
            },
            {
                "timestamp": pd.Timestamp("2024-01-01 00:02:00"),
                "trader": "B",
                "action_type": "buy",
                "amount": 50,
                "amount_usd": 50,
            },
            {
                "timestamp": pd.Timestamp("2024-01-01 00:03:00"),
                "trader": "B",
                "action_type": "buy",
                "amount": 60,
                "amount_usd": 60,
            },
            {
                "timestamp": pd.Timestamp("2024-01-01 00:04:00"),
                "trader": "B",
                "action_type": "buy",
                "amount": 70,
                "amount_usd": 70,
            },
        ]
    )
