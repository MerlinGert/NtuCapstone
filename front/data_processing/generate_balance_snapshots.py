import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime

# Increase CSV field limit for large fields
csv.field_size_limit(sys.maxsize)

def generate_balance_snapshots(trade_csv_path, transfer_csv_path, output_path):
    print(f"Loading trades from {trade_csv_path}...")
    
    # Store trade info by tx_id
    trades = {}
    
    try:
        with open(trade_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tx_id = row.get('tx_id', '').strip()
                if not tx_id:
                    continue
                    
                trades[tx_id] = {
                    'project': row.get('project', 'unknown'),
                    'pair': row.get('token_pair', ''),
                    'bought': row.get('token_bought_symbol', ''),
                    'sold': row.get('token_sold_symbol', ''),
                    'amount_usd': row.get('amount_usd', '0'),
                    'block_time': row.get('block_time', '')
                }
    except FileNotFoundError:
        print(f"Error: Trade file not found at {trade_csv_path}")
        return

    print(f"Loaded {len(trades)} trades.")

    print(f"Loading transfers from {transfer_csv_path}...")
    transfers = []
    
    try:
        with open(transfer_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Parse sorting keys
                try:
                    slot = int(row.get('block_slot', 0))
                except ValueError:
                    slot = 0
                    
                try:
                    tx_idx = int(row.get('tx_index', 0))
                except ValueError:
                    tx_idx = 0
                    
                try:
                    outer_idx = int(row.get('outer_instruction_index', 0) or 0) # Handle empty string
                except ValueError:
                    outer_idx = 0
                    
                try:
                    inner_idx = int(row.get('inner_instruction_index', 0) or 0)
                except ValueError:
                    inner_idx = 0
                
                transfers.append({
                    'data': row,
                    'sort_key': (slot, tx_idx, outer_idx, inner_idx)
                })
                
    except FileNotFoundError:
        print(f"Error: Transfer file not found at {transfer_csv_path}")
        return

    print(f"Loaded {len(transfers)} transfers. Sorting by block_slot/tx_index...")
    
    # Sort transfers chronologically
    transfers.sort(key=lambda x: x['sort_key'])
    
    print(f"Processing balance history and writing to {output_path}...")
    
    # owner -> token_symbol -> balance
    balances = defaultdict(lambda: defaultdict(float))
    
    # Open output CSV
    with open(output_path, 'w', encoding='utf-8', newline='') as out_f:
        fieldnames = [
            'time', 'block_slot', 'tx_id', 'owner_address', 'token_symbol', 
            'change_amount', 'balance_after', 'reason', 'context'
        ]
        writer = csv.DictWriter(out_f, fieldnames=fieldnames)
        writer.writeheader()
        
        count = 0
        for item in transfers:
            row = item['data']
            tx_id = row.get('tx_id', '')
            symbol = row.get('symbol', 'UNKNOWN')
            
            # Get amount
            try:
                amount = float(row.get('amount_display', 0))
            except ValueError:
                amount = 0.0
                
            if amount == 0:
                continue

            # Identify sender and receiver
            source_owner = row.get('from_owner', '').strip()
            dest_owner = row.get('to_owner', '').strip()
            
            # If owner fields are missing, fallback to token account (though less ideal)
            if not source_owner:
                source_owner = row.get('from_token_account', 'UNKNOWN_SOURCE')
            if not dest_owner:
                dest_owner = row.get('to_token_account', 'UNKNOWN_DEST')
                
            block_time = row.get('block_time', '')
            if 'T' in block_time and 'UTC' not in block_time:
                 block_time = block_time.replace('T', ' ').replace('Z', ' UTC')
            slot = row.get('block_slot', '')
            
            # Determine context (Trade or Transfer)
            context = "Transfer"
            trade_info = {}
            if tx_id in trades:
                trade = trades[tx_id]
                trade_info = trade
                # Check if it's a buy or sell for this user
                # If user is receiving ACT and gave SOL, it's a Buy
                # But here we just label it as "Trade"
                context = f"Trade on {trade.get('project', 'DEX')}"

            # Update Source Balance (Decrease)
            if source_owner and source_owner != 'UNKNOWN_SOURCE':
                balances[source_owner][symbol] -= amount
                new_bal = balances[source_owner][symbol]
                
                reason = f"Sent to {dest_owner[:8]}..."
                if context.startswith("Trade"):
                    reason = f"Sold on {trade_info.get('project', 'DEX')}"
                
                writer.writerow({
                    'time': block_time,
                    'block_slot': slot,
                    'tx_id': tx_id,
                    'owner_address': source_owner,
                    'token_symbol': symbol,
                    'change_amount': -amount,
                    'balance_after': new_bal,
                    'reason': reason,
                    'context': context
                })
                count += 1

            # Update Destination Balance (Increase)
            if dest_owner and dest_owner != 'UNKNOWN_DEST':
                balances[dest_owner][symbol] += amount
                new_bal = balances[dest_owner][symbol]
                
                reason = f"Received from {source_owner[:8]}..."
                if context.startswith("Trade"):
                    reason = f"Bought on {trade_info.get('project', 'DEX')}"
                
                writer.writerow({
                    'time': block_time,
                    'block_slot': slot,
                    'tx_id': tx_id,
                    'owner_address': dest_owner,
                    'token_symbol': symbol,
                    'change_amount': amount,
                    'balance_after': new_bal,
                    'reason': reason,
                    'context': context
                })
                count += 1
                
            if count % 10000 == 0:
                print(f"Processed {count} balance updates...", end='\r')

    print(f"\nDone! Generated {count} balance snapshots in {output_path}")

if __name__ == "__main__":
    # Define paths
    base_dir = "/Users/xiaolin/Projects/CryptoVis/code/front/public"
    processed_dir = os.path.join(base_dir, "processed/transfers")
    trade_csv = os.path.join(base_dir, "ACT-24-11-10.csv")
    transfer_csv = os.path.join(base_dir, "ACT_transfer_before_2024-11-10.csv")
    output_csv = os.path.join(processed_dir, "balance_snapshots.csv")
    
    generate_balance_snapshots(trade_csv, transfer_csv, output_csv)
