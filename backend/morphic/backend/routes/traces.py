"""
/api/traces  — trace event timeline
"""

import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from db import postgres, neo4j_client

logger = logging.getLogger(__name__)
bp = Blueprint("traces", __name__, url_prefix="/api/traces")
graph_bp = Blueprint("graph", __name__, url_prefix="/api/graph")


def _serialize_row(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


@bp.get("/<trace_id>/events")
def get_trace_events(trace_id: str):
    """GET /api/traces/<trace_id>/events?limit=500"""
    limit = min(int(request.args.get("limit", 500)), 1000)
    try:
        rows = postgres.get_trace_events(trace_id, limit=limit)
        return jsonify([_serialize_row(r) for r in rows])
    except Exception as exc:
        logger.error("get_trace_events error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@bp.get("/<trace_id>/graph")
def get_trace_graph(trace_id: str):
    """GET /api/traces/<trace_id>/graph — Neo4j relationship graph for a trace."""
    try:
        graph = neo4j_client.get_incident_graph(trace_id)
        return jsonify(graph)
    except Exception as exc:
        logger.error("get_trace_graph error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@graph_bp.get("/incidents")
def get_graph_incidents():
    """GET /api/graph/incidents"""
    try:
        graph = neo4j_client.get_all_incidents_cytoscape()
        return jsonify(graph)
    except Exception as exc:
        logger.error("get_graph_incidents error: %s", exc)
        return jsonify({"error": str(exc)}), 500
