import pandas as pd
import json
import os
import logging
import numpy as np
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
PROCESSED_DIR = os.path.join(PUBLIC_DIR, "processed")

# Input Paths
TRANSFER_CSV_PATH = os.path.join(PUBLIC_DIR, "ACT_transfer_before_2024-11-10.csv")
TRADING_CSV_PATH = os.path.join(PUBLIC_DIR, "ACT-24-11-10.csv") # Correct filename
OWNER_LABELS_PATH = os.path.join(PROCESSED_DIR, "transfers", "owner_labels.json")

# Output Paths
SORTED_TRANSFERS_PATH = os.path.join(PUBLIC_DIR, "data", "sorted_transfers.csv")
SORTED_TRADES_PATH = os.path.join(PUBLIC_DIR, "data", "sorted_trades.csv")
SIMPLIFIED_LABELS_PATH = os.path.join(PUBLIC_DIR, "data", "simplified_owner_labels.json")
USER_RELATIONS_PATH = os.path.join(PUBLIC_DIR, "data", "user_relations.json")
USER_ACTIONS_PATH = os.path.join(PUBLIC_DIR, "data", "user_actions.json")
USER_BALANCE_1MIN_PATH = os.path.join(PUBLIC_DIR, "data", "user_balance_1min.json")
USER_BALANCE_1H_PATH = os.path.join(PUBLIC_DIR, "data", "user_balance_1h.json")
USER_BALANCE_1D_PATH = os.path.join(PUBLIC_DIR, "data", "user_balance_1d.json")
USER_EARNINGS_1MIN_PATH = os.path.join(PUBLIC_DIR, "data", "user_earnings_1min.json")
USER_EARNINGS_1H_PATH = os.path.join(PUBLIC_DIR, "data", "user_earnings_1h.json")
USER_EARNINGS_1D_PATH = os.path.join(PUBLIC_DIR, "data", "user_earnings_1d.json")

USER_BEHAVIOR_SEQUENCES_PATH = os.path.join(PUBLIC_DIR, "data", "user_behavior_sequences.json")

def load_and_process_transfers():
    """Loads, sorts, and saves transfer data."""
    logger.info(f"Loading transfer data from {TRANSFER_CSV_PATH}...")
    if not os.path.exists(TRANSFER_CSV_PATH):
        logger.error(f"Transfer CSV not found at {TRANSFER_CSV_PATH}")
        return None

    try:
        # Load Labels first
        labels = load_owner_labels()
        if labels is None:
            # Try loading from simplified if processing labels is disabled
            if os.path.exists(SIMPLIFIED_LABELS_PATH):
                with open(SIMPLIFIED_LABELS_PATH, 'r') as f:
                    labels = json.load(f)
            else:
                logger.warning("Owner labels not available. proceeding without labels.")
                labels = {}

        df = pd.read_csv(TRANSFER_CSV_PATH)
        logger.info(f"Loaded {len(df)} transfer records.")

        if 'block_time' in df.columns:
            logger.info("Sorting transfers by block_time...")
            # Convert to datetime for accurate sorting
            df['block_time_dt'] = pd.to_datetime(df['block_time'], errors='coerce')
            
            # Sort
            df = df.sort_values(by='block_time_dt')
            
            # Keep only required columns
            # timestamp, from owner, from owner label, to owner, to owner label, amount
            # block_time is the timestamp
            # amount_display is usually the readable amount
            
            # Add labels
            logger.info("Adding owner labels...")
            df['from_owner_label'] = df['from_owner'].map(labels).fillna('')
            df['to_owner_label'] = df['to_owner'].map(labels).fillna('')
            
            # Select columns
            cols_to_keep = ['block_time', 'from_owner', 'from_owner_label', 'to_owner', 'to_owner_label', 'amount_display', 'tx_id']
            
            # Check if columns exist
            existing_cols = [c for c in cols_to_keep if c in df.columns]
            if len(existing_cols) < len(cols_to_keep):
                missing = set(cols_to_keep) - set(existing_cols)
                logger.warning(f"Missing columns: {missing}. Available: {df.columns.tolist()}")
            
            df_final = df[existing_cols]
            
            # Rename for clarity if needed, or keep original names
            # User asked for: timestamp, from owner, from owner label, to owner, to owner label, amount
            # block_time -> timestamp (optional, but keeping original name is often safer unless requested rename)
            # amount_display -> amount
            
            df_final = df_final.rename(columns={
                'block_time': 'timestamp',
                'amount_display': 'amount'
            })
            
            # Save sorted data
            logger.info(f"Saving sorted transfers to {SORTED_TRANSFERS_PATH}...")
            df_final.to_csv(SORTED_TRANSFERS_PATH, index=False)
            logger.info("Transfer data processing complete.")
            return df_final
        else:
            logger.warning("'block_time' column not found in transfer data. Skipping sort.")
            return df
            
    except Exception as e:
        logger.error(f"Error processing transfer data: {e}")
        return None

def load_and_process_trades():
    """Loads, sorts, and saves trading data."""
    logger.info(f"Loading trading data from {TRADING_CSV_PATH}...")
    if not os.path.exists(TRADING_CSV_PATH):
        logger.error(f"Trading CSV not found at {TRADING_CSV_PATH}")
        return None

    try:
        # Load with optimized types if possible, but standard read is fine for preprocessing
        df = pd.read_csv(TRADING_CSV_PATH, dtype=str) # Read as string initially to avoid type issues
        logger.info(f"Loaded {len(df)} trading records.")
        
        # Convert numeric columns
        numeric_cols = ["token_bought_amount", "token_sold_amount", "amount_usd"]
        for c in numeric_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

        # Simplify Trade Data
        TARGET_TOKEN = 'ACT'
        
        # Determine Action Type
        # If bought symbol is ACT -> buy
        # If sold symbol is ACT -> sell
        # Else -> unknown (or ignore)
        
        # Vectorized logic
        conditions = [
            df['token_bought_symbol'] == TARGET_TOKEN,
            df['token_sold_symbol'] == TARGET_TOKEN
        ]
        choices = ['buy', 'sell']
        df['action_type'] = np.select(conditions, choices, default='unknown')
        
        # Filter out unknown if any
        # df = df[df['action_type'] != 'unknown'] # Optional: keep all or filter? Assuming file is ACT trades.
        
        # Determine Amount
        df['amount'] = np.where(df['action_type'] == 'buy', df['token_bought_amount'], 
                                np.where(df['action_type'] == 'sell', df['token_sold_amount'], 0))
        
        # Determine Price
        # price = amount_usd / amount
        # Handle division by zero
        df['price'] = df['amount_usd'] / df['amount'].replace(0, np.nan)
        df['price'] = df['price'].fillna(0)
        
        # Determine Counterparty
        # Using 'project' column as counterparty (e.g. raydium, whirlpool)
        df['counterparty'] = df['project']
        
        # Determine Counterparty Address
        df['counterparty_address'] = df['project_main_id']
        
        # Rename columns
        df = df.rename(columns={
            'block_time': 'timestamp',
            'trader_id': 'trader'
        })
        
        # Select required columns
        cols_to_keep = ['timestamp', 'trader', 'amount_usd','amount', 'price', 'action_type', 'counterparty', 'tx_id', 'counterparty_address']
        
        # Check if columns exist (trader_id might be missing in some sources?)
        existing_cols = [c for c in cols_to_keep if c in df.columns]
        df_final = df[existing_cols]

        if 'timestamp' in df_final.columns:
            logger.info("Sorting trades by timestamp...")
            df_final['timestamp_dt'] = pd.to_datetime(df_final['timestamp'], errors='coerce')
            df_final = df_final.sort_values(by='timestamp_dt')
            # Drop temp column
            df_final = df_final.drop(columns=['timestamp_dt'])
            
            logger.info(f"Saving sorted trades to {SORTED_TRADES_PATH}...")
            # Ensure directory exists
            os.makedirs(os.path.dirname(SORTED_TRADES_PATH), exist_ok=True)
            df_final.to_csv(SORTED_TRADES_PATH, index=False)
            logger.info("Trading data processing complete.")
            return df_final
        else:
            logger.warning("'timestamp' column not found in trading data. Skipping sort.")
            return df_final

    except Exception as e:
        logger.error(f"Error processing trading data: {e}")
        return None

def load_owner_labels():
    """Loads, simplifies, and saves owner labels."""
    logger.info(f"Loading owner labels from {OWNER_LABELS_PATH}...")
    if not os.path.exists(OWNER_LABELS_PATH):
        logger.warning(f"Owner labels not found at {OWNER_LABELS_PATH}")
        return None
    
    try:
        with open(OWNER_LABELS_PATH, 'r') as f:
            labels_list = json.load(f)
            logger.info(f"Loaded {len(labels_list)} owner label records.")
            
            # Simplify to {owner_address: label}
            simplified_labels = {}
            for item in labels_list:
                if "owner_address" in item and "label" in item:
                    simplified_labels[item["owner_address"]] = item["label"]
            
            logger.info(f"Simplified into {len(simplified_labels)} label mappings.")
            
            # Save simplified labels
            logger.info(f"Saving simplified labels to {SIMPLIFIED_LABELS_PATH}...")
            with open(SIMPLIFIED_LABELS_PATH, 'w') as f_out:
                json.dump(simplified_labels, f_out, indent=2)
            
            return simplified_labels
    except Exception as e:
        logger.error(f"Error processing owner labels: {e}")
        return None

def generate_user_relations():
    """
    Generates a file containing all user senders and recipients for non-contract/exchange users.
    Structure:
    {
      "senders": { user_address: [{address: sender_address, timestamp: ts, amount: val}, ...], ... },
      "recipients": { user_address: [{address: recipient_address, timestamp: ts, amount: val}, ...], ... }
    }
    """
    logger.info("Generating user relations...")
    
    # Ensure sorted transfers exist
    if not os.path.exists(SORTED_TRANSFERS_PATH):
        logger.warning(f"Sorted transfers not found at {SORTED_TRANSFERS_PATH}. Please run transfer processing first.")
        return

    try:
        # Load sorted transfers
        # Columns: timestamp, from_owner, from_owner_label, to_owner, to_owner_label, amount
        # Note: pandas might load 'timestamp' as object, convert if needed but string is fine for JSON
        df = pd.read_csv(SORTED_TRANSFERS_PATH)
        logger.info(f"Loaded {len(df)} sorted transfer records for relation generation.")
        
        # Helper to check if user is valid (non-contract, non-exchange)
        def is_valid_user(label):
            if pd.isna(label) or label == "":
                return True
            label_lower = str(label).lower()
            if "contract" in label_lower or "exchange" in label_lower:
                return False
            return True

        senders = {}
        recipients = {}
        
        # Count for progress logging
        count = 0
        total = len(df)
        
        # Iterate through rows
        # Using itertuples for better performance than iterrows
        for row in df.itertuples(index=False):
            # Row(timestamp, from_owner, from_owner_label, to_owner, to_owner_label, amount)
            # Adjust field access based on actual column names in CSV
            # We renamed them in load_and_process_transfers: 
            # 'timestamp', 'from_owner', 'from_owner_label', 'to_owner', 'to_owner_label', 'amount'
            
            ts = row.timestamp
            u_from = row.from_owner
            l_from = row.from_owner_label
            u_to = row.to_owner
            l_to = row.to_owner_label
            amt = row.amount
            
            # Check if From is valid user
            valid_from = is_valid_user(l_from)
            # Check if To is valid user
            valid_to = is_valid_user(l_to)
            
            # Record for From user (Sender)
            if valid_from and valid_to:
                if u_from not in recipients:
                    recipients[u_from] = []
                recipients[u_from].append({
                    "address": u_to,
                    "timestamp": ts,
                    "amount": amt
                })
            
            # Record for To user (Recipient)
                if u_to not in senders:
                    senders[u_to] = []
                senders[u_to].append({
                    "address": u_from,
                    "timestamp": ts,
                    "amount": amt
                })
            
            count += 1
            if count % 100000 == 0:
                logger.info(f"Processed {count}/{total} records...")

        # Construct final structure
        result = {
            "senders": senders,
            "recipients": recipients
        }
        
        # Save to JSON
        logger.info(f"Saving user relations to {USER_RELATIONS_PATH}...")
        with open(USER_RELATIONS_PATH, 'w') as f:
            json.dump(result, f, indent=2)
            
        logger.info(f"User relations generation complete. Found {len(senders)} users with senders and {len(recipients)} users with recipients.")
        
    except Exception as e:
        logger.error(f"Error generating user relations: {e}")

def generate_user_actions():
    """
    Generates a file containing user action sequences from trade data.
    Structure:
    {
      user_address: [
        {timestamp: ts, action_type: buy/sell, amount: val, price: val},
        ...
      ],
      ...
    }
    """
    logger.info("Generating user actions...")
    
    if not os.path.exists(SORTED_TRADES_PATH):
        logger.warning(f"Sorted trades not found at {SORTED_TRADES_PATH}. Please run trade processing first.")
        return

    try:
        # Load sorted trades
        # Columns: timestamp, trader, amount, price, action_type, counterparty, tx_id, counterparty_address
        df = pd.read_csv(SORTED_TRADES_PATH)
        logger.info(f"Loaded {len(df)} sorted trade records for action generation.")
        
        user_actions = {}
        
        count = 0
        total = len(df)
        
        # Iterate through rows
        for row in df.itertuples(index=False):
            # timestamp, trader, amount, price, action_type, ...
            ts = row.timestamp
            user = row.trader
            amt = row.amount
            price = row.price
            action = row.action_type
            
            # Skip if user is missing
            if pd.isna(user) or user == "":
                continue
                
            if user not in user_actions:
                user_actions[user] = []
            
            user_actions[user].append({
                "timestamp": ts,
                "action_type": action,
                "amount": amt,
                "price": price
            })
            
            count += 1
            if count % 100000 == 0:
                logger.info(f"Processed {count}/{total} trade records...")
        
        # Save to JSON
        logger.info(f"Saving user actions to {USER_ACTIONS_PATH}...")
        with open(USER_ACTIONS_PATH, 'w') as f:
            json.dump(user_actions, f, indent=2)
            
        logger.info(f"User actions generation complete. Found {len(user_actions)} users with actions.")
        
    except Exception as e:
        logger.error(f"Error generating user actions: {e}")

def generate_user_balances():
    """
    Generates files containing user balance sequences from transfer data for non-contract/exchange users.
    Time slices: 1Min, 1H, 1D
    """
    logger.info("Generating user balances...")
    
    if not os.path.exists(SORTED_TRANSFERS_PATH):
        logger.warning(f"Sorted transfers not found at {SORTED_TRANSFERS_PATH}. Please run transfer processing first.")
        return

    try:
        # Load sorted transfers
        df = pd.read_csv(SORTED_TRANSFERS_PATH)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        logger.info(f"Loaded {len(df)} sorted transfer records for balance generation.")
        
        # Helper to check if user is valid
        def is_valid_user(label):
            if pd.isna(label) or label == "":
                return True
            label_lower = str(label).lower()
            if "contract" in label_lower or "exchange" in label_lower:
                return False
            return True

        # Identify all unique users and filter valid ones
        all_users = set(df['from_owner'].unique()) | set(df['to_owner'].unique())
        
        # Load labels map for validation
        labels_map = {}
        if os.path.exists(SIMPLIFIED_LABELS_PATH):
             with open(SIMPLIFIED_LABELS_PATH, 'r') as f:
                labels_map = json.load(f)

        valid_users = set()
        for u in all_users:
            label = labels_map.get(u, "")
            if is_valid_user(label):
                valid_users.add(u)
        
        logger.info(f"Found {len(valid_users)} valid users out of {len(all_users)} total users.")

        # Process balances
        # We need to calculate cumulative balance for each user over time.
        # Since we want sampled time series (1Min, 1H, 1D), we can resample.
        
        # Create a long-format dataframe of balance changes
        # user | timestamp | change
        
        # Changes from 'from_owner' (negative)
        df_from = df[df['from_owner'].isin(valid_users)][['timestamp', 'from_owner', 'amount']].copy()
        df_from['amount'] = -df_from['amount']
        df_from = df_from.rename(columns={'from_owner': 'user'})
        
        # Changes from 'to_owner' (positive)
        df_to = df[df['to_owner'].isin(valid_users)][['timestamp', 'to_owner', 'amount']].copy()
        df_to = df_to.rename(columns={'to_owner': 'user'})
        
        # Combine
        df_changes = pd.concat([df_from, df_to])
        
        # Sort by timestamp
        df_changes = df_changes.sort_values('timestamp')
        
        # Group by user and timestamp, summing changes at same timestamp
        # But for resampling we need to handle it carefully.
        
        # Function to process and save for a specific frequency
        def process_and_save(freq, output_path):
            logger.info(f"Processing balances for frequency: {freq}...")
            
            result = {}
            
            # Process each user
            # To optimize, we can iterate over users. 
            # But iterating 60k users might be slow if we do full pandas resample for each.
            # Let's try iterating groups.
            
            grouped = df_changes.groupby('user')
            
            count = 0
            total_users = len(grouped)
            
            for user, group in grouped:
                # Resample
                # Set index to timestamp
                g = group.set_index('timestamp')
                
                # Resample and sum changes in each bin
                resampled = g['amount'].resample(freq).sum()
                
                # Calculate cumulative sum to get balance at end of each bin
                # Note: This gives balance *change* cumulative. 
                # Assuming initial balance is 0 before first transfer.
                balance = resampled.cumsum()
                
                # Filter out leading zeros if desired, or keep all from first activity
                # We usually want the balance history from the first activity onwards.
                # However, resample might introduce earlier dates if range is fixed? 
                # No, resample on a user's data starts from their min timestamp.
                
                # Convert to list of dicts
                # {timestamp: ts, balance: val}
                
                # Optimization: only store non-zero balances or changes? 
                # User asked for "balance sequence". 
                # If we store every minute, it will be huge.
                # Maybe only store when it changes? But user asked for time slices.
                # If "time slice 1Min", it implies a data point every minute?
                # Or maybe just the value at that time if it existed?
                # Usually "1Min time slice" means we want the state at 1Min intervals.
                # But storing 60k users * minutes is too big.
                # Let's interpret as: Resample to freq, and store the resulting series.
                # To save space, we can convert to list of [ts, val] or {ts, val}.
                
                # Let's clean up: remove NaNs (which happen if no activity in bin? No, sum() gives 0)
                # cumsum propagates values.
                
                # Wait, resample().sum() gives sum of changes in that minute.
                # If no changes, sum is 0.
                # Then cumsum() adds 0, so balance stays same.
                
                # If we simply output the resampled series, it includes all intervals.
                # For 1Min, if user is active for a year, that's 500k points. Too big for JSON?
                # Maybe user just wants the points where balance changed, but "snapped" to nearest grid?
                # "生成三个文件分别时间切片为1Min，1H，1D" usually implies aggregation.
                
                # Let's stick to the generated series but maybe sparse format?
                # For now, let's implement standard resample. If file is too big, we might need sparse.
                # Actually, for 1Min, let's just do it. If it explodes, we'll see.
                # But wait, 1Min for 60k users is definitely too big for a single JSON file.
                # 60k users * 1000 points = 60M objects. JSON will be GBs.
                
                # Alternative interpretation: 
                # User wants a sequence of balances, but only recorded at 1Min resolution?
                # i.e. if multiple transfers in a minute, take the last one?
                # Or just aggregated changes?
                
                # Let's try to be smart:
                # If we just output the points where balance changed (and the timestamp), 
                # the frontend can interpolate.
                # But user asked for specific time slices.
                # Maybe they want global snapshots?
                # "每个users的balance序列" -> per user.
                
                # Let's assume sparse representation is acceptable:
                # Only include points where balance changed, but rounded/binned to the frequency?
                # OR, strictly follow frequency.
                
                # Given the "1Min, 1H, 1D" requirement, it sounds like they want the data aggregated/smoothed.
                # I will generate the series. For 1Min, if it's too large, I might need to optimize.
                # Optimization: only store if value changed from previous step?
                # Yes, run-length encoding logic essentially.
                
                # Let's do: resample -> cumsum -> filter consecutive duplicates.
                
                balance_vals = balance.values
                timestamps = balance.index
                
                # Identify changes
                # Prepend a value different from first to keep first
                if len(balance_vals) > 0:
                    # changes = balance_vals != np.roll(balance_vals, 1)
                    # changes[0] = True # Always keep first
                    # But we also need to keep the last one? Not necessarily if it didn't change.
                    
                    # Actually, if we resample to 1H, we get one point per hour.
                    # If balance doesn't change for 10 hours, do we store 10 points?
                    # Storing 10 points is redundant.
                    # Let's store only when balance changes.
                    
                    mask = np.concatenate(([True], balance_vals[1:] != balance_vals[:-1]))
                    selected_balance = balance_vals[mask]
                    selected_ts = timestamps[mask]
                    
                    user_seq = []
                    for t, b in zip(selected_ts, selected_balance):
                         user_seq.append({
                             "timestamp": t.strftime('%Y-%m-%d %H:%M:%S'),
                             "balance": b
                         })
                    
                    result[user] = user_seq
                
                count += 1
                if count % 10000 == 0:
                    logger.info(f"Processed {count}/{total_users} users for {freq}...")

            logger.info(f"Saving balances for {freq} to {output_path}...")
            with open(output_path, 'w') as f:
                json.dump(result, f) # Minify to save space
            logger.info(f"Saved {output_path}. Size: {os.path.getsize(output_path)/1024/1024:.2f} MB")

        # Run for 1Min, 1H, 1D
        process_and_save('1D', USER_BALANCE_1D_PATH)
        process_and_save('1h', USER_BALANCE_1H_PATH)
        # process_and_save('1min', USER_BALANCE_1MIN_PATH) 
        # 1Min might still be huge even with sparse encoding if many trades.
        # But let's try.
        process_and_save('1min', USER_BALANCE_1MIN_PATH)

    except Exception as e:
        logger.error(f"Error generating user balances: {e}")

def generate_user_earnings():
    """
    Generates files containing user earning sequences from trade data.
    Earning Logic:
      - Maintain Weighted Average Buy Price (WABP)
      - On Buy: Update WABP
      - On Sell: Earning = (Sell Price - WABP) * Sell Amount
      - Result is cumulative earning over time.
    Time slices: 1Min, 1H, 1D
    """
    logger.info("Generating user earnings...")
    
    if not os.path.exists(SORTED_TRADES_PATH):
        logger.warning(f"Sorted trades not found at {SORTED_TRADES_PATH}. Please run trade processing first.")
        return

    try:
        # Load sorted trades
        # Columns: timestamp, trader, amount, price, action_type, counterparty, tx_id, counterparty_address
        df = pd.read_csv(SORTED_TRADES_PATH)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        logger.info(f"Loaded {len(df)} sorted trade records for earning generation.")
        
        # We need to process trades sequentially per user to calculate earnings
        # Group by user
        grouped = df.groupby('trader')
        
        # Store earning events: {user: [(ts, earning_change), ...]}
        # Or better, collect all changes into a list of dicts to create a dataframe later
        earning_changes = []
        
        count = 0
        total_users = len(grouped)
        
        for user, group in grouped:
            # Sort by timestamp (should be already sorted but ensuring)
            group = group.sort_values('timestamp')
            
            current_balance = 0.0
            avg_buy_price = 0.0
            
            user_changes = []
            
            for row in group.itertuples(index=False):
                # timestamp, trader, amount, price, action_type
                ts = row.timestamp
                amt = float(row.amount)
                price = float(row.price)
                action = row.action_type
                
                earning_change = 0.0
                
                if action == 'buy':
                    # Update WABP
                    # new_avg = (current_balance * current_avg + amt * price) / (current_balance + amt)
                    if current_balance < 0:
                        # Covering short position?
                        # If balance is negative, buying reduces the negative balance.
                        # For simplicity, if balance < 0, we just treat the positive portion as new inventory?
                        # Or reset?
                        # Let's assume standard logic: 
                        # If balance < 0, buying just covers. Cost basis of short?
                        # Let's ignore short complexity and assume WABP only tracks long positions.
                        # If balance <= 0, new WABP = price.
                        avg_buy_price = price
                        current_balance += amt
                    else:
                        total_cost = (current_balance * avg_buy_price) + (amt * price)
                        current_balance += amt
                        if current_balance > 0:
                            avg_buy_price = total_cost / current_balance
                        else:
                            avg_buy_price = 0 # Should not happen if adding positive amount
                            
                elif action == 'sell':
                    # Calculate Earning
                    # earning = (price - avg_buy_price) * amt
                    earning_change = (price - avg_buy_price) * amt
                    
                    # Update Balance
                    current_balance -= amt
                    
                    # WABP stays same on sell (FIFO/LIFO might differ, but Average Cost stays same)
                    
                    # Record earning change
                    # We only record if there is an earning event (sell)
                    # But actually, we want the cumulative earning curve.
                    # So we record the change at this timestamp.
                    if earning_change != 0:
                        user_changes.append({
                            'user': user,
                            'timestamp': ts,
                            'earning_change': earning_change
                        })
            
            earning_changes.extend(user_changes)
            
            count += 1
            if count % 10000 == 0:
                logger.info(f"Processed earnings for {count}/{total_users} users...")
                
        logger.info(f"Calculated earnings for {len(earning_changes)} trade events.")
        
        # Create DataFrame from changes
        if not earning_changes:
            logger.warning("No earning events found.")
            return

        df_changes = pd.DataFrame(earning_changes)
        df_changes['timestamp'] = pd.to_datetime(df_changes['timestamp'])
        
        # Function to process and save for a specific frequency
        def process_and_save(freq, output_path):
            logger.info(f"Processing earnings for frequency: {freq}...")
            
            result = {}
            
            # Group by user
            grouped_changes = df_changes.groupby('user')
            
            count = 0
            total = len(grouped_changes)
            
            for user, group in grouped_changes:
                # Resample
                g = group.set_index('timestamp')
                
                # Resample sum of changes
                resampled = g['earning_change'].resample(freq).sum()
                
                # Cumulative sum to get total realized earning
                cumulative = resampled.cumsum()
                
                # Convert to sparse format (only changes)
                vals = cumulative.values
                timestamps = cumulative.index
                
                if len(vals) > 0:
                    # Filter consecutive duplicates
                    # Always keep first? resample starts from first event.
                    # Actually, if resample fills with 0 (default for sum), 
                    # cumsum propagates previous value.
                    # So we will have runs of identical values.
                    
                    mask = np.concatenate(([True], vals[1:] != vals[:-1]))
                    selected_vals = vals[mask]
                    selected_ts = timestamps[mask]
                    
                    user_seq = []
                    for t, v in zip(selected_ts, selected_vals):
                         user_seq.append({
                             "timestamp": t.strftime('%Y-%m-%d %H:%M:%S'),
                             "earning": v
                         })
                    
                    result[user] = user_seq
                
                count += 1
                if count % 10000 == 0:
                    logger.info(f"Processed {count}/{total} users for {freq}...")

            logger.info(f"Saving earnings for {freq} to {output_path}...")
            with open(output_path, 'w') as f:
                json.dump(result, f) 
            logger.info(f"Saved {output_path}. Size: {os.path.getsize(output_path)/1024/1024:.2f} MB")

        # Run for 1Min, 1H, 1D
        process_and_save('1D', USER_EARNINGS_1D_PATH)
        process_and_save('1h', USER_EARNINGS_1H_PATH)
        process_and_save('1min', USER_EARNINGS_1MIN_PATH)

    except Exception as e:
        logger.error(f"Error generating user earnings: {e}")

def generate_user_behavior_sequences():
    """
    Generates a file containing user behavior sequences from transfer and trade data.
    Only includes non-contract and non-exchange users.
    Structure:
    {
      user_address: [
        {
          timestamp: ts,
          type: "transfer_in" | "transfer_out",
          amount: val,
          tx_id: val,
          counterparty: val,
          isTrade: true/false,
          trade_info: {
            action: "buy" | "sell",
            amount: val,
            price_usd: val,
            total_usd: val
          } (only if isTrade is true)
        },
        ...
      ]
    }
    """
    logger.info("Generating user behavior sequences...")
    
    if not os.path.exists(SORTED_TRANSFERS_PATH):
        logger.warning(f"Sorted transfers not found at {SORTED_TRANSFERS_PATH}.")
        return
    if not os.path.exists(SORTED_TRADES_PATH):
        logger.warning(f"Sorted trades not found at {SORTED_TRADES_PATH}.")
        return
        
    try:
        # Load simplified labels to filter out exchanges and contracts
        labels = {}
        if os.path.exists(SIMPLIFIED_LABELS_PATH):
            with open(SIMPLIFIED_LABELS_PATH, 'r') as f:
                labels = json.load(f)
        
        def is_valid_user(address):
            if pd.isna(address) or address == "":
                return False
            label = labels.get(address, "").lower()
            if "exchange" in label or "contract" in label or "pool" in label or "router" in label or "treasury" in label:
                return False
            return True
            
        # 1. Load Trades and index by tx_id for fast lookup
        logger.info("Loading trades for behavior sequences...")
        df_trades = pd.read_csv(SORTED_TRADES_PATH)
        df_trades = df_trades.replace({np.nan: None})
        # Assuming tx_id is unique enough or we group by tx_id
        trade_dict = {}
        for row in df_trades.itertuples(index=False):
            # cols: timestamp, trader, amount, price, action_type, counterparty, tx_id, counterparty_address
            if pd.isna(row.tx_id) or row.tx_id == "" or row.tx_id is None:
                continue
            
            # Store trade info by tx_id. If a tx has multiple trades, we might need a list, 
            # but usually one main action per tx for a user.
            trade_dict[row.tx_id] = {
                "action": row.action_type,
                "amount": row.amount,
                "price_usd": row.price,
                "total_usd": getattr(row, 'amount_usd', row.amount * row.price) if getattr(row, 'amount_usd', None) is not None else (row.amount * row.price if row.amount is not None and row.price is not None else None)
            }
            
        logger.info(f"Indexed {len(trade_dict)} unique trade transactions.")

        # 2. Load Transfers and build sequences
        logger.info("Loading transfers for behavior sequences...")
        df_transfers = pd.read_csv(SORTED_TRANSFERS_PATH)
        df_transfers = df_transfers.replace({np.nan: None})
        
        user_sequences = {}
        count = 0
        total = len(df_transfers)
        
        for row in df_transfers.itertuples(index=False):
            # cols: timestamp, from_owner, from_owner_label, to_owner, to_owner_label, amount, tx_id
            ts = row.timestamp
            u_from = row.from_owner
            u_to = row.to_owner
            amt = row.amount
            
            # Use getattr for tx_id as it might be missing if SORTED_TRANSFERS wasn't regenerated
            tx_id = getattr(row, 'tx_id', '') 
            if tx_id is None:
                tx_id = ''
            if u_from is None:
                u_from = ''
            if u_to is None:
                u_to = ''
            
            # Check if this tx is a trade
            trade_info = trade_dict.get(tx_id)
            is_trade = trade_info is not None

            # Process 'from_owner' (transfer_out)
            if is_valid_user(u_from):
                if u_from not in user_sequences:
                    user_sequences[u_from] = []
                
                event = {
                    "timestamp": ts,
                    "type": "transfer_out",
                    "amount": amt,
                    "tx_id": tx_id,
                    "counterparty": u_to,
                    "isTrade": is_trade
                }
                if is_trade:
                    event["trade_info"] = trade_info
                    
                user_sequences[u_from].append(event)
                
            # Process 'to_owner' (transfer_in)
            if is_valid_user(u_to):
                if u_to not in user_sequences:
                    user_sequences[u_to] = []
                
                event = {
                    "timestamp": ts,
                    "type": "transfer_in",
                    "amount": amt,
                    "tx_id": tx_id,
                    "counterparty": u_from,
                    "isTrade": is_trade
                }
                if is_trade:
                    event["trade_info"] = trade_info
                    
                user_sequences[u_to].append(event)

            count += 1
            if count % 100000 == 0:
                logger.info(f"Processed {count}/{total} transfers for behavior sequences...")

        # Save to JSON
        logger.info(f"Saving user behavior sequences to {USER_BEHAVIOR_SEQUENCES_PATH}...")
        with open(USER_BEHAVIOR_SEQUENCES_PATH, 'w') as f:
            json.dump(user_sequences, f, indent=2)
            
        logger.info(f"User behavior sequences generation complete. Found {len(user_sequences)} valid users.")
        
    except Exception as e:
        logger.error(f"Error generating user behavior sequences: {e}")

def main():
    logger.info("Starting data preprocessing...")
    
    # Load Labels
    logger.info("Simplifying owner labels...")
    process_owner_label = False # Enable label processing to ensure simplified labels exist
    if process_owner_label:
        load_owner_labels()
    
    # Process Transfers
    process_transfers = False
    if process_transfers:
        load_and_process_transfers()
        
    # Process Trades
    process_trades = False # Enabled for trade data processing
    if process_trades:
        load_and_process_trades()
    
    # Generate User Relations
    generate_relations = False
    if generate_relations:
        generate_user_relations()
        
    # Generate User Actions
    generate_actions = False
    if generate_actions:
        generate_user_actions()
        
    # Generate User Balances
    generate_balances = False
    if generate_balances:
        generate_user_balances()
        
    # Generate User Earnings
    generate_earnings = False
    if generate_earnings:
        generate_user_earnings()
        
    # Generate User Behavior Sequences
    generate_behavior_sequences = True
    if generate_behavior_sequences:
        generate_user_behavior_sequences()
    
    logger.info("Data preprocessing finished.")

if __name__ == "__main__":
    main()
