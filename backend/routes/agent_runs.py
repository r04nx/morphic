"""
Agent Runs API Routes
Endpoints for tracking Claude agent runs and PR status
"""
from flask import Blueprint, jsonify, request
import logging

logger = logging.getLogger(__name__)

agent_runs_bp = Blueprint('agent_runs', __name__)


def register_agent_runs_routes(app, db_manager):
    """Register agent runs routes with the Flask app."""
    
    @agent_runs_bp.route('/api/agent-runs', methods=['GET'])
    def list_agent_runs():
        """List all agent runs with optional filtering."""
        try:
            limit = request.args.get('limit', 50, type=int)
            status = request.args.get('status')
            monitor_id = request.args.get('monitor_id')
            
            with db_manager.postgres_conn.cursor() as cur:
                query = "SELECT * FROM agent_runs"
                params = []
                
                conditions = []
                if status:
                    conditions.append("status = %s")
                    params.append(status)
                if monitor_id:
                    conditions.append("monitor_id = %s")
                    params.append(monitor_id)
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                query += " ORDER BY triggered_at DESC LIMIT %s"
                params.append(limit)
                
                cur.execute(query, params)
                rows = cur.fetchall()
                
                # Get column names
                col_names = [desc[0] for desc in cur.description]
                
                runs = []
                for row in rows:
                    run_dict = dict(zip(col_names, row))
                    runs.append(run_dict)

                return jsonify(runs)
        except Exception as e:
            logger.error(f"Failed to list agent runs: {e}")
            return jsonify({"error": str(e)}), 500
    
    @agent_runs_bp.route('/api/agent-runs/<run_id>', methods=['GET'])
    def get_agent_run(run_id):
        """Get details of a specific agent run."""
        try:
            with db_manager.postgres_conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM agent_runs WHERE id = %s",
                    (run_id,)
                )
                row = cur.fetchone()
                
                if not row:
                    return jsonify({"error": "Agent run not found"}), 404
                
                col_names = [desc[0] for desc in cur.description]
                run_dict = dict(zip(col_names, row))

                return jsonify(run_dict)
        except Exception as e:
            logger.error(f"Failed to get agent run: {e}")
            return jsonify({"error": str(e)}), 500
    
    @agent_runs_bp.route('/api/agent-runs/trace/<trace_id>', methods=['GET'])
    def get_agent_run_by_trace(trace_id):
        """Get agent run by trace ID."""
        try:
            with db_manager.postgres_conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM agent_runs WHERE trace_id = %s ORDER BY triggered_at DESC LIMIT 1",
                    (trace_id,)
                )
                row = cur.fetchone()
                
                if not row:
                    return jsonify({"error": "Agent run not found for this trace"}), 404
                
                col_names = [desc[0] for desc in cur.description]
                run_dict = dict(zip(col_names, row))

                return jsonify(run_dict)
        except Exception as e:
            logger.error(f"Failed to get agent run by trace: {e}")
            return jsonify({"error": str(e)}), 500
    
    @agent_runs_bp.route('/api/agent-runs/incident/<incident_id>', methods=['GET'])
    def get_agent_runs_by_incident(incident_id):
        """Get agent runs for a specific incident."""
        try:
            with db_manager.postgres_conn.cursor() as cur:
                # First get the trace_id from the incident
                cur.execute(
                    "SELECT trace_id FROM incidents WHERE id = %s",
                    (incident_id,)
                )
                incident_row = cur.fetchone()
                
                if not incident_row:
                    return jsonify({"error": "Incident not found"}), 404
                
                trace_id = incident_row[0]
                
                # Then get agent runs for this trace
                cur.execute(
                    "SELECT * FROM agent_runs WHERE trace_id = %s ORDER BY triggered_at DESC",
                    (trace_id,)
                )
                rows = cur.fetchall()
                
                col_names = [desc[0] for desc in cur.description]
                runs = [dict(zip(col_names, row)) for row in rows]

                return jsonify(runs)
        except Exception as e:
            logger.error(f"Failed to get agent runs by incident: {e}")
            return jsonify({"error": str(e)}), 500
    
    @agent_runs_bp.route('/api/agent-runs/stats', methods=['GET'])
    def get_agent_run_stats():
        """Get statistics about agent runs."""
        try:
            with db_manager.postgres_conn.cursor() as cur:
                # Total runs
                cur.execute("SELECT COUNT(*) FROM agent_runs")
                total = cur.fetchone()[0]
                
                # By status
                cur.execute("""
                    SELECT status, COUNT(*) 
                    FROM agent_runs 
                    GROUP BY status
                """)
                by_status = {row[0]: row[1] for row in cur.fetchall()}
                
                # PRs created
                cur.execute("SELECT COUNT(*) FROM agent_runs WHERE github_pr_url IS NOT NULL")
                prs_created = cur.fetchone()[0]
                
                # Success rate
                cur.execute("""
                    SELECT COUNT(*) FROM agent_runs 
                    WHERE status IN ('COMPLETED', 'PR_CREATED')
                """)
                successful = cur.fetchone()[0]
                success_rate = (successful / total * 100) if total > 0 else 0
                
                return jsonify({
                    "total_runs": total,
                    "by_status": by_status,
                    "prs_created": prs_created,
                    "success_rate": round(success_rate, 2),
                })
        except Exception as e:
            logger.error(f"Failed to get agent run stats: {e}")
            return jsonify({"error": str(e)}), 500
    
    app.register_blueprint(agent_runs_bp)
