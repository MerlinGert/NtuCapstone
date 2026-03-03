"""
End-to-end pipeline to generate all data files needed for:
  - Snapshot Time dropdown  (hourly_balance_snapshots.json)
  - Run Detection           (transfer_network_stats.csv)

Run from project root or any directory:
    python front/data_processing/run_pipeline.py
"""
import csv
import sys
import os

# ── Windows-safe field size limit ─────────────────────────────────────────────
csv.field_size_limit(2**31 - 1)

# ── Paths ──────────────────────────────────────────────────────────────────────
HERE          = os.path.dirname(os.path.abspath(__file__))
FRONT_DIR     = os.path.dirname(HERE)                              # .../front
ROOT_DIR      = os.path.dirname(FRONT_DIR)                         # project root
PUBLIC_DIR    = os.path.join(FRONT_DIR,  'public')
PROC_DIR      = os.path.join(PUBLIC_DIR, 'processed', 'transfers')

TRADE_CSV     = os.path.join(ROOT_DIR, 'ACT-24-11-10(1).csv')
TRANSFER_CSV  = os.path.join(ROOT_DIR, 'ACT_transfer_before_2024-11-10(1).csv')
LABELS_JSON   = os.path.join(ROOT_DIR, 'owner_labels.json')        # root copy (840 k lines)

BAL_SNAP_CSV  = os.path.join(PROC_DIR, 'balance_snapshots.csv')
HOURLY_JSON   = os.path.join(PROC_DIR, 'hourly_balance_snapshots.json')
STATS_CSV     = os.path.join(PUBLIC_DIR, 'transfer_network_stats.csv')

os.makedirs(PROC_DIR, exist_ok=True)
os.makedirs(PUBLIC_DIR, exist_ok=True)

sys.path.insert(0, HERE)

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — balance_snapshots.csv
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("STEP 1: generate_balance_snapshots → balance_snapshots.csv")
print("="*60)

from generate_balance_snapshots import generate_balance_snapshots
generate_balance_snapshots(TRADE_CSV, TRANSFER_CSV, BAL_SNAP_CSV)

# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — hourly_balance_snapshots.json
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("STEP 2: generate_hourly_snapshots → hourly_balance_snapshots.json")
print("="*60)

from generate_hourly_snapshots import generate_hourly_snapshots
generate_hourly_snapshots(BAL_SNAP_CSV, HOURLY_JSON, LABELS_JSON)

# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — transfer_network_stats.csv  (for Run Detection)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("STEP 3: precompute_transfer_stats → transfer_network_stats.csv")
print("="*60)

from precompute_transfer_stats import precompute_transfer_stats
precompute_transfer_stats(TRANSFER_CSV, STATS_CSV)

print("\n✅ Pipeline complete.")
print(f"   hourly snapshots : {HOURLY_JSON}")
print(f"   transfer stats   : {STATS_CSV}")
