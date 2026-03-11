"""
Fraudulent-Activity-Based Entity Detection
  Wash Trading in the Same Colluding Group

Detects cycles (loops) in the transfer graph where tokens circulate
among a group of addresses within a time window, indicating coordinated
wash trading.

Parameters:
  Enable, Time_window, Time_span, Loop_size, Require_temporal_order,
  Net_position_abs, Amount_similarity, Tx_frequency,
  Net_Position_Score, SpeedScore
"""

import csv
import os
import time as _time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter(
    prefix="/api/fraudulent_activity",
    tags=["fraudulent_activity_detection"],
    responses={404: {"description": "Not found"}},
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSFER_CSV = os.path.join(BASE_DIR, "public", "ACT_transfer_before_2024-11-10.csv")
TRADE_CSV = os.path.join(BASE_DIR, "public", "ACT-24-11-10.csv")

csv.field_size_limit(2**31 - 1)

# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class WashTradingCollusionParams(BaseModel):
    """Wash Trading in the Same Colluding Group"""
    enable: bool = True
    time_window: float = Field(
        default=168.0, gt=0,
        description="Overall detection time window in hours",
    )
    time_span: float = Field(
        default=48.0, gt=0,
        description="Max time span (hours) from first tx to last tx in a loop",
    )
    loop_size: int = Field(
        default=2, ge=2,
        description="Min cycle size (number of distinct nodes in the loop)",
    )
    require_temporal_order: bool = Field(
        default=False,
        description="True: edges in cycle must be temporally increasing; "
                    "False: just need cycle in the graph",
    )
    net_position_abs: float = Field(
        default=1000.0, ge=0,
        description="Max |In(v) - Out(v)| for each node in the loop",
    )
    amount_similarity: float = Field(
        default=0.5, ge=0, le=1,
        description="Min similarity of transfer amounts within the loop "
                    "(min_amount / max_amount)",
    )
    tx_frequency: float = Field(
        default=0.0, ge=0, le=1,
        description="Min fraction of a node's total txs that go to next node "
                    "in loop: num(a,b)/num(a)",
    )
    net_position_score: float = Field(
        default=0.3, ge=0, le=1,
        description="Max |In(v)-Out(v)| / (In(v)+Out(v)) for each node",
    )
    speed_score: float = Field(
        default=0.0, ge=0, le=1,
        description="Min speed score: 1 - (time_span / time_window). "
                    "Higher = faster loop completion.",
    )


class FraudulentActivityRequest(BaseModel):
    target_users: Optional[List[str]] = Field(
        None, description="Addresses to analyse. None = all.",
    )
    time_range: Optional[Dict[str, str]] = Field(
        None, description="{'start': ..., 'end': ...}",
    )
    wash_trading_collusion: Optional[WashTradingCollusionParams] = None


class CollusionLoopEdge(BaseModel):
    source: str
    target: str
    total_amount: float
    tx_count: int
    earliest_time: str
    latest_time: str


class CollusionLoopHit(BaseModel):
    loop_id: str
    members: List[str]
    loop_size: int
    edges: List[CollusionLoopEdge]
    time_span_hours: float
    speed_score: float
    avg_amount_similarity: float
    avg_net_position_score: float
    max_net_position_abs: float
    total_volume: float
    details: Dict[str, Any] = {}


class FraudulentActivityResponse(BaseModel):
    status: str
    collusion_loops: List[CollusionLoopHit] = []
    metadata: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Data Loading (cached)
# ---------------------------------------------------------------------------
_transfer_cache: Optional[pd.DataFrame] = None
_trade_cache: Optional[pd.DataFrame] = None


def _load_transfers() -> pd.DataFrame:
    """Load and cache the transfer CSV."""
    global _transfer_cache
    if _transfer_cache is not None:
        return _transfer_cache

    if not os.path.exists(TRANSFER_CSV):
        raise HTTPException(status_code=500, detail=f"Transfer file not found: {TRANSFER_CSV}")

    usecols = ["from_owner", "to_owner", "amount_display", "block_time", "tx_id"]
    df = pd.read_csv(TRANSFER_CSV, usecols=usecols)
    df = df.dropna(subset=["from_owner", "to_owner"])
    df["amount_display"] = pd.to_numeric(df["amount_display"], errors="coerce").fillna(0)
    df["block_time"] = pd.to_datetime(df["block_time"], utc=True, errors="coerce")
    df = df.dropna(subset=["block_time"])
    df = df.sort_values("block_time").reset_index(drop=True)
    _transfer_cache = df
    return df


def _load_trades() -> pd.DataFrame:
    """Load and cache the DEX trade CSV (used for context only)."""
    global _trade_cache
    if _trade_cache is not None:
        return _trade_cache

    if not os.path.exists(TRADE_CSV):
        raise HTTPException(status_code=500, detail=f"Trade file not found: {TRADE_CSV}")

    usecols = ["trader_id", "block_time", "token_bought_symbol",
               "token_sold_symbol", "token_bought_amount",
               "token_sold_amount", "amount_usd", "tx_id"]
    df = pd.read_csv(TRADE_CSV, usecols=usecols)
    df["block_time"] = pd.to_datetime(df["block_time"], utc=True, errors="coerce")
    df = df.dropna(subset=["block_time"])
    df = df.sort_values("block_time").reset_index(drop=True)
    _trade_cache = df
    return df



# ---------------------------------------------------------------------------
# Graph Building
# ---------------------------------------------------------------------------

def _build_transfer_graph(
    df: pd.DataFrame,
    target_users: Optional[Set[str]],
    time_start: Optional[datetime],
    time_end: Optional[datetime],
) -> Tuple[nx.DiGraph, Dict[str, int]]:
    """
    Build a directed transfer graph from transfer data.

    Returns:
        G  – nx.DiGraph where each edge (u, v) carries:
             'transactions': list[dict] with keys tx_id, amount, time
             'total_amount': sum of amounts
             'tx_count': number of transactions
             'earliest': earliest datetime
             'latest': latest datetime
        out_count – dict[address, total_outgoing_tx_count]
    """
    sub = df.copy()

    # ---- time filter ----
    if time_start is not None:
        sub = sub[sub["block_time"] >= time_start]
    if time_end is not None:
        sub = sub[sub["block_time"] <= time_end]

    # ---- target user filter ----
    if target_users:
        sub = sub[
            sub["from_owner"].isin(target_users)
            | sub["to_owner"].isin(target_users)
        ]

    if sub.empty:
        return nx.DiGraph(), {}

    # per-address outgoing tx count (for tx_frequency calculation)
    out_count: Dict[str, int] = sub.groupby("from_owner")["tx_id"].count().to_dict()

    # group by edge
    G = nx.DiGraph()
    grouped = sub.groupby(["from_owner", "to_owner"])
    for (u, v), grp in grouped:
        txs = grp[["tx_id", "amount_display", "block_time"]].sort_values("block_time")
        tx_list = [
            {"tx_id": r["tx_id"], "amount": r["amount_display"], "time": r["block_time"]}
            for _, r in txs.iterrows()
        ]
        total_amt = grp["amount_display"].sum()
        G.add_edge(
            u, v,
            transactions=tx_list,
            total_amount=total_amt,
            tx_count=len(tx_list),
            earliest=txs["block_time"].iloc[0],
            latest=txs["block_time"].iloc[-1],
        )

    return G, out_count


# ---------------------------------------------------------------------------
# Cycle Analysis Helpers
# ---------------------------------------------------------------------------

def _cycle_edges(cycle: List[str], G: nx.DiGraph) -> List[dict]:
    """Return the edge data dicts for consecutive nodes in *cycle* (wrapping)."""
    edges = []
    n = len(cycle)
    for i in range(n):
        u, v = cycle[i], cycle[(i + 1) % n]
        edata = G.edges[u, v]
        edges.append({"u": u, "v": v, **edata})
    return edges


def _check_temporal_order(edges: List[dict]) -> bool:
    """Return True if edge *latest* times are strictly increasing around the cycle."""
    times = [e["latest"] for e in edges]
    return all(times[i] < times[i + 1] for i in range(len(times) - 1))


def _compute_time_span_hours(edges: List[dict]) -> float:
    """Compute hours between earliest tx and latest tx across all edges."""
    all_earliest = [e["earliest"] for e in edges]
    all_latest = [e["latest"] for e in edges]
    first = min(all_earliest)
    last = max(all_latest)
    return (last - first).total_seconds() / 3600.0


def _compute_net_positions(
    cycle: List[str], edges: List[dict],
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    For each node v in *cycle*, compute:
      in_v  = sum of amounts on edges coming INTO v
      out_v = sum of amounts on edges going OUT of v
    Returns (abs_positions, score_positions):
      abs_positions[v]  = |in_v - out_v|
      score_positions[v] = |in_v - out_v| / (in_v + out_v)  (0 if denom==0)
    """
    in_amt: Dict[str, float] = defaultdict(float)
    out_amt: Dict[str, float] = defaultdict(float)
    for e in edges:
        out_amt[e["u"]] += e["total_amount"]
        in_amt[e["v"]] += e["total_amount"]

    abs_pos: Dict[str, float] = {}
    score_pos: Dict[str, float] = {}
    for v in cycle:
        iv = in_amt.get(v, 0.0)
        ov = out_amt.get(v, 0.0)
        abs_pos[v] = abs(iv - ov)
        denom = iv + ov
        score_pos[v] = abs(iv - ov) / denom if denom > 0 else 0.0

    return abs_pos, score_pos


def _compute_amount_similarity(edges: List[dict]) -> float:
    """min(total_amount) / max(total_amount) across edges. 1.0 = perfect match."""
    amounts = [e["total_amount"] for e in edges]
    if not amounts:
        return 0.0
    mx = max(amounts)
    if mx == 0:
        return 0.0
    return min(amounts) / mx


def _compute_tx_frequency(
    cycle: List[str], edges: List[dict], out_count: Dict[str, int],
) -> float:
    """Min of num(a,b)/num(a) across edges (a→b) in the cycle."""
    freqs = []
    for e in edges:
        total_out = out_count.get(e["u"], 0)
        if total_out == 0:
            freqs.append(0.0)
        else:
            freqs.append(e["tx_count"] / total_out)
    return min(freqs) if freqs else 0.0


# ---------------------------------------------------------------------------
# Main Processing
# ---------------------------------------------------------------------------

def process_wash_trading_collusion(
    params: WashTradingCollusionParams,
    df: pd.DataFrame,
    target_users: Optional[Set[str]],
    time_start: Optional[datetime],
    time_end: Optional[datetime],
) -> List[CollusionLoopHit]:
    """
    Detect wash-trading colluding groups by finding cycles in the
    transfer graph that satisfy all parameter thresholds.
    """
    if not params.enable:
        return []

    print("[fraudulent] Building transfer graph …")
    t0 = _time.time()

    # Determine effective time window
    # If time_start/end not given, use full range but cap by time_window
    if time_start is None:
        time_start = df["block_time"].min()
    if time_end is None:
        time_end = df["block_time"].max()

    # Further restrict by time_window (hours) relative to time_end
    window_start = time_end - timedelta(hours=params.time_window)
    if window_start > time_start:
        time_start = window_start

    G, out_count = _build_transfer_graph(df, target_users, time_start, time_end)
    print(f"[fraudulent] Graph built: {G.number_of_nodes()} nodes, "
          f"{G.number_of_edges()} edges  ({_time.time() - t0:.2f}s)")

    if G.number_of_nodes() == 0:
        return []

    # --- Cycle detection ---
    # nx.simple_cycles returns all simple cycles.
    # For large graphs we limit the search to keep it tractable.
    print("[fraudulent] Finding cycles …")
    t1 = _time.time()

    MAX_CYCLES = 50_000  # safety cap
    hits: List[CollusionLoopHit] = []
    loop_counter = 0
    checked = 0

    for cycle in nx.simple_cycles(G):
        checked += 1
        if checked > MAX_CYCLES:
            print(f"[fraudulent] Reached {MAX_CYCLES} cycle cap, stopping search.")
            break

        # --- Filter: loop_size ---
        if len(cycle) < params.loop_size:
            continue

        # Gather edge data for this cycle
        try:
            edges = _cycle_edges(cycle, G)
        except KeyError:
            continue  # edge missing (shouldn't happen but be safe)

        # --- Filter: temporal order ---
        if params.require_temporal_order and not _check_temporal_order(edges):
            continue

        # --- Filter: time_span ---
        span_h = _compute_time_span_hours(edges)
        if span_h > params.time_span:
            continue

        # --- Filter: amount_similarity ---
        amt_sim = _compute_amount_similarity(edges)
        if amt_sim < params.amount_similarity:
            continue

        # --- Filter: net_position_abs and net_position_score ---
        abs_pos, score_pos = _compute_net_positions(cycle, edges)
        max_abs = max(abs_pos.values()) if abs_pos else 0.0
        if max_abs > params.net_position_abs:
            continue
        avg_score = (sum(score_pos.values()) / len(score_pos)) if score_pos else 0.0
        if avg_score > params.net_position_score:
            continue

        # --- Filter: tx_frequency ---
        min_freq = _compute_tx_frequency(cycle, edges, out_count)
        if min_freq < params.tx_frequency:
            continue

        # --- Filter: speed_score ---
        spd = 1.0 - (span_h / params.time_window) if params.time_window > 0 else 0.0
        spd = max(0.0, min(1.0, spd))
        if spd < params.speed_score:
            continue

        # --- Build hit ---
        loop_counter += 1
        total_vol = sum(e["total_amount"] for e in edges)

        hit = CollusionLoopHit(
            loop_id=f"loop_{loop_counter}",
            members=list(cycle),
            loop_size=len(cycle),
            edges=[
                CollusionLoopEdge(
                    source=e["u"],
                    target=e["v"],
                    total_amount=round(e["total_amount"], 4),
                    tx_count=e["tx_count"],
                    earliest_time=str(e["earliest"]),
                    latest_time=str(e["latest"]),
                )
                for e in edges
            ],
            time_span_hours=round(span_h, 4),
            speed_score=round(spd, 4),
            avg_amount_similarity=round(amt_sim, 4),
            avg_net_position_score=round(avg_score, 4),
            max_net_position_abs=round(max_abs, 4),
            total_volume=round(total_vol, 4),
            details={
                "per_node_net_abs": {k: round(v, 4) for k, v in abs_pos.items()},
                "per_node_net_score": {k: round(v, 4) for k, v in score_pos.items()},
                "min_tx_frequency": round(min_freq, 4),
            },
        )
        hits.append(hit)

    elapsed = _time.time() - t1
    print(f"[fraudulent] Cycle search done: checked {checked} cycles, "
          f"found {len(hits)} collusion loops  ({elapsed:.2f}s)")

    # Sort by total_volume descending (most suspicious first)
    hits.sort(key=lambda h: h.total_volume, reverse=True)
    return hits


# ---------------------------------------------------------------------------
# API Endpoint
# ---------------------------------------------------------------------------

@router.post("/detect", response_model=FraudulentActivityResponse)
async def detect_fraudulent_activity(request: FraudulentActivityRequest):
    """
    Detect fraudulent activity (wash-trading collusion groups).

    Analyses the transfer graph to find cycles of token flow where
    participants exchange tokens in a circular pattern — a hallmark
    of wash-trading collusion.
    """
    print("[fraudulent] === Fraudulent-Activity Detection Request ===")
    t_start = _time.time()

    # Load data
    df = _load_transfers()

    # Parse time range
    time_start: Optional[datetime] = None
    time_end: Optional[datetime] = None
    if request.time_range:
        if "start" in request.time_range and request.time_range["start"]:
            time_start = pd.to_datetime(request.time_range["start"], utc=True)
        if "end" in request.time_range and request.time_range["end"]:
            time_end = pd.to_datetime(request.time_range["end"], utc=True)

    target_set: Optional[Set[str]] = None
    if request.target_users:
        target_set = set(request.target_users)

    # Default params if not provided
    params = request.wash_trading_collusion or WashTradingCollusionParams()

    collusion_loops: List[CollusionLoopHit] = []

    if params.enable:
        collusion_loops = process_wash_trading_collusion(
            params=params,
            df=df,
            target_users=target_set,
            time_start=time_start,
            time_end=time_end,
        )

    elapsed = _time.time() - t_start
    print(f"[fraudulent] Total elapsed: {elapsed:.2f}s  "
          f"loops={len(collusion_loops)}")

    # Gather unique members across all loops
    all_members: Set[str] = set()
    for loop in collusion_loops:
        all_members.update(loop.members)

    return FraudulentActivityResponse(
        status="success",
        collusion_loops=collusion_loops,
        metadata={
            "total_loops": len(collusion_loops),
            "unique_addresses_involved": len(all_members),
            "elapsed_seconds": round(elapsed, 2),
            "params": params.dict(),
        },
    )