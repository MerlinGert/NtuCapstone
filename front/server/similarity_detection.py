"""
Behavior-Similarity-Based Entity Detection Rules:
  Rule3: Similar Trading Sequence
  Rule4: Similar Balance Sequence
  Rule5: Similar Earning Sequence
"""

import os
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from itertools import combinations
from datetime import datetime, timedelta

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BALANCE_SNAPSHOTS_CSV = os.path.join(BASE_DIR, "public", "processed", "transfers", "balance_snapshots.csv")
HOURLY_SNAPSHOTS_JSON = os.path.join(BASE_DIR, "public", "processed", "transfers", "hourly_balance_snapshots.json")
ACT_OHLC_JSON = os.path.join(BASE_DIR, "public", "ACT_OHLC.json")

# --- Limits ---
MAX_USERS_RULE3 = 5000       # max users when target_users is explicitly specified
MAX_USERS_RULE3_AUTO = 200   # max users when target_users=None (fallback only; frontend always sends explicit list)
MAX_SEQ_LEN_RULE3 = 300      # truncate sequences to this length before DP
MAX_CANDIDATE_PAIRS = 100000 # cap on n-gram candidate pairs

# --- Caches ---
_balance_df_cache = None
_hourly_snapshots_cache = None
_ohlc_cache = None


def _load_balance_df() -> pd.DataFrame:
    """Load and cache balance_snapshots.csv."""
    global _balance_df_cache
    if _balance_df_cache is None:
        if not os.path.exists(BALANCE_SNAPSHOTS_CSV):
            return pd.DataFrame()
        df = pd.read_csv(BALANCE_SNAPSHOTS_CSV)
        df['time'] = pd.to_datetime(df['time'].str.replace(' UTC', '', regex=False), utc=True)
        _balance_df_cache = df
    return _balance_df_cache


def _load_hourly_snapshots() -> list:
    """Load and cache hourly_balance_snapshots.json."""
    global _hourly_snapshots_cache
    if _hourly_snapshots_cache is None:
        if not os.path.exists(HOURLY_SNAPSHOTS_JSON):
            return []
        with open(HOURLY_SNAPSHOTS_JSON, 'r') as f:
            _hourly_snapshots_cache = json.load(f)
    return _hourly_snapshots_cache


# Cached dict {"YYYY-MM-DD HH:00:00": price} for O(1) OHLC lookups
_ohlc_price_dict_cache: Optional[Dict[str, float]] = None


def _load_ohlc() -> dict:
    """Load and cache ACT OHLC price data."""
    global _ohlc_cache
    if _ohlc_cache is None:
        if not os.path.exists(ACT_OHLC_JSON):
            return {}
        with open(ACT_OHLC_JSON, 'r') as f:
            _ohlc_cache = json.load(f)
    return _ohlc_cache


def _get_ohlc_price_dict() -> Dict[str, float]:
    """Return a flat {time_str: price} dict built from 1H OHLC (cached)."""
    global _ohlc_price_dict_cache
    if _ohlc_price_dict_cache is None:
        ohlc = _load_ohlc()
        _ohlc_price_dict_cache = {
            c['t']: float(c['c']) for c in ohlc.get('1H', [])
        }
    return _ohlc_price_dict_cache


def _get_price_at_time(timestamp: pd.Timestamp, price_dict: Dict[str, float]) -> float:
    """O(1) price lookup by truncating timestamp to hour."""
    if not price_dict:
        return 0.0
    ts_str = timestamp.strftime("%Y-%m-%d %H:00:00")
    return price_dict.get(ts_str, 0.0)


def _pearson_correlation(a: np.ndarray, b: np.ndarray) -> float:
    """Compute Pearson correlation between two arrays. Returns 0 if undefined."""
    if len(a) < 2 or len(b) < 2 or len(a) != len(b):
        return 0.0
    std_a, std_b = np.std(a), np.std(b)
    if std_a < 1e-12 or std_b < 1e-12:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


# ===========================================================================
# Rule 3: Similar Trading Sequence
# ===========================================================================

def _extract_trading_sequences(
    df: pd.DataFrame,
    target_users: Optional[List[str]],
    time_window: Optional[Dict[str, str]],
    need_price: bool = False,
    need_amount: bool = True,
) -> Dict[str, List[Dict]]:
    """
    Extract trading event sequences from balance_snapshots.csv.
    Each event: {action, amount?, price?}

    Optimizations:
    - Uses itertuples() instead of iterrows() (~5-10x faster).
    - Skips price lookup entirely when need_price=False (action_only / action+amount).
    - Price lookup is O(1) via pre-built dict instead of O(OHLC_len) scan.
    """
    filtered = df

    if time_window:
        if time_window.get("start"):
            start = pd.to_datetime(time_window["start"], utc=True)
            filtered = filtered[filtered['time'] >= start]
        if time_window.get("end"):
            end = pd.to_datetime(time_window["end"], utc=True)
            filtered = filtered[filtered['time'] <= end]

    if target_users:
        filtered = filtered[filtered['owner_address'].isin(set(target_users))]

    price_dict: Dict[str, float] = _get_ohlc_price_dict() if need_price else {}

    sequences: Dict[str, List[Dict]] = {}
    for row in filtered.itertuples(index=False):
        addr = row.owner_address
        change = float(row.change_amount)
        reason = str(row.reason)

        # Determine action
        if 'Bought' in reason or 'buy' in reason.lower():
            action = 'buy'
        elif 'Sold' in reason or 'sell' in reason.lower():
            action = 'sell'
        elif change > 0:
            action = 'transfer_in'
        else:
            action = 'transfer_out'

        event: Dict[str, Any] = {'action': action}
        if need_amount:
            event['amount'] = abs(change)
        if need_price:
            event['price'] = _get_price_at_time(row.time, price_dict)

        if addr not in sequences:
            sequences[addr] = []
        sequences[addr].append(event)

    return sequences


def _encode_sequence(events: List[Dict], representation: str) -> List[tuple]:
    """
    Encode a list of trading events into a comparable sequence based on representation mode.
    representation: 'action_only' | 'action+amount' | 'action+price' | 'action+amount+price'
    """
    encoded = []
    for e in events:
        if representation == 'action_only':
            encoded.append((e['action'],))
        elif representation == 'action+amount':
            encoded.append((e['action'], e['amount']))
        elif representation == 'action+price':
            encoded.append((e['action'], e['price']))
        elif representation == 'action+amount+price':
            encoded.append((e['action'], e['amount'], e['price']))
        else:
            encoded.append((e['action'],))
    return encoded


def _longest_contiguous_match(
    seq_a: List[tuple],
    seq_b: List[tuple],
    representation: str,
    amount_sim: float,
    price_sim: float,
    direction_mode: str,
) -> int:
    """
    Find the longest contiguous subsequence match between two encoded sequences.
    Uses a sliding-window approach.
    direction_mode: 'same_side_only' | 'mixed_allowed'
    """
    if not seq_a or not seq_b:
        return 0

    def items_match(a: tuple, b: tuple) -> bool:
        # Action must match
        if direction_mode == 'same_side_only':
            if a[0] != b[0]:
                return False
        else:  # mixed_allowed: buy matches sell relative pattern
            action_a = a[0].replace('transfer_in', 'buy').replace('transfer_out', 'sell')
            action_b = b[0].replace('transfer_in', 'buy').replace('transfer_out', 'sell')
            if action_a != action_b:
                return False

        idx = 1
        if 'amount' in representation:
            if len(a) > idx and len(b) > idx:
                max_amt = max(a[idx], b[idx], 1e-12)
                if abs(a[idx] - b[idx]) / max_amt > (1 - amount_sim):
                    return False
            idx += 1
        if 'price' in representation:
            if len(a) > idx and len(b) > idx:
                max_prc = max(a[idx], b[idx], 1e-12)
                if abs(a[idx] - b[idx]) / max_prc > (1 - price_sim):
                    return False
        return True

    # Dynamic programming approach for longest common contiguous subsequence
    max_len = 0
    n, m = len(seq_a), len(seq_b)
    # Use rolling row to save memory
    prev = [0] * (m + 1)
    for i in range(1, n + 1):
        curr = [0] * (m + 1)
        for j in range(1, m + 1):
            if items_match(seq_a[i - 1], seq_b[j - 1]):
                curr[j] = prev[j - 1] + 1
                if curr[j] > max_len:
                    max_len = curr[j]
            else:
                curr[j] = 0
        prev = curr
    return max_len


# Action-to-int mapping for fast numpy LCCS
_ACTION_INT = {'buy': 1, 'sell': 2, 'transfer_in': 3, 'transfer_out': 4}


def _lccs_action_only_numpy(a_tuples: List[tuple], b_tuples: List[tuple]) -> int:
    """
    Optimized LCCS for action_only mode using numpy vectorization.
    Replaces the inner Python loop with numpy row operations — ~20x faster.
    """
    a = np.array([_ACTION_INT.get(t[0], 0) for t in a_tuples], dtype=np.int16)
    b = np.array([_ACTION_INT.get(t[0], 0) for t in b_tuples], dtype=np.int16)
    n, m = len(a), len(b)
    max_len = 0
    prev = np.zeros(m + 1, dtype=np.int32)
    for i in range(n):
        curr = np.zeros(m + 1, dtype=np.int32)
        matches = (b == a[i])          # shape (m,) boolean
        curr[1:] = np.where(matches, prev[:m] + 1, 0)
        local_max = int(curr.max())
        if local_max > max_len:
            max_len = local_max
        prev = curr
    return max_len


def rule3_similar_trading_sequence(
    target_users: Optional[List[str]],
    time_window: Optional[Dict[str, str]],
    direction_mode: str = "same_side_only",
    sequence_representation: str = "action_only",
    min_contiguous_length: int = 3,
    amount_similarity: float = 0.8,
    price_similarity: float = 0.8,
) -> List[Dict[str, Any]]:
    """
    Rule3: Find pairs of addresses with similar trading action sequences.

    Optimizations applied:
    1. User cap: if target_users is unspecified or too large, keep only the top
       MAX_USERS_RULE3 addresses by transaction count to bound pairwise complexity.
    2. Sequence truncation: sequences are capped at MAX_SEQ_LEN_RULE3 events so
       the O(m×n) DP per pair stays manageable.
    3. n-gram inverted index (action_only mode): builds a {n-gram → [addr]} index
       from the first `min_contiguous_length` action tokens and only runs the full
       DP on pairs that share at least one common n-gram.  For richer representation
       modes the index is skipped (fewer users typically specified explicitly).

    Returns list of {source, target, similarity_score, match_length, details}.
    """
    df = _load_balance_df()
    if df.empty:
        return []

    # --- 1. User cap ---
    if not target_users:
        # Pick top-N users by transaction count (stricter limit for auto mode)
        top_users = (
            df['owner_address'].value_counts()
            .head(MAX_USERS_RULE3_AUTO)
            .index.tolist()
        )
        effective_users: Optional[List[str]] = top_users
    elif len(target_users) > MAX_USERS_RULE3:
        # Caller specified too many users — keep those with most transactions
        counts = df[df['owner_address'].isin(set(target_users))]['owner_address'].value_counts()
        effective_users = counts.head(MAX_USERS_RULE3).index.tolist()
    else:
        effective_users = target_users

    need_price = 'price' in sequence_representation
    need_amount = 'amount' in sequence_representation
    sequences = _extract_trading_sequences(
        df, effective_users, time_window,
        need_price=need_price,
        need_amount=need_amount,
    )
    if len(sequences) < 2:
        return []

    # --- 2. Encode + truncate ---
    encoded: Dict[str, List[tuple]] = {}
    for addr, events in sequences.items():
        enc = _encode_sequence(events, sequence_representation)
        if len(enc) < min_contiguous_length:
            continue
        # Truncate to keep DP fast
        if len(enc) > MAX_SEQ_LEN_RULE3:
            enc = enc[:MAX_SEQ_LEN_RULE3]
        encoded[addr] = enc

    if len(encoded) < 2:
        return []

    addrs = list(encoded.keys())

    # --- 3. n-gram inverted index pre-filter (action-only mode) ---
    # For action_only we can build an exact n-gram index cheaply because each
    # element is a 1-tuple of a string — hashable and small.
    use_ngram_index = (sequence_representation == 'action_only')

    if use_ngram_index:
        ngram_len = min_contiguous_length
        # Build inverted index: tuple(n-gram) → set of addr indices
        ngram_to_addrs: Dict[tuple, List[int]] = {}
        for i, addr in enumerate(addrs):
            seq = encoded[addr]
            seen_ngrams: set = set()
            for k in range(len(seq) - ngram_len + 1):
                ng = tuple(seq[k: k + ngram_len])
                if ng not in seen_ngrams:
                    seen_ngrams.add(ng)
                    ngram_to_addrs.setdefault(ng, []).append(i)

        # Collect candidate pairs that share at least one n-gram
        candidate_pairs: set = set()
        for addr_list in ngram_to_addrs.values():
            if len(addr_list) < 2:
                continue
            # Guard: if a single n-gram matches too many addresses (very common
            # pattern like all-transfer_in), cap to avoid quadratic explosion
            if len(addr_list) > 200:
                addr_list = addr_list[:200]
            for pi in range(len(addr_list)):
                for pj in range(pi + 1, len(addr_list)):
                    a_i, b_i = addr_list[pi], addr_list[pj]
                    if a_i > b_i:
                        a_i, b_i = b_i, a_i
                    candidate_pairs.add((a_i, b_i))
                    if len(candidate_pairs) >= MAX_CANDIDATE_PAIRS:
                        break
                if len(candidate_pairs) >= MAX_CANDIDATE_PAIRS:
                    break
            if len(candidate_pairs) >= MAX_CANDIDATE_PAIRS:
                break

        pairs_to_check = list(candidate_pairs)
    else:
        # Full pairwise — only safe when target_users is small (already capped)
        pairs_to_check = [
            (i, j)
            for i in range(len(addrs))
            for j in range(i + 1, len(addrs))
        ]

    # --- 4. Run DP on candidate pairs ---
    # For action_only mode use the numpy-vectorized fast path (~20x faster).
    use_numpy_lccs = (sequence_representation == 'action_only' and direction_mode == 'same_side_only')
    results = []
    for i, j in pairs_to_check:
        a, b = addrs[i], addrs[j]
        if use_numpy_lccs:
            match_len = _lccs_action_only_numpy(encoded[a], encoded[b])
        else:
            match_len = _longest_contiguous_match(
                encoded[a], encoded[b],
                sequence_representation, amount_similarity, price_similarity,
                direction_mode,
            )
        if match_len >= min_contiguous_length:
            max_len = max(len(encoded[a]), len(encoded[b]))
            score = match_len / max_len if max_len > 0 else 0
            results.append({
                "source": a,
                "target": b,
                "similarity_score": round(score, 4),
                "match_length": match_len,
                "details": {
                    "rule": "similar_trading_sequence",
                    "direction_mode": direction_mode,
                    "representation": sequence_representation,
                    "seq_len_a": len(encoded[a]),
                    "seq_len_b": len(encoded[b]),
                }
            })

    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return results


# ===========================================================================
# Rule 4: Similar Balance Sequence
# ===========================================================================

def _build_balance_series_time_grid(
    target_users: Optional[List[str]],
    time_window: Optional[Dict[str, str]],
    time_bin: str = "1h",
) -> Dict[str, np.ndarray]:
    """
    Build balance time series for each address using hourly snapshots (time_grid mode).
    time_bin: '5m', '1h', '1d' — currently only '1h' is directly supported from data.
    """
    snapshots = _load_hourly_snapshots()
    if not snapshots:
        return {}

    # Parse time filters
    start_ts = None
    end_ts = None
    if time_window:
        if time_window.get("start"):
            start_ts = pd.to_datetime(time_window["start"])
        if time_window.get("end"):
            end_ts = pd.to_datetime(time_window["end"])

    target_set = set(target_users) if target_users else None

    # Collect balance series: {addr: {time_idx: balance}}
    addr_balances: Dict[str, Dict[int, float]] = {}
    valid_indices = []

    for idx, snap in enumerate(snapshots):
        snap_time = pd.to_datetime(snap.get("time", "").replace(" UTC", ""))
        if start_ts and snap_time < start_ts:
            continue
        if end_ts and snap_time > end_ts:
            continue

        valid_indices.append(idx)
        balances = snap.get("balances", {})
        # Merge all categories
        all_balances = {}
        for category in ["users", "contracts", "exchanges"]:
            all_balances.update(balances.get(category, {}))

        for addr, bal in all_balances.items():
            if target_set and addr not in target_set:
                continue
            if addr not in addr_balances:
                addr_balances[addr] = {}
            addr_balances[addr][len(valid_indices) - 1] = float(bal)

    if not valid_indices:
        return {}

    # Determine bin aggregation factor
    bin_factor = 1  # default 1h
    if time_bin == '1d':
        bin_factor = 24
    elif time_bin == '5m':
        bin_factor = 1  # unsupported, keep 1h

    n_bins = max(1, len(valid_indices) // bin_factor)

    # Convert to arrays
    result = {}
    for addr, bal_dict in addr_balances.items():
        arr = np.zeros(len(valid_indices))
        for time_idx, bal in bal_dict.items():
            if time_idx < len(arr):
                arr[time_idx] = bal
        # Forward-fill zeros (if address had balance before but no entry at this time)
        for k in range(1, len(arr)):
            if arr[k] == 0.0 and arr[k - 1] > 0:
                arr[k] = arr[k - 1]

        # Aggregate by bin_factor
        if bin_factor > 1:
            binned = []
            for b in range(n_bins):
                start_i = b * bin_factor
                end_i = min(start_i + bin_factor, len(arr))
                binned.append(np.mean(arr[start_i:end_i]))
            arr = np.array(binned)

        if len(arr) >= 2:
            result[addr] = arr

    return result


def _build_balance_series_tx_step(
    target_users: Optional[List[str]],
    time_window: Optional[Dict[str, str]],
    tx_step: int = 5,
) -> Dict[str, np.ndarray]:
    """
    Build balance series by transaction steps (every N-th transaction as a sample point).
    """
    df = _load_balance_df()
    if df.empty:
        return {}

    filtered = df.copy()
    if time_window:
        if time_window.get("start"):
            start = pd.to_datetime(time_window["start"], utc=True)
            filtered = filtered[filtered['time'] >= start]
        if time_window.get("end"):
            end = pd.to_datetime(time_window["end"], utc=True)
            filtered = filtered[filtered['time'] <= end]

    if target_users:
        filtered = filtered[filtered['owner_address'].isin(set(target_users))]

    result = {}
    for addr, group in filtered.groupby('owner_address'):
        balances = group['balance_after'].values.astype(float)
        # Sample every tx_step-th transaction
        sampled = balances[::tx_step]
        if len(sampled) >= 2:
            result[addr] = sampled

    return result


def rule4_similar_balance_sequence(
    target_users: Optional[List[str]],
    time_window: Optional[Dict[str, str]],
    balance_axis: str = "time_grid",
    tx_step: int = 5,
    time_bin: str = "1h",
    similarity: float = 0.8,
    topk_neighbors: int = 5,
) -> List[Dict[str, Any]]:
    """
    Rule4: Find pairs of addresses with similar balance curves.
    Returns list of {source, target, similarity_score, details}.
    """
    if balance_axis == "tx_step":
        series = _build_balance_series_tx_step(target_users, time_window, tx_step)
    else:
        series = _build_balance_series_time_grid(target_users, time_window, time_bin)

    if len(series) < 2:
        return []

    addrs = list(series.keys())
    # Pre-compute all pairwise correlations
    pair_scores: List[Tuple[str, str, float]] = []

    for i in range(len(addrs)):
        for j in range(i + 1, len(addrs)):
            a, b = addrs[i], addrs[j]
            sa, sb = series[a], series[b]
            # Align lengths (use shorter length)
            min_len = min(len(sa), len(sb))
            if min_len < 2:
                continue
            corr = _pearson_correlation(sa[:min_len], sb[:min_len])
            if corr >= similarity:
                pair_scores.append((a, b, corr))

    # For each address, keep only topk_neighbors
    addr_neighbors: Dict[str, List[Tuple[str, float]]] = {}
    for a, b, corr in pair_scores:
        addr_neighbors.setdefault(a, []).append((b, corr))
        addr_neighbors.setdefault(b, []).append((a, corr))

    # Filter to topk
    kept_pairs = set()
    for addr, neighbors in addr_neighbors.items():
        neighbors.sort(key=lambda x: x[1], reverse=True)
        for neighbor, corr in neighbors[:topk_neighbors]:
            pair_key = tuple(sorted([addr, neighbor]))
            kept_pairs.add(pair_key)

    results = []
    for a, b, corr in pair_scores:
        pair_key = tuple(sorted([a, b]))
        if pair_key in kept_pairs:
            results.append({
                "source": a,
                "target": b,
                "similarity_score": round(corr, 4),
                "details": {
                    "rule": "similar_balance_sequence",
                    "balance_axis": balance_axis,
                    "pearson_correlation": round(corr, 4),
                    "series_len_a": int(len(series[a])),
                    "series_len_b": int(len(series[b])),
                }
            })

    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return results


# ===========================================================================
# Rule 5: Similar Earning Sequence
# ===========================================================================

def _compute_earning_series_time_grid(
    target_users: Optional[List[str]],
    time_window: Optional[Dict[str, str]],
    time_bin: str = "1h",
) -> Dict[str, np.ndarray]:
    """
    Compute earning (equity curve) series per address using time grid.
    Earning = current_balance * current_price (estimated equity).
    """
    balance_series = _build_balance_series_time_grid(target_users, time_window, time_bin)
    if not balance_series:
        return {}

    price_dict = _get_ohlc_price_dict()
    if not price_dict:
        # Can't compute earning without price data
        return {}

    # Build price array aligned with snapshots
    snapshots = _load_hourly_snapshots()
    start_ts = None
    end_ts = None
    if time_window:
        if time_window.get("start"):
            start_ts = pd.to_datetime(time_window["start"])
        if time_window.get("end"):
            end_ts = pd.to_datetime(time_window["end"])

    prices = []
    for snap in snapshots:
        snap_time = pd.to_datetime(snap.get("time", "").replace(" UTC", ""))
        if start_ts and snap_time < start_ts:
            continue
        if end_ts and snap_time > end_ts:
            continue
        ts_str = snap_time.strftime("%Y-%m-%d %H:00:00")
        prices.append(price_dict.get(ts_str, 0.0))

    if not prices:
        return {}

    prices_arr = np.array(prices)

    # Determine bin aggregation
    bin_factor = 1
    if time_bin == '1d':
        bin_factor = 24

    if bin_factor > 1:
        n_bins = max(1, len(prices_arr) // bin_factor)
        binned_prices = []
        for b in range(n_bins):
            s = b * bin_factor
            e = min(s + bin_factor, len(prices_arr))
            binned_prices.append(np.mean(prices_arr[s:e]))
        prices_arr = np.array(binned_prices)

    result = {}
    for addr, bal_arr in balance_series.items():
        min_len = min(len(bal_arr), len(prices_arr))
        if min_len < 2:
            continue
        earning = bal_arr[:min_len] * prices_arr[:min_len]
        result[addr] = earning

    return result


def _compute_earning_series_tx_step(
    target_users: Optional[List[str]],
    time_window: Optional[Dict[str, str]],
    tx_step: int = 5,
) -> Dict[str, np.ndarray]:
    """
    Compute earning series per address using transaction steps.
    For each sampled transaction, earning = balance_after * price_at_time.
    """
    df = _load_balance_df()
    if df.empty:
        return {}

    price_dict = _get_ohlc_price_dict()
    if not price_dict:
        return {}

    filtered = df
    if time_window:
        if time_window.get("start"):
            start = pd.to_datetime(time_window["start"], utc=True)
            filtered = filtered[filtered['time'] >= start]
        if time_window.get("end"):
            end = pd.to_datetime(time_window["end"], utc=True)
            filtered = filtered[filtered['time'] <= end]

    if target_users:
        filtered = filtered[filtered['owner_address'].isin(set(target_users))]

    result = {}
    for addr, group in filtered.groupby('owner_address'):
        sampled = group.iloc[::tx_step]
        if len(sampled) < 2:
            continue
        earnings = []
        for _, row in sampled.iterrows():
            bal = float(row['balance_after'])
            price = _get_price_at_time(row['time'], price_dict)
            earnings.append(bal * price)
        result[addr] = np.array(earnings)

    return result


def rule5_similar_earning_sequence(
    target_users: Optional[List[str]],
    time_window: Optional[Dict[str, str]],
    earning_axis: str = "time_grid",
    tx_step: int = 5,
    time_bin: str = "1h",
    similarity: float = 0.8,
    topk_neighbors: int = 5,
) -> List[Dict[str, Any]]:
    """
    Rule5: Find pairs of addresses with similar earning (equity) curves.
    Returns list of {source, target, similarity_score, details}.
    """
    if earning_axis == "tx_step":
        series = _compute_earning_series_tx_step(target_users, time_window, tx_step)
    else:
        series = _compute_earning_series_time_grid(target_users, time_window, time_bin)

    if len(series) < 2:
        return []

    addrs = list(series.keys())
    pair_scores: List[Tuple[str, str, float]] = []

    for i in range(len(addrs)):
        for j in range(i + 1, len(addrs)):
            a, b = addrs[i], addrs[j]
            sa, sb = series[a], series[b]
            min_len = min(len(sa), len(sb))
            if min_len < 2:
                continue
            corr = _pearson_correlation(sa[:min_len], sb[:min_len])
            if corr >= similarity:
                pair_scores.append((a, b, corr))

    # TopK neighbors filtering
    addr_neighbors: Dict[str, List[Tuple[str, float]]] = {}
    for a, b, corr in pair_scores:
        addr_neighbors.setdefault(a, []).append((b, corr))
        addr_neighbors.setdefault(b, []).append((a, corr))

    kept_pairs = set()
    for addr, neighbors in addr_neighbors.items():
        neighbors.sort(key=lambda x: x[1], reverse=True)
        for neighbor, corr in neighbors[:topk_neighbors]:
            pair_key = tuple(sorted([addr, neighbor]))
            kept_pairs.add(pair_key)

    results = []
    for a, b, corr in pair_scores:
        pair_key = tuple(sorted([a, b]))
        if pair_key in kept_pairs:
            results.append({
                "source": a,
                "target": b,
                "similarity_score": round(corr, 4),
                "details": {
                    "rule": "similar_earning_sequence",
                    "earning_axis": earning_axis,
                    "pearson_correlation": round(corr, 4),
                    "series_len_a": int(len(series[a])),
                    "series_len_b": int(len(series[b])),
                }
            })

    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return results
