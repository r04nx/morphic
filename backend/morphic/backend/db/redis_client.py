"""
Redis client — thin wrapper used exclusively for deduplication watermarks.
"""

import logging
from typing import Optional

import redis as redis_lib

from config import Config

logger = logging.getLogger(__name__)

_client: redis_lib.Redis | None = None

# Key prefix
_PREFIX = "morphic:"
_WATERMARK_KEY = f"{_PREFIX}ingestion:watermark"
_SEEN_PREFIX = f"{_PREFIX}seen:"


def get_client() -> redis_lib.Redis:
    global _client
    if _client is None:
        _client = redis_lib.from_url(
            Config.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        logger.info("Redis client initialised at %s", Config.REDIS_URL)
    return _client


def ping() -> bool:
    try:
        return get_client().ping()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Watermark helpers
# ---------------------------------------------------------------------------

def get_watermark() -> Optional[str]:
    """Return the last-seen watermark timestamp (ISO string) or None."""
    return get_client().get(_WATERMARK_KEY)


def set_watermark(ts: str) -> None:
    """Persist the latest processed timestamp as the new watermark."""
    get_client().set(_WATERMARK_KEY, ts)


# ---------------------------------------------------------------------------
# Deduplication helpers
# ---------------------------------------------------------------------------

def _seen_key(timestamp: str, trace_id: str) -> str:
    return f"{_SEEN_PREFIX}{timestamp}:{trace_id}"


def is_seen(timestamp: str, trace_id: str) -> bool:
    """Return True if this (timestamp, trace_id) compound key was already processed."""
    return get_client().exists(_seen_key(timestamp, trace_id)) == 1


def mark_seen(timestamp: str, trace_id: str, ttl_seconds: int = 86400 * 7) -> None:
    """Mark a (timestamp, trace_id) pair as processed. Default TTL = 7 days."""
    get_client().set(_seen_key(timestamp, trace_id), "1", ex=ttl_seconds)


# ---------------------------------------------------------------------------
# Rate-limiting helpers (for triage)
# ---------------------------------------------------------------------------

_RATE_PREFIX = f"{_PREFIX}rate:"


def rate_limit_key(classification: str) -> str:
    return f"{_RATE_PREFIX}{classification.lower().replace(' ', '_')}"


def is_rate_limited(classification: str, window_seconds: int = 300) -> bool:
    """Return True if we have sent >=3 alerts for this classification in the window."""
    key = rate_limit_key(classification)
    count = get_client().get(key)
    return count is not None and int(count) >= 3


def increment_rate_counter(classification: str, window_seconds: int = 300) -> int:
    key = rate_limit_key(classification)
    pipe = get_client().pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    results = pipe.execute()
    return results[0]
