"""Orchestration routes for Morphic backend"""
from flask import jsonify, request
from datetime import datetime


def register_orchestrate_routes(app, orchestrator_service):
    """Register orchestration routes"""
    
    @app.route('/api/orchestrate', methods=['POST'])
    def orchestrate_incident():
        """
        Main orchestration endpoint for incident workflow.
        
        Request Body:
            {
                "trace_id": "string",
                "severity": "LOW|MEDIUM|HIGH|CRITICAL",
                "classification": "string",
                "root_cause": "string (optional)",
                "impact": "string (optional)",
                "confidence_score": float (optional),
                "logs": [] (optional),
                "monitor_id": "string (optional)",
                "github_repo": "string (optional)",
                "github_token": "string (optional)"
            }
        
        Response:
            {
                "trace_id": "string",
                "orchestration_id": "string",
                "timestamp": "string",
                "success": bool,
                "rca": {...},
                "alerts": {...},
                "remediation": {...}
            }
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({"error": "Request body required"}), 400
            
            # Validate required fields
            if not data.get('trace_id'):
                return jsonify({"error": "trace_id is required"}), 400
            
            if not data.get('severity'):
                return jsonify({"error": "severity is required"}), 400
            
            if not data.get('classification'):
                return jsonify({"error": "classification is required"}), 400
            
            # Execute orchestration
            result = orchestrator_service.orchestrate(data)
            
            if result.get('success'):
                return jsonify(result), 200
            else:
                return jsonify(result), 500
                
        except Exception as e:
            return jsonify({
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "success": False
            }), 500
    
    @app.route('/api/orchestrate/status', methods=['GET'])
    def orchestrate_status():
        """Get orchestrator service status and channel configuration"""
        try:
            status = orchestrator_service.get_status()
            return jsonify(status)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/orchestrate/test-channels', methods=['POST'])
    def test_alert_channels():
        """Test all configured alert channels"""
        try:
            results = orchestrator_service.test_channels()
            return jsonify({
                "results": results,
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/alerts/send', methods=['POST'])
    def send_alert():
        """
        Direct alert sending endpoint.
        
        Request Body:
            {
                "severity": "LOW|MEDIUM|HIGH|CRITICAL",
                "trace_id": "string",
                "classification": "string",
                "root_cause": "string",
                "impact": "string",
                "confidence_score": float,
                "channels": ["email", "slack", "webhook"] (optional)
            }
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({"error": "Request body required"}), 400
            
            # Build alert payload
            alert_payload = {
                'severity': data.get('severity', 'INFO'),
                'trace_id': data.get('trace_id', 'unknown'),
                'classification': data.get('classification', 'Alert'),
                'root_cause': data.get('root_cause', ''),
                'impact': data.get('impact', ''),
                'confidence_score': data.get('confidence_score', 0.0),
                'timestamp': datetime.utcnow().isoformat(),
                'blast_radius': data.get('severity', 'MEDIUM')
            }
            
            # Send to specified channels or all
            channels = data.get('channels')  # None = all enabled
            result = orchestrator_service.alert_service.send_alert(alert_payload, channels)
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
