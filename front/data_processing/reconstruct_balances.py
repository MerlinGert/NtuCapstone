import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime

# Increase CSV field limit for large fields
csv.field_size_limit(sys.maxsize)

def reconstruct_balances(trade_csv_path, transfer_csv_path, output_dir):
    print(f"Loading trades from {trade_csv_path}...")
    
    # Store trade info by tx_id
    # tx_id -> { 'type': 'buy/sell', 'dex': 'raydium', 'pair': 'WSOL-ACT', ... }
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
    
    print("Processing balance history...")
    
    # owner -> token_symbol -> { 'balance': float, 'history': [] }
    balances = defaultdict(lambda: defaultdict(lambda: {'balance': 0.0, 'history': []}))
    
    # Process sorted transfers
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
            
        from_owner = row.get('from_owner', '').strip()
        to_owner = row.get('to_owner', '').strip()
        block_time = row.get('block_time', '')
        
        # Determine transaction context from Trade CSV
        context = "Transfer"
        trade_details = {}
        if tx_id in trades:
            t = trades[tx_id]
            context = f"Trade on {t['project']}"
            trade_details = {
                'pair': t['pair'],
                'action': f"Swap {t['sold']} -> {t['bought']}",
                'usd_value': t['amount_usd']
            }
        
        # Process Sender (Balance Decrease)
        if from_owner:
            token_data = balances[from_owner][symbol]
            old_bal = token_data['balance']
            new_bal = old_bal - amount
            token_data['balance'] = new_bal
            
            token_data['history'].append({
                'time': block_time,
                'tx_id': tx_id,
                'change': -amount,
                'balance_after': new_bal,
                'reason': f"Sent to {to_owner[:8]}...",
                'context': context,
                'trade_details': trade_details
            })
            
        # Process Receiver (Balance Increase)
        if to_owner:
            token_data = balances[to_owner][symbol]
            old_bal = token_data['balance']
            new_bal = old_bal + amount
            token_data['balance'] = new_bal
            
            token_data['history'].append({
                'time': block_time,
                'tx_id': tx_id,
                'change': +amount,
                'balance_after': new_bal,
                'reason': f"Received from {from_owner[:8]}...",
                'context': context,
                'trade_details': trade_details
            })

    print(f"Processed balances for {len(balances)} owners.")
    
    # Save results
    # Since the file might be huge, let's split by owner hash or just save top holders?
    # Or save one big JSON for now (if < 500MB).
    # Given 70k owners, history could be large. Let's try to save all but minify.
    
    output_path = os.path.join(output_dir, "owner_balance_history.json")
    os.makedirs(output_dir, exist_ok=True)
    
    # Convert defaultdict to dict
    final_output = {}
    for owner, tokens in balances.items():
        final_output[owner] = dict(tokens)
        
    print(f"Saving to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, ensure_ascii=False) # No indent to save space
        
    # Also save a top_holders_history.json for visualization (Top 50 by ACT balance)
    print("Extracting top 50 holders for visualization...")
    
    # Calculate final ACT balance for each owner
    owner_act_balances = []
    for owner, tokens in balances.items():
        act_data = tokens.get('ACT', {})
        bal = act_data.get('balance', 0)
        owner_act_balances.append((owner, bal))
        
    # Sort by balance descending
    owner_act_balances.sort(key=lambda x: x[1], reverse=True)
    
    top_50 = owner_act_balances[:50]
    top_50_output = {}
    for owner, _ in top_50:
        top_50_output[owner] = final_output[owner]
        
    top_path = os.path.join(output_dir, "top_holders_history.json")
    print(f"Saving top 50 holders to {top_path}...")
    with open(top_path, 'w', encoding='utf-8') as f:
        json.dump(top_50_output, f, ensure_ascii=False)
        
    print("Done.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Reconstruct owner balance history")
    parser.add_argument("--trade-csv", required=True, help="Path to trade CSV")
    parser.add_argument("--transfer-csv", required=True, help="Path to transfer CSV")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    
    args = parser.parse_args()
    
    reconstruct_balances(args.trade_csv, args.transfer_csv, args.output_dir)
