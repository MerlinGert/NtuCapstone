import os
import sys

# Add the directory to sys.path so we can import preprocess_data
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import preprocess_data

# Override the paths to use data2
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
DATA2_DIR = os.path.join(PUBLIC_DIR, "data2")

preprocess_data.SORTED_TRADES_PATH = os.path.join(DATA2_DIR, "sorted_trades.csv")
preprocess_data.USER_EARNINGS_1MIN_PATH = os.path.join(DATA2_DIR, "user_earnings_1min.json")
preprocess_data.USER_EARNINGS_1H_PATH = os.path.join(DATA2_DIR, "user_earnings_1h.json")
preprocess_data.USER_EARNINGS_1D_PATH = os.path.join(DATA2_DIR, "user_earnings_1d.json")

print("Paths overridden for data2:")
print(f"Trades: {preprocess_data.SORTED_TRADES_PATH}")
print(f"Earnings 1H: {preprocess_data.USER_EARNINGS_1H_PATH}")

print("\nStarting generation...")
preprocess_data.generate_user_earnings()
print("Finished generation.")
