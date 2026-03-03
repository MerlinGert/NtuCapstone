"""
Reads top_holders_history.json (full tx history, ~278MB)
and outputs top_holders_summary.json (daily close balance, <1MB).

Usage:
    python summarize_holders.py
"""
import json
import os
from datetime import datetime, timezone

INPUT  = os.path.join(os.path.dirname(__file__), '..', 'public', 'processed', 'transfers', 'top_holders_history.json')
OUTPUT = os.path.join(os.path.dirname(__file__), '..', 'public', 'processed', 'transfers', 'top_holders_summary.json')

def parse_time(s):
    """Parse 'YYYY-MM-DD HH:MM:SS.mmm UTC' → datetime (UTC)."""
    try:
        return datetime.strptime(s.replace(' UTC', ''), '%Y-%m-%d %H:%M:%S.%f')
    except Exception:
        try:
            return datetime.strptime(s.replace(' UTC', ''), '%Y-%m-%d %H:%M:%S')
        except Exception:
            return None

def summarize():
    print(f"Loading {INPUT} ...")
    with open(INPUT, 'r', encoding='utf-8') as f:
        data = json.load(f)

    result = {}
    total_owners = len(data)
    for i, (owner, tokens) in enumerate(data.items()):
        print(f"  [{i+1}/{total_owners}] {owner[:12]}...")
        owner_summary = {}
        for symbol, token_data in tokens.items():
            history = token_data.get('history', [])
            if not history:
                continue

            # ── Build daily close: keep last record per calendar day ──────
            daily = {}   # 'YYYY-MM-DD' → {time, balance_after, change, reason, context}
            for rec in history:
                t = parse_time(rec.get('time', ''))
                if t is None:
                    continue
                day_key = t.strftime('%Y-%m-%d')
                # Last record of each day wins
                daily[day_key] = {
                    'time': rec.get('time', ''),
                    'balance_after': rec.get('balance_after', 0),
                    'change': rec.get('change', 0),
                    'reason': rec.get('reason', ''),
                    'context': rec.get('context', '')
                }

            if not daily:
                continue

            # Sort by date
            sorted_days = sorted(daily.items())
            owner_summary[symbol] = {
                'balance': token_data.get('balance', sorted_days[-1][1]['balance_after']),
                'history': [v for _, v in sorted_days]
            }

        if owner_summary:
            result[owner] = owner_summary

    print(f"Saving to {OUTPUT} ...")
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, separators=(',', ':'))

    size_kb = os.path.getsize(OUTPUT) / 1024
    print(f"Done. Output size: {size_kb:.1f} KB ({size_kb/1024:.2f} MB)")

if __name__ == '__main__':
    summarize()
