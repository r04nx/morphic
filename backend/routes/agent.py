"""Agent routes for Morphic backend"""
from flask import jsonify, request
from datetime import datetime
from psycopg2.extras import RealDictCursor


def register_agent_routes(app, agent_orchestrator):
    """Register agent routes"""
    
    @app.route('/api/monitors/<monitor_id>/trigger-agent', methods=['POST'])
    def trigger_agent(monitor_id):
        """Trigger agent run for a monitor"""
        try:
            data = request.get_json() or {}
            trace_id = data.get('trace_id')
            logs = data.get('logs', [])
            analysis = data.get('analysis', {})
            github_repo = data.get('github_repo')
            github_token = data.get('github_token')
            github_branch = data.get('github_branch', 'main')
            
            # Get monitor details
            from models.monitor import MonitorManager
            monitor_manager = MonitorManager(app.db_manager)
            monitor = monitor_manager.get_monitor(monitor_id)
            
            if not monitor:
                return jsonify({"error": "Monitor not found"}), 404
            
            # Use monitor's GitHub settings if not provided
            if not github_repo:
                github_repo = monitor.get('github_repo')
            if not github_token:
                github_token = monitor.get('github_token')
            if not github_branch:
                github_branch = monitor.get('github_branch', 'main')
            
            # Trigger agent
            run_id = agent_orchestrator.trigger_async(
                monitor_id=monitor_id,
                trace_id=trace_id or f"manual-{datetime.now().isoformat()}",
                logs=logs,
                analysis=analysis,
                github_repo=github_repo,
                github_token=github_token,
                github_branch=github_branch
            )
            
            return jsonify({
                "run_id": run_id,
                "trace_id": trace_id or f"manual-{datetime.now().isoformat()}",
                "status": "QUEUED"
            })
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/agent-runs', methods=['GET'])
    def list_agent_runs():
        """List all agent runs"""
        try:
            monitor_id = request.args.get('monitor_id')
            limit = request.args.get('limit', 50, type=int)
            
            with app.db_manager.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query = """
                SELECT id, monitor_id, trace_id, status, triggered_at, completed_at, 
                       github_repo, github_pr_url, github_pr_number, rca_summary, error_message
                FROM agent_runs
                """
                params = []
                if monitor_id:
                    query += " WHERE monitor_id = %s"
                    params.append(monitor_id)
                query += " ORDER BY triggered_at DESC LIMIT %s"
                params.append(limit)
                
                cursor.execute(query, params)
                runs = cursor.fetchall()
                
                for run in runs:
                    if run.get('triggered_at'):
                        run['triggered_at'] = run['triggered_at'].isoformat()
                    if run.get('completed_at'):
                        run['completed_at'] = run['completed_at'].isoformat()
                        
                return jsonify(runs)
                
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/agent-runs/<run_id>', methods=['GET'])
    def get_agent_run(run_id):
        """Get a specific agent run"""
        try:
            with app.db_manager.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                SELECT id, monitor_id, trace_id, status, triggered_at, completed_at, 
                       github_repo, github_pr_url, github_pr_number, rca_summary, error_message
                FROM agent_runs WHERE id = %s
                """, (run_id,))
                run = cursor.fetchone()
                
                if not run:
                    return jsonify({"error": "Agent run not found"}), 404
                
                if run.get('triggered_at'):
                    run['triggered_at'] = run['triggered_at'].isoformat()
                if run.get('completed_at'):
                    run['completed_at'] = run['completed_at'].isoformat()
                    
                return jsonify(run)
                
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/monitors/<monitor_id>/agent-runs', methods=['GET'])
    def list_monitor_agent_runs(monitor_id):
        """List agent runs for a specific monitor"""
        try:
            limit = request.args.get('limit', 10, type=int)
            
            with app.db_manager.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                SELECT id, monitor_id, trace_id, status, triggered_at, completed_at, 
                       github_repo, github_pr_url, github_pr_number, rca_summary, error_message
                FROM agent_runs 
                WHERE monitor_id = %s
                ORDER BY triggered_at DESC 
                LIMIT %s
                """, (monitor_id, limit))
                runs = cursor.fetchall()
                
                for run in runs:
                    if run.get('triggered_at'):
                        run['triggered_at'] = run['triggered_at'].isoformat()
                    if run.get('completed_at'):
                        run['completed_at'] = run['completed_at'].isoformat()
                    
                return jsonify(runs)
                
        except Exception as e:
            return jsonify({"error": str(e)}), 500
