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
from datetime import datetime, timedelta

HERE         = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR     = os.path.dirname(os.path.dirname(HERE))
FRONT_DIR    = os.path.dirname(HERE)
TRADE_CSV    = os.path.join(ROOT_DIR, 'ACT-24-11-10(1).csv')
OUTPUT_JSON  = os.path.join(FRONT_DIR, 'public', 'ACT_OHLC.json')

GRANULARITIES = {
    '1H': 1,
    '1D': 24,
    '3D': 72,
    '1W': 168,
}

def parse_time(s):
    s = s.replace(' UTC', '').strip()
    for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None

def floor_hour(dt):
    return dt.replace(minute=0, second=0, microsecond=0)

def aggregate_hours(ticks, hours):
    """Aggregate 1H ticks into N-hour candles."""
    buckets = defaultdict(list)
    for tk in ticks:
        t = datetime.fromisoformat(tk['t'])
        bucket_start = floor_hour(t)
        # Align to N-hour boundary since epoch
        total_hours = int(t.timestamp() // 3600)
        aligned = (total_hours // hours) * hours * 3600
        key = aligned
        buckets[key].append(tk)

    result = []
    for key in sorted(buckets):
        group = buckets[key]
        result.append({
            't': datetime.utcfromtimestamp(key).strftime('%Y-%m-%d %H:%M:%S'),
            'o': group[0]['o'],
            'h': max(c['h'] for c in group),
            'l': min(c['l'] for c in group),
            'c': group[-1]['c'],
            'v': sum(c['v'] for c in group),
        })
    return result

def main():
    print(f'Reading {TRADE_CSV} ...')

    # ── Collect per-hour OHLC ───────────────────────────────────────────────
    hour_buckets = defaultdict(list)   # hour_timestamp_int → [price, ...]
    hour_vol     = defaultdict(int)

    total = 0
    skipped = 0

    with open(TRADE_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            bt = row.get('block_time', '').strip()
            dt = parse_time(bt)
            if dt is None:
                skipped += 1
                continue

            bought_sym = row.get('token_bought_symbol', '').strip()
            sold_sym   = row.get('token_sold_symbol', '').strip()
            bought_amt = row.get('token_bought_amount', '').strip()
            sold_amt   = row.get('token_sold_amount', '').strip()
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

            # Hour bucket key (integer seconds)
            hour_key = int(floor_hour(dt).timestamp())
            hour_buckets[hour_key].append(price)
            hour_vol[hour_key] += 1

            if total % 100000 == 0:
                print(f'  processed {total:,} rows ...', end='\r')

    print(f'\nTotal rows: {total:,}  |  skipped: {skipped:,}  |  valid hours: {len(hour_buckets)}')

    # ── Global percentile clipping to remove outlier ticks ──────────────────
    all_prices = sorted(p for prices in hour_buckets.values() for p in prices)
    n = len(all_prices)
    p01 = all_prices[max(0, int(n * 0.001))]
    p99 = all_prices[min(n - 1, int(n * 0.999))]
    print(f'   Price clip range: [{p01:.6f}, {p99:.6f}]  (0.1%–99.9% percentile)')

    # ── Build 1H candles ────────────────────────────────────────────────────
    ticks_1h = []
    for key in sorted(hour_buckets):
        prices = [p for p in hour_buckets[key] if p01 <= p <= p99]
        if not prices:
            continue
        ticks_1h.append({
            't': datetime.utcfromtimestamp(key).strftime('%Y-%m-%d %H:%M:%S'),
            'o': prices[0],
            'h': max(prices),
            'l': min(prices),
            'c': prices[-1],
            'v': hour_vol[key],
        })

    # ── Build other granularities ────────────────────────────────────────────
    output = {'1H': ticks_1h}
    for gran, hours in GRANULARITIES.items():
        if gran == '1H':
            continue
        output[gran] = aggregate_hours(ticks_1h, hours)
        print(f"  {gran}: {len(output[gran])} candles")

    # ── Save ────────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output, f, separators=(',', ':'))

    size_kb = os.path.getsize(OUTPUT_JSON) / 1024
    print(f'\n✅ Saved to {OUTPUT_JSON}  ({size_kb:.1f} KB)')
    print(f'   1H candles: {len(ticks_1h)}')

if __name__ == '__main__':
    main()
