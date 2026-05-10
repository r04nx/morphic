"""Actions routes for Morphic backend"""

import json
from datetime import datetime

from flask import jsonify, request
from psycopg2.extras import RealDictCursor


def _serialize_action(row: dict) -> dict:
    res = dict(row)
    for k in ("started_at", "completed_at", "created_at"):
        if isinstance(res.get(k), datetime):
            res[k] = res[k].isoformat()
    if isinstance(res.get("details"), str):
        try:
            res["details"] = json.loads(res["details"])
        except Exception:
            pass
    return res


def register_action_routes(app, db_manager):
    """Register /api/actions routes"""

    @app.route('/api/actions', methods=['GET'])
    def list_actions():
        try:
            limit = request.args.get('limit', 200, type=int)
            limit = min(max(limit, 1), 500)

            with db_manager.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT ra.id, ra.incident_id, ra.action_type, ra.status,
                           ra.details, ra.started_at, ra.completed_at, ra.created_at,
                           i.trace_id
                    FROM remediation_actions ra
                    JOIN incidents i ON i.id = ra.incident_id
                    ORDER BY ra.created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cursor.fetchall()

            return jsonify([_serialize_action(r) for r in rows])
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/actions/incident/<incident_id>', methods=['GET'])
    def list_actions_for_incident(incident_id):
        try:
            with db_manager.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT id, incident_id, action_type, status, details,
                           started_at, completed_at, created_at
                    FROM remediation_actions
                    WHERE incident_id = %s
                    ORDER BY created_at DESC
                    """,
                    (incident_id,),
                )
                rows = cursor.fetchall()

            return jsonify([_serialize_action(r) for r in rows])
        except Exception as e:
            return jsonify({"error": str(e)}), 500
