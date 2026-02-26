import csv
import json
import os
import sys
from collections import defaultdict

def check_contracts(trade_csv_path, transfer_csv_path, output_path):
    print(f"Reading contracts from {trade_csv_path}...")
    
    # Store addresses and their types
    # address -> set of types (e.g. {'project_main_id', 'token_bought_vault'})
    contracts = defaultdict(set)
    
    contract_cols = [
        'project_program_id', 
        'project_main_id', 
        'token_bought_vault', 
        'token_sold_vault',
        'outer_executing_account'
    ]
    
    try:
        with open(trade_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                for col in contract_cols:
                    addr = row.get(col, '').strip()
                    if addr:
                        contracts[addr].add(col)
    except FileNotFoundError:
        print(f"Error: Trade file not found at {trade_csv_path}")
        return

    print(f"Found {len(contracts)} unique contract-related addresses.")
    
    # Prepare stats container
    # address -> { 'types': [...], 'found_in_transfers': { 'from_owner': count, 'to_owner': count, ... } }
    results = {}
    for addr, types in contracts.items():
        results[addr] = {
            'types': list(types),
            'found_in_transfers': defaultdict(int),
            'total_matches': 0
        }

    print(f"Scanning transfers in {transfer_csv_path}...")
    
    transfer_check_cols = [
        'from_owner', 'to_owner', 
        'from_token_account', 'to_token_account', 
        'token_mint_address',
        'outer_executing_account'
    ]
    
    row_count = 0
    match_count = 0
    
    try:
        with open(transfer_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row_count += 1
                if row_count % 100000 == 0:
                    print(f"Processed {row_count} rows...")
                
                for col in transfer_check_cols:
                    val = row.get(col, '').strip()
                    if val in results:
                        results[val]['found_in_transfers'][col] += 1
                        results[val]['total_matches'] += 1
                        match_count += 1
                        
    except FileNotFoundError:
        print(f"Error: Transfer file not found at {transfer_csv_path}")
        return

    print(f"Finished scanning {row_count} rows. Found {match_count} matches.")

    # Filter out addresses that were not found
    found_contracts = {k: v for k, v in results.items() if v['total_matches'] > 0}
    
    # Convert defaultdict to dict for JSON serialization
    final_output = []
    for addr, data in found_contracts.items():
        entry = {
            'address': addr,
            'types': data['types'],
            'total_matches': data['total_matches'],
            'matches_by_column': dict(data['found_in_transfers'])
        }
        final_output.append(entry)
        
    # Sort by total matches descending
    final_output.sort(key=lambda x: x['total_matches'], reverse=True)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)
    
    print(f"Results saved to {output_path}")
    
    # Print summary
    print("\nTop 10 matched addresses:")
    for item in final_output[:10]:
        print(f"{item['address']} ({', '.join(item['types'])}): {item['total_matches']} matches")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract contract addresses and check them in transfers")
    parser.add_argument("--trade-csv", required=True, help="Path to trade CSV")
    parser.add_argument("--transfer-csv", required=True, help="Path to transfer CSV")
    parser.add_argument("--output", required=True, help="Path to output JSON")
    
    args = parser.parse_args()
    
    check_contracts(args.trade_csv, args.transfer_csv, args.output)
