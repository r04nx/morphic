#!/usr/bin/env python3
"""
Morphic Backend - AI Incident Assistant
Flask application with PostgreSQL, Neo4j, Redis, and LogAI integration
Modular architecture
"""

import os
import sys
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import configuration
from config.settings import Config

# Import models and services
from models.database import DatabaseManager
from models.incident import IncidentManager
from models.monitor import MonitorManager

# Import services
from services.log_analysis import LogAIAnalyzer
from services.monitor_checker import MonitorChecker
from services.incident_service import get_incident_service
from services.claude_agent import claude_agent_service
from services.notifications import NotificationManager

# Import routes
from routes.health import register_health_routes
from routes.incidents import register_incident_routes
from routes.monitors import register_monitor_routes
from routes.analyze import register_analyze_routes
from routes.agent import register_agent_routes
from routes.notifications import register_notification_routes
from routes.actions import register_action_routes
from routes.agent_runs import register_agent_runs_routes
from routes.github import register_github_routes

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
CORS(app)

# Initialize database manager
db_manager = DatabaseManager()
db_manager.connect_all()

# Initialize managers
incident_manager = IncidentManager(db_manager)
monitor_manager = MonitorManager(db_manager)
log_analyzer = LogAIAnalyzer()

# Initialize services
incident_service = get_incident_service(db_manager)
notification_manager = NotificationManager(db_manager)

# Import and initialize log tailer and agent orchestrator (if available)
TAILER_ENABLED = False
tailer_registry = None
agent_orchestrator = None

try:
    from log_tailer import TailerRegistry
    from agent_orchestrator import AgentOrchestrator
    agent_orchestrator = AgentOrchestrator(db_manager)
    import asyncio
    import threading

    def _update_agent_run_status(trace_id: str, status: str, pr_url: str = None, error_message: str = None):
        """Helper function to update agent run status in database."""
        try:
            with db_manager.postgres_conn.cursor() as cur:
                if pr_url:
                    cur.execute(
                        """UPDATE agent_runs 
                        SET status=%s, github_pr_url=%s, completed_at=NOW()
                        WHERE trace_id=%s AND status != 'COMPLETED'""",
                        (status, pr_url, trace_id)
                    )
                elif error_message:
                    cur.execute(
                        """UPDATE agent_runs 
                        SET status=%s, error_message=%s, completed_at=NOW()
                        WHERE trace_id=%s AND status != 'COMPLETED'""",
                        (status, error_message, trace_id)
                    )
                else:
                    cur.execute(
                        """UPDATE agent_runs 
                        SET status=%s 
                        WHERE trace_id=%s AND status != 'COMPLETED'""",
                        (status, trace_id)
                    )
                db_manager.postgres_conn.commit()
        except Exception as e:
            print(f"Failed to update agent run status: {e}")
            try:
                db_manager.postgres_conn.rollback()
            except:
                pass

    def _on_anomaly(monitor_id, trace_id, logs, analysis, github_owner, github_repo, github_token, github_branch):
        """Callback fired when a tailer detects an anomaly."""
        print(f"🚨 Anomaly on monitor {monitor_id} → creating incident for trace {trace_id}")
        
        def _handle_async():
            asyncio.run(_handle_incident_async(
                monitor_id, trace_id, logs, analysis, github_owner, github_repo, github_token, github_branch
            ))
        
        # Run async handler in a thread
        thread = threading.Thread(target=_handle_async, daemon=True)
        thread.start()
    
    async def _handle_incident_async(monitor_id, trace_id, logs, analysis, github_owner, github_repo, github_token, github_branch):
        """Async handler for incident creation and Claude agent."""
        # Step 1: Create incident
        incident_result = incident_service.create_incident_from_anomaly(
            monitor_id=monitor_id,
            trace_id=trace_id,
            logs=logs,
            analysis=analysis,
            github_owner=github_owner,
            github_repo=github_repo,
            github_branch=github_branch,
        )
        
        if incident_result.get("status") == "error":
            print(f"❌ Failed to create incident: {incident_result.get('message')}")
            return
        
        incident_id = incident_result["incident_id"]
        print(f"✅ Created incident {incident_id}")
        
        # Step 2: Send notifications
        try:
            notification_manager.send_incident_alert(
                incident_id=incident_id,
                trace_id=trace_id,
                severity=incident_result["severity"],
                rca=incident_result["rca"],
                logs=logs[:5],  # Send first 5 logs as context
            )
            print(f"✅ Sent notifications for incident {incident_id}")
        except Exception as e:
            print(f"⚠️  Failed to send notifications: {e}")
        
        # Step 3: Trigger Claude agent for remediation
        try:
            print(f"🤖 Starting Claude agent for incident {incident_id}")
            
            # Update agent run status to RUNNING
            _update_agent_run_status(trace_id, 'RUNNING')
            
            # Get error details from logs
            error_log = next((l for l in logs if l.get('level', '').upper() in ('ERROR', 'CRITICAL')), logs[0] if logs else {})
            
            agent_result = await claude_agent_service.handle_incident(
                incident_id=incident_id,
                trace_id=trace_id,
                error_type=error_log.get('error_type', 'UNKNOWN'),
                log_message=error_log.get('message', ''),
                service=error_log.get('service', 'unknown'),
                github_owner=github_owner,
                github_repo=github_repo,
                github_token=github_token,
                github_branch=github_branch,
                additional_context={
                    'rca': incident_result["rca"].get('root_cause', ''),
                    'suggested_fix': incident_result["rca"].get('suggested_fix', {}),
                }
            )
            
            # Update incident with agent results
            if agent_result.get("status") == "completed":
                incident_service.update_incident_status(
                    incident_id,
                    "IN_PROGRESS",
                    metadata={
                        "agent_run": agent_result,
                        "pr_url": agent_result.get("pr_url"),
                    }
                )
                # Update agent run status
                _update_agent_run_status(trace_id, 'PR_CREATED', pr_url=agent_result.get("pr_url"))
                print(f"✅ Claude agent completed for incident {incident_id}")
                print(f"   PR URL: {agent_result.get('pr_url', 'N/A')}")
            else:
                incident_service.update_incident_status(
                    incident_id,
                    "FAILED",
                    metadata={"agent_error": agent_result.get("message")}
                )
                _update_agent_run_status(trace_id, 'FAILED', error_message=agent_result.get("message"))
                print(f"❌ Claude agent failed for incident {incident_id}")
                
        except Exception as e:
            print(f"❌ Claude agent error: {e}", exc_info=True)
            incident_service.update_incident_status(
                incident_id,
                "FAILED",
                metadata={"agent_error": str(e)}
            )
            _update_agent_run_status(trace_id, 'FAILED', error_message=str(e))

    tailer_registry = TailerRegistry(db_manager, _on_anomaly)
    TAILER_ENABLED = True
    print("✅ Log tailer and agent orchestrator initialised")
except Exception as _tailer_init_err:
    TAILER_ENABLED = False
    tailer_registry = None
    agent_orchestrator = None
    print(f"⚠️  Log tailer unavailable: {_tailer_init_err}")

# Initialize monitor checker (background monitoring)
monitor_checker = MonitorChecker(
    monitor_manager,
    interval_seconds=Config.MONITOR_CHECK_INTERVAL,
    tailer_registry=tailer_registry,
    tailer_enabled=TAILER_ENABLED,
)
monitor_checker.start()

# Register routes
register_health_routes(app, db_manager)
register_incident_routes(app, incident_manager)
register_monitor_routes(app, monitor_manager, tailer_registry, TAILER_ENABLED)
register_analyze_routes(app, log_analyzer)
register_notification_routes(app, monitor_manager)
register_action_routes(app, db_manager)
register_agent_runs_routes(app, db_manager)
if agent_orchestrator:
    register_agent_routes(app, agent_orchestrator)
register_github_routes(app)

@app.route('/')
def index():
    """Health check and API info"""
    return jsonify({
        "service": "Morphic Backend API",
        "version": "2.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "health": "/api/health",
            "incidents": "/api/incidents",
            "analyze": "/api/analyze",
            "logs": "/api/logs",
            "monitors": "/api/monitors"
        }
    })

@app.route('/api/test-db-connections')
def test_db_connections():
    """Test all database connections"""
    results = {}
    
    # Test PostgreSQL
    try:
        with db_manager.postgres_conn.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
        results["postgres"] = {
            "status": "connected",
            "version": version[:50] + "..."
        }
    except Exception as e:
        results["postgres"] = {
            "status": "failed",
            "error": str(e)
        }
    
    # Test Neo4j
    try:
        with db_manager.neo4j_driver.session() as session:
            session.run("RETURN 1")
        results["neo4j"] = {
            "status": "connected"
        }
    except Exception as e:
        results["neo4j"] = {
            "status": "failed",
            "error": str(e)
        }
    
    # Test Redis
    try:
        db_manager.redis_client.ping()
        results["redis"] = {
            "status": "connected"
        }
    except Exception as e:
        results["redis"] = {
            "status": "failed",
            "error": str(e)
        }
    
    return jsonify(results)

# Cleanup on shutdown
import atexit
atexit.register(monitor_checker.stop)
atexit.register(db_manager.close_connections)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=Config.FLASK_DEBUG)
