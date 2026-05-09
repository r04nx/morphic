"""Monitor routes for Morphic backend"""
from flask import jsonify, request
import base64
import requests
from requests.exceptions import RequestException


def register_monitor_routes(app, monitor_manager, tailer_registry=None, tailer_enabled=False):
    """Register monitor routes"""
    
    @app.route('/api/monitors', methods=['GET', 'POST'])
    def monitors_api():
        """Manage monitors"""
        if request.method == 'GET':
            try:
                monitors = monitor_manager.list_monitors()
                # Sync tailers whenever monitors are fetched
                if tailer_enabled and tailer_registry:
                    tailer_registry.sync_monitors(monitors)
                return jsonify(monitors)
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        elif request.method == 'POST':
            try:
                data = request.get_json()
                monitor = monitor_manager.create_monitor(data)
                # Start tailer for new monitor if logs_url is set
                if tailer_enabled and tailer_registry and monitor.get('logs_url'):
                    tailer_registry.sync_monitors(monitor_manager.list_monitors())
                return jsonify(monitor), 201
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    @app.route('/api/monitors/<monitor_id>', methods=['GET', 'PATCH', 'DELETE'])
    def monitor_detail_api(monitor_id):
        """Get, update, or delete monitor details"""
        if request.method == 'GET':
            try:
                monitor = monitor_manager.get_monitor(monitor_id)
                if not monitor:
                    return jsonify({"error": "Monitor not found"}), 404
                
                # Return in the format the frontend expects: { monitor, metrics }
                return jsonify({
                    "monitor": monitor,
                    "metrics": [] # Placeholder for now
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500
            
        elif request.method == 'PATCH':
            try:
                data = request.get_json()
                monitor = monitor_manager.update_monitor(monitor_id, data)
                if not monitor:
                    return jsonify({"error": "Monitor not found"}), 404
                # Re-sync tailers after update (github_repo/logs_url may have changed)
                if tailer_enabled and tailer_registry:
                    tailer_registry.sync_monitors(monitor_manager.list_monitors())
                return jsonify({
                    "monitor": monitor,
                    "metrics": []
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500
            
        elif request.method == 'DELETE':
            try:
                monitor_manager.delete_monitor(monitor_id)
                if tailer_enabled and tailer_registry:
                    tailer_registry.sync_monitors(monitor_manager.list_monitors())
                return '', 204
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    @app.route('/api/monitors/<monitor_id>/logs', methods=['GET'])
    def monitor_logs_api(monitor_id):
        """Get recent log entries for a monitor"""
        try:
            limit = request.args.get('limit', 100, type=int)
            logs = monitor_manager.get_monitor_logs(monitor_id, limit)
            return jsonify(logs)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/monitors/<monitor_id>/metrics', methods=['GET'])
    def monitor_metrics_api(monitor_id):
        """Get performance metrics (latency/uptime) for a monitor"""
        try:
            hours = request.args.get('hours', 24, type=int)
            metrics = monitor_manager.get_monitor_metrics(monitor_id, hours)
            return jsonify(metrics)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/monitors/test', methods=['POST'])
    def test_monitor():
        """Proxy for testing monitor connections to bypass CORS"""
        try:
            data = request.get_json()
            target_url = data.get('url')
            test_type = data.get('type') # 'health' or 'logs'
            auth_type = data.get('auth_type', 'NONE')
            bearer_token = data.get('bearer_token')
            username = data.get('username')
            password = data.get('password')
            
            if not target_url:
                return jsonify({"error": "URL is required"}), 400
                
            headers = {"Accept": "application/json"}
            if auth_type == 'BEARER' and bearer_token:
                headers["Authorization"] = f"Bearer {bearer_token}"
            elif auth_type == 'BASIC' and username and password:
                auth_str = f"{username}:{password}"
                encoded_auth = base64.b64encode(auth_str.encode()).decode()
                headers["Authorization"] = f"Basic {encoded_auth}"
                
            try:
                response = requests.get(target_url, headers=headers, timeout=10)
                
                result = {
                    "success": response.ok,
                    "status": response.status_code,
                }
                
                if test_type == 'logs' and response.ok:
                    try:
                        logs = response.json()
                        result["tail"] = logs
                    except:
                        result["tail"] = response.text[:5000]
                elif not response.ok:
                    result["message"] = f"HTTP {response.status_code}: {response.reason}"
                    
                return jsonify(result)
            except RequestException as e:
                return jsonify({
                    "success": False,
                    "status": 0,
                    "message": str(e)
                })
                
        except Exception as e:
            return jsonify({"error": str(e)}), 500
