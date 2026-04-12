import argparse
import csv
import json
import os
from datetime import datetime, timedelta

csv.field_size_limit(2**31 - 1)


def parse_timestamp(timestamp_str):
    timestamp_str = timestamp_str.strip()
    if "." in timestamp_str:
        timestamp_str = timestamp_str.split(".")[0] + " UTC"
    return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S UTC")


def load_labels(labels_json_path):
    if not labels_json_path or not os.path.exists(labels_json_path):
        return {}

    with open(labels_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        return data

    labels = {}
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "owner_address" in item and "label" in item:
                labels[item["owner_address"]] = item["label"]
    return labels


def classify_owner(owner, inline_label, labels_map):
    label = (inline_label or "").strip() or labels_map.get(owner, "")
    label = label.lower()
    if label == "contract":
        return "contracts"
    if label == "exchange":
        return "exchanges"
    return "users"


def snapshot_balances(current_balances, current_labels):
    snapshot = {"users": {}, "contracts": {}, "exchanges": {}}
    for owner, balance in current_balances.items():
        if not owner or balance <= 0:
            continue
        bucket = current_labels.get(owner, "users")
        snapshot[bucket][owner] = balance
    return snapshot


def apply_transfer(row, current_balances, current_labels, labels_map):
    amount_str = (row.get("amount") or "").strip()
    if not amount_str:
        return

    try:
        amount = float(amount_str)
    except ValueError:
        return

    from_owner = (row.get("from_owner") or "").strip()
    to_owner = (row.get("to_owner") or "").strip()
    from_label = row.get("from_owner_label")
    to_label = row.get("to_owner_label")

    if from_owner:
        current_balances[from_owner] = current_balances.get(from_owner, 0.0) - amount
        current_labels[from_owner] = classify_owner(from_owner, from_label, labels_map)
        if abs(current_balances[from_owner]) < 1e-12:
            current_balances[from_owner] = 0.0

    if to_owner:
        current_balances[to_owner] = current_balances.get(to_owner, 0.0) + amount
        current_labels[to_owner] = classify_owner(to_owner, to_label, labels_map)


def generate_hourly_snapshots_from_sorted_transfers(
    input_csv_path, output_json_path, labels_json_path=None
):
    labels_map = load_labels(labels_json_path)
    current_balances = {}
    current_labels = {}
    snapshots = []

    with open(input_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        try:
            first_row = next(reader)
        except StopIteration:
            raise ValueError("Input sorted_transfers.csv is empty.")

        time_column = "timestamp" if "timestamp" in first_row else "time"
        current_time = parse_timestamp(first_row[time_column])
        next_snapshot_time = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(
            hours=1
        )

        apply_transfer(first_row, current_balances, current_labels, labels_map)
        row_count = 1

        for row in reader:
            try:
                row_time = parse_timestamp(row[time_column])
            except Exception:
                continue

            while row_time >= next_snapshot_time:
                snapshots.append(
                    {
                        "time": next_snapshot_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "balances": snapshot_balances(current_balances, current_labels),
                    }
                )
                next_snapshot_time += timedelta(hours=1)

            apply_transfer(row, current_balances, current_labels, labels_map)
            row_count += 1

            if row_count % 100000 == 0:
                print(f"Processed {row_count} rows...", end="\r")

    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(snapshots, f, ensure_ascii=False)

    print(f"\nProcessed {row_count} rows.")
    print(f"Generated {len(snapshots)} hourly snapshots.")
    print(f"Saved to {output_json_path}")

    return snapshots


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    parser = argparse.ArgumentParser(
        description="Generate hourly_balance_snapshots.json directly from sorted_transfers.csv"
    )
    parser.add_argument(
        "--data-dir",
        default=os.path.join(base_dir, "public", "data2"),
        help="Target data directory, e.g. public/data or public/data2",
    )
    parser.add_argument(
        "--input",
        dest="input_csv",
        default=None,
        help="Optional explicit sorted_transfers.csv path",
    )
    parser.add_argument(
        "--labels",
        dest="labels_json",
        default=None,
        help="Optional explicit simplified_owner_labels.json path",
    )
    parser.add_argument(
        "--output",
        dest="output_json",
        default=None,
        help="Optional explicit hourly_balance_snapshots.json path",
    )
    args = parser.parse_args()

    data_dir = os.path.abspath(args.data_dir)
    input_csv_path = args.input_csv or os.path.join(data_dir, "sorted_transfers.csv")
    labels_json_path = args.labels_json or os.path.join(data_dir, "simplified_owner_labels.json")
    output_json_path = args.output_json or os.path.join(data_dir, "hourly_balance_snapshots.json")

    generate_hourly_snapshots_from_sorted_transfers(
        input_csv_path=input_csv_path,
        output_json_path=output_json_path,
        labels_json_path=labels_json_path,
    )


if __name__ == "__main__":
    main()
