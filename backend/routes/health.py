"""
/api/health  — liveness / readiness check
"""

import logging

from flask import Blueprint, jsonify

from db import postgres, redis_client, neo4j_client
from config import Config

logger = logging.getLogger(__name__)
bp = Blueprint("health", __name__, url_prefix="/api/health")


@bp.get("")
def health():
    """GET /api/health — returns status of all subsystems."""
    checks: dict[str, dict] = {}

    # PostgreSQL
    try:
        with postgres.get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        checks["postgres"] = {"status": "ok"}
    except Exception as exc:
        checks["postgres"] = {"status": "error", "detail": str(exc)}

    # Redis
    try:
        ok = redis_client.ping()
        checks["redis"] = {"status": "ok" if ok else "error"}
    except Exception as exc:
        checks["redis"] = {"status": "error", "detail": str(exc)}

    # Neo4j
    try:
        ok = neo4j_client.ping()
        checks["neo4j"] = {"status": "ok" if ok else "error"}
    except Exception as exc:
        checks["neo4j"] = {"status": "error", "detail": str(exc)}

    # Config sanity
    missing = Config.validate()
    checks["config"] = {
        "status": "ok" if not missing else "warning",
        "missing_keys": missing,
    }

    overall_ok = all(
        v.get("status") in {"ok", "warning"} for v in checks.values()
    )
    status_code = 200 if overall_ok else 503

    return jsonify({
        "status": "healthy" if overall_ok else "degraded",
        "checks": checks,
        "chaos_backend": Config.CHAOS_BACKEND_URL,
        "model": Config.ANTHROPIC_MODEL,
    }), status_code
