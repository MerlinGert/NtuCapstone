"""
Generate 5M, 15M, 30M OHLC candles for ACT and PNUT tokens,
then merge them into the existing OHLC JSON files.

Usage:
    python front/data_processing/generate_sub_hour_ohlc.py
"""
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
FRONT_DIR = os.path.dirname(HERE)

# ── Config ──────────────────────────────────────────────────────────────────
TOKENS = {
    'ACT': {
        'csv': os.path.join(FRONT_DIR, 'public', 'ACT-24-11-10.csv'),
        'ohlc': os.path.join(FRONT_DIR, 'public', 'ACT_OHLC.json'),
    },
    'PNUT': {
        'csv': os.path.join(FRONT_DIR, 'public', 'tokens', 'PNUT', 'data', 'sorted_trades.csv'),
        'ohlc': os.path.join(FRONT_DIR, 'public', 'tokens', 'PNUT', 'OHLC.json'),
    },
}

SUB_HOUR = {
    '5M': 5 * 60,
    '15M': 15 * 60,
    '30M': 30 * 60,
}


def parse_time(s):
    s = s.replace(' UTC', '').strip()
    for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def floor_bucket(dt, seconds):
    ts = int(dt.timestamp())
    aligned = (ts // seconds) * seconds
    return aligned


def build_candles(buckets, vol_buckets):
    """Build sorted OHLC candle list from bucket dict."""
    result = []
    for key in sorted(buckets):
        prices = buckets[key]
        if not prices:
            continue
        result.append({
            't': datetime.utcfromtimestamp(key).strftime('%Y-%m-%d %H:%M:%S'),
            'o': prices[0],
            'h': max(prices),
            'l': min(prices),
            'c': prices[-1],
            'v': vol_buckets.get(key, len(prices)),
        })
    return result


def process_act(csv_path):
    """Read ACT Dune trade CSV, return dict of prices per 5-min bucket."""
    print(f'  Reading ACT trades from {csv_path} ...')
    buckets = defaultdict(list)
    total = 0
    skipped = 0

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            bt = row.get('block_time', '').strip()
            dt = parse_time(bt)
            if dt is None:
                skipped += 1
                continue

            bought_sym = row.get('token_bought_symbol', '').strip()
            sold_sym = row.get('token_sold_symbol', '').strip()
            bought_amt = row.get('token_bought_amount', '').strip()
            sold_amt = row.get('token_sold_amount', '').strip()
            amount_usd = row.get('amount_usd', '').strip()

            price = None
            try:
                usd = float(amount_usd) if amount_usd else 0.0
                if bought_sym == 'ACT' and bought_amt:
                    ba = float(bought_amt)
                    if ba > 0:
                        price = usd / ba
                elif sold_sym == 'ACT' and sold_amt:
                    sa = float(sold_amt)
                    if sa > 0:
                        price = usd / sa
            except (ValueError, ZeroDivisionError):
                pass

            if price is None or price <= 0:
                skipped += 1
                continue

            # Use finest bucket (5 min)
            key = floor_bucket(dt, 5 * 60)
            buckets[key].append(price)

            if total % 200000 == 0:
                print(f'    processed {total:,} rows ...', end='\r')

    print(f'  ACT: {total:,} rows, {skipped:,} skipped, {len(buckets)} 5-min buckets')

    # Clip outliers
    all_prices = sorted(p for prices in buckets.values() for p in prices)
    if len(all_prices) > 100:
        n = len(all_prices)
        lo = all_prices[max(0, int(n * 0.001))]
        hi = all_prices[min(n - 1, int(n * 0.999))]
        print(f'  Price clip: [{lo:.8f}, {hi:.8f}]')
        clipped = defaultdict(list)
        for k, prices in buckets.items():
            clipped[k] = [p for p in prices if lo <= p <= hi]
        buckets = clipped

    return buckets


def process_pnut(csv_path):
    """Read PNUT sorted_trades.csv, return dict of prices per 5-min bucket."""
    print(f'  Reading PNUT trades from {csv_path} ...')
    buckets = defaultdict(list)
    total = 0
    skipped = 0

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            ts_str = row.get('timestamp', '').strip()
            dt = parse_time(ts_str)
            if dt is None:
                skipped += 1
                continue

            try:
                price = float(row.get('price', ''))
            except (ValueError, TypeError):
                skipped += 1
                continue

            if price <= 0:
                skipped += 1
                continue

            key = floor_bucket(dt, 5 * 60)
            buckets[key].append(price)

            if total % 200000 == 0:
                print(f'    processed {total:,} rows ...', end='\r')

    print(f'  PNUT: {total:,} rows, {skipped:,} skipped, {len(buckets)} 5-min buckets')

    # Clip outliers
    all_prices = sorted(p for prices in buckets.values() for p in prices)
    if len(all_prices) > 100:
        n = len(all_prices)
        lo = all_prices[max(0, int(n * 0.001))]
        hi = all_prices[min(n - 1, int(n * 0.999))]
        print(f'  Price clip: [{lo:.8f}, {hi:.8f}]')
        clipped = defaultdict(list)
        for k, prices in buckets.items():
            clipped[k] = [p for p in prices if lo <= p <= hi]
        buckets = clipped

    return buckets


def aggregate_buckets(fine_buckets, target_seconds, fine_seconds=300):
    """Aggregate fine (5-min) buckets into coarser buckets."""
    coarse = defaultdict(list)
    for key, prices in fine_buckets.items():
        aligned = (key // target_seconds) * target_seconds
        coarse[aligned].extend(prices)
    return coarse


def main():
    for token, paths in TOKENS.items():
        csv_path = paths['csv']
        ohlc_path = paths['ohlc']

        if not os.path.exists(csv_path):
            print(f'[SKIP] {token}: CSV not found at {csv_path}')
            continue

        print(f'\n=== Processing {token} ===')

        # Step 1: Read raw trades into 5-min buckets
        if token == 'ACT':
            fine_buckets = process_act(csv_path)
        else:
            fine_buckets = process_pnut(csv_path)

        if not fine_buckets:
            print(f'  No data for {token}, skipping.')
            continue

        # Step 2: Build candles for each sub-hour granularity
        new_data = {}
        for gran, secs in SUB_HOUR.items():
            if secs == 300:
                agg = fine_buckets
            else:
                agg = aggregate_buckets(fine_buckets, secs)
            candles = build_candles(agg, {})
            new_data[gran] = candles
            print(f'  {gran}: {len(candles)} candles')

        # Step 3: Merge into existing OHLC JSON
        if os.path.exists(ohlc_path):
            with open(ohlc_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        else:
            existing = {}

        existing.update(new_data)

        with open(ohlc_path, 'w', encoding='utf-8') as f:
            json.dump(existing, f, separators=(',', ':'))

        size_kb = os.path.getsize(ohlc_path) / 1024
        print(f'  Saved to {ohlc_path} ({size_kb:.1f} KB)')
        print(f'  Granularities: {list(existing.keys())}')

    print('\nDone!')


if __name__ == '__main__':
    main()
