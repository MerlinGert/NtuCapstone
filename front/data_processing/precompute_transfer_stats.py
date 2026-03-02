
import pandas as pd
import os

def precompute_transfer_stats(input_path, output_path):
    print(f"Processing data from: {input_path}")
    
    # 1. Check if file exists
    if not os.path.exists(input_path):
        print(f"Error: Input file {input_path} not found.")
        return

    try:
        # 2. Load relevant columns
        # We only need block_time, from_owner, to_owner
        df = pd.read_csv(input_path, usecols=['block_time', 'from_owner', 'to_owner'])
        print(f"Loaded {len(df)} transactions.")

        # 3. Filter valid transactions
        # Remove empty owners
        df = df.dropna(subset=['from_owner', 'to_owner'])
        
        # 4. Compute Pairwise Statistics
        # Group by (from_owner, to_owner)
        # Count transactions
        # Find min and max block_time for the pair
        stats = df.groupby(['from_owner', 'to_owner']).agg(
            transaction_count=('block_time', 'count'),
            first_transaction=('block_time', 'min'),
            last_transaction=('block_time', 'max')
        ).reset_index()

        print(f"Computed statistics for {len(stats)} unique pairs.")

        # 5. Save to CSV
        stats.to_csv(output_path, index=False)
        print(f"Saved processed stats to: {output_path}")
        
        # Optional: Print preview
        print("\nPreview of generated data:")
        print(stats.head())

    except Exception as e:
        print(f"Error processing data: {e}")

if __name__ == "__main__":
    # Define paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # Assuming the public folder is at ../public relative to data_processing
    PUBLIC_DIR = os.path.join(os.path.dirname(BASE_DIR), 'public')
    
    INPUT_FILE = os.path.join(PUBLIC_DIR, 'ACT_transfer_before_2024-11-10.csv')
    OUTPUT_FILE = os.path.join(PUBLIC_DIR, 'transfer_network_stats.csv')

    precompute_transfer_stats(INPUT_FILE, OUTPUT_FILE)
