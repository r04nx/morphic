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
from models.settings import SettingsManager

# Import services
from services.log_analysis import LogAIAnalyzer
from services.monitor_checker import MonitorChecker

# Import routes
from routes.health import register_health_routes
from routes.incidents import register_incident_routes
from routes.monitors import register_monitor_routes
from routes.analyze import register_analyze_routes
from routes.agent import register_agent_routes
from routes.notifications import register_notification_routes
from routes.settings import register_settings_routes

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
CORS(app)

# Initialize database manager
db_manager = DatabaseManager()
db_manager.connect_all()

# Initialize managers
incident_manager = IncidentManager(db_manager)
settings_manager = SettingsManager(db_manager)
monitor_manager = MonitorManager(db_manager, settings_manager)
log_analyzer = LogAIAnalyzer()

# Initialize monitor checker (background monitoring)
monitor_checker = MonitorChecker(monitor_manager, interval_seconds=Config.MONITOR_CHECK_INTERVAL)
monitor_checker.start()

# Import and initialize log tailer and agent orchestrator (if available)
TAILER_ENABLED = False
tailer_registry = None
agent_orchestrator = None

try:
    from log_tailer import TailerRegistry
    from agent_orchestrator import AgentOrchestrator
    agent_orchestrator = AgentOrchestrator(db_manager)

    def _on_anomaly(monitor_id, trace_id, logs, analysis, github_repo, github_token, github_branch):
        """Callback fired when a tailer detects an anomaly."""
        print(f"🚨 Anomaly on monitor {monitor_id} → launching agent for trace {trace_id}")
        agent_orchestrator.trigger_async(
            monitor_id=monitor_id,
            trace_id=trace_id,
            logs=logs,
            analysis=analysis,
            github_repo=github_repo,
            github_token=github_token,
            github_branch=github_branch,
        )

    tailer_registry = TailerRegistry(db_manager, _on_anomaly)
    TAILER_ENABLED = True
    print("✅ Log tailer and agent orchestrator initialised")
except Exception as _tailer_init_err:
    TAILER_ENABLED = False
    tailer_registry = None
    agent_orchestrator = None
    print(f"⚠️  Log tailer unavailable: {_tailer_init_err}")

# Register routes
register_health_routes(app, db_manager)
register_incident_routes(app, incident_manager)
register_monitor_routes(app, monitor_manager, tailer_registry, TAILER_ENABLED)
register_analyze_routes(app, log_analyzer)
register_notification_routes(app, monitor_manager)
register_settings_routes(app, settings_manager)
if agent_orchestrator:
    register_agent_routes(app, agent_orchestrator)

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
