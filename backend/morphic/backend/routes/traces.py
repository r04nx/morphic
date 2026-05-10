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
        
        # Fallback to postgres if Neo4j graph is empty
        if not graph.get("nodes"):
            logger.info("Neo4j graph empty, falling back to PostgreSQL incidents")
            try:
                pg_incidents = postgres.list_incidents(limit=100)
                nodes = {}
                edges = []
                
                for inc in pg_incidents:
                    i_id = f"incident-{inc.get('trace_id') or inc.get('id')}"
                    i_label = inc.get("classification") or inc.get("summary") or "Unknown Incident"
                    
                    if i_id not in nodes:
                        nodes[i_id] = {
                            "data": {
                                "id": str(i_id),
                                "label": str(i_label)[:30],
                                "type": "incident",
                                "severity": str(inc.get("blast_radius", "LOW")),
                                "confidence": float(inc.get("confidence_score") or 0.0),
                                "status": str(inc.get("status", "unknown")),
                                "trace_id": str(inc.get("trace_id", "")),
                                "root_cause": str(inc.get("root_cause", "")),
                                "classification": str(inc.get("classification", ""))
                            }
                        }
                    
                    service_name = inc.get("service")
                    if service_name:
                        s_id = f"service-{service_name}"
                        if s_id not in nodes:
                            nodes[s_id] = {
                                "data": {
                                    "id": str(s_id),
                                    "label": str(service_name),
                                    "type": "service"
                                }
                            }
                        
                        edge_id = f"edge-pg-{i_id}-{s_id}"
                        edges.append({
                            "data": {
                                "id": str(edge_id),
                                "source": str(i_id),
                                "target": str(s_id),
                                "label": "ORIGINATED_IN"
                            }
                        })
                
                graph = {
                    "nodes": list(nodes.values()),
                    "edges": edges
                }
            except Exception as pg_exc:
                logger.warning("PostgreSQL fallback failed: %s", pg_exc)
                
        return jsonify(graph)
    except Exception as exc:
        logger.error("get_graph_incidents error: %s", exc)
        return jsonify({"error": str(exc)}), 500
