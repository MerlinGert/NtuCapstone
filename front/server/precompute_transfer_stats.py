
import pandas as pd
import os

# Adjust BASE_DIR to point to project root (parent of server/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSFER_CSV_PATH = os.path.join(BASE_DIR, "public", "ACT_transfer_before_2024-11-10.csv")
OUTPUT_PATH = os.path.join(BASE_DIR, "public", "transfer_network_stats.csv")

def main():
    if not os.path.exists(TRANSFER_CSV_PATH):
        print(f"Error: Input file not found at {TRANSFER_CSV_PATH}")
        return

    print(f"Reading {TRANSFER_CSV_PATH}...")
    df = pd.read_csv(TRANSFER_CSV_PATH)
    
    # Ensure amount_display is numeric
    # Using amount_display as the volume metric
    df['amount_display'] = pd.to_numeric(df['amount_display'], errors='coerce').fillna(0)
    
    print("Grouping and aggregating...")
    # Group by from_owner, to_owner
    # Aggregate: count, min time, max time, sum amount
    stats = df.groupby(['from_owner', 'to_owner']).agg(
        transaction_count=('block_time', 'count'),
        first_transaction=('block_time', 'min'),
        last_transaction=('block_time', 'max'),
        total_volume=('amount_display', 'sum')
    ).reset_index()
    
    print(f"Writing to {OUTPUT_PATH}...")
    stats.to_csv(OUTPUT_PATH, index=False)
    print("Done.")

if __name__ == "__main__":
    main()
