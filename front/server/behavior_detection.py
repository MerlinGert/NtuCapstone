"""
Behavior-similarity-based entity detection rules:
  Rule3: Similar Trading Sequence
  Rule4: Similar Balance Sequence
  Rule5: Similar Earning Sequence
"""

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
    time_window: float = Field(default=float("inf"), gt=0, description="Time window in hours")
    direction_mode: str = Field(default="same_side_only", description="same_side_only | mixed_allowed")
    sequence_representation: str = Field(default="action_only", description="action_only | action+amount | action+price | action+amount+price")
    min_contiguous_length: int = Field(default=3, ge=1, description="Min contiguous matching length")
    amount_similarity: float = Field(default=0.8, ge=0, le=1)
    price_similarity: float = Field(default=0.8, ge=0, le=1)

class BalanceSequenceParams(BaseModel):
    """Rule4: Similar Balance Sequence"""
    enable: bool = True
    time_window: float = Field(default=float("inf"), gt=0, description="Time window in hours")
    balance_axis: str = Field(default="time_grid", description="time_grid | tx_step")
    tx_step: int = Field(default=10, ge=2, description="Only for tx_step mode")
    time_bin: str = Field(default="1h", description="Only for time_grid mode, e.g. 5m/1h/1d")
    similarity: float = Field(default=0.8, ge=0, le=1, description="Pearson correlation threshold")
    topk_neighbors: int = Field(default=5, ge=1, description="Max similar neighbors per address")

class EarningSequenceParams(BaseModel):
    """Rule5: Similar Earning Sequence"""
    enable: bool = True
    time_window: float = Field(default=float("inf"), gt=0, description="Time window in hours")
    earning_axis: str = Field(default="time_grid", description="time_grid | tx_step")
    tx_step: int = Field(default=10, ge=2)
    time_bin: str = Field(default="1h")
    similarity: float = Field(default=0.8, ge=0, le=1)
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
    t_str = t_str.strip()
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
    Each event = {action: 'buy'|'sell', amount: float, price: float, time: str}
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
            "time": str(row.get("block_time", "")),
        })

    return dict(sequences)


def _compare_trading_sequences(
    seq_a: List[Dict], seq_b: List[Dict], params: TradingSequenceParams
) -> Tuple[float, Dict]:
    """
    Compare two trading sequences and return (similarity_score, detail_dict).
    Uses longest contiguous matching sub-sequence approach.
    """
    rep = params.sequence_representation

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
                curr[j] = prev[j - 1] + 1
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

    # Apply time_window: keep only trades within the last N hours relative to the latest trade
    if params.time_window != float("inf") and "block_time" in df_trades.columns:
        df_sorted = df_trades.sort_values("block_time")
        latest_str = df_sorted["block_time"].iloc[-1] if not df_sorted.empty else None
        if latest_str:
            try:
                latest_dt = parse_time(str(latest_str))
                cutoff = latest_dt - timedelta(hours=params.time_window)
                cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
                df_trades = df_sorted[df_sorted["block_time"] >= cutoff_str]
            except Exception:
                pass

    sequences = _build_trading_sequences(df_trades, target_users, params)
    if len(sequences) < 2:
        return []

    addresses = list(sequences.keys())

    # Guard against O(n²) blowup: truncate to first _MAX_PAIRWISE_ADDRESSES addresses
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
      time_grid  – resample balances at fixed time intervals
      tx_step    – take balance at every N-th transaction
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
    """Run Rule4: Similar Balance Sequence."""
    df_bal = _load_balance_snapshots(time_range)
    if df_bal.empty:
        return []

    sequences = _build_balance_sequences(df_bal, target_users, params)
    if len(sequences) < 2:
        return []

    addresses = list(sequences.keys())
    neighbor_scores: Dict[str, List[Tuple[str, float]]] = defaultdict(list)

    for i in range(len(addresses)):
        for j in range(i + 1, len(addresses)):
            a, b = addresses[i], addresses[j]
            sa, sb = sequences[a], sequences[b]
            min_len = min(len(sa), len(sb))
            corr = pearson_correlation(sa[:min_len], sb[:min_len])
            if corr >= params.similarity:
                neighbor_scores[a].append((b, corr))
                neighbor_scores[b].append((a, corr))

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
    Realized PnL = (sell_price - avg_buy_price) * sell_amount
    We accumulate cumulative PnL and sample it like balance sequences.
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
    # Track avg cost basis per trader
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

    # Sample the PnL sequences using the same approach as balance sequences
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
        all_times = []
        for events in pnl_events.values():
            for e in events:
                if e["time"]:
                    try:
                        all_times.append(parse_time(e["time"]))
                    except Exception:
                        pass
        if not all_times:
            return {}
        t_min = min(all_times)
        t_max = max(all_times)

        grid: List[datetime] = []
        t = t_min
        while t <= t_max:
            grid.append(t)
            t += td
        if len(grid) < 2:
            return {}

        for trader, events in pnl_events.items():
            e_times = []
            e_pnls = []
            for e in events:
                try:
                    e_times.append(parse_time(e["time"]))
                    e_pnls.append(e["cum_pnl"])
                except Exception:
                    pass

            sampled: List[float] = []
            idx = 0
            last_pnl = 0.0
            for gp in grid:
                while idx < len(e_times) and e_times[idx] <= gp:
                    last_pnl = e_pnls[idx]
                    idx += 1
                sampled.append(last_pnl)

            if len(sampled) >= 2:
                sequences[trader] = sampled

    return sequences


def process_rule5(
    target_users: Optional[List[str]],
    time_range: Optional[Dict[str, str]],
    params: EarningSequenceParams,
) -> List[SimilarityEdge]:
    """Run Rule5: Similar Earning Sequence."""
    df_trades = _load_trades(time_range)
    if df_trades.empty:
        return []

    sequences = _build_earning_sequences(df_trades, target_users, params)
    if len(sequences) < 2:
        return []

    addresses = list(sequences.keys())
    neighbor_scores: Dict[str, List[Tuple[str, float]]] = defaultdict(list)

    for i in range(len(addresses)):
        for j in range(i + 1, len(addresses)):
            a, b = addresses[i], addresses[j]
            sa, sb = sequences[a], sequences[b]
            min_len = min(len(sa), len(sb))
            corr = pearson_correlation(sa[:min_len], sb[:min_len])
            if corr >= params.similarity:
                neighbor_scores[a].append((b, corr))
                neighbor_scores[b].append((a, corr))

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
# Grouping utility
# ===================================================================

def _edges_to_groups(edges: List[SimilarityEdge]) -> List[Dict[str, Any]]:
    """Convert similarity edges into connected-component groups via Union-Find."""
    import networkx as nx
    G = nx.Graph()
    for e in edges:
        G.add_edge(e.source, e.target, similarity=e.similarity, rule=e.rule)

    groups = []
    for i, comp in enumerate(nx.connected_components(G)):
        if len(comp) < 2:
            continue
        members = list(comp)
        sub = G.subgraph(comp)
        rules_used = set()
        avg_sim = 0.0
        edge_count = 0
        for _, _, d in sub.edges(data=True):
            rules_used.add(d.get("rule", ""))
            avg_sim += d.get("similarity", 0)
            edge_count += 1
        if edge_count:
            avg_sim /= edge_count

        groups.append({
            "group_id": f"behavior_group_{i}",
            "members": members,
            "member_count": len(members),
            "avg_similarity": round(avg_sim, 4),
            "rules_matched": list(rules_used),
        })

    groups.sort(key=lambda g: -g["member_count"])
    return groups


# ===================================================================
# API Endpoints
# ===================================================================

@router.post("/detect", response_model=BehaviorDetectionResponse)
async def detect_behavior(request: BehaviorDetectionRequest):
    """
    Run behavior-similarity-based entity detection.
    Accepts Rule3, Rule4, Rule5 parameters; returns similarity edges and groups.
    """
    try:
        start = time.time()
        all_edges: List[SimilarityEdge] = []

        # Rule 3 – Similar Trading Sequence
        if request.trading_sequence and request.trading_sequence.enable:
            r3 = process_rule3(request.target_users, request.time_range, request.trading_sequence)
            all_edges.extend(r3)

        # Rule 4 – Similar Balance Sequence
        if request.balance_sequence and request.balance_sequence.enable:
            r4 = process_rule4(request.target_users, request.time_range, request.balance_sequence)
            all_edges.extend(r4)

        # Rule 5 – Similar Earning Sequence
        if request.earning_sequence and request.earning_sequence.enable:
            r5 = process_rule5(request.target_users, request.time_range, request.earning_sequence)
            all_edges.extend(r5)

        groups = _edges_to_groups(all_edges)
        elapsed = time.time() - start

        return BehaviorDetectionResponse(
            status="success",
            edges=all_edges,
            groups=groups,
            metadata={
                "execution_time_seconds": round(elapsed, 3),
                "edge_count": len(all_edges),
                "group_count": len(groups),
                "rules_applied": {
                    "trading_sequence": bool(request.trading_sequence and request.trading_sequence.enable),
                    "balance_sequence": bool(request.balance_sequence and request.balance_sequence.enable),
                    "earning_sequence": bool(request.earning_sequence and request.earning_sequence.enable),
                },
            },
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))