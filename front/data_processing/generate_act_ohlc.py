"""
Generates ACT_OHLC.json from ACT trade CSV.
Aggregates prices into hourly OHLC candles.

Output: front/public/ACT_OHLC.json
  { "1H": [{t, o, h, l, c, v}, ...], ... }
  Granularities stored: 1H (all others computed in browser from 1H buckets)

Run:
    python front/data_processing/generate_act_ohlc.py
"""

import csv
import json
import os
from collections import defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(HERE))
FRONT_DIR = os.path.dirname(HERE)
TRADE_CSV = os.path.join(ROOT_DIR, "ACT-24-11-10(1).csv")
OUTPUT_JSON = os.path.join(FRONT_DIR, "public", "ACT_OHLC.json")

GRANULARITIES = {
    "1min": 1,         # 1 minute
    "5min": 5,         # 5 minutes
    "15min": 15,       # 15 minutes
    "30min": 30,       # 30 minutes
    "1H": 60,          # 60 minutes
    "1D": 24 * 60,     # 1 day in minutes
    "3D": 72 * 60,     # 3 days in minutes
    "1W": 168 * 60,    # 1 week in minutes
}


def parse_time(s):
    s = s.replace(" UTC", "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def floor_minute(dt):
    return dt.replace(second=0, microsecond=0)


def aggregate_minutes(ticks, minutes):
    """Aggregate 1-minute ticks into N-minute candles."""
    buckets = defaultdict(list)
    for tk in ticks:
        t = datetime.fromisoformat(tk["t"])
        # Align to N-minute boundary since epoch
        total_minutes = int(t.timestamp() // 60)
        aligned = (total_minutes // minutes) * minutes * 60
        key = aligned
        buckets[key].append(tk)

    result = []
    for key in sorted(buckets):
        group = buckets[key]
        result.append(
            {
                "t": datetime.utcfromtimestamp(key).strftime("%Y-%m-%d %H:%M:%S"),
                "o": group[0]["o"],
                "h": max(c["h"] for c in group),
                "l": min(c["l"] for c in group),
                "c": group[-1]["c"],
                "v": sum(c["v"] for c in group),
            }
        )
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--coin", type=str, default="ACT", help="Coin to process (ACT or PNUT)")
    parser.add_argument("--trade-csv", type=str, help="Path to input trades CSV")
    parser.add_argument("--output-json", type=str, help="Path to output OHLC JSON")
    args = parser.parse_args()

    coin = args.coin
    if args.trade_csv:
        trade_csv = args.trade_csv
    else:
        if coin == "ACT":
            trade_csv = os.path.join(ROOT_DIR, "..", "data", "ACT-24-11-10.csv")
        else:
            trade_csv = os.path.join(ROOT_DIR, "..", "data", "PNUT_data_part1", "sorted_trades.csv")

    if args.output_json:
        output_json = args.output_json
    else:
        data_dir = "data" if coin == "ACT" else "data2"
        output_json = os.path.join(FRONT_DIR, "public", data_dir, f"{coin}_OHLC.json")

    print(f"Reading {trade_csv} ...")

    # ── Collect per-minute OHLC ───────────────────────────────────────────────
    minute_buckets = defaultdict(list)  # minute_timestamp_int → [price, ...]
    minute_vol = defaultdict(int)

    total = 0
    skipped = 0

    with open(trade_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            # Check for standard 'block_time' or fallback to 'timestamp' (PNUT format)
            bt = row.get("block_time") or row.get("timestamp", "")
            bt = bt.strip()
            dt = parse_time(bt)
            if dt is None:
                skipped += 1
                continue

            bought_sym = row.get("token_bought_symbol", "").strip()
            sold_sym = row.get("token_sold_symbol", "").strip()
            bought_amt = row.get("token_bought_amount", "").strip()
            sold_amt = row.get("token_sold_amount", "").strip()
            amount_usd = row.get("amount_usd", "").strip()

            price = None
            try:
                usd = float(amount_usd) if amount_usd else 0.0
                if usd > 0:
                    if bought_sym == coin and bought_amt:
                        ba = float(bought_amt)
                        if ba > 0:
                            price = usd / ba
                    elif sold_sym == coin and sold_amt:
                        sa = float(sold_amt)
                        if sa > 0:
                            price = usd / sa
                    # Handle PNUT fallback since it uses different column format
                    elif coin == "PNUT" and row.get("price"):
                        price = float(row.get("price"))
            except (ValueError, ZeroDivisionError):
                pass

            if price is None or price <= 0:
                skipped += 1
                continue

            # Minute bucket key (integer seconds)
            minute_key = int(floor_minute(dt).timestamp())
            minute_buckets[minute_key].append(price)
            minute_vol[minute_key] += 1

            if total % 100000 == 0:
                print(f"  processed {total:,} rows ...", end="\r")

    print(f"\nTotal rows: {total:,}  |  skipped: {skipped:,}  |  valid minutes: {len(minute_buckets)}")

    # ── Global percentile clipping to remove outlier ticks ──────────────────
    all_prices = sorted(p for prices in minute_buckets.values() for p in prices)
    n = len(all_prices)
    if n == 0:
        print("No valid prices found!")
        return

    p01 = all_prices[max(0, int(n * 0.001))]
    p99 = all_prices[min(n - 1, int(n * 0.999))]
    print(f"   Price clip range: [{p01:.6f}, {p99:.6f}]  (0.1%–99.9% percentile)")

    # ── Build 1min candles ────────────────────────────────────────────────────
    ticks_1m = []
    for key in sorted(minute_buckets):
        prices = [p for p in minute_buckets[key] if p01 <= p <= p99]
        if not prices:
            continue
        ticks_1m.append(
            {
                "t": datetime.utcfromtimestamp(key).strftime("%Y-%m-%d %H:%M:%S"),
                "o": prices[0],
                "h": max(prices),
                "l": min(prices),
                "c": prices[-1],
                "v": minute_vol[key],
            }
        )

    # ── Build other granularities ────────────────────────────────────────────
    output = {"1min": ticks_1m}
    for gran, minutes in GRANULARITIES.items():
        if gran == "1min":
            continue
        output[gran] = aggregate_minutes(ticks_1m, minutes)
        print(f"  {gran}: {len(output[gran])} candles")

    # ── Save ────────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(output, f, separators=(",", ":"))

    size_kb = os.path.getsize(output_json) / 1024
    print(f"\n✅ Saved to {output_json}  ({size_kb:.1f} KB)")
    print(f"   1min candles: {len(ticks_1m)}")


if __name__ == "__main__":
    main()
