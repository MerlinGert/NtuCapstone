"""
Manipulation Detection Backend
  Rule 1  – Wash Trading: Matched Buy/Sell Roundtrip
  Rule 2  – Pump & Dump: Coordinated Trading-Driven Price Move
"""

import bisect
import csv
import math
import os
import threading
import time as _time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter(
    prefix="/api/manipulation_v2",
    tags=["manipulation_detection"],
    responses={404: {"description": "Not found"}},
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADE_CSV = os.path.join(BASE_DIR, "public", "ACT-24-11-10.csv")

csv.field_size_limit(2**31 - 1)

# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class WashTradingParams(BaseModel):
    """Rule 1: Matched Buy/Sell Roundtrip (Wash Trading)"""
    enable: bool = True
    time_window: float = Field(default=24.0, gt=0, description="Sliding window in hours")
    min_tx_number: int = Field(default=4, ge=1, description="Min trades in window")
    alt_ratio: float = Field(default=0.6, gt=0, lt=1,
                             description="Direction alternation ratio = #direction-changes / (tx_count - 1)")
    net_position_score: float = Field(default=0.1, ge=0, le=1,
                                      description="Max |net_qty| / total_volume allowed")


class PumpDumpParams(BaseModel):
    """Rule 2: Coordinated Trading-Driven Price Move"""
    enable: bool = True
    time_window: float = Field(default=24.0, gt=0, description="Sliding window in hours")
    min_tx_number: int = Field(default=4, ge=1, description="Min trades per entity in window")
    alt_ratio: float = Field(default=0.3, gt=0, lt=1,
                             description="Max alternation ratio (low = mostly one direction)")
    min_entity_number: int = Field(default=3, ge=1, description="Min coordinated entities")
    price_trend: str = Field(default="up", description="up | down")
    price_ratio: float = Field(default=0.05, gt=0, lt=1,
                               description="Min price change ratio within window")


class ManipulationDetectionRequest(BaseModel):
    target_users: Optional[List[str]] = Field(None, description="Addresses to analyse. None = all.")
    time_range: Optional[Dict[str, str]] = Field(None, description="{'start': ..., 'end': ...}")
    wash_trading: Optional[WashTradingParams] = None
    pump_dump: Optional[PumpDumpParams] = None


class WashTradingHit(BaseModel):
    trader_id: str
    window_start: str
    window_end: str
    tx_count: int
    buy_count: int
    sell_count: int
    alt_ratio: float
    net_position_score: float
    total_volume: float
    net_qty: float
    details: Dict[str, Any] = {}


class PumpDumpHit(BaseModel):
    window_start: str
    window_end: str
    entity_count: int
    entities: List[str]
    dominant_direction: str
    avg_alt_ratio: float
    price_start: float
    price_end: float
    price_change_ratio: float
    total_volume: float
    details: Dict[str, Any] = {}


class ManipulationDetectionResponse(BaseModel):
    status: str
    wash_trading_hits: List[WashTradingHit] = []
    pump_dump_hits: List[PumpDumpHit] = []
    metadata: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Data Loading (cached)
# ---------------------------------------------------------------------------
_trade_cache: Optional[pd.DataFrame] = None
_cache_lock = threading.Lock()


def _load_trades(time_range: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    global _trade_cache
    if _trade_cache is None:
        with _cache_lock:  # double-checked locking for thread safety
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
                # Parse block_time to datetime
                if "block_time" in _trade_cache.columns:
                    _trade_cache["block_time_dt"] = pd.to_datetime(
                        _trade_cache["block_time"], errors="coerce"
                    )
    df = _trade_cache.copy()
    if time_range:
        start_str = time_range.get("start")
        end_str = time_range.get("end")
        if start_str and "block_time_dt" in df.columns:
            start_dt = pd.to_datetime(start_str, errors="coerce")
            if pd.notna(start_dt):
                df = df[df["block_time_dt"] >= start_dt]
        if end_str and "block_time_dt" in df.columns:
            end_dt = pd.to_datetime(end_str, errors="coerce")
            if pd.notna(end_dt):
                df = df[df["block_time_dt"] <= end_dt]
    return df



# ---------------------------------------------------------------------------
# Helper: build per-trader event list
# ---------------------------------------------------------------------------

def _build_trader_events(
    df: pd.DataFrame,
    target_users: Optional[List[str]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Convert the trade DataFrame into a dict of trader_id -> sorted list of events.
    Each event: {action: 'buy'|'sell', amount: float, usd: float, time_dt: datetime, block_time: str}
    """
    if df.empty:
        return {}

    trader_col = "trader_id"
    if trader_col not in df.columns:
        return {}

    if target_users:
        df = df[df[trader_col].isin(set(target_users))]
    if df.empty:
        return {}

    events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for _, row in df.iterrows():
        trader = str(row.get(trader_col, ""))
        if not trader:
            continue

        bought_sym = str(row.get("token_bought_symbol", ""))
        sold_sym = str(row.get("token_sold_symbol", ""))
        bought_amt = float(row.get("token_bought_amount", 0))
        sold_amt = float(row.get("token_sold_amount", 0))
        usd = float(row.get("amount_usd", 0))
        time_dt = row.get("block_time_dt", pd.NaT)
        block_time = str(row.get("block_time", ""))

        if bought_sym == "ACT" and bought_amt > 0:
            events[trader].append({
                "action": "buy",
                "amount": bought_amt,
                "usd": usd,
                "price": usd / bought_amt if bought_amt > 0 else 0,
                "time_dt": time_dt,
                "block_time": block_time,
            })
        elif sold_sym == "ACT" and sold_amt > 0:
            events[trader].append({
                "action": "sell",
                "amount": sold_amt,
                "usd": usd,
                "price": usd / sold_amt if sold_amt > 0 else 0,
                "time_dt": time_dt,
                "block_time": block_time,
            })

    # Sort each trader's events by time
    for trader in events:
        events[trader].sort(key=lambda e: e["time_dt"] if pd.notna(e["time_dt"]) else datetime.min)

    return dict(events)


# ---------------------------------------------------------------------------
# Helper: build global price timeline for price lookups
# ---------------------------------------------------------------------------

def _build_price_timeline(df: pd.DataFrame) -> Tuple[List[datetime], List[float]]:
    """
    Build sorted (time, price) arrays from ACT trades for price estimation.
    """
    if df.empty or "block_time_dt" not in df.columns:
        return [], []

    act_mask = (
        (df["token_bought_symbol"] == "ACT") | (df["token_sold_symbol"] == "ACT")
    )
    act_df = df[act_mask].copy()

    def _calc_price(row):
        usd = float(row["amount_usd"])
        if str(row["token_bought_symbol"]) == "ACT":
            amt = float(row["token_bought_amount"])
        else:
            amt = float(row["token_sold_amount"])
        return usd / amt if amt > 0 else 0.0

    act_df["_price"] = act_df.apply(_calc_price, axis=1)
    act_df = act_df[act_df["_price"] > 0].dropna(subset=["block_time_dt"])
    act_df = act_df.sort_values("block_time_dt")

    return act_df["block_time_dt"].tolist(), act_df["_price"].tolist()


def _lookup_price(
    price_times: List[datetime],
    price_values: List[float],
    t: datetime,
) -> float:
    """Return estimated price at time *t* via nearest-neighbour lookup."""
    if not price_times:
        return 0.0
    idx = bisect.bisect_left(price_times, t)
    if idx == 0:
        return price_values[0]
    if idx >= len(price_times):
        return price_values[-1]
    before = price_times[idx - 1]
    after = price_times[idx]
    if abs((t - before).total_seconds()) <= abs((after - t).total_seconds()):
        return price_values[idx - 1]
    return price_values[idx]


# ===================================================================
# Rule 1: Wash Trading – Matched Buy/Sell Roundtrip
# ===================================================================

def _calc_alternation_ratio(actions: List[str]) -> float:
    """
    Direction alternation ratio = number of direction changes / (len - 1).
    A high ratio means the trader keeps switching buy/sell.
    """
    if len(actions) < 2:
        return 0.0
    changes = sum(1 for i in range(1, len(actions)) if actions[i] != actions[i - 1])
    return changes / (len(actions) - 1)


def _calc_net_position_score(events_in_window: List[Dict]) -> Tuple[float, float, float]:
    """
    Returns (net_position_score, total_volume, net_qty).
    net_qty = sum(buy_amounts) - sum(sell_amounts)
    total_volume = sum(all amounts)
    net_position_score = |net_qty| / total_volume   (0 = perfectly balanced)
    """
    buy_vol = sum(e["amount"] for e in events_in_window if e["action"] == "buy")
    sell_vol = sum(e["amount"] for e in events_in_window if e["action"] == "sell")
    total = buy_vol + sell_vol
    net = buy_vol - sell_vol
    if total == 0:
        return 0.0, 0.0, 0.0
    return abs(net) / total, total, net


def process_wash_trading(
    trader_events: Dict[str, List[Dict[str, Any]]],
    params: WashTradingParams,
) -> List[WashTradingHit]:
    """
    Rule 1 – Wash Trading: Matched Buy/Sell Roundtrip.

    For each trader, slide a window of `time_window` hours across their trade
    timeline. In each window check:
      1. tx_count >= min_tx_number
      2. alternation_ratio >= alt_ratio   (frequent direction switches)
      3. net_position_score <= net_position_score   (close to zero net)
    """
    hits: List[WashTradingHit] = []
    window_td = timedelta(hours=params.time_window)

    for trader, events in trader_events.items():
        if len(events) < params.min_tx_number:
            continue

        n = len(events)
        left = 0

        for right in range(n):
            # Expand right edge; shrink left edge so window fits
            while left < right:
                t_left = events[left].get("time_dt")
                t_right = events[right].get("time_dt")
                if pd.isna(t_left) or pd.isna(t_right):
                    break
                if (t_right - t_left) <= window_td:
                    break
                left += 1

            window_events = events[left: right + 1]
            tx_count = len(window_events)
            if tx_count < params.min_tx_number:
                continue

            actions = [e["action"] for e in window_events]
            alt_r = _calc_alternation_ratio(actions)
            if alt_r < params.alt_ratio:
                continue

            nps, total_vol, net_qty = _calc_net_position_score(window_events)
            if nps > params.net_position_score:
                continue

            buy_count = sum(1 for a in actions if a == "buy")
            sell_count = tx_count - buy_count

            w_start = events[left].get("block_time", "")
            w_end = events[right].get("block_time", "")

            hits.append(WashTradingHit(
                trader_id=trader,
                window_start=str(w_start),
                window_end=str(w_end),
                tx_count=tx_count,
                buy_count=buy_count,
                sell_count=sell_count,
                alt_ratio=round(alt_r, 4),
                net_position_score=round(nps, 4),
                total_volume=round(total_vol, 4),
                net_qty=round(net_qty, 4),
            ))

            # Skip ahead to avoid near-duplicate overlapping windows
            left = right + 1

    return hits


# ===================================================================
# Rule 2: Pump & Dump – Coordinated Trading-Driven Price Move
# ===================================================================

def process_pump_dump(
    trader_events: Dict[str, List[Dict[str, Any]]],
    params: PumpDumpParams,
    price_times: List[datetime],
    price_values: List[float],
) -> List[PumpDumpHit]:
    """
    Rule 2 – Pump & Dump: Coordinated Trading-Driven Price Move.

    Approach:
    1. Build a global timeline of all trade events sorted by time.
    2. Slide a window of `time_window` hours.
    3. Within each window, group events by trader. Keep only traders whose
       alt_ratio <= params.alt_ratio (mostly one-directional, i.e. mostly
       buying or mostly selling).
    4. If the number of qualifying entities >= min_entity_number,
       compute window price change.
    5. If price_change_ratio >= price_ratio and direction matches price_trend,
       record a PumpDumpHit.
    """
    hits: List[PumpDumpHit] = []
    window_td = timedelta(hours=params.time_window)

    if not price_times:
        return hits

    # Flatten all events into a single sorted list with trader info
    all_events: List[Tuple[datetime, str, Dict]] = []
    for trader, events in trader_events.items():
        for e in events:
            t_dt = e.get("time_dt")
            if pd.notna(t_dt):
                all_events.append((t_dt, trader, e))

    if not all_events:
        return hits

    all_events.sort(key=lambda x: x[0])
    n = len(all_events)

    # Use a step-based approach: advance window start by chunks to avoid O(n²)
    # We use discrete window anchors at each unique event time
    seen_windows: set = set()  # Track (window_start_idx) to avoid exact duplicates
    left = 0
    prev_left = -1

    for right in range(n):
        # Shrink left edge to fit window
        while left < right:
            if (all_events[right][0] - all_events[left][0]) > window_td:
                left += 1
            else:
                break

        # Always evaluate when the window start shifts (left moved), so boundary
        # transitions are never skipped; also sample at regular intervals.
        step = max(1, n // 200)
        if left == prev_left and right % step != 0 and right != n - 1:
            continue
        prev_left = left

        window_slice = all_events[left: right + 1]
        if len(window_slice) < params.min_tx_number:
            continue

        # Group by trader within this window
        trader_window: Dict[str, List[Dict]] = defaultdict(list)
        for _, trader, evt in window_slice:
            trader_window[trader].append(evt)

        # Filter traders: need min_tx_number trades and low alt_ratio
        qualifying_traders: List[Tuple[str, str, float, float]] = []
        # Each entry: (trader, dominant_dir, alt_ratio, volume)

        for trader, tevts in trader_window.items():
            if len(tevts) < params.min_tx_number:
                continue
            actions = [e["action"] for e in tevts]
            alt_r = _calc_alternation_ratio(actions)
            if alt_r > params.alt_ratio:
                # High alternation = not one-directional, skip
                continue
            buy_c = sum(1 for a in actions if a == "buy")
            sell_c = len(actions) - buy_c
            dominant = "buy" if buy_c >= sell_c else "sell"
            vol = sum(e["amount"] for e in tevts)
            qualifying_traders.append((trader, dominant, alt_r, vol))

        if len(qualifying_traders) < params.min_entity_number:
            continue

        # Check dominant direction consensus
        buy_entities = sum(1 for _, d, _, _ in qualifying_traders if d == "buy")
        sell_entities = len(qualifying_traders) - buy_entities
        if buy_entities >= sell_entities:
            group_direction = "buy"
        else:
            group_direction = "sell"

        # Check price trend match
        expected_trend = params.price_trend.lower()
        if expected_trend == "up" and group_direction != "buy":
            continue
        if expected_trend == "down" and group_direction != "sell":
            continue

        # Compute price change within window
        w_start_time = all_events[left][0]
        w_end_time = all_events[right][0]

        p_start = _lookup_price(price_times, price_values, w_start_time)
        p_end = _lookup_price(price_times, price_values, w_end_time)

        if p_start <= 0:
            continue

        price_change_ratio = (p_end - p_start) / p_start

        # Verify direction and magnitude
        if expected_trend == "up" and price_change_ratio < params.price_ratio:
            continue
        if expected_trend == "down" and price_change_ratio > -params.price_ratio:
            continue

        avg_alt = sum(ar for _, _, ar, _ in qualifying_traders) / len(qualifying_traders)
        total_vol = sum(v for _, _, _, v in qualifying_traders)

        # Dedup key based on window bounds (rounded to minutes)
        dedup_key = (
            w_start_time.strftime("%Y-%m-%d %H:%M"),
            w_end_time.strftime("%Y-%m-%d %H:%M"),
        )
        if dedup_key in seen_windows:
            continue
        seen_windows.add(dedup_key)

        hits.append(PumpDumpHit(
            window_start=str(all_events[left][2].get("block_time", "")),
            window_end=str(all_events[right][2].get("block_time", "")),
            entity_count=len(qualifying_traders),
            entities=[t[0] for t in qualifying_traders],
            dominant_direction=group_direction,
            avg_alt_ratio=round(avg_alt, 4),
            price_start=round(p_start, 8),
            price_end=round(p_end, 8),
            price_change_ratio=round(abs(price_change_ratio), 4),
            total_volume=round(total_vol, 4),
        ))

    return hits


# ===================================================================
# API Endpoint
# ===================================================================

@router.post("/detect", response_model=ManipulationDetectionResponse)
async def detect_manipulation_v2(request: ManipulationDetectionRequest):
    """
    Run manipulation detection.
    Accepts Rule1 (Wash Trading) and Rule2 (Pump & Dump) parameters.
    Returns detected hits with metadata.
    """
    try:
        start = _time.time()

        # Load trade data once
        df = _load_trades(request.time_range)
        if df.empty:
            return ManipulationDetectionResponse(
                status="success",
                wash_trading_hits=[],
                pump_dump_hits=[],
                metadata={"error": "No trade data found"},
            )

        # Build per-trader events
        trader_events = _build_trader_events(df, request.target_users)

        wash_hits: List[WashTradingHit] = []
        pd_hits: List[PumpDumpHit] = []

        # Rule 1 – Wash Trading
        if request.wash_trading and request.wash_trading.enable:
            wash_hits = process_wash_trading(trader_events, request.wash_trading)

        # Rule 2 – Pump & Dump
        if request.pump_dump and request.pump_dump.enable:
            price_times, price_values = _build_price_timeline(df)
            pd_hits = process_pump_dump(
                trader_events, request.pump_dump, price_times, price_values,
            )

        elapsed = _time.time() - start

        return ManipulationDetectionResponse(
            status="success",
            wash_trading_hits=wash_hits,
            pump_dump_hits=pd_hits,
            metadata={
                "execution_time_seconds": round(elapsed, 3),
                "total_traders_analysed": len(trader_events),
                "wash_trading_hit_count": len(wash_hits),
                "pump_dump_hit_count": len(pd_hits),
                "rules_applied": {
                    "wash_trading": bool(request.wash_trading and request.wash_trading.enable),
                    "pump_dump": bool(request.pump_dump and request.pump_dump.enable),
                },
            },
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))