"""
/api/actions  — remediation action history
"""

import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from db import postgres

logger = logging.getLogger(__name__)
bp = Blueprint("actions", __name__, url_prefix="/api/actions")


def _serialize(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


@bp.get("")
def list_actions():
    """GET /api/actions?limit=200"""
    limit = min(int(request.args.get("limit", 200)), 500)
    try:
        rows = postgres.list_actions(limit=limit)
        return jsonify([_serialize(r) for r in rows])
    except Exception as exc:
        logger.error("list_actions error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@bp.get("/incident/<incident_id>")
def get_actions_for_incident(incident_id: str):
    """GET /api/actions/incident/<incident_id>"""
    try:
        rows = postgres.get_actions_for_incident(incident_id)
        return jsonify([_serialize(r) for r in rows])
    except Exception as exc:
        logger.error("get_actions_for_incident error: %s", exc)
        return jsonify({"error": str(exc)}), 500
