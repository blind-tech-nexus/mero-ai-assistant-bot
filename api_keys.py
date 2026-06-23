import httpx
import logging
import time
import asyncio
from typing import Optional
from config import POOL_API

logger = logging.getLogger("mero.api_keys")

# Global variables to store API keys and their statuses across request cycles
api_keys: list[str] = []
LAST_FETCH_TIME: float = 0
CACHE_TTL = 300  # 5 minutes cache

_key_index = 0
_key_lock = asyncio.Lock()


async def fetch_api_keys() -> bool:
    """Fetch API keys from the pool API and update the global tracker with caching."""
    global api_keys, LAST_FETCH_TIME
    current_time = time.time()

    # Return cached keys if available and fresh
    if api_keys and (current_time - LAST_FETCH_TIME) < CACHE_TTL:
        return True

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(POOL_API)
            if resp.status_code == 200:
                keys = resp.json()
                if isinstance(keys, list) and keys:
                    new_keys = [k for k in keys if k and isinstance(k, str)]
                    api_keys = new_keys
                    LAST_FETCH_TIME = current_time
                    logger.info("Fetched %d api keys.", len(api_keys))
                    return bool(api_keys)
    except Exception as exc:
        logger.warning("fetch_api_keys failed: %s", exc)

    # Fallback to existing keys if fetch failed
    return bool(api_keys)


async def get_next_key_index() -> int:
    """Return and advance the global round-robin index."""
    global _key_index
    async with _key_lock:
        if not api_keys:
            return 0
        idx = _key_index
        _key_index = (_key_index + 1) % len(api_keys)
        return idx


class KeyRotator:
    def __init__(self, start_idx: int):
        self._keys = list(api_keys)
        self._start_idx = start_idx
        self._tried = 0

    def get_next_key(self) -> Optional[str]:
        if not self._keys or self._tried >= len(self._keys):
            return None
        idx = (self._start_idx + self._tried) % len(self._keys)
        self._tried += 1
        return self._keys[idx]


def is_retriable_error(e: Exception) -> bool:
    err_str = str(e).lower()
    non_retriable = {"400", "401", "403", "404", "invalid", "permission",
                     "denied", "malformed", "bad request", "safety"}
    if any(c in err_str for c in non_retriable):
        return False
    retriable = {"429", "500", "502", "503", "504", "resource_exhausted",
                 "unavailable", "connection", "timeout", "deadline"}
    if any(c in err_str for c in retriable):
        return True
    if hasattr(e, "code"):
        code = getattr(e, "code", None)
        if code in (400, 401, 403, 404):
            return False
        if code in (429, 500, 502, 503, 504):
            return True
    if isinstance(e, (httpx.HTTPStatusError, httpx.ConnectError,
                      httpx.TimeoutException, httpx.NetworkError)):
        return True
    return False
