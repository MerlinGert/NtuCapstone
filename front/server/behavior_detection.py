
import csv
import os
import json
import time
import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter(
    prefix="/api/behavior",
    tags=["behavior_detection"],
    responses={404: {"description": "Not found"}},
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BALANCE_SNAPSHOT_CSV = os.path.join(BASE_DIR, "public", "processed", "transfers", "balance_snapshots.csv")
TRADE_CSV = os.path.join(BASE_DIR, "public", "ACT-24-11-10.csv")
TRANSFER_CSV = os.path.join(BASE_DIR, "public", "ACT_transfer_before_2024-11-10.csv")

csv.field_size_limit(2**31 - 1)

# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class TradingSequenceParams(BaseModel):
    """Rule3: Similar Trading Sequence"""
    enable: bool = True
    time_window: float = Field(default=24.0, gt=0, description="Time window in hours for data loading")
    max_time_diff_minutes: float = Field(default=2.0, ge=0, description="Max time difference between matched transactions in minutes")
    direction_mode: str = Field(default="same_side_only", description="same_side_only | mixed_allowed")
    sequence_representation: str = Field(default="action+amount", description="action_only | action+amount | action+price | action+amount+price")
    min_contiguous_length: int = Field(default=5, ge=1, description="Min contiguous matching length")
    amount_similarity: float = Field(default=0.9, ge=0, le=1)
    price_similarity: float = Field(default=0.9, ge=0, le=1)

class BalanceSequenceParams(BaseModel):
    """Rule4: Similar Balance Sequence"""
    enable: bool = True
    time_window: float = Field(default=1.0, gt=0, description="Time window in hours")
    balance_axis: str = Field(default="time_grid", description="time_grid | tx_step")
    tx_step: int = Field(default=10, ge=2, description="Only for tx_step mode")
    time_bin: str = Field(default="1h", description="Only for time_grid mode, e.g. 5m/1h/1d")
    similarity: float = Field(default=0.9, ge=0, le=1, description="Pearson correlation threshold")
    topk_neighbors: int = Field(default=5, ge=1, description="Max similar neighbors per address")

class EarningSequenceParams(BaseModel):
    """Rule5: Similar Earning Sequence"""
    enable: bool = True
    time_window: float = Field(default=1.0, gt=0, description="Time window in hours")
    earning_axis: str = Field(default="time_grid", description="time_grid | tx_step")
    tx_step: int = Field(default=10, ge=2)
    time_bin: str = Field(default="1h")
    similarity: float = Field(default=0.9, ge=0, le=1)
    topk_neighbors: int = Field(default=5, ge=1)

class BehaviorDetectionRequest(BaseModel):
    target_users: Optional[List[str]] = Field(None, description="User addresses to analyse. None = all.")
    time_range: Optional[Dict[str, str]] = Field(None, description="{'start': ..., 'end': ...}")
    trading_sequence: Optional[TradingSequenceParams] = None
    balance_sequence: Optional[BalanceSequenceParams] = None
    earning_sequence: Optional[EarningSequenceParams] = None

class SimilarityEdge(BaseModel):
    source: str
    target: str
    similarity: float
    rule: str
    details: Dict[str, Any] = {}

class BehaviorDetectionResponse(BaseModel):
    status: str
    edges: List[SimilarityEdge]
    groups: List[Dict[str, Any]]
    metadata: Dict[str, Any]

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def parse_time(t_str: str) -> datetime:
    """Parse time strings like '2024-10-19 11:27:09.000 UTC'."""
    t_str = str(t_str).strip()
    if "." in t_str:
        t_str = t_str.split(".")[0] + " UTC"
    if t_str.endswith(" UTC"):
        return datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S UTC")
    return datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S")

def parse_time_bin(bin_str: str) -> timedelta:
    """Convert '5m', '1h', '1d' to timedelta."""
    bin_str = bin_str.strip().lower()
    if bin_str.endswith("m"):
        return timedelta(minutes=int(bin_str[:-1]))
    if bin_str.endswith("h"):
        return timedelta(hours=int(bin_str[:-1]))
    if bin_str.endswith("d"):
        return timedelta(days=int(bin_str[:-1]))
    return timedelta(hours=1)

def get_time_bin_seconds(bin_str: str) -> float:
    return parse_time_bin(bin_str).total_seconds()

# Max addresses allowed in Rule3 pairwise comparison to prevent O(n²) timeout
_MAX_PAIRWISE_ADDRESSES = 500

def pearson_correlation(a: List[float], b: List[float]) -> float:
    """Pearson correlation between two equal-length sequences. Returns 0 on degenerate input."""
    if len(a) < 2:
        return 0.0
    arr = np.array([a, b], dtype=float)
    std = arr.std(axis=1)
    if std[0] == 0.0 or std[1] == 0.0:
        return 0.0
    return float(np.corrcoef(arr)[0, 1])


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

_balance_cache: Optional[pd.DataFrame] = None
_trade_cache: Optional[pd.DataFrame] = None


def _load_balance_snapshots(time_range: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """Load balance_snapshots.csv with caching and optional time-range filter."""
    global _balance_cache
    if _balance_cache is None:
        if not os.path.exists(BALANCE_SNAPSHOT_CSV):
            return pd.DataFrame()
        _balance_cache = pd.read_csv(BALANCE_SNAPSHOT_CSV, dtype=str)
        # Convert numeric columns
        _balance_cache["change_amount"] = pd.to_numeric(_balance_cache["change_amount"], errors="coerce").fillna(0)
        _balance_cache["balance_after"] = pd.to_numeric(_balance_cache["balance_after"], errors="coerce").fillna(0)
    df = _balance_cache.copy()

    if time_range:
        if time_range.get("start"):
            df = df[df["time"] >= time_range["start"]]
        if time_range.get("end"):
            df = df[df["time"] <= time_range["end"]]
    return df


def _load_trades(time_range: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """Load the DEX trade CSV (ACT-24-11-10.csv) with caching."""
    global _trade_cache
    if _trade_cache is None:
        if not os.path.exists(TRADE_CSV):
            return pd.DataFrame()
        cols = [
            "tx_id", "block_time", "trader_id",
            "token_bought_symbol", "token_sold_symbol",
            "token_bought_amount", "token_sold_amount",
            "amount_usd",
        ]
        try:
            _trade_cache = pd.read_csv(TRADE_CSV, usecols=cols, dtype=str)
        except ValueError:
            _trade_cache = pd.read_csv(TRADE_CSV, dtype=str)
        for c in ["token_bought_amount", "token_sold_amount", "amount_usd"]:
            if c in _trade_cache.columns:
                _trade_cache[c] = pd.to_numeric(_trade_cache[c], errors="coerce").fillna(0)
    df = _trade_cache.copy()
    if time_range:
        if time_range.get("start") and "block_time" in df.columns:
            df = df[df["block_time"] >= time_range["start"]]
        if time_range.get("end") and "block_time" in df.columns:
            df = df[df["block_time"] <= time_range["end"]]
    return df


# ===================================================================
# Rule 3: Similar Trading Sequence
# ===================================================================

def _build_trading_sequences(
    df_trades: pd.DataFrame,
    target_users: Optional[List[str]],
    params: TradingSequenceParams,
) -> Dict[str, List[Dict]]:
    """
    Build per-address trading event sequence.
    Each event = {action: 'buy'|'sell', amount: float, price: float, time: str, ts: float}
    """
    if df_trades.empty:
        return {}

    # Determine which column identifies the trader
    trader_col = "trader_id"
    if trader_col not in df_trades.columns:
        return {}

    if target_users:
        df_trades = df_trades[df_trades[trader_col].isin(set(target_users))]

    # Sort by time
    if "block_time" in df_trades.columns:
        df_trades = df_trades.sort_values("block_time")

    sequences: Dict[str, List[Dict]] = defaultdict(list)

    for _, row in df_trades.iterrows():
        trader = row.get(trader_col, "")
        if not trader:
            continue

        bought_sym = str(row.get("token_bought_symbol", ""))
        sold_sym = str(row.get("token_sold_symbol", ""))
        bought_amt = float(row.get("token_bought_amount", 0))
        sold_amt = float(row.get("token_sold_amount", 0))
        usd = float(row.get("amount_usd", 0))
        time_str = str(row.get("block_time", ""))
        
        try:
            ts = parse_time(time_str).timestamp()
        except:
            ts = 0.0

        # Determine action: buy ACT or sell ACT
        if bought_sym == "ACT":
            action = "buy"
            amount = bought_amt
            price = usd / bought_amt if bought_amt > 0 else 0
        elif sold_sym == "ACT":
            action = "sell"
            amount = sold_amt
            price = usd / sold_amt if sold_amt > 0 else 0
        else:
            continue

        sequences[trader].append({
            "action": action,
            "amount": amount,
            "price": price,
            "time": time_str,
            "ts": ts
        })

    return dict(sequences)


def _compare_trading_sequences(
    seq_a: List[Dict], seq_b: List[Dict], params: TradingSequenceParams
) -> Tuple[float, Dict]:
    """
    Compare two trading sequences and return (similarity_score, detail_dict).
    Uses longest contiguous matching sub-sequence approach with Time Window constraint.
    """
    rep = params.sequence_representation
    time_window_sec = params.time_window * 3600

    def _action_match(a: Dict, b: Dict) -> bool:
        if a["action"] != b["action"]:
            if params.direction_mode == "same_side_only":
                return False
        return True

    def _amount_match(a: Dict, b: Dict) -> bool:
        if "amount" not in rep:
            return True
        ma = max(a["amount"], b["amount"])
        if ma == 0:
            return True
        ratio = min(a["amount"], b["amount"]) / ma
        return ratio >= params.amount_similarity

    def _price_match(a: Dict, b: Dict) -> bool:
        if "price" not in rep:
            return True
        mp = max(a["price"], b["price"])
        if mp == 0:
            return True
        ratio = min(a["price"], b["price"]) / mp
        return ratio >= params.price_similarity

    def _events_match(a: Dict, b: Dict) -> bool:
        # Check time difference
        time_diff = abs(a["ts"] - b["ts"])
        max_diff = params.max_time_diff_minutes * 60
        if time_diff > max_diff:
            return False
            
        return _action_match(a, b) and _amount_match(a, b) and _price_match(a, b)

    # Find longest contiguous matching sub-sequence (DP)
    n, m = len(seq_a), len(seq_b)
    if n == 0 or m == 0:
        return 0.0, {}

    max_len = 0
    # dp[j] = length of contiguous match ending at seq_a[i-1], seq_b[j-1]
    prev = [0] * (m + 1)
    
    for i in range(1, n + 1):
        curr = [0] * (m + 1)
        for j in range(1, m + 1):
            if _events_match(seq_a[i - 1], seq_b[j - 1]):
                candidate_len = prev[j - 1] + 1
                
                # Verify time span constraint
                # Sequence A match: from seq_a[i - candidate_len] to seq_a[i - 1]
                # Sequence B match: from seq_b[j - candidate_len] to seq_b[j - 1]
                
                # We need to trim candidate_len if duration exceeds time_window
                while candidate_len > 0:
                    start_idx_a = i - candidate_len
                    end_idx_a = i - 1
                    duration_a = seq_a[end_idx_a]["ts"] - seq_a[start_idx_a]["ts"]
                    
                    start_idx_b = j - candidate_len
                    end_idx_b = j - 1
                    duration_b = seq_b[end_idx_b]["ts"] - seq_b[start_idx_b]["ts"]
                    
                    if duration_a <= time_window_sec and duration_b <= time_window_sec:
                        break
                    
                    candidate_len -= 1
                
                curr[j] = candidate_len
                
                if curr[j] > max_len:
                    max_len = curr[j]
            else:
                curr[j] = 0
        prev = curr

    if max_len < params.min_contiguous_length:
        return 0.0, {"max_contiguous": max_len}

    score = max_len / max(n, m)
    return score, {"max_contiguous": max_len, "len_a": n, "len_b": m}


def process_rule3(
    target_users: Optional[List[str]],
    time_range: Optional[Dict[str, str]],
    params: TradingSequenceParams,
) -> List[SimilarityEdge]:
    """Run Rule3: Similar Trading Sequence."""
    df_trades = _load_trades(time_range)
    if df_trades.empty:
        return []

    # Removed "last N hours" clipping. Now we use the full loaded data (respecting time_range).
    
    sequences = _build_trading_sequences(df_trades, target_users, params)
    if len(sequences) < 2:
        return []

    addresses = list(sequences.keys())

    # Guard against O(n²) blowup
    if len(addresses) > _MAX_PAIRWISE_ADDRESSES:
        print(f"[Rule3] WARNING: {len(addresses)} addresses exceeds limit {_MAX_PAIRWISE_ADDRESSES}, truncating.")
        addresses = addresses[:_MAX_PAIRWISE_ADDRESSES]

    edges: List[SimilarityEdge] = []

    for i in range(len(addresses)):
        for j in range(i + 1, len(addresses)):
            a, b = addresses[i], addresses[j]
            score, detail = _compare_trading_sequences(sequences[a], sequences[b], params)
            if score > 0:
                edges.append(SimilarityEdge(
                    source=a, target=b,
                    similarity=round(score, 4),
                    rule="similar_trading_sequence",
                    details=detail,
                ))

    return edges


# ===================================================================
# Rule 4: Similar Balance Sequence
# ===================================================================

def _build_balance_sequences(
    df_bal: pd.DataFrame,
    target_users: Optional[List[str]],
    params: BalanceSequenceParams,
) -> Dict[str, List[float]]:
    """
    Build per-address balance sequence.
    """
    if df_bal.empty:
        return {}

    if target_users:
        df_bal = df_bal[df_bal["owner_address"].isin(set(target_users))]
    if df_bal.empty:
        return {}

    sequences: Dict[str, List[float]] = {}

    if params.balance_axis == "tx_step":
        for owner, grp in df_bal.groupby("owner_address"):
            vals = grp["balance_after"].tolist()
            sampled = vals[:: params.tx_step]
            if len(sampled) >= 2:
                sequences[owner] = sampled
    else:
        # time_grid mode
        td = parse_time_bin(params.time_bin)
        times = df_bal["time"].dropna()
        if times.empty:
            return {}
        t_min = parse_time(times.iloc[0])
        t_max = parse_time(times.iloc[-1])

        grid: List[datetime] = []
        t = t_min
        while t <= t_max:
            grid.append(t)
            t += td
        if len(grid) < 2:
            return {}

        for owner, grp in df_bal.groupby("owner_address"):
            grp = grp.sort_values("time")
            owner_times = [parse_time(t) for t in grp["time"]]
            owner_bals = grp["balance_after"].tolist()

            sampled: List[float] = []
            idx = 0
            last_bal = 0.0
            for gp in grid:
                while idx < len(owner_times) and owner_times[idx] <= gp:
                    last_bal = owner_bals[idx]
                    idx += 1
                sampled.append(last_bal)

            if len(sampled) >= 2:
                sequences[owner] = sampled

    return sequences


def process_rule4(
    target_users: Optional[List[str]],
    time_range: Optional[Dict[str, str]],
    params: BalanceSequenceParams,
) -> List[SimilarityEdge]:
    """Run Rule4: Similar Balance Sequence with Rolling Window."""
    df_bal = _load_balance_snapshots(time_range)
    if df_bal.empty:
        return []

    sequences = _build_balance_sequences(df_bal, target_users, params)
    if len(sequences) < 2:
        return []

    addresses = list(sequences.keys())
    neighbor_scores: Dict[str, List[Tuple[str, float]]] = defaultdict(list)

    # Calculate window size in points
    window_size_points = None
    if params.balance_axis == "time_grid" and params.time_window > 0:
        bin_seconds = get_time_bin_seconds(params.time_bin)
        if bin_seconds > 0:
            window_size_points = int((params.time_window * 3600) / bin_seconds)
            if window_size_points < 2:
                window_size_points = 2
    
    # If using tx_step or invalid window, fallback to full sequence
    use_rolling = (window_size_points is not None)

    for i in range(len(addresses)):
        for j in range(i + 1, len(addresses)):
            a, b = addresses[i], addresses[j]
            sa, sb = sequences[a], sequences[b]
            min_len = min(len(sa), len(sb))
            
            # Truncate to same length for comparison
            sa_trunc = sa[:min_len]
            sb_trunc = sb[:min_len]
            
            max_corr = 0.0
            
            if use_rolling and min_len >= window_size_points:
                # Use rolling correlation
                s_a = pd.Series(sa_trunc)
                s_b = pd.Series(sb_trunc)
                # Compute rolling correlation
                rolling_corr = s_a.rolling(window=window_size_points).corr(s_b)
                # Max correlation (ignoring NaNs)
                valid_corrs = rolling_corr.dropna()
                if not valid_corrs.empty:
                    max_corr = float(valid_corrs.max())
                else:
                    max_corr = 0.0
            else:
                # Fallback to full sequence correlation
                max_corr = pearson_correlation(sa_trunc, sb_trunc)
                
            if max_corr >= params.similarity:
                neighbor_scores[a].append((b, max_corr))
                neighbor_scores[b].append((a, max_corr))

    edges: List[SimilarityEdge] = []
    seen = set()
    for addr, neighbors in neighbor_scores.items():
        neighbors.sort(key=lambda x: -x[1])
        for peer, corr in neighbors[: params.topk_neighbors]:
            key = tuple(sorted([addr, peer]))
            if key not in seen:
                seen.add(key)
                edges.append(SimilarityEdge(
                    source=key[0], target=key[1],
                    similarity=round(corr, 4),
                    rule="similar_balance_sequence",
                    details={"pearson": round(corr, 4)},
                ))

    return edges


# ===================================================================
# Rule 5: Similar Earning Sequence
# ===================================================================

def _build_earning_sequences(
    df_trades: pd.DataFrame,
    target_users: Optional[List[str]],
    params: EarningSequenceParams,
) -> Dict[str, List[float]]:
    """
    Build per-address earning (realized PnL) sequence.
    """
    if df_trades.empty:
        return {}

    trader_col = "trader_id"
    if trader_col not in df_trades.columns:
        return {}

    if target_users:
        df_trades = df_trades[df_trades[trader_col].isin(set(target_users))]
    if df_trades.empty:
        return {}

    if "block_time" in df_trades.columns:
        df_trades = df_trades.sort_values("block_time")

    # Compute cumulative realized PnL per trader
    cost_basis: Dict[str, float] = {}  # trader -> weighted avg buy price
    holdings: Dict[str, float] = {}     # trader -> current holding amount
    pnl_events: Dict[str, List[Dict]] = defaultdict(list)  # trader -> [{time, cum_pnl}]
    cum_pnl: Dict[str, float] = defaultdict(float)

    for _, row in df_trades.iterrows():
        trader = row.get(trader_col, "")
        if not trader:
            continue

        bought_sym = str(row.get("token_bought_symbol", ""))
        sold_sym = str(row.get("token_sold_symbol", ""))
        bought_amt = float(row.get("token_bought_amount", 0))
        sold_amt = float(row.get("token_sold_amount", 0))
        usd = float(row.get("amount_usd", 0))
        t = str(row.get("block_time", ""))

        if bought_sym == "ACT" and bought_amt > 0:
            # Buy: update cost basis
            buy_price = usd / bought_amt if bought_amt > 0 else 0
            old_hold = holdings.get(trader, 0)
            old_cost = cost_basis.get(trader, 0)
            new_hold = old_hold + bought_amt
            if new_hold > 0:
                cost_basis[trader] = (old_cost * old_hold + buy_price * bought_amt) / new_hold
            holdings[trader] = new_hold

        elif sold_sym == "ACT" and sold_amt > 0:
            # Sell: realize PnL
            sell_price = usd / sold_amt if sold_amt > 0 else 0
            avg_cost = cost_basis.get(trader, 0)
            realized = (sell_price - avg_cost) * sold_amt
            cum_pnl[trader] += realized
            holdings[trader] = max(holdings.get(trader, 0) - sold_amt, 0)

            pnl_events[trader].append({"time": t, "cum_pnl": cum_pnl[trader]})

    if not pnl_events:
        return {}

    # Sample the PnL sequences
    sequences: Dict[str, List[float]] = {}

    if params.earning_axis == "tx_step":
        for trader, events in pnl_events.items():
            vals = [e["cum_pnl"] for e in events]
            sampled = vals[:: params.tx_step]
            if len(sampled) >= 2:
                sequences[trader] = sampled
    else:
        # time_grid mode
        td = parse_time_bin(params.time_bin)
        
        # Determine global time range
        all_times = []
        for events in pnl_events.values():
            for e in events:
                all_times.append(parse_time(e["time"]))
        if not all_times:
            return {}
        
        all_times.sort()
        t_min = all_times[0]
        t_max = all_times[-1]

        grid: List[datetime] = []
        t = t_min
        while t <= t_max:
            grid.append(t)
            t += td
        if len(grid) < 2:
            return {}

        for trader, events in pnl_events.items():
            # Sort events by time
            events.sort(key=lambda x: parse_time(x["time"]))
            
            evt_times = [parse_time(e["time"]) for e in events]
            evt_vals = [e["cum_pnl"] for e in events]

            sampled: List[float] = []
            idx = 0
            last_val = 0.0
            for gp in grid:
                while idx < len(evt_times) and evt_times[idx] <= gp:
                    last_val = evt_vals[idx]
                    idx += 1
                sampled.append(last_val)

            if len(sampled) >= 2:
                sequences[trader] = sampled

    return sequences


def process_rule5(
    target_users: Optional[List[str]],
    time_range: Optional[Dict[str, str]],
    params: EarningSequenceParams,
) -> List[SimilarityEdge]:
    """Run Rule5: Similar Earning Sequence with Rolling Window."""
    df_trades = _load_trades(time_range)
    if df_trades.empty:
        return []

    sequences = _build_earning_sequences(df_trades, target_users, params)
    if len(sequences) < 2:
        return []

    addresses = list(sequences.keys())
    neighbor_scores: Dict[str, List[Tuple[str, float]]] = defaultdict(list)

    # Calculate window size in points
    window_size_points = None
    if params.earning_axis == "time_grid" and params.time_window > 0:
        bin_seconds = get_time_bin_seconds(params.time_bin)
        if bin_seconds > 0:
            window_size_points = int((params.time_window * 3600) / bin_seconds)
            if window_size_points < 2:
                window_size_points = 2
    
    use_rolling = (window_size_points is not None)

    for i in range(len(addresses)):
        for j in range(i + 1, len(addresses)):
            a, b = addresses[i], addresses[j]
            sa, sb = sequences[a], sequences[b]
            min_len = min(len(sa), len(sb))
            
            sa_trunc = sa[:min_len]
            sb_trunc = sb[:min_len]
            
            max_corr = 0.0
            
            if use_rolling and min_len >= window_size_points:
                s_a = pd.Series(sa_trunc)
                s_b = pd.Series(sb_trunc)
                rolling_corr = s_a.rolling(window=window_size_points).corr(s_b)
                valid_corrs = rolling_corr.dropna()
                if not valid_corrs.empty:
                    max_corr = float(valid_corrs.max())
                else:
                    max_corr = 0.0
            else:
                max_corr = pearson_correlation(sa_trunc, sb_trunc)
                
            if max_corr >= params.similarity:
                neighbor_scores[a].append((b, max_corr))
                neighbor_scores[b].append((a, max_corr))

    edges: List[SimilarityEdge] = []
    seen = set()
    for addr, neighbors in neighbor_scores.items():
        neighbors.sort(key=lambda x: -x[1])
        for peer, corr in neighbors[: params.topk_neighbors]:
            key = tuple(sorted([addr, peer]))
            if key not in seen:
                seen.add(key)
                edges.append(SimilarityEdge(
                    source=key[0], target=key[1],
                    similarity=round(corr, 4),
                    rule="similar_earning_sequence",
                    details={"pearson": round(corr, 4)},
                ))

    return edges


# ===================================================================
# Main detection entry point
# ===================================================================

class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, i):
        if i not in self.parent:
            self.parent[i] = i
        if self.parent[i] != i:
            self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i, j):
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            self.parent[root_i] = root_j


def edges_to_groups(edges: List[SimilarityEdge]) -> List[Dict[str, Any]]:
    """Convert pairwise edges into connected component groups."""
    uf = UnionFind()
    
    # Track rules per node pair to summarize group rules
    # key: (min(a,b), max(a,b)) -> set(rules)
    pair_rules = defaultdict(set)
    pair_sims = defaultdict(list)
    pair_details = defaultdict(list)

    for e in edges:
        uf.union(e.source, e.target)
        key = tuple(sorted([e.source, e.target]))
        pair_rules[key].add(e.rule)
        pair_sims[key].append(e.similarity)
        pair_details[key].append(e.details)

    # Collect components
    groups_map = defaultdict(set)
    all_nodes = set(uf.parent.keys())
    for node in all_nodes:
        root = uf.find(node)
        groups_map[root].add(node)

    results = []
    for root, members in groups_map.items():
        member_list = list(members)
        if len(member_list) < 2:
            continue
            
        # Aggregate group stats
        group_rules = set()
        total_sim = 0.0
        count_sim = 0
        aggregated_details = []
        
        # Check all internal pairs
        for i in range(len(member_list)):
            for j in range(i + 1, len(member_list)):
                key = tuple(sorted([member_list[i], member_list[j]]))
                if key in pair_rules:
                    group_rules.update(pair_rules[key])
                    total_sim += max(pair_sims[key])
                    count_sim += 1
                    # Add simplified details for this pair
                    aggregated_details.append({
                        "pair": list(key),
                        "rules": list(pair_rules[key]),
                        "details": pair_details[key]
                    })
        
        avg_sim = total_sim / count_sim if count_sim > 0 else 0.0
        
        results.append({
            "group_id": f"behavior_group_{len(results)}",
            "members": member_list,
            "member_count": len(member_list),
            "rules_matched": list(group_rules),
            "avg_similarity": round(avg_sim, 4),
            "pair_details": aggregated_details
        })
    
    results.sort(key=lambda x: x["member_count"], reverse=True)
    return results


@router.post("/detect", response_model=BehaviorDetectionResponse)
async def detect_behavior(request: BehaviorDetectionRequest):
    """
    Run behavior-similarity-based entity detection.
    Combines Rule3, Rule4, Rule5 edges and groups connected components.
    """
    all_edges: List[SimilarityEdge] = []

    # Rule 3
    if request.trading_sequence and request.trading_sequence.enable:
        try:
            edges3 = process_rule3(request.target_users, request.time_range, request.trading_sequence)
            all_edges.extend(edges3)
        except Exception as e:
            print(f"Error in Rule3: {e}")

    # Rule 4
    if request.balance_sequence and request.balance_sequence.enable:
        try:
            edges4 = process_rule4(request.target_users, request.time_range, request.balance_sequence)
            all_edges.extend(edges4)
        except Exception as e:
            print(f"Error in Rule4: {e}")

    # Rule 5
    if request.earning_sequence and request.earning_sequence.enable:
        try:
            edges5 = process_rule5(request.target_users, request.time_range, request.earning_sequence)
            all_edges.extend(edges5)
        except Exception as e:
            print(f"Error in Rule5: {e}")

    # Grouping
    groups = edges_to_groups(all_edges)

    return BehaviorDetectionResponse(
        status="success",
        edges=all_edges,
        groups=groups,
        metadata={
            "total_edges": len(all_edges),
            "total_groups": len(groups),
        }
    )
