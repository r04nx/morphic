"""Incident routes for Morphic backend"""
from datetime import datetime
from flask import jsonify, request

# Valid status values the frontend understands
_VALID_STATUSES = {
    "NEW", "TRIAGED", "RCA_PENDING", "RCA_READY",
    "ACTIONS_RUNNING", "RESOLVED", "SUPPRESSED",
}

# Map DB status values -> frontend status values (per frontend spec)
_STATUS_MAP = {
    "active":        "RCA_READY",
    "investigating": "ACTIONS_RUNNING",
    "resolved":      "RESOLVED",
    "healed":        "RESOLVED",
    "suppressed":    "SUPPRESSED",
    "new":           "NEW",
    "triaged":       "TRIAGED",
    "rca_pending":   "RCA_PENDING",
}

_VALID_BLAST = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def _normalize_incident(raw: dict) -> dict:
    """
    Coerce a raw PostgreSQL row dict into the shape the frontend expects:
      - blast_radius  : one of LOW/MEDIUM/HIGH/CRITICAL  (never null)
      - confidence_score : float 0–1                     (never null/NaN)
      - status        : one of the 7 valid frontend values
      - summary       : short human-readable string
    """
    inc = dict(raw)

    # ── blast_radius: pass through exactly as stored ─────────────────
    br = inc.get("blast_radius")
    if br and str(br).upper().strip() in _VALID_BLAST:
        inc["blast_radius"] = str(br).upper().strip()
    else:
        inc["blast_radius"] = "MEDIUM"

    # ── confidence_score: pass through as float ───────────────────────
    raw_score = inc.get("confidence_score")
    try:
        score = float(raw_score)
        if score != score:   # NaN
            score = 0.0
        score = max(0.0, min(1.0, score))
    except (TypeError, ValueError):
        score = 0.0
    inc["confidence_score"] = round(score, 4)

    # ── status: map DB values to frontend enum ────────────────────────
    raw_status = str(inc.get("status") or "active").strip()
    inc["status"] = (
        raw_status if raw_status in _VALID_STATUSES
        else _STATUS_MAP.get(raw_status.lower(), "RCA_READY")
    )

    # ── summary: classification only, no template ─────────────────────
    # Priority: stored summary > classification > trace_id
    stored_summary = (inc.get("summary") or "").strip()
    classification  = (inc.get("classification") or "").strip()
    trace_id        = (inc.get("trace_id") or "").strip()
    inc["summary"] = stored_summary or classification or trace_id or "Incident"

    # ── datetime serialisation ────────────────────────────────────────
    for field in ("timestamp", "created_at", "updated_at"):
        val = inc.get(field)
        if isinstance(val, datetime):
            inc[field] = val.isoformat()

    return inc


def register_incident_routes(app, incident_manager):
    """Register incident routes"""

    @app.route('/api/incidents', methods=['GET', 'POST'])
    def incidents():
        """Handle incidents"""
        if request.method == 'GET':
            try:
                limit  = int(request.args.get('limit', 50))
                offset = int(request.args.get('offset', 0))
                # Optional severity filter: ?blast_radius=CRITICAL
                br_filter = request.args.get('blast_radius', '').strip().upper() or None
                if br_filter and br_filter not in _VALID_BLAST:
                    return jsonify({"error": f"Invalid blast_radius filter '{br_filter}'. Use one of: {sorted(_VALID_BLAST)}"}), 400

                raw        = incident_manager.list_incidents(limit, offset, blast_radius_filter=br_filter)
                normalized = [_normalize_incident(inc) for inc in raw]
                return jsonify({
                    "incidents": normalized,
                    "total":     len(normalized),
                    "limit":     limit,
                    "offset":    offset,
                    "filter":    {"blast_radius": br_filter} if br_filter else {},
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        elif request.method == 'POST':
            try:
                incident_data = request.get_json()
                if not incident_data or not incident_data.get('trace_id'):
                    return jsonify({"error": "trace_id is required"}), 400
                incident = incident_manager.create_incident(incident_data)
                return jsonify(_normalize_incident(incident)), 201
            except Exception as e:
                return jsonify({"error": str(e)}), 500


    @app.route('/api/incidents/<incident_id>')
    def get_incident(incident_id):
        """
        Get a single incident by UUID id or trace_id.
        Returns: { incident, rca?, actions }
        """
        try:
            raw = incident_manager.get_incident(incident_id)
            if not raw:
                return jsonify({"error": "Incident not found"}), 404

            inc = _normalize_incident(raw)

            # Extract rca_json → rca (frontend expects it as a sibling key)
            rca = inc.pop("rca_json", None)

            # Extract actions → actions (also a sibling key)
            actions = inc.pop("actions", [])

            # Serialize datetime objects inside actions
            clean_actions = []
            for a in (actions or []):
                ca = dict(a)
                for field in ("started_at", "completed_at", "created_at"):
                    val = ca.get(field)
                    if isinstance(val, datetime):
                        ca[field] = val.isoformat()
                clean_actions.append(ca)

            return jsonify({
                "incident": inc,
                "rca":      rca,       # None if no RCA yet → frontend shows "RCA not ready"
                "actions":  clean_actions,
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500


    @app.route('/api/incidents/<incident_id>/actions/github-pr', methods=['POST'])
    def trigger_github_pr(incident_id):
        """POST /api/incidents/<incident_id>/actions/github-pr"""
        try:
            raw = incident_manager.get_incident(incident_id)
            if not raw:
                return jsonify({"error": "Incident not found"}), 404

            rca_json = raw.get("rca_json") or {}
            # Ensure trace_id is present in the rca payload
            rca_json["trace_id"]    = rca_json.get("trace_id") or raw.get("trace_id")
            rca_json["incident_id"] = str(raw.get("id") or incident_id)

            # Import from the morphic sub-package (has PyGithub)
            import sys, os as _os
            _mb = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "morphic", "backend")
            if _mb not in sys.path:
                sys.path.insert(0, _mb)
            from agents.github_pr import raise_pr

            pr_url = raise_pr(rca_json)

            if pr_url:
                return jsonify({"success": True, "pr_url": pr_url})
            return jsonify({"success": False, "error": "PR creation failed or GITHUB_TOKEN not configured"}), 422
        except Exception as e:
            return jsonify({"error": str(e)}), 500


    @app.route('/api/incidents/<incident_id>/actions/email', methods=['POST'])
    def trigger_email_alert(incident_id):
        """POST /api/incidents/<incident_id>/actions/email"""
        try:
            raw = incident_manager.get_incident(incident_id)
            if not raw:
                return jsonify({"error": "Incident not found"}), 404

            rca_json = raw.get("rca_json") or {}
            rca_json["trace_id"]    = rca_json.get("trace_id") or raw.get("trace_id")
            rca_json["incident_id"] = str(raw.get("id") or incident_id)

            import sys, os as _os
            _mb = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "morphic", "backend")
            if _mb not in sys.path:
                sys.path.insert(0, _mb)
            from agents.notification import send_alert

            result = send_alert(rca=rca_json, incident=dict(raw))

            if result.get("success"):
                return jsonify({"success": True, "email": result.get("email"), "telegram": result.get("telegram")})
            return jsonify({"success": False, "error": result.get("error", "Email send failed")}), 422
        except Exception as e:
            return jsonify({"error": str(e)}), 500


    @app.route('/api/logs', methods=['GET', 'POST'])
    def logs():
        """Handle log operations"""
        if request.method == 'GET':
            try:
                import requests as _req
                import os
                response = _req.get(
                    os.getenv('LOG_API_URL', 'https://hackathonps-ykxr.onrender.com/logs'),
                    timeout=10,
                )
                if response.status_code == 200:
                    log_data = response.json()
                    return jsonify({
                        "logs":      log_data if isinstance(log_data, list) else [log_data],
                        "source":    "external_api",
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                return jsonify({"error": f"API returned {response.status_code}"}), 502
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        elif request.method == 'POST':
            try:
                data = request.get_json()
                incident_id = data.get('incident_id')
                log_data    = data.get('log_data')
                if not incident_id or not log_data:
                    return jsonify({"error": "incident_id and log_data are required"}), 400
                log_entry = incident_manager.add_incident_log(incident_id, log_data)
                return jsonify(log_entry), 201
            except Exception as e:
                return jsonify({"error": str(e)}), 500
