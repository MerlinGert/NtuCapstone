import pandas as pd
import json
import os
import sys

# File paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OWNER_LABELS_PATH = os.path.join(BASE_DIR, 'public/processed/transfers/owner_labels.json')
TRANSFERS_CSV_PATH = os.path.join(BASE_DIR, 'public/ACT_transfer_before_2024-11-10.csv')
ACT_TRADES_CSV_PATH = os.path.join(BASE_DIR, 'public/ACT-24-11-10.csv')
OUTPUT_PATH = os.path.join(BASE_DIR, 'public/processed/user_behavior_sequences.json')

def load_user_addresses():
    print(f"Loading user addresses from {OWNER_LABELS_PATH}...")
    try:
        with open(OWNER_LABELS_PATH, 'r') as f:
            labels = json.load(f)
        
        user_addresses = set()
        for entry in labels:
            if entry.get('label') == 'user':
                user_addresses.add(entry['owner_address'])
                
        print(f"Found {len(user_addresses)} user addresses.")
        return user_addresses
    except Exception as e:
        print(f"Error loading user addresses: {e}")
        return set()

def load_act_trades():
    print(f"Loading ACT trades from {ACT_TRADES_CSV_PATH}...")
    try:
        # Read the CSV
        df = pd.read_csv(ACT_TRADES_CSV_PATH)
        
        trades_map = {}
        count = 0
        
        for _, row in df.iterrows():
            tx_id = row['tx_id']
            if pd.isna(tx_id):
                continue
                
            trade_info = {
                'project': row['project'], # e.g. raydium, whirlpool
                'block_time': row['block_time'],
                'trader_id': row['trader_id'],
                'token_pair': row['token_pair'],
                'amount_usd': row['amount_usd'],
                'token_bought_symbol': row['token_bought_symbol'],
                'token_sold_symbol': row['token_sold_symbol'],
                'token_bought_amount': row['token_bought_amount'],
                'token_sold_amount': row['token_sold_amount']
            }
            
            # Determine type and amounts
            if row['token_bought_symbol'] == 'ACT':
                trade_info['type'] = 'buy'
                trade_info['act_amount'] = row['token_bought_amount']
                if row['token_bought_amount'] > 0:
                    trade_info['price_usd'] = row['amount_usd'] / row['token_bought_amount']
                else:
                    trade_info['price_usd'] = 0
            elif row['token_sold_symbol'] == 'ACT':
                trade_info['type'] = 'sell'
                trade_info['act_amount'] = row['token_sold_amount']
                if row['token_sold_amount'] > 0:
                    trade_info['price_usd'] = row['amount_usd'] / row['token_sold_amount']
                else:
                    trade_info['price_usd'] = 0
            else:
                # Neither bought nor sold ACT? Skip or mark unknown.
                # The file is ACT-24-11-10, so presumably ACT related.
                continue
                
            if tx_id not in trades_map:
                trades_map[tx_id] = []
            trades_map[tx_id].append(trade_info)
            count += 1
            
        print(f"Loaded {count} trades across {len(trades_map)} transactions.")
        return trades_map
    except Exception as e:
        print(f"Error loading ACT trades: {e}")
        return {}

def process_transfers(user_addresses, trades_map):
    print(f"Processing transfers from {TRANSFERS_CSV_PATH}...")
    
    chunk_size = 100000
    user_sequences = {} # key: user_address, value: list of events
    
    # Pre-initialize dict for known users to save checks? 
    # Or just add as we go. Users set is large (65k), dict is fine.
    # But we only want to store sequences for users in our set.
    
    processed_rows = 0
    matched_trades = 0
    
    # Iterate over chunks
    for chunk in pd.read_csv(TRANSFERS_CSV_PATH, chunksize=chunk_size):
        # Filter: keep rows where from_owner OR to_owner is in user_addresses
        # This is the most expensive part if done row by row.
        # Vectorized check:
        mask_from = chunk['from_owner'].isin(user_addresses)
        mask_to = chunk['to_owner'].isin(user_addresses)
        relevant_rows = chunk[mask_from | mask_to]
        
        for _, row in relevant_rows.iterrows():
            tx_id = row['tx_id']
            amount = row['amount_display']
            block_time = row['block_time']
            from_owner = row['from_owner']
            to_owner = row['to_owner']
            
            # Identify the user(s)
            users_in_tx = []
            if from_owner in user_addresses:
                users_in_tx.append({'addr': from_owner, 'role': 'sender', 'counterparty': to_owner})
            if to_owner in user_addresses:
                users_in_tx.append({'addr': to_owner, 'role': 'receiver', 'counterparty': from_owner})
                
            for user in users_in_tx:
                addr = user['addr']
                if addr not in user_sequences:
                    user_sequences[addr] = []
                
                event_type = 'transfer_out' if user['role'] == 'sender' else 'transfer_in'
                
                event = {
                    'time': block_time,
                    'type': event_type,
                    'amount': amount,
                    'counterparty': user['counterparty'],
                    'tx_id': tx_id
                }
                
                # Try to match with trade data
                if tx_id in trades_map:
                    trades = trades_map[tx_id]
                    # Find best match
                    best_match = None
                    
                    for trade in trades:
                        # Logic 1: Trader ID match with direction check
                        if trade['trader_id'] == addr:
                            # Verify direction matches
                            # Buy means I receive ACT (transfer_in)
                            if trade['type'] == 'buy' and event_type == 'transfer_in':
                                best_match = trade
                                break
                            # Sell means I send ACT (transfer_out)
                            elif trade['type'] == 'sell' and event_type == 'transfer_out':
                                best_match = trade
                                break
                        
                        # Logic 2: Amount match (fallback if trader_id doesn't match or direction mismatch)
                        # If receiving ACT (transfer_in) -> match with BUY
                        if event_type == 'transfer_in' and trade['type'] == 'buy':
                            if abs(trade['act_amount'] - amount) < (amount * 0.01 + 1e-6):
                                best_match = trade
                                break
                        # If sending ACT (transfer_out) -> match with SELL
                        elif event_type == 'transfer_out' and trade['type'] == 'sell':
                            if abs(trade['act_amount'] - amount) < (amount * 0.01 + 1e-6):
                                best_match = trade
                                break
                    
                    if best_match:
                        event['trade_info'] = {
                            'action': best_match['type'], # buy/sell
                            'price_usd': best_match.get('price_usd', 0),
                            'total_usd': best_match['amount_usd'],
                            'dex': best_match['project'],
                            'pair': best_match['token_pair']
                        }
                        matched_trades += 1
                
                user_sequences[addr].append(event)
        
        processed_rows += len(chunk)
        if processed_rows % 500000 == 0:
            print(f"Processed {processed_rows} rows... (Matched {matched_trades} trades so far)")

    print(f"Finished processing. Total matched trades: {matched_trades}")
    return user_sequences

def main():
    if not os.path.exists(TRANSFERS_CSV_PATH):
        print(f"Error: Transfers file not found at {TRANSFERS_CSV_PATH}")
        return
        
    user_addresses = load_user_addresses()
    if not user_addresses:
        return

    trades_map = load_act_trades()
    
    user_sequences = process_transfers(user_addresses, trades_map)
    
    print("Sorting sequences...")
    final_data = {}
    for addr, events in user_sequences.items():
        if not events:
            continue
        # Sort by time
        events.sort(key=lambda x: x['time'])
        final_data[addr] = events
        
    print(f"Saving sequences for {len(final_data)} users to {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(final_data, f, indent=2)
    print("Done.")

if __name__ == "__main__":
    main()
