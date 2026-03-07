
import bisect
import pandas as pd
import os
import json
import networkx as nx
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

router = APIRouter(
    prefix="/api/manipulation",
    tags=["manipulation"],
    responses={404: {"description": "Not found"}},
)

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "public", "ACT-24-11-10.csv")
TRANSFER_FILE = os.path.join(BASE_DIR, "public", "ACT_transfer_before_2024-11-10.csv")
RESULTS_DIR = os.path.join(BASE_DIR, "public", "wash_trading_results")

# Ensure results directory exists
if not os.path.exists(RESULTS_DIR):
    os.makedirs(RESULTS_DIR)

class ManipulationRequest(BaseModel):
    threshold: float = 100.0  # Default difference threshold for self-trading
    limit_traders: Optional[List[str]] = None  # Optional list of trader IDs to check

class SuspiciousTrader(BaseModel):
    trader_id: str
    total_bought: float
    total_sold: float
    diff: float
    transaction_count: int

class ManipulationResponse(BaseModel):
    suspicious_traders: List[SuspiciousTrader]
    count: int
    saved_file: Optional[str] = None

class WashTradingRequest(BaseModel):
    min_scc_size: int = 2
    net_threshold: float = 10.0

class WashTradingResponse(BaseModel):
    sccs: List[Dict[str, Any]]
    count: int
    saved_file: Optional[str] = None

@router.post("/detect", response_model=ManipulationResponse)
async def detect_manipulation(request: ManipulationRequest):
    if not os.path.exists(DATA_FILE):
        raise HTTPException(status_code=500, detail=f"Data file not found at {DATA_FILE}")
    
    try:
        # Read only necessary columns to save memory/time
        usecols = ['trader_id', 'token_bought_symbol', 'token_sold_symbol', 'token_bought_amount', 'token_sold_amount']
        df = pd.read_csv(DATA_FILE, usecols=usecols)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading data file: {str(e)}")
    
    # 1. Filter by trader_id if limit provided
    if request.limit_traders:
        allowed_traders = set(request.limit_traders)
        df = df[df['trader_id'].isin(allowed_traders)]
    
    if df.empty:
        return ManipulationResponse(suspicious_traders=[], count=0)

    # 2. Convert amounts to numeric, coercing errors
    df['token_bought_amount'] = pd.to_numeric(df['token_bought_amount'], errors='coerce').fillna(0)
    df['token_sold_amount'] = pd.to_numeric(df['token_sold_amount'], errors='coerce').fillna(0)

    # 3. Aggregation
    # Calculate total bought ACT per trader
    bought_mask = df['token_bought_symbol'] == 'ACT'
    bought_act = df[bought_mask].groupby('trader_id')['token_bought_amount'].sum()

    # Calculate total sold ACT per trader
    sold_mask = df['token_sold_symbol'] == 'ACT'
    sold_act = df[sold_mask].groupby('trader_id')['token_sold_amount'].sum()

    # Calculate transaction counts (total trades involving this trader)
    tx_counts = df['trader_id'].value_counts()

    # 4. Combine stats
    # We need traders who exist in either bought or sold (outer join), or just use tx_counts index
    # But we specifically care about those who have BOTH bought and sold activity for self-trading detection?
    # User said "buy once sell twice", implying both actions must happen.
    # So we can look at the intersection of bought and sold indices, or handle fillna(0).
    
    stats_df = pd.DataFrame({
        'bought': bought_act,
        'sold': sold_act,
        'count': tx_counts
    }).fillna(0)

    # 5. Apply Detection Rules
    # Rule: Self-buying and self-selling behavior
    # Must have both buy and sell activity > 0
    # Difference between bought and sold is small (< threshold)
    
    suspicious_mask = (
        (stats_df['bought'] > 0) & 
        (stats_df['sold'] > 0) & 
        (abs(stats_df['bought'] - stats_df['sold']) <= request.threshold)
    )
    
    suspicious_df = stats_df[suspicious_mask].copy()
    suspicious_df['diff'] = abs(suspicious_df['bought'] - suspicious_df['sold'])
    
    # Format results
    suspicious_traders = []
    for trader_id, row in suspicious_df.iterrows():
        suspicious_traders.append(SuspiciousTrader(
            trader_id=str(trader_id),
            total_bought=float(row['bought']),
            total_sold=float(row['sold']),
            diff=float(row['diff']),
            transaction_count=int(row['count'])
        ))
    
    # Sort by difference (smallest diff first?) or total volume?
    # User didn't specify, but smallest diff might be more interesting for "wash trading".
    suspicious_traders.sort(key=lambda x: x.diff)

    return ManipulationResponse(
        suspicious_traders=suspicious_traders,
        count=len(suspicious_traders),
        saved_file=None
    )

@router.post("/detect_wash_trading", response_model=WashTradingResponse)
async def detect_wash_trading(request: WashTradingRequest):
    if not os.path.exists(TRANSFER_FILE):
        raise HTTPException(status_code=500, detail=f"Transfer file not found at {TRANSFER_FILE}")

    # Load DEX Trade Data for Verification
    trade_lookup = {}
    price_times = []
    price_values = []
    
    if os.path.exists(DATA_FILE):
        try:
            trade_cols = ['tx_id', 'token_bought_symbol', 'token_sold_symbol', 'amount_usd', 'token_bought_amount', 'token_sold_amount', 'block_time']
            trades_df = pd.read_csv(DATA_FILE, usecols=trade_cols)
            trades_df['block_time'] = pd.to_datetime(trades_df['block_time'])
            
            # Create lookup for direct matches (keep first occurrence per tx_id)
            trade_lookup = trades_df.drop_duplicates('tx_id').set_index('tx_id').to_dict('index')
            
            # Create sorted price history for estimation
            act_trades = trades_df[
                (trades_df['token_bought_symbol'] == 'ACT') | 
                (trades_df['token_sold_symbol'] == 'ACT')
            ].copy()
            
            def calculate_price_row(row):
                try:
                    usd = float(row['amount_usd'])
                    if row['token_bought_symbol'] == 'ACT':
                        amt = float(row['token_bought_amount'])
                    else:
                        amt = float(row['token_sold_amount'])
                    return usd / amt if amt > 0 else 0
                except:
                    return 0
                    
            act_trades['price'] = act_trades.apply(calculate_price_row, axis=1)
            act_trades = act_trades[act_trades['price'] > 0].sort_values('block_time')
            
            price_times = act_trades['block_time'].tolist()
            price_values = act_trades['price'].tolist()
        except Exception as e:
            print(f"Warning: Could not load trade data: {e}")

    # Helper to find nearest price
    def get_estimated_price(tx_time):
        if not price_times:
            return 0.0
        # bisect_left returns insertion point to maintain order
        # price_times are timestamps
        idx = bisect.bisect_left(price_times, tx_time)
        if idx == 0:
            return price_values[0]
        if idx == len(price_times):
            return price_values[-1]
        
        # Linear interpolation or nearest neighbor
        before_time = price_times[idx-1]
        after_time = price_times[idx]
        before_price = price_values[idx-1]
        after_price = price_values[idx]
        
        # Simple nearest neighbor
        if abs((tx_time - before_time).total_seconds()) < abs((after_time - tx_time).total_seconds()):
            return before_price
        else:
            return after_price

    try:
        # 1. Load Transfer Data
        usecols = ['from_owner', 'to_owner', 'tx_id', 'amount_display', 'block_time']
        df = pd.read_csv(TRANSFER_FILE, usecols=usecols)
        
        # Filter out rows with missing owners
        df = df.dropna(subset=['from_owner', 'to_owner'])
        
        # Ensure amount is numeric
        df['amount_display'] = pd.to_numeric(df['amount_display'], errors='coerce').fillna(0)
        df['block_time'] = pd.to_datetime(df['block_time'])
        
        # 2. Build Graph
        G = nx.DiGraph()
        
        # Group by from/to owner to aggregate transactions
        grouped = df.groupby(['from_owner', 'to_owner'])
        
        for (u, v), group in grouped:
            if u == v:
                pass
            
            # Sort transactions by time
            transactions = group[['tx_id', 'amount_display', 'block_time']].sort_values('block_time').to_dict('records')
            
            # Enrich transactions with trade info
            for tx in transactions:
                tx_id = tx['tx_id']
                tx_time = tx['block_time'] # Already datetime
                
                # Format time as string for JSON
                tx['block_time_str'] = tx_time.strftime("%Y-%m-%d %H:%M:%S")
                
                if tx_id in trade_lookup:
                    trade = trade_lookup[tx_id]
                    tx['is_dex_trade'] = True
                    tx['dex_amount_usd'] = float(trade['amount_usd'])
                    tx['dex_type'] = 'buy' if trade['token_bought_symbol'] == 'ACT' else 'sell'
                    
                    # Calculate price from trade
                    if tx['dex_type'] == 'buy':
                        amt = float(trade['token_bought_amount'])
                    else:
                        amt = float(trade['token_sold_amount'])
                    tx['dex_price'] = float(trade['amount_usd']) / amt if amt > 0 else 0
                else:
                    tx['is_dex_trade'] = False
                    est_price = get_estimated_price(tx_time)
                    tx['estimated_price'] = est_price
                    tx['estimated_value_usd'] = float(tx['amount_display']) * est_price
            
            # Add edge with transaction info
            G.add_edge(u, v, transactions=transactions)
            
        # 3. Find SCCs
        scc_generator = nx.strongly_connected_components(G)
        sccs_list = [list(scc) for scc in scc_generator]
        
        # 4. Filter and Format Results
        results = []
        for i, nodes in enumerate(sccs_list):
            if len(nodes) < request.min_scc_size:
                if len(nodes) == 1:
                    node = nodes[0]
                    if not G.has_edge(node, node):
                        continue
                else:
                    continue
            
            subgraph = G.subgraph(nodes)
            edges_data = []
            
            node_balances = {n: 0.0 for n in nodes}
            total_volume = 0.0
            
            for u, v, data in subgraph.edges(data=True):
                tx_list = data.get("transactions", [])
                
                # Convert timestamps to string for JSON serialization
                serializable_tx_list = []
                for tx in tx_list:
                    tx_copy = tx.copy()
                    if 'block_time' in tx_copy:
                        tx_copy['block_time'] = tx_copy['block_time_str']
                        del tx_copy['block_time_str'] # clean up
                        # remove datetime obj
                        del tx_copy['block_time'] 
                    serializable_tx_list.append(tx_copy)

                edges_data.append({
                    "source": u,
                    "target": v,
                    "transactions": serializable_tx_list
                })
                
                # Update balances
                for tx in tx_list:
                    amount = float(tx.get('amount_display', 0))
                    node_balances[u] -= amount
                    node_balances[v] += amount
                    total_volume += amount
            
            is_wash_trading = False
            if total_volume > 0:
                 is_wash_trading = all(abs(b) <= request.net_threshold for b in node_balances.values())
            
            results.append({
                "scc_id": f"scc_{i}",
                "nodes": nodes,
                "edges": edges_data,
                "size": len(nodes),
                "is_wash_trading": is_wash_trading,
                "net_balances": node_balances,
                "total_volume": total_volume
            })
            
        results.sort(key=lambda x: (not x['is_wash_trading'], -x['size']))
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"wash_trading_results_{timestamp}.json"
        filepath = os.path.join(RESULTS_DIR, filename)
        
        with open(filepath, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "min_scc_size": request.min_scc_size,
                "net_threshold": request.net_threshold,
                "count": len(results),
                "sccs": results
            }, f, indent=2)
            
        return WashTradingResponse(
            sccs=results,
            count=len(results),
            saved_file=f"/wash_trading_results/{filename}"
        )
        
    except Exception as e:
        print(f"Error in wash trading detection: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
