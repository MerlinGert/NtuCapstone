import csv
import json
import os
from collections import defaultdict

def extract_account_labels(trade_csv_path, transfer_csv_path, output_path):
    # 1. Load known contract addresses from Trade CSV
    known_contracts = set()
    contract_info = {} # address -> {type: "program" | "pool" | "vault" | "other", project: "raydium" | ...}
    
    print(f"Loading known contracts from {trade_csv_path}...")
    
    try:
        with open(trade_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                project = row.get('project', 'unknown')
                
                # Project Program ID
                prog_id = row.get('project_program_id', '').strip()
                if prog_id:
                    known_contracts.add(prog_id)
                    contract_info[prog_id] = {'type': 'program', 'project': project}
                
                # Project Main ID (Pool Address)
                pool_id = row.get('project_main_id', '').strip()
                if pool_id:
                    known_contracts.add(pool_id)
                    contract_info[pool_id] = {'type': 'pool', 'project': project}
                
                # Vaults
                bought_vault = row.get('token_bought_vault', '').strip()
                if bought_vault:
                    known_contracts.add(bought_vault)
                    contract_info[bought_vault] = {'type': 'vault', 'project': project}
                    
                sold_vault = row.get('token_sold_vault', '').strip()
                if sold_vault:
                    known_contracts.add(sold_vault)
                    contract_info[sold_vault] = {'type': 'vault', 'project': project}
                    
                # Mints
                bought_mint = row.get('token_bought_mint_address', '').strip()
                if bought_mint:
                    known_contracts.add(bought_mint)
                    contract_info[bought_mint] = {'type': 'mint', 'project': project}
                    
                sold_mint = row.get('token_sold_mint_address', '').strip()
                if sold_mint:
                    known_contracts.add(sold_mint)
                    contract_info[sold_mint] = {'type': 'mint', 'project': project}

                # Outer Executing Account
                exec_acc = row.get('outer_executing_account', '').strip()
                if exec_acc:
                    # Often same as program or pool, but capture it
                    if exec_acc not in known_contracts:
                        known_contracts.add(exec_acc)
                        contract_info[exec_acc] = {'type': 'executor', 'project': project}

    except FileNotFoundError:
        print(f"Error: Trade file not found at {trade_csv_path}")
        return

    print(f"Loaded {len(known_contracts)} known contract addresses.")

    # 2. Process Transfer CSV
    print(f"Processing transfers from {transfer_csv_path}...")
    
    # Store unique token accounts found
    # address -> { 'owner': owner_address, 'label': 'user' | 'contract', 'details': ... }
    token_accounts = {}
    
    row_count = 0
    try:
        with open(transfer_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row_count += 1
                if row_count % 500000 == 0:
                    print(f"Processed {row_count} rows...")
                
                # Process FROM
                from_ta = row.get('from_token_account', '').strip()
                from_owner = row.get('from_owner', '').strip()
                
                if from_ta:
                    if from_ta not in token_accounts:
                        label = 'user'
                        details = ''
                        
                        # Check if TA itself is a known contract (e.g. vault)
                        if from_ta in known_contracts:
                            info = contract_info[from_ta]
                            label = 'contract'
                            details = f"{info['project']} {info['type']}"
                        
                        # Check if Owner is a known contract (e.g. program or pool)
                        elif from_owner in known_contracts:
                            info = contract_info[from_owner]
                            label = 'contract'
                            details = f"Owned by {info['project']} {info['type']}"
                            
                        token_accounts[from_ta] = {
                            'address': from_ta,
                            'owner': from_owner,
                            'label': label,
                            'details': details
                        }
                
                # Process TO
                to_ta = row.get('to_token_account', '').strip()
                to_owner = row.get('to_owner', '').strip()
                
                if to_ta:
                    if to_ta not in token_accounts:
                        label = 'user'
                        details = ''
                        
                        if to_ta in known_contracts:
                            info = contract_info[to_ta]
                            label = 'contract'
                            details = f"{info['project']} {info['type']}"
                        elif to_owner in known_contracts:
                            info = contract_info[to_owner]
                            label = 'contract'
                            details = f"Owned by {info['project']} {info['type']}"
                            
                        token_accounts[to_ta] = {
                            'address': to_ta,
                            'owner': to_owner,
                            'label': label,
                            'details': details
                        }
                        
    except FileNotFoundError:
        print(f"Error: Transfer file not found at {transfer_csv_path}")
        return

    print(f"Finished processing {row_count} rows.")
    print(f"Found {len(token_accounts)} unique token accounts.")
    
    # 3. Aggregate by Owner
    print(f"Aggregating by owner...")
    owner_aggregation = {} # owner -> { 'token_accounts': [], 'label': ..., 'details': ... }
    
    for ta_data in token_accounts.values():
        owner = ta_data['owner']
        if not owner: # skip if no owner info
            continue
            
        if owner not in owner_aggregation:
            # Determine label for owner based on known contracts
            label = 'user'
            details = ''
            
            if owner in known_contracts:
                info = contract_info[owner]
                label = 'contract'
                details = f"{info['project']} {info['type']}"
            
            # If any of its TAs are known contracts, the owner is likely a program authority
            # (This is already covered by known_contracts check usually, but good for safety)
            
            owner_aggregation[owner] = {
                'owner_address': owner,
                'label': label,
                'details': details,
                'token_accounts': []
            }
            
        # Add TA to this owner
        # Only include necessary TA info to keep file size manageable
        owner_aggregation[owner]['token_accounts'].append({
            'address': ta_data['address'],
            'label': ta_data['label'],
            'details': ta_data['details']
        })

    # Convert to list
    results_list = list(owner_aggregation.values())
    
    # Sort: contracts first, then by number of token accounts descending
    results_list.sort(key=lambda x: (x['label'] != 'contract', -len(x['token_accounts'])))
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results_list, f, indent=2, ensure_ascii=False)
        
    print(f"Results saved to {output_path}")
    
    # Stats
    contract_count = sum(1 for x in results_list if x['label'] == 'contract')
    user_count = len(results_list) - contract_count
    print(f"Summary: {contract_count} Owner Contracts, {user_count} Owner Users")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract and label token accounts from transfers")
    parser.add_argument("--trade-csv", required=True, help="Path to trade CSV")
    parser.add_argument("--transfer-csv", required=True, help="Path to transfer CSV")
    parser.add_argument("--output", required=True, help="Path to output JSON")
    
    args = parser.parse_args()
    
    extract_account_labels(args.trade_csv, args.transfer_csv, args.output)
