"""
/api/actions  — remediation action history
"""

import json
import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from db import postgres

logger = logging.getLogger(__name__)
bp = Blueprint("actions", __name__, url_prefix="/api/actions")

# DB stores lowercase action_type/status; frontend expects uppercase enums
_ACTION_TYPE_MAP = {
    "email":      "EMAIL",
    "github_pr":  "GITHUB_PR",
    "github-pr":  "GITHUB_PR",
    "restart":    "RESTART",
    "ticket":     "TICKET",
    "rollback":   "RESTART",
}

_STATUS_MAP = {
    "running":   "RUNNING",
    "completed": "SUCCEEDED",
    "succeeded": "SUCCEEDED",
    "failed":    "FAILED",
    "queued":    "QUEUED",
    "skipped":   "SKIPPED",
}


def _normalize(row: dict) -> dict:
    """Map a remediation_actions DB row to the ActionExecution frontend shape."""
    # Parse details JSON if stored as string
    raw_details = row.get("details") or {}
    if isinstance(raw_details, str):
        try:
            raw_details = json.loads(raw_details)
        except Exception:
            raw_details = {}

    action_type_raw = str(row.get("action_type") or "").lower()
    status_raw      = str(row.get("status") or "").lower()

    # Build a human-readable summary from the details blob
    summary = (
        raw_details.get("summary")
        or raw_details.get("subject")          # email subject
        or raw_details.get("pr_title")         # github PR title
        or raw_details.get("message")
        or f"{_ACTION_TYPE_MAP.get(action_type_raw, action_type_raw.upper())} action"
    )

    # Output/result text
    output = (
        raw_details.get("output")
        or raw_details.get("result")
        or raw_details.get("to")               # email recipient
        or raw_details.get("error")
        or None
    )

    # External link (PR URL, ticket URL, etc.)
    link = (
        raw_details.get("link")
        or raw_details.get("pr_url")
        or raw_details.get("url")
        or None
    )

    def _iso(val):
        if isinstance(val, datetime):
            return val.isoformat()
        return val

    return {
        "id":          str(row.get("id") or ""),
        "incident_id": str(row.get("incident_id") or ""),
        "action_type": _ACTION_TYPE_MAP.get(action_type_raw, action_type_raw.upper()),
        "status":      _STATUS_MAP.get(status_raw, status_raw.upper()),
        "started_at":  _iso(row.get("started_at")),
        "finished_at": _iso(row.get("completed_at")),   # DB col is completed_at
        "summary":     summary,
        "output":      output,
        "link":        link,
        # Bonus: include trace_id if the query joined it
        "trace_id":    row.get("trace_id"),
    }


@bp.get("")
def list_actions():
    """GET /api/actions?limit=200"""
    limit = min(int(request.args.get("limit", 200)), 500)
    try:
        rows = postgres.list_actions(limit=limit)
        return jsonify([_normalize(r) for r in rows])
    except Exception as exc:
        logger.error("list_actions error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@bp.get("/incident/<incident_id>")
def get_actions_for_incident(incident_id: str):
    """GET /api/actions/incident/<incident_id>"""
    try:
        rows = postgres.get_actions_for_incident(incident_id)
        return jsonify([_normalize(r) for r in rows])
    except Exception as exc:
        logger.error("get_actions_for_incident error: %s", exc)
        return jsonify({"error": str(exc)}), 500
