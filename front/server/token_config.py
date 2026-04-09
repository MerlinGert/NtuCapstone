"""
Token configuration module.
Maps token names to their data directories and provides path resolution.
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Token registry: token_name -> path prefix relative to public/
# ACT uses the legacy root-level paths, PNUT uses tokens/PNUT/
TOKEN_REGISTRY = {
    "ACT": {
        "data_dir": os.path.join(BASE_DIR, "public", "data"),
        "processed_dir": os.path.join(BASE_DIR, "public", "processed"),
        "ohlc": "ACT_OHLC.json",  # relative to public/
        "transfer_network_stats": os.path.join(BASE_DIR, "public", "transfer_network_stats.csv"),
    },
    "PNUT": {
        "data_dir": os.path.join(BASE_DIR, "public", "tokens", "PNUT", "data"),
        "processed_dir": os.path.join(BASE_DIR, "public", "tokens", "PNUT", "processed"),
        "ohlc": "tokens/PNUT/OHLC.json",  # relative to public/
        "transfer_network_stats": os.path.join(BASE_DIR, "public", "tokens", "PNUT", "transfer_network_stats.csv"),
    },
}

DEFAULT_TOKEN = "ACT"

def get_token_paths(token: str = None) -> dict:
    """Get path configuration for a token. Returns dict with data_dir, processed_dir, etc."""
    token = (token or DEFAULT_TOKEN).upper()
    if token not in TOKEN_REGISTRY:
        raise ValueError(f"Unknown token: {token}. Available: {list(TOKEN_REGISTRY.keys())}")
    return TOKEN_REGISTRY[token]

def get_data_path(token: str, filename: str) -> str:
    """Get full path to a file in the token's data directory."""
    paths = get_token_paths(token)
    return os.path.join(paths["data_dir"], filename)

def get_processed_path(token: str, *parts: str) -> str:
    """Get full path to a file in the token's processed directory."""
    paths = get_token_paths(token)
    return os.path.join(paths["processed_dir"], *parts)

def get_available_tokens():
    """Return list of available token names."""
    return list(TOKEN_REGISTRY.keys())
