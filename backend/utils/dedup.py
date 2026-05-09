"""
Deduplication utilities — compound key helpers that wrap the Redis layer.
"""

from db import redis_client


def is_duplicate(timestamp: str, trace_id: str) -> bool:
    """Return True when this (timestamp, trace_id) pair has already been processed."""
    try:
        return redis_client.is_seen(timestamp, trace_id)
    except Exception:
        # If Redis is unavailable, allow processing to continue (fail-open).
        return False


def record_processed(timestamp: str, trace_id: str) -> None:
    """Mark the pair as processed in Redis."""
    try:
        redis_client.mark_seen(timestamp, trace_id)
    except Exception:
        pass


def is_async_orphan(log_entry: dict) -> bool:
    """
    Flag a log entry as ASYNC-ORPHAN when it is missing MDC / trace-correlation fields.
    Expected fields for a correlated entry:  trace_id, span_id (or spanId).
    """
    has_trace = bool(
        log_entry.get("trace_id")
        or log_entry.get("traceId")
        or log_entry.get("X-B3-TraceId")
    )
    has_span = bool(
        log_entry.get("span_id")
        or log_entry.get("spanId")
        or log_entry.get("X-B3-SpanId")
    )
    is_async = bool(
        log_entry.get("thread", "").lower().startswith("async")
        or log_entry.get("logger", "").lower().find("async") != -1
        or log_entry.get("message", "").lower().find("async") != -1
    )
    # An entry is an ASYNC-ORPHAN when it comes from an async context but lacks
    # proper trace correlation.
    return is_async and not (has_trace and has_span)
