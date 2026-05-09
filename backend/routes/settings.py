"""
/api/settings  — runtime configuration status
"""

import logging

from flask import Blueprint, jsonify

from config import Config
from db import redis_client

logger = logging.getLogger(__name__)
bp = Blueprint("settings", __name__, url_prefix="/api/settings")


@bp.get("/status")
def settings_status():
    """GET /api/settings/status — return redacted config state."""
    missing = Config.validate()
    watermark = None
    try:
        watermark = redis_client.get_watermark()
    except Exception:
        pass

    return jsonify({
        "chaos_backend_url":       Config.CHAOS_BACKEND_URL,
        "poll_interval_seconds":   Config.POLL_INTERVAL_SECONDS,
        "anthropic_model":         Config.ANTHROPIC_MODEL,
        "anthropic_key_set":       bool(Config.ANTHROPIC_API_KEY),
        "github_token_set":        bool(Config.GITHUB_TOKEN),
        "github_repo":             Config.GITHUB_REPO or "(not set)",
        "email_from":              Config.EMAIL_FROM or "(not set)",
        "email_to":                Config.EMAIL_TO or "(not set)",
        "database_url_set":        bool(Config.DATABASE_URL),
        "neo4j_uri":               Config.NEO4J_URI,
        "redis_url_set":           bool(Config.REDIS_URL),
        "dashboard_url":           Config.DASHBOARD_URL,
        "missing_config":          missing,
        "high_confidence_threshold": Config.HIGH_CONFIDENCE_THRESHOLD,
        "min_confidence_for_pr":   Config.MIN_CONFIDENCE_FOR_PR,
        "last_ingestion_watermark": watermark,
    })
