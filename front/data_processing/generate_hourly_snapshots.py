
import csv
import json
import os
import sys
from datetime import datetime, timedelta

# Increase CSV field limit
csv.field_size_limit(2**31 - 1)

def load_owner_labels(json_path):
    print(f"Loading owner labels from {json_path}...")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            labels_data = json.load(f)
        
        labels_map = {}
        for item in labels_data:
            if 'owner_address' in item and 'label' in item:
                labels_map[item['owner_address']] = item['label']
        
        print(f"Loaded {len(labels_map)} labels.")
        return labels_map
    except Exception as e:
        print(f"Error loading labels: {e}")
        return {}

def generate_hourly_snapshots(input_csv_path, output_json_path, labels_json_path):
    labels_map = load_owner_labels(labels_json_path)
    
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
                    users = {}
                    contracts = {}
                    exchanges = {}
                    
                    for owner, bal in current_balances.items():
                        if bal > 0:
                            label = labels_map.get(owner, 'user')
                            if label == 'contract':
                                contracts[owner] = bal
                            elif label == 'exchange':
                                exchanges[owner] = bal
                            else:
                                users[owner] = bal
                    
                    snapshot_data = {
                        "time": next_snapshot_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "balances": {
                            "users": users,
                            "contracts": contracts
                        }
                    }
                    if exchanges:
                        snapshot_data["balances"]["exchanges"] = exchanges
                        
                    snapshots.append(snapshot_data)
                    
                    if len(snapshots) % 10 == 0:
                        total_holders = len(users) + len(contracts) + len(exchanges)
                        print(f"Generated snapshot for {next_snapshot_time} ({total_holders} holders)...")
                        
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

            # Add final snapshot if needed? The user logic implies continuous process.
            # We stick to the loop logic which captures passed hours.
            
    except FileNotFoundError:
        print(f"Error: File not found at {input_csv_path}")
        return

    print(f"\nFinished processing {row_count} rows. Generated {len(snapshots)} hourly snapshots.")
    
    print(f"Saving to {output_json_path}...")
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(snapshots, f, ensure_ascii=False) # No indent to save space
        
    if snapshots:
        output_dir = os.path.dirname(output_json_path)
        latest_output_path = os.path.join(output_dir, 'latest_balance_snapshot.json')
        print(f"Saving latest snapshot to {latest_output_path}...")
        with open(latest_output_path, 'w', encoding='utf-8') as f:
            json.dump(snapshots[-1], f, ensure_ascii=False, indent=2)
            
    print("Done.")

if __name__ == "__main__":
    # Define paths
    base_dir = "/Users/xiaolin/Projects/CryptoVis/code/front/public/processed/transfers"
    input_csv = os.path.join(base_dir, "balance_snapshots.csv")
    output_json = os.path.join(base_dir, "hourly_balance_snapshots.json")
    labels_json = os.path.join(base_dir, "owner_labels.json")
    
    generate_hourly_snapshots(input_csv, output_json, labels_json)
