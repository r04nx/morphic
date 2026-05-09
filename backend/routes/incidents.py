"""Incident routes for Morphic backend"""
from datetime import datetime
from flask import jsonify, request


def register_incident_routes(app, incident_manager):
    """Register incident routes"""
    
    @app.route('/api/incidents', methods=['GET', 'POST'])
    def incidents():
        """Handle incidents"""
        if request.method == 'GET':
            try:
                limit = int(request.args.get('limit', 50))
                offset = int(request.args.get('offset', 0))
                incidents = incident_manager.list_incidents(limit, offset)
                return jsonify({
                    "incidents": incidents,
                    "total": len(incidents),
                    "limit": limit,
                    "offset": offset
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        elif request.method == 'POST':
            try:
                incident_data = request.get_json()
                if not incident_data or not incident_data.get('trace_id'):
                    return jsonify({"error": "trace_id is required"}), 400
                
                incident = incident_manager.create_incident(incident_data)
                return jsonify(incident), 201
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    @app.route('/api/incidents/<trace_id>')
    def get_incident(trace_id):
        """Get specific incident"""
        try:
            incident = incident_manager.get_incident(trace_id)
            if incident:
                return jsonify(incident)
            else:
                return jsonify({"error": "Incident not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/logs', methods=['GET', 'POST'])
    def logs():
        """Handle log operations"""
        if request.method == 'GET':
            # Fetch logs from external API
            try:
                import requests
                import os
                response = requests.get(os.getenv('LOG_API_URL', 'https://hackathonps-ykxr.onrender.com/logs'), timeout=10)
                if response.status_code == 200:
                    logs = response.json()
                    return jsonify({
                        "logs": logs if isinstance(logs, list) else [logs],
                        "source": "external_api",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                else:
                    return jsonify({"error": f"API returned {response.status_code}"}), 502
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        elif request.method == 'POST':
            # Store logs for an incident
            try:
                data = request.get_json()
                incident_id = data.get('incident_id')
                log_data = data.get('log_data')
                
                if not incident_id or not log_data:
                    return jsonify({"error": "incident_id and log_data are required"}), 400
                
                log_entry = incident_manager.add_incident_log(incident_id, log_data)
                return jsonify(log_entry), 201
            except Exception as e:
                return jsonify({"error": str(e)}), 500
