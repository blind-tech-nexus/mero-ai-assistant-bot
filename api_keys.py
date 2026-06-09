import httpx
import logging
from typing import Optional
from config import POOL_API

logger = logging.getLogger("mero.api_keys")

api_keys: list[str] = []


async def fetch_api_keys() -> bool:
    """Fetch API keys from the pool API. Returns True if keys are available."""
    global api_keys
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(POOL_API)
            if resp.status_code == 200:
                keys = resp.json()
                if isinstance(keys, list) and keys:
                    api_keys = [k for k in keys if k and isinstance(k, str)]
                    logger.info("fetched %d api keys", len(api_keys))
                    return bool(api_keys)
    except Exception as exc:
        logger.warning("fetch_api_keys failed: %s", exc)
    return bool(api_keys)


def get_keys() -> list[str]:
    return api_keys


class KeyRotator:
    """Tracks API key usage with a dictionary for proper sequential iteration.

    Usage:
        rotator = KeyRotator()
        while True:
            key = rotator.get_next_key()
            if key is None:
                break  # all keys exhausted
            try:
                result = call_api(key)
                rotator.mark_success(key)
                return result
            except RetryableError:
                rotator.mark_failed(key)
                continue
    """

    def __init__(self, preferred_key: Optional[str] = None):
        all_keys = [k for k in get_keys() if k]
        # Build the ordered key list with preferred key first
        if preferred_key and preferred_key in all_keys:
            self._keys = [preferred_key] + [k for k in all_keys if k != preferred_key]
        else:
            self._keys = all_keys
        # Dictionary tracking status: "unused", "success", or "failed"
        self._status: dict[str, str] = {k: "unused" for k in self._keys}
        self._failures: list[str] = []
        self._current_index = 0

    @property
    def total_keys(self) -> int:
        return len(self._keys)

    @property
    def tried_keys(self) -> dict[str, str]:
        """Return copy of the status dictionary."""
        return dict(self._status)

    @property
    def remaining_keys(self) -> list[str]:
        """Return keys that haven't been tried yet."""
        return [k for k, s in self._status.items() if s == "unused"]

    @property
    def failed_keys(self) -> list[str]:
        """Return keys that failed."""
        return [k for k, s in self._status.items() if s == "failed"]

    @property
    def successful_key(self) -> Optional[str]:
        """Return the key that succeeded, if any."""
        for k, s in self._status.items():
            if s == "success":
                return k
        return None

    def get_next_key(self) -> Optional[str]:
        """Get the next untried key. Returns None when all keys are exhausted."""
        while self._current_index < len(self._keys):
            key = self._keys[self._current_index]
            if self._status[key] == "unused":
                return key
            self._current_index += 1
        return None

    def mark_success(self, key: str) -> None:
        """Mark a key as successful."""
        if key in self._status:
            self._status[key] = "success"
            logger.debug("key #%d succeeded", self._keys.index(key) + 1)

    def mark_failed(self, key: str, reason: str = "") -> None:
        """Mark a key as failed and advance to next."""
        if key in self._status:
            self._status[key] = "failed"
            idx = self._keys.index(key) + 1
            failure_msg = f"key#{idx}: {reason}" if reason else f"key#{idx}: failed"
            self._failures.append(failure_msg)
            logger.debug("key #%d failed: %s", idx, reason)
            self._current_index += 1

    def get_failure_summary(self) -> str:
        """Get a summary of all failures for error reporting."""
        if not self._failures:
            return "No keys available"
        return "; ".join(self._failures)

    def has_keys(self) -> bool:
        """Check if there are any keys to try."""
        return len(self._keys) > 0