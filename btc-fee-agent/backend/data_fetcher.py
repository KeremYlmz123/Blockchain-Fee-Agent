import json
import os
import time
from pathlib import Path
from typing import Any, Tuple

import requests

BASE_URL = os.getenv("MEMPOOL_BASE_URL", "https://mempool.space/api")
REQUEST_TIMEOUT = float(os.getenv("MEMPOOL_TIMEOUT", "10"))
RETRY_COUNT = int(os.getenv("MEMPOOL_RETRY_COUNT", "2"))
RETRY_DELAY = float(os.getenv("MEMPOOL_RETRY_DELAY", "0.5"))
RATE_LIMIT_SECONDS = float(os.getenv("MEMPOOL_RATE_LIMIT_SECONDS", "0.2"))
CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "cache.json"

_last_request_ts = 0.0


def _respect_rate_limit() -> None:
    """Ensure we do not exceed a simple rate limit between requests."""
    global _last_request_ts
    elapsed = time.monotonic() - _last_request_ts
    if elapsed < RATE_LIMIT_SECONDS:
        time.sleep(RATE_LIMIT_SECONDS - elapsed)
    _last_request_ts = time.monotonic()


def _load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    try:
        with CACHE_PATH.open("r", encoding="utf-8") as cache_file:
            return json.load(cache_file)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_cache(cache_key: str, payload: Any) -> None:
    cache = _load_cache()
    cache[cache_key] = payload
    cache.setdefault("last_updated", {})[cache_key] = int(time.time())
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CACHE_PATH.open("w", encoding="utf-8") as cache_file:
        json.dump(cache, cache_file, indent=2)


def _get_cached(cache_key: str) -> Any:
    cache = _load_cache()
    return cache.get(cache_key)


def _fetch(endpoint: str, cache_key: str) -> Tuple[Any, bool]:
    """Fetch JSON with retry, rate limit, and cache fallback."""
    last_exception: Exception | None = None
    for attempt in range(RETRY_COUNT + 1):
        try:
            _respect_rate_limit()
            response = requests.get(
                f"{BASE_URL}{endpoint}", timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            _save_cache(cache_key, data)
            return data, False
        except (requests.RequestException, ValueError) as exc:
            last_exception = exc
            if attempt < RETRY_COUNT:
                time.sleep(RETRY_DELAY)

    cached = _get_cached(cache_key)
    if cached is not None:
        return cached, True

    if last_exception:
        raise last_exception
    raise RuntimeError(f"Failed to fetch {endpoint} with no cached data")


def get_fee_recommendations() -> Tuple[dict, bool]:
    return _fetch("/v1/fees/recommended", "fees")


def get_mempool_stats() -> Tuple[dict, bool]:
    return _fetch("/mempool", "mempool")


def get_blocks() -> Tuple[list, bool]:
    return _fetch("/blocks", "blocks")


def get_tip_height() -> Tuple[int, bool]:
    height, cache_used = _fetch("/blocks/tip/height", "blocks_tip_height")
    return height, cache_used


def get_mining_targets() -> Tuple[list, bool]:
    """Fetch projected mempool blocks with cache fallback."""
    return _fetch("/v1/fees/mempool-blocks", "mempool_blocks")
