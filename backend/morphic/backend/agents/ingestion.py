"""
Ingestion Agent — Layer 1
Polls https://hackathonps-ykxr.onrender.com/logs every 30 seconds,
deduplicates events, flags ASYNC-ORPHANs, persists to PostgreSQL + Neo4j.
"""

import logging
from datetime import datetime, timezone
from typing import Any

import requests

from config import Config
from db import postgres, redis_client, neo4j_client
from utils.dedup import is_duplicate, record_processed, is_async_orphan

logger = logging.getLogger(__name__)

CHAOS_LOGS_URL = f"{Config.CHAOS_BACKEND_URL}/logs"

# Fields we expect to be present in a well-correlated log entry
_REQUIRED_TRACE_FIELDS = {"trace_id", "service"}


def _normalize_entry(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize a raw log entry from the chaos backend into a canonical shape.
    The chaos backend may use camelCase or snake_case — we accept both.
    """
    trace_id = (
        raw.get("trace_id")
        or raw.get("traceId")
        or raw.get("X-B3-TraceId")
        or "unknown"
    )
    timestamp_raw = (
        raw.get("timestamp")
        or raw.get("time")
        or raw.get("@timestamp")
        or datetime.now(timezone.utc).isoformat()
    )
    # Normalise timestamp to a string ISO-8601 — keep original if it already is
    if isinstance(timestamp_raw, (int, float)):
        # epoch millis
        timestamp_raw = datetime.fromtimestamp(
            timestamp_raw / 1000, tz=timezone.utc
        ).isoformat()

    service = (
        raw.get("service")
        or raw.get("serviceName")
        or raw.get("application")
        or "unknown"
    )
    endpoint = (
        raw.get("endpoint")
        or raw.get("uri")
        or raw.get("path")
        or raw.get("url")
        or ""
    )
    level = (
        raw.get("level")
        or raw.get("severity")
        or raw.get("log_level")
        or "INFO"
    ).upper()
    message = (
        raw.get("message")
        or raw.get("msg")
        or raw.get("log")
        or ""
    )
    exception = (
        raw.get("exception")
        or raw.get("error")
        or raw.get("exception_class")
        or raw.get("exceptionClass")
        or ""
    )
    order_id = raw.get("orderId") or raw.get("order_id")
    user_id = raw.get("userId") or raw.get("user_id")

    return {
        "trace_id":   trace_id,
        "timestamp":  timestamp_raw,
        "service":    service,
        "endpoint":   endpoint,
        "level":      level,
        "message":    message,
        "exception":  exception,
        "order_id":   order_id,
        "user_id":    user_id,
        "raw":        raw,
    }


def _fetch_logs() -> list[dict[str, Any]]:
    """HTTP GET /logs from the chaos backend. Returns a list of log entries."""
    try:
        resp = requests.get(
            CHAOS_LOGS_URL,
            timeout=15,
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        # The endpoint may return a list directly or {"logs": [...]}
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("logs") or data.get("data") or list(data.values())[0] if data else []
        return []
    except requests.exceptions.Timeout:
        logger.warning("Timeout fetching logs from %s", CHAOS_LOGS_URL)
    except requests.exceptions.ConnectionError:
        logger.warning("Connection error fetching logs from %s", CHAOS_LOGS_URL)
    except Exception as exc:
        logger.error("Unexpected error fetching logs: %s", exc)
    return []


def run_ingestion() -> list[dict[str, Any]]:
    """
    Main ingestion cycle:
    1. Fetch raw logs from chaos backend
    2. Deduplicate against Redis watermark
    3. Flag ASYNC-ORPHANs
    4. Persist to PostgreSQL + Neo4j
    5. Update Redis watermark

    Returns list of new, normalised incident dicts that need triage.
    """
    raw_logs = _fetch_logs()
    if not raw_logs:
        logger.debug("No logs returned from chaos backend")
        return []

    logger.info("Fetched %d raw log entries", len(raw_logs))

    new_incidents: list[dict[str, Any]] = []
    latest_ts: str | None = None

    for raw in raw_logs:
        entry = _normalize_entry(raw)
        ts = entry["timestamp"]
        trace_id = entry["trace_id"]

        # Skip already-processed events
        if is_duplicate(ts, trace_id):
            continue

        orphan = is_async_orphan(raw)
        entry["async_orphan"] = orphan
        if orphan:
            logger.info("ASYNC-ORPHAN detected: trace_id=%s ts=%s", trace_id, ts)

        # Persist to PostgreSQL incidents table (upsert by trace_id)
        try:
            stored = postgres.upsert_incident({
                "trace_id":       trace_id,
                "timestamp":      ts,
                "service":        entry["service"],
                "status":         "active",
                "blast_radius":   None,
                "confidence_score": None,
                "summary":        entry["message"][:500] if entry["message"] else None,
                "classification": None,
                "root_cause":     None,
                "impact":         None,
                "rca_json":       None,
            })
            incident_id = str(stored["id"])
        except Exception as exc:
            logger.error("Failed to upsert incident for trace_id=%s: %s", trace_id, exc)
            continue

        # Persist log entry to incident_logs
        try:
            postgres.insert_incident_log({
                "incident_id": incident_id,
                "timestamp":   ts,
                "service":     entry["service"],
                "endpoint":    entry["endpoint"],
                "log_level":   entry["level"],
                "message":     entry["message"],
                "raw_log":     raw,
                "async_orphan": orphan,
            })
        except Exception as exc:
            logger.warning("Failed to insert incident_log: %s", exc)

        # Write to Neo4j
        try:
            neo4j_client.upsert_incident_graph({
                "trace_id":       trace_id,
                "timestamp":      ts,
                "service":        entry["service"],
                "classification": "",
                "blast_radius":   "LOW",
                "root_cause":     entry["message"][:200] if entry["message"] else "",
                "status":         "active",
                "confidence_score": 0.0,
                "summary":        entry["message"][:200] if entry["message"] else "",
            })
            if entry.get("order_id"):
                neo4j_client.link_order_to_incident(trace_id, str(entry["order_id"]))
            if entry.get("user_id"):
                neo4j_client.link_user_to_incident(trace_id, str(entry["user_id"]))
        except Exception as exc:
            logger.warning("Neo4j graph write failed: %s", exc)

        # Mark as processed in Redis
        record_processed(ts, trace_id)
        if latest_ts is None or ts > latest_ts:
            latest_ts = ts

        entry["incident_id"] = incident_id
        new_incidents.append(entry)

    # Update the watermark
    if latest_ts:
        try:
            redis_client.set_watermark(latest_ts)
        except Exception as exc:
            logger.warning("Failed to update watermark: %s", exc)

    logger.info(
        "Ingestion complete: %d new incidents out of %d log entries",
        len(new_incidents),
        len(raw_logs),
    )
    return new_incidents
