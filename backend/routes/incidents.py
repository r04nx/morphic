"""
/api/incidents  — CRUD + manual action triggers
"""

import json
import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from db import postgres
from agents import notification, github_pr
from config import Config

logger = logging.getLogger(__name__)
bp = Blueprint("incidents", __name__, url_prefix="/api/incidents")


def _serialize(row: dict) -> dict:
    """Convert DB row to JSON-safe dict."""
    out = {}
    for k, v in row.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, str) and k == "rca_json":
            try:
                out[k] = json.loads(v)
            except Exception:
                out[k] = v
        else:
            out[k] = v
    return out


@bp.get("")
def list_incidents():
    """GET /api/incidents?limit=50&offset=0"""
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = int(request.args.get("offset", 0))
    try:
        rows = postgres.list_incidents(limit=limit, offset=offset)
        return jsonify([_serialize(r) for r in rows])
    except Exception as exc:
        logger.error("list_incidents error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@bp.get("/<incident_id>")
def get_incident(incident_id: str):
    """GET /api/incidents/<incident_id>"""
    try:
        row = postgres.get_incident_by_id(incident_id)
        if not row:
            return jsonify({"error": "Incident not found"}), 404
        return jsonify(_serialize(row))
    except Exception as exc:
        logger.error("get_incident error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@bp.post("/<incident_id>/actions/email")
def trigger_email(incident_id: str):
    """POST /api/incidents/<incident_id>/actions/email — manually resend alert email."""
    try:
        row = postgres.get_incident_by_id(incident_id)
        if not row:
            return jsonify({"error": "Incident not found"}), 404

        rca_json = row.get("rca_json")
        if isinstance(rca_json, str):
            try:
                rca_json = json.loads(rca_json)
            except Exception:
                rca_json = {}
        rca_json = rca_json or {}

        # Build a minimal RCA if we don't have one
        if not rca_json.get("classification"):
            rca_json = {
                "trace_id":        row.get("trace_id"),
                "classification":  row.get("classification") or "Unknown",
                "blast_radius":    row.get("blast_radius") or "MEDIUM",
                "root_cause":      row.get("root_cause") or row.get("summary") or "",
                "impact":          row.get("impact") or "",
                "confidence_score": float(row.get("confidence_score") or 0),
                "log_signals":     {"service": row.get("service", "")},
                "suggested_fix":   {},
                "github_pr":       {},
            }

        incident_ctx = {"incident_id": incident_id, "trace_id": row.get("trace_id")}
        result = notification.send_alert(rca_json, incident_ctx)
        status = 200 if result["success"] else 500
        return jsonify(result), status
    except Exception as exc:
        logger.error("trigger_email error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@bp.post("/<incident_id>/actions/github-pr")
def trigger_github_pr(incident_id: str):
    """POST /api/incidents/<incident_id>/actions/github-pr — manually open a PR."""
    try:
        row = postgres.get_incident_by_id(incident_id)
        if not row:
            return jsonify({"error": "Incident not found"}), 404

        rca_json = row.get("rca_json")
        if isinstance(rca_json, str):
            try:
                rca_json = json.loads(rca_json)
            except Exception:
                rca_json = {}
        rca_json = rca_json or {}

        incident_ctx = {"incident_id": incident_id, "trace_id": row.get("trace_id")}
        result = github_pr.create_pr(
            incident_ctx,
            rca_json,
            incident_id=incident_id,
            dashboard_url=Config.DASHBOARD_URL,
        )
        status = 200 if result.get("success") else 500
        return jsonify(result), status
    except Exception as exc:
        logger.error("trigger_github_pr error: %s", exc)
        return jsonify({"error": str(exc)}), 500
