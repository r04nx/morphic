"""Log analysis routes for Morphic backend"""
from datetime import datetime
from flask import jsonify, request


def register_analyze_routes(app, log_analyzer):
    """Register log analysis routes"""
    
    @app.route('/api/analyze', methods=['POST'])
    def analyze_logs():
        """Analyze logs using LogAI"""
        try:
            data = request.get_json()
            logs = data.get('logs', [])
            
            if not logs:
                return jsonify({"error": "No logs provided"}), 400
            
            analysis = log_analyzer.analyze_logs(logs)
            return jsonify(analysis)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
