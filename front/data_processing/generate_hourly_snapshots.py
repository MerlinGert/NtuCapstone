import csv
import json
import os
import sys
from datetime import datetime, timedelta

# Increase CSV field limit
csv.field_size_limit(sys.maxsize)

def generate_hourly_snapshots(input_csv_path, output_json_path):
    print(f"Reading balance history from {input_csv_path}...")
    
    current_balances = {}  # {owner: balance}
    snapshots = []
    
    try:
        with open(input_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Read first row to initialize time
            try:
                first_row = next(reader)
            except StopIteration:
                print("Error: Input CSV is empty.")
                return

            # Parse time format: "2024-10-19 11:27:09.000 UTC"
            def parse_time(t_str):
                # Remove milliseconds if present
                if '.' in t_str:
                    t_str = t_str.split('.')[0] + ' UTC'
                return datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S UTC")

            current_time = parse_time(first_row['time'])
            
            # Align to the next hour (e.g., 11:27 -> 12:00)
            next_snapshot_time = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            
            print(f"Start time: {current_time}, First snapshot target: {next_snapshot_time}")

            # Process first row
            owner = first_row['owner_address']
            bal = float(first_row['balance_after'])
            current_balances[owner] = bal
            
            # Iterate through remaining rows
            row_count = 1
            for row in reader:
                row_time_str = row['time']
                try:
                    row_time = parse_time(row_time_str)
                except ValueError:
                    continue # Skip invalid time

                # Check if we crossed one or more hourly boundaries
                while row_time >= next_snapshot_time:
                    # Take snapshot of current state
                    snapshot_data = {
                        owner: bal 
                        for owner, bal in current_balances.items() 
                        if bal > 0  # Filter out zero balances to save space
                    }
                    
                    snapshots.append({
                        "time": next_snapshot_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "balances": snapshot_data
                    })
                    
                    if len(snapshots) % 10 == 0:
                        print(f"Generated snapshot for {next_snapshot_time} ({len(snapshot_data)} holders)...")
                        
                    next_snapshot_time += timedelta(hours=1)
                
                # Update current balance
                owner = row['owner_address']
                try:
                    bal = float(row['balance_after'])
                    current_balances[owner] = bal
                except ValueError:
                    continue
                    
                row_count += 1
                if row_count % 100000 == 0:
                    print(f"Processed {row_count} rows...", end='\r')

            # Add final snapshot if needed (up to the last processed time's hour)
            # Actually, the loop handles up to the last row time.
            # If the last row is 14:30, and next_snapshot was 14:00 (already done) -> 15:00.
            # We might want to capture the final state as well? 
            # The user asked for "hourly snapshots".
            
    except FileNotFoundError:
        print(f"Error: File not found at {input_csv_path}")
        return

    print(f"\nFinished processing {row_count} rows. Generated {len(snapshots)} hourly snapshots.")
    
    print(f"Saving to {output_json_path}...")
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(snapshots, f, ensure_ascii=False) # No indent to save space
        
    print("Done.")

if __name__ == "__main__":
    # Define paths
    base_dir = "/Users/xiaolin/Projects/CryptoVis/code/front/public/processed/transfers"
    input_csv = os.path.join(base_dir, "balance_snapshots.csv")
    output_json = os.path.join(base_dir, "hourly_balance_snapshots.json")
    
    generate_hourly_snapshots(input_csv, output_json)
