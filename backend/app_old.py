#!/usr/bin/env python3
"""
Morphic Backend - AI Incident Assistant
Flask application with PostgreSQL, Neo4j, Redis, and LogAI integration
"""

import os
import sys
import json
import uuid
import threading
import time
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
import neo4j
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add LogAI to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'morphic_development_secret_key_2024')
CORS(app)

# Database connections
postgres_conn = None
neo4j_driver = None
redis_client = None

class DatabaseManager:
    """Manages all database connections for Morphic"""
    
    def __init__(self):
        self.postgres_conn = None
        self.neo4j_driver = None
        self.redis_client = None
    
    def connect_postgres(self):
        """Connect to PostgreSQL database"""
        try:
            self.postgres_conn = psycopg2.connect(
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=os.getenv('POSTGRES_PORT', '5432'),
                database=os.getenv('POSTGRES_DB', 'morphic'),
                user=os.getenv('POSTGRES_USER', 'morphic_user'),
                password=os.getenv('POSTGRES_PASSWORD', 'morphic_password_2024')
            )
            print("✅ PostgreSQL connected")
            return True
        except Exception as e:
            print(f"❌ PostgreSQL failed: {e}")
            return False
    
    def connect_neo4j(self):
        """Connect to Neo4j database"""
        try:
            self.neo4j_driver = neo4j.GraphDatabase.driver(
                os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
                auth=(os.getenv('NEO4J_USER', 'neo4j'), 
                      os.getenv('NEO4J_PASSWORD', 'morphic_neo4j_password_2024'))
            )
            # Test connection
            with self.neo4j_driver.session() as session:
                session.run("RETURN 1")
            print("✅ Neo4j connected")
            return True
        except Exception as e:
            print(f"❌ Neo4j failed: {e}")
            return False
    
    def connect_redis(self):
        """Connect to Redis cache"""
        try:
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=os.getenv('REDIS_PORT', 6379),
                password=os.getenv('REDIS_PASSWORD', 'morphic_redis_password_2024'),
                decode_responses=True
            )
            self.redis_client.ping()
            print("✅ Redis connected")
            return True
        except Exception as e:
            print(f"❌ Redis failed: {e}")
            return False
    
    def close_connections(self):
        """Close all database connections"""
        if self.postgres_conn:
            self.postgres_conn.close()
        if self.neo4j_driver:
            self.neo4j_driver.close()
        if self.redis_client:
            self.redis_client.close()

# Initialize database manager
db_manager = DatabaseManager()

# Initialize databases
print("Connecting to databases...")
success_count = 0
if db_manager.connect_postgres():
    success_count += 1
if db_manager.connect_neo4j():
    success_count += 1
if db_manager.connect_redis():
    success_count += 1
print(f"Databases connected: {success_count}/3\n")

class IncidentManager:
    """Manages incident operations"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def create_incident(self, incident_data):
        """Create a new incident"""
        try:
            with self.db.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query = """
                INSERT INTO incidents 
                (trace_id, timestamp, classification, root_cause, blast_radius, 
                 impact, confidence_score, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """
                cursor.execute(query, (
                    incident_data.get('trace_id'),
                    incident_data.get('timestamp', datetime.utcnow()),
                    incident_data.get('classification'),
                    incident_data.get('root_cause'),
                    incident_data.get('blast_radius'),
                    incident_data.get('impact'),
                    incident_data.get('confidence_score'),
                    incident_data.get('status', 'active')
                ))
                incident = cursor.fetchone()
                self.db.postgres_conn.commit()
                
                # Cache in Redis
                if self.db.redis_client:
                    self.db.redis_client.setex(
                        f"incident:{incident['trace_id']}", 
                        3600, 
                        json.dumps(dict(incident), default=str)
                    )
                
                return dict(incident)
        except Exception as e:
            self.db.postgres_conn.rollback()
            raise e
    
    def get_incident(self, trace_id):
        """Get incident by trace_id"""
        # Try cache first
        if self.db.redis_client:
            cached = self.db.redis_client.get(f"incident:{trace_id}")
            if cached:
                return json.loads(cached)
        
        # Query database
        try:
            with self.db.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query = "SELECT * FROM incidents WHERE trace_id = %s"
                cursor.execute(query, (trace_id,))
                incident = cursor.fetchone()
                
                if incident:
                    incident_dict = dict(incident)
                    # Cache in Redis
                    if self.db.redis_client:
                        self.db.redis_client.setex(
                            f"incident:{trace_id}", 
                            3600, 
                            json.dumps(incident_dict, default=str)
                        )
                    return incident_dict
                return None
        except Exception as e:
            raise e
    
    def list_incidents(self, limit=50, offset=0):
        """List incidents with pagination"""
        try:
            with self.db.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query = """
                SELECT * FROM incidents 
                ORDER BY timestamp DESC 
                LIMIT %s OFFSET %s
                """
                cursor.execute(query, (limit, offset))
                incidents = cursor.fetchall()
                return [dict(incident) for incident in incidents]
        except Exception as e:
            raise e
    
    def add_incident_log(self, incident_id, log_data):
        """Add log entry to incident timeline"""
        try:
            with self.db.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query = """
                INSERT INTO incident_logs 
                (incident_id, timestamp, service, endpoint, log_level, message, raw_log)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """
                cursor.execute(query, (
                    incident_id,
                    log_data.get('timestamp', datetime.utcnow()),
                    log_data.get('service'),
                    log_data.get('endpoint'),
                    log_data.get('log_level'),
                    log_data.get('message'),
                    json.dumps(log_data.get('raw_log', {}))
                ))
                log_entry = cursor.fetchone()
                self.db.postgres_conn.commit()
                return dict(log_entry)
        except Exception as e:
            self.db.postgres_conn.rollback()
            raise e


class MonitorManager:
    """Manages system monitor operations"""
    
    def __init__(self, db_manager):
        self.db = db_manager

    SERIALIZABLE_FIELDS = ['last_check', 'created_at', 'last_anomaly_at']
    JSON_FIELDS = ['notifications', 'workflows']

    def _serialize(self, monitor: dict) -> dict:
        """Convert a raw DB row dict to API-safe format."""
        res = dict(monitor)
        for key in self.SERIALIZABLE_FIELDS:
            if isinstance(res.get(key), datetime):
                res[key] = res[key].isoformat()
        for key in self.JSON_FIELDS:
            if isinstance(res.get(key), str):
                res[key] = json.loads(res[key])
            if not res.get(key):
                res[key] = []
        return res

    def create_monitor(self, data):
        """Create a new monitor"""
        try:
            with self.db.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                monitor_id = data.get('id', 'mon_' + str(uuid.uuid4())[:8])
                query = """
                INSERT INTO monitors 
                (id, name, url, logs_url, auth_type, status, uptime_pct, latency_ms,
                 last_check, notifications, workflows,
                 github_repo, github_token, github_branch, log_tail_enabled)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """
                cursor.execute(query, (
                    monitor_id,
                    data.get('name'),
                    data.get('url'),
                    data.get('logs_url'),
                    data.get('auth_type', 'NONE'),
                    data.get('status', 'UP'),
                    data.get('uptime_pct', 100.0),
                    data.get('latency_ms', 0),
                    data.get('last_check', datetime.utcnow()),
                    json.dumps(data.get('notifications', [])),
                    json.dumps(data.get('workflows', [])),
                    data.get('github_repo'),
                    data.get('github_token'),
                    data.get('github_branch', 'main'),
                    data.get('log_tail_enabled', True),
                ))
                monitor = cursor.fetchone()
                self.db.postgres_conn.commit()
                self.add_history(monitor_id, monitor['status'], monitor['latency_ms'])
                res = self._serialize(monitor)
                res['history'] = self.get_history(monitor_id)
                return res
        except Exception as e:
            self.db.postgres_conn.rollback()
            raise e
        
    def get_monitor(self, monitor_id):
        """Get a single monitor with history"""
        try:
            with self.db.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM monitors WHERE id = %s", (monitor_id,))
                m = cursor.fetchone()
                if not m:
                    return None
                monitor = self._serialize(m)
                monitor['history'] = self.get_history(monitor_id)
                return monitor
        except Exception as e:
            raise e

    def list_monitors(self):
        """List all monitors with their recent history"""
        try:
            with self.db.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM monitors ORDER BY created_at DESC")
                monitors = cursor.fetchall()
                res = []
                for m in monitors:
                    monitor = self._serialize(m)
                    monitor['history'] = self.get_history(m['id'])
                    res.append(monitor)
                return res
        except Exception as e:
            raise e

    def add_history(self, monitor_id, status, latency_ms):
        """Add a history entry for a monitor"""
        try:
            with self.db.postgres_conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO monitor_history (monitor_id, status, latency_ms) VALUES (%s, %s, %s)",
                    (monitor_id, status, latency_ms)
                )
                self.db.postgres_conn.commit()
        except Exception as e:
            self.db.postgres_conn.rollback()
            print(f"Failed to add history: {e}")

    def get_history(self, monitor_id, limit=20):
        """Get recent history for a monitor"""
        try:
            with self.db.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT status, latency_ms, created_at FROM monitor_history WHERE monitor_id = %s ORDER BY created_at DESC LIMIT %s",
                    (monitor_id, limit)
                )
                history = cursor.fetchall()
                for h in history:
                    if isinstance(h['created_at'], datetime):
                        h['created_at'] = h['created_at'].isoformat()
                return history
        except Exception as e:
            print(f"Failed to get history: {e}")
            return []

    def update_monitor(self, monitor_id, data):
        """Update a monitor"""
        try:
            with self.db.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                fields = []
                values = []
                
                updatable_fields = [
                    'name', 'url', 'logs_url', 'auth_type', 'status',
                    'uptime_pct', 'latency_ms', 'github_repo', 'github_token',
                    'github_branch', 'log_tail_enabled', 'agent_run_status',
                ]
                for field in updatable_fields:
                    if field in data:
                        fields.append(f"{field} = %s")
                        values.append(data[field])
                
                if 'notifications' in data:
                    fields.append("notifications = %s")
                    values.append(json.dumps(data['notifications']))
                if 'workflows' in data:
                    fields.append("workflows = %s")
                    values.append(json.dumps(data['workflows']))
                
                if not fields:
                    return self.get_monitor(monitor_id)
                
                values.append(monitor_id)
                query = f"UPDATE monitors SET {', '.join(fields)}, last_check = CURRENT_TIMESTAMP WHERE id = %s RETURNING *"
                cursor.execute(query, values)
                monitor = cursor.fetchone()
                self.db.postgres_conn.commit()
                
                if not monitor:
                    return None
                if 'status' in data:
                    self.add_history(monitor_id, monitor['status'], monitor['latency_ms'])
                
                return self.get_monitor(monitor_id)
        except Exception as e:
            self.db.postgres_conn.rollback()
            raise e

    def delete_monitor(self, monitor_id):
        """Delete a monitor"""
        try:
            with self.db.postgres_conn.cursor() as cursor:
                cursor.execute("DELETE FROM monitors WHERE id = %s", (monitor_id,))
                self.db.postgres_conn.commit()
                return True
        except Exception as e:
            self.db.postgres_conn.rollback()
            raise e

class MonitorChecker:
    """Background thread to check monitor URLs and update status"""
    
    def __init__(self, monitor_manager, interval_seconds=30):
        self.monitor_manager = monitor_manager
        self.interval_seconds = interval_seconds
        self.running = False
        self.thread = None
    
    def check_url(self, url, timeout=5):
        """Check a URL and return status and latency"""
        try:
            start_time = datetime.utcnow()
            response = requests.get(url, timeout=timeout)
            end_time = datetime.utcnow()
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            
            if response.status_code < 400:
                return 'UP', latency_ms
            else:
                return 'DOWN', latency_ms
        except Exception as e:
            return 'DOWN', 0
    
    def calculate_uptime(self, monitor_id):
        """Calculate uptime percentage from history"""
        try:
            history = self.monitor_manager.get_history(monitor_id, limit=100)
            if not history:
                return 100.0
            
            up_count = sum(1 for h in history if h['status'] == 'UP')
            return round((up_count / len(history)) * 100, 2)
        except:
            return 100.0
    
    def check_all_monitors(self):
        """Check all monitors and update their status"""
        try:
            monitors = self.monitor_manager.list_monitors()
            for monitor in monitors:
                monitor_id = monitor['id']
                url = monitor.get('url')
                
                if not url:
                    continue
                
                status, latency_ms = self.check_url(url)
                uptime_pct = self.calculate_uptime(monitor_id)
                
                # Update monitor in database
                self.monitor_manager.update_monitor(monitor_id, {
                    'status': status,
                    'latency_ms': latency_ms,
                    'uptime_pct': uptime_pct
                })
        except Exception as e:
            print(f"Monitor check error: {e}")
    
    def run(self):
        """Run the monitoring loop"""
        while self.running:
            self.check_all_monitors()
            time.sleep(self.interval_seconds)
    
    def start(self):
        """Start the monitoring thread"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            print("✅ Monitor checker started")
    
    def stop(self):
        """Stop the monitoring thread"""
        self.running = False
        if self.thread:
            self.thread.join()
            print("⏹️ Monitor checker stopped")

class LogAIAnalyzer:
    """LogAI-based log analysis"""
    
    def __init__(self):
        self.logai_available = False
        try:
            import logai
            self.logai_available = True
            print("✅ LogAI available for analysis")
        except ImportError:
            print("⚠️ LogAI not available, using basic analysis")
    
    def analyze_logs(self, logs):
        """Analyze logs using LogAI or basic methods"""
        if not logs:
            return {"error": "No logs to analyze"}
        
        analysis = {
            "total_logs": len(logs),
            "timestamp": datetime.utcnow().isoformat(),
            "analysis": {}
        }
        
        # Basic analysis
        levels = {}
        services = {}
        error_patterns = []
        
        for log in logs:
            # Count log levels
            level = log.get('level', 'INFO')
            levels[level] = levels.get(level, 0) + 1
            
            # Count services
            service = log.get('service', 'unknown')
            services[service] = services.get(service, 0) + 1
            
            # Look for error patterns
            message = str(log.get('message', '')).lower()
            if any(keyword in message for keyword in ['error', 'exception', 'failed', 'timeout']):
                error_patterns.append({
                    'timestamp': log.get('timestamp'),
                    'service': service,
                    'level': level,
                    'message': log.get('message')[:200] + '...' if len(str(log.get('message', ''))) > 200 else log.get('message')
                })
        
        analysis["analysis"]["log_levels"] = levels
        analysis["analysis"]["services"] = services
        analysis["analysis"]["error_patterns"] = error_patterns
        analysis["analysis"]["error_rate"] = (levels.get('ERROR', 0) + levels.get('CRITICAL', 0)) / len(logs) * 100
        
        # Calculate recommendations
        recommendations = []
        if analysis["analysis"]["error_rate"] > 5:
            recommendations.append("High error rate detected - immediate attention required")
        elif analysis["analysis"]["error_rate"] > 2:
            recommendations.append("Elevated error rate - monitor closely")
        
        if error_patterns:
            recommendations.append(f"Found {len(error_patterns)} error patterns - investigate root causes")
        
        analysis["recommendations"] = recommendations
        
        return analysis

# Initialize managers
incident_manager = IncidentManager(db_manager)
monitor_manager = MonitorManager(db_manager)
log_analyzer = LogAIAnalyzer()

# Initialize monitor checker (background monitoring)
monitor_checker = MonitorChecker(monitor_manager, interval_seconds=30)
monitor_checker.start()

# Import new modules (lazy – avoids startup crash if deps missing)
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

# Routes
@app.route('/')
def index():
    """Health check and API info"""
    return jsonify({
        "service": "Morphic Backend API",
        "version": "1.0.0",
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

@app.route('/api/monitors', methods=['GET', 'POST'])
def monitors_api():
    """Manage monitors"""
    if request.method == 'GET':
        try:
            monitors = monitor_manager.list_monitors()
            # Sync tailers whenever monitors are fetched
            if TAILER_ENABLED and tailer_registry:
                tailer_registry.sync_monitors(monitors)
            return jsonify(monitors)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            monitor = monitor_manager.create_monitor(data)
            # Start tailer for new monitor if logs_url is set
            if TAILER_ENABLED and tailer_registry and monitor.get('logs_url'):
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
            if TAILER_ENABLED and tailer_registry:
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
            if TAILER_ENABLED and tailer_registry:
                tailer_registry.sync_monitors(monitor_manager.list_monitors())
            return '', 204
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/health')
def health_check():
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Check PostgreSQL
    try:
        with db_manager.postgres_conn.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status["services"]["postgres"] = "healthy"
    except:
        health_status["services"]["postgres"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check Neo4j
    try:
        with db_manager.neo4j_driver.session() as session:
            session.run("RETURN 1")
        health_status["services"]["neo4j"] = "healthy"
    except:
        health_status["services"]["neo4j"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        db_manager.redis_client.ping()
        health_status["services"]["redis"] = "healthy"
    except:
        health_status["services"]["redis"] = "unhealthy"
        health_status["status"] = "degraded"
    
    return jsonify(health_status)

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

@app.route('/api/logs', methods=['GET', 'POST'])
def logs():
    """Handle log operations"""
    if request.method == 'GET':
        # Fetch logs from external API
        try:
            import requests
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

@app.route('/api/monitors/test', methods=['POST'])
def test_monitor():
    """Proxy for testing monitor connections to bypass CORS"""
    try:
        import requests
        import base64
        from requests.exceptions import RequestException
        
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
            "version": version,
            "database": os.getenv('POSTGRES_DB')
        }
    except Exception as e:
        results["postgres"] = {"status": "error", "error": str(e)}
    
    # Test Neo4j
    try:
        with db_manager.neo4j_driver.session() as session:
            result = session.run("RETURN 'Neo4j working' AS status, version() AS version")
            record = result.single()
        results["neo4j"] = {
            "status": "connected",
            "status_message": record["status"],
            "version": str(record["version"]) if record.get("version") else "Unknown"
        }
    except Exception as e:
        results["neo4j"] = {"status": "error", "error": str(e)}
    
    # Test Redis
    try:
        info = db_manager.redis_client.info()
        results["redis"] = {
            "status": "connected",
            "version": info.get('redis_version'),
            "used_memory": info.get('used_memory_human'),
            "connected_clients": info.get('connected_clients')
        }
    except Exception as e:
        results["redis"] = {"status": "error", "error": str(e)}
    
    return jsonify(results)

# ─────────────────────────────────────────────────────────────
# Agent Runs & Log Entries Routes
# ─────────────────────────────────────────────────────────────

@app.route('/api/monitors/<monitor_id>/agent-runs', methods=['GET'])
def list_agent_runs(monitor_id):
    """List agent runs for a monitor."""
    if not agent_orchestrator:
        return jsonify([])
    try:
        limit = int(request.args.get('limit', 10))
        runs = agent_orchestrator.list_runs(monitor_id, limit)
        return jsonify(runs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/agent-runs/<run_id>', methods=['GET'])
def get_agent_run(run_id):
    """Get a specific agent run with full details."""
    if not agent_orchestrator:
        return jsonify({"error": "Agent orchestrator not available"}), 503
    try:
        run = agent_orchestrator.get_run(run_id)
        if not run:
            return jsonify({"error": "Run not found"}), 404
        return jsonify(run)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/monitors/<monitor_id>/trigger-agent', methods=['POST'])
def trigger_agent(monitor_id):
    """Manually trigger an agent run for a monitor."""
    if not agent_orchestrator:
        return jsonify({"error": "Agent orchestrator not available"}), 503
    try:
        monitor = monitor_manager.get_monitor(monitor_id)
        if not monitor:
            return jsonify({"error": "Monitor not found"}), 404

        body = request.get_json() or {}
        # Accept optional override logs from body, else use recent DB logs
        logs = body.get('logs', [])
        if not logs:
            # Pull last 50 log entries from DB
            try:
                from psycopg2.extras import RealDictCursor as _RDC
                with db_manager.postgres_conn.cursor(cursor_factory=_RDC) as cur:
                    cur.execute(
                        "SELECT log_level, message, raw, fetched_at FROM monitor_log_entries "
                        "WHERE monitor_id=%s ORDER BY fetched_at DESC LIMIT 50",
                        (monitor_id,)
                    )
                    rows = cur.fetchall()
                    logs = [dict(r) for r in rows]
            except Exception:
                pass

        analysis = {
            "anomaly_detected": True,
            "score": body.get('score', 0.8),
            "error_rate": body.get('error_rate', 0.2),
            "signals": body.get('signals', []),
            "manual_trigger": True,
        }

        import uuid as _uuid
        trace_id = body.get('trace_id') or f"manual-{monitor_id[:8]}-{_uuid.uuid4().hex[:8]}"
        run_id = agent_orchestrator.trigger_async(
            monitor_id=monitor_id,
            trace_id=trace_id,
            logs=logs,
            analysis=analysis,
            github_repo=monitor.get('github_repo'),
            github_token=monitor.get('github_token'),
            github_branch=monitor.get('github_branch', 'main'),
        )
        return jsonify({"run_id": run_id, "trace_id": trace_id, "status": "QUEUED"}), 202
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/monitors/<monitor_id>/logs', methods=['GET'])
def get_monitor_logs(monitor_id):
    """Fetch recent tailed log entries for a monitor."""
    try:
        limit = int(request.args.get('limit', 100))
        from psycopg2.extras import RealDictCursor as _RDC
        with db_manager.postgres_conn.cursor(cursor_factory=_RDC) as cur:
            cur.execute(
                """SELECT id, log_level, message, raw, fetched_at, anomaly_score, is_anomaly
                   FROM monitor_log_entries
                   WHERE monitor_id=%s
                   ORDER BY fetched_at DESC
                   LIMIT %s""",
                (monitor_id, limit)
            )
            rows = cur.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                if d.get('fetched_at'):
                    d['fetched_at'] = d['fetched_at'].isoformat()
                result.append(d)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tailer/status', methods=['GET'])
def tailer_status():
    """Get status of all active log tailers."""
    if not TAILER_ENABLED or not tailer_registry:
        return jsonify({"enabled": False, "tailers": {}})
    return jsonify({"enabled": True, "tailers": tailer_registry.get_status()})

@app.teardown_appcontext
def teardown_db(exception):
    """Clean up database connections"""
    pass  # Connections are managed by DatabaseManager

if __name__ == '__main__':
    print("🎯 Starting Morphic Backend Server...")
    app.run(host='0.0.0.0', port=5000, debug=True)
