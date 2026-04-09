"""
Generate missing PNUT data files (user_actions.json, user_balance_*.json)
by reusing preprocess_data.py functions with PNUT paths.
"""
import sys
import os

# Patch the paths before importing preprocess_data
import preprocess_data

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PNUT_DATA_DIR = os.path.join(BASE_DIR, "public", "tokens", "PNUT", "data")

# Override input/output paths to point to PNUT
preprocess_data.SORTED_TRANSFERS_PATH = os.path.join(PNUT_DATA_DIR, "sorted_transfers.csv")
preprocess_data.SORTED_TRADES_PATH = os.path.join(PNUT_DATA_DIR, "sorted_trades.csv")
preprocess_data.USER_ACTIONS_PATH = os.path.join(PNUT_DATA_DIR, "user_actions.json")
preprocess_data.USER_BALANCE_1MIN_PATH = os.path.join(PNUT_DATA_DIR, "user_balance_1min.json")
preprocess_data.USER_BALANCE_1H_PATH = os.path.join(PNUT_DATA_DIR, "user_balance_1h.json")
preprocess_data.USER_BALANCE_1D_PATH = os.path.join(PNUT_DATA_DIR, "user_balance_1d.json")
preprocess_data.USER_EARNINGS_1MIN_PATH = os.path.join(PNUT_DATA_DIR, "user_earnings_1min.json")
preprocess_data.USER_EARNINGS_1H_PATH = os.path.join(PNUT_DATA_DIR, "user_earnings_1h.json")
preprocess_data.USER_EARNINGS_1D_PATH = os.path.join(PNUT_DATA_DIR, "user_earnings_1d.json")

print(f"PNUT data dir: {PNUT_DATA_DIR}")
print(f"Sorted trades: {preprocess_data.SORTED_TRADES_PATH}")
print(f"Sorted transfers: {preprocess_data.SORTED_TRANSFERS_PATH}")

# Generate user_actions.json
print("\n=== Generating user_actions.json ===")
preprocess_data.generate_user_actions()

# Generate user_balance_*.json
print("\n=== Generating user_balance_*.json ===")
preprocess_data.generate_user_balances()

print("\nDone! PNUT data files generated.")
