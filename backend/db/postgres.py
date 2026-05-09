"""
PostgreSQL client — wraps psycopg2 with a simple connection pool.
All DDL lives in backend/init-db.sql (run via Docker volume mount).
"""

import json
import logging
from contextlib import contextmanager
from typing import Any, Generator

import psycopg2
import psycopg2.extras
from psycopg2 import pool

from config import Config

logger = logging.getLogger(__name__)

_pool: pool.ThreadedConnectionPool | None = None


def get_pool() -> pool.ThreadedConnectionPool:
    global _pool
    if _pool is None or _pool.closed:
        _pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=Config.DATABASE_URL,
        )
        logger.info("PostgreSQL connection pool initialised")
    return _pool


@contextmanager
def get_db() -> Generator[psycopg2.extensions.connection, None, None]:
    """Context manager that yields a psycopg2 connection from the pool."""
    conn = None
    try:
        conn = get_pool().getconn()
        conn.autocommit = False
        yield conn
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            get_pool().putconn(conn)


# ---------------------------------------------------------------------------
# Incident helpers
# ---------------------------------------------------------------------------

def upsert_incident(incident: dict[str, Any]) -> dict[str, Any]:
    """Insert or update an incident row. Returns the stored row as a dict."""
    sql = """
        INSERT INTO incidents (
            trace_id, timestamp, classification, root_cause, blast_radius,
            impact, confidence_score, status, rca_json, service, summary
        ) VALUES (
            %(trace_id)s, %(timestamp)s, %(classification)s, %(root_cause)s,
            %(blast_radius)s, %(impact)s, %(confidence_score)s, %(status)s,
            %(rca_json)s, %(service)s, %(summary)s
        )
        ON CONFLICT (trace_id) DO UPDATE SET
            classification   = EXCLUDED.classification,
            root_cause       = EXCLUDED.root_cause,
            blast_radius     = EXCLUDED.blast_radius,
            impact           = EXCLUDED.impact,
            confidence_score = EXCLUDED.confidence_score,
            status           = EXCLUDED.status,
            rca_json         = EXCLUDED.rca_json,
            service          = EXCLUDED.service,
            summary          = EXCLUDED.summary,
            updated_at       = NOW()
        RETURNING id, trace_id, timestamp, classification, root_cause,
                  blast_radius, impact, confidence_score, status, service,
                  summary, rca_json, created_at, updated_at
    """
    params = {
        "trace_id":        incident.get("trace_id"),
        "timestamp":       incident.get("timestamp"),
        "classification":  incident.get("classification"),
        "root_cause":      incident.get("root_cause"),
        "blast_radius":    incident.get("blast_radius"),
        "impact":          incident.get("impact"),
        "confidence_score": incident.get("confidence_score"),
        "status":          incident.get("status", "active"),
        "rca_json":        json.dumps(incident.get("rca_json")) if incident.get("rca_json") else None,
        "service":         incident.get("service"),
        "summary":         incident.get("summary"),
    }
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return dict(cur.fetchone())


def get_incident_by_id(incident_id: str) -> dict[str, Any] | None:
    sql = """
        SELECT id, trace_id, timestamp, classification, root_cause,
               blast_radius, impact, confidence_score, status, service,
               summary, rca_json, created_at, updated_at
        FROM incidents WHERE id = %s
    """
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (incident_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def get_incident_by_trace(trace_id: str) -> dict[str, Any] | None:
    sql = """
        SELECT id, trace_id, timestamp, classification, root_cause,
               blast_radius, impact, confidence_score, status, service,
               summary, rca_json, created_at, updated_at
        FROM incidents WHERE trace_id = %s
    """
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (trace_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def list_incidents(limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    sql = """
        SELECT id, trace_id, timestamp, classification, root_cause,
               blast_radius, impact, confidence_score, status, service,
               summary, created_at, updated_at
        FROM incidents
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (limit, offset))
            return [dict(r) for r in cur.fetchall()]


def update_incident_status(trace_id: str, status: str) -> None:
    sql = "UPDATE incidents SET status = %s, updated_at = NOW() WHERE trace_id = %s"
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (status, trace_id))


# ---------------------------------------------------------------------------
# Incident log helpers
# ---------------------------------------------------------------------------

def insert_incident_log(log_entry: dict[str, Any]) -> None:
    sql = """
        INSERT INTO incident_logs (
            incident_id, timestamp, service, endpoint, log_level, message,
            raw_log, async_orphan
        ) VALUES (
            %(incident_id)s, %(timestamp)s, %(service)s, %(endpoint)s,
            %(log_level)s, %(message)s, %(raw_log)s, %(async_orphan)s
        )
    """
    params = {
        "incident_id":  log_entry.get("incident_id"),
        "timestamp":    log_entry.get("timestamp"),
        "service":      log_entry.get("service"),
        "endpoint":     log_entry.get("endpoint"),
        "log_level":    log_entry.get("log_level", "INFO"),
        "message":      log_entry.get("message"),
        "raw_log":      json.dumps(log_entry.get("raw_log", {})),
        "async_orphan": log_entry.get("async_orphan", False),
    }
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)


def get_trace_events(trace_id: str, limit: int = 500) -> list[dict[str, Any]]:
    sql = """
        SELECT il.id, il.incident_id, il.timestamp, il.service, il.endpoint,
               il.log_level, il.message, il.raw_log, il.async_orphan, il.created_at
        FROM incident_logs il
        JOIN incidents i ON i.id = il.incident_id
        WHERE i.trace_id = %s
        ORDER BY il.timestamp ASC
        LIMIT %s
    """
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (trace_id, limit))
            return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Remediation action helpers
# ---------------------------------------------------------------------------

def insert_action(action: dict[str, Any]) -> dict[str, Any]:
    sql = """
        INSERT INTO remediation_actions (
            incident_id, action_type, status, details, started_at
        ) VALUES (
            %(incident_id)s, %(action_type)s, %(status)s, %(details)s, NOW()
        )
        RETURNING id, incident_id, action_type, status, details,
                  started_at, completed_at, created_at
    """
    params = {
        "incident_id": action.get("incident_id"),
        "action_type": action.get("action_type"),
        "status":      action.get("status", "running"),
        "details":     json.dumps(action.get("details", {})),
    }
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return dict(cur.fetchone())


def complete_action(action_id: str, status: str, details: dict[str, Any]) -> None:
    sql = """
        UPDATE remediation_actions
        SET status = %s, details = %s, completed_at = NOW()
        WHERE id = %s
    """
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (status, json.dumps(details), action_id))


def list_actions(limit: int = 200) -> list[dict[str, Any]]:
    sql = """
        SELECT ra.id, ra.incident_id, ra.action_type, ra.status,
               ra.details, ra.started_at, ra.completed_at, ra.created_at,
               i.trace_id
        FROM remediation_actions ra
        JOIN incidents i ON i.id = ra.incident_id
        ORDER BY ra.created_at DESC
        LIMIT %s
    """
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (limit,))
            return [dict(r) for r in cur.fetchall()]


def get_actions_for_incident(incident_id: str) -> list[dict[str, Any]]:
    sql = """
        SELECT id, incident_id, action_type, status, details,
               started_at, completed_at, created_at
        FROM remediation_actions
        WHERE incident_id = %s
        ORDER BY created_at DESC
    """
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (incident_id,))
            return [dict(r) for r in cur.fetchall()]


def close_pool() -> None:
    global _pool
    if _pool and not _pool.closed:
        _pool.closeall()
        logger.info("PostgreSQL connection pool closed")
