"""Monitor model and manager for Morphic backend"""
import json
import uuid
from datetime import datetime, timezone
from psycopg2.extras import RealDictCursor
from services.notifications import NotificationManager

class MonitorManager:
    """Manages system monitor operations"""
    
    def __init__(self, db_manager, settings_manager=None):
        self.db = db_manager
        self.notification_manager = NotificationManager(settings_manager)

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
                    datetime.utcnow(),
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
                        h['timestamp'] = h['created_at'].isoformat()
                        del h['created_at']
                    else:
                        h['timestamp'] = h.get('created_at', '')
                        del h['created_at']
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

    def get_monitor_logs(self, monitor_id, limit=100):
        """Get recent log entries for a monitor"""
        try:
            with self.db.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """SELECT id, log_level, message, fetched_at, anomaly_score, is_anomaly, raw
                       FROM monitor_log_entries 
                       WHERE monitor_id = %s 
                       ORDER BY fetched_at DESC 
                       LIMIT %s""",
                    (monitor_id, limit)
                )
                logs = cursor.fetchall()
                formatted_logs = []
                for log in logs:
                    formatted_log = dict(log)
                    if isinstance(log['fetched_at'], datetime):
                        formatted_log['fetched_at'] = log['fetched_at'].isoformat()
                    
                    # Parse the raw JSON log from chaos-backend if available
                    if 'raw' in log and log['raw']:
                        try:
                            raw_data = log['raw']
                            if isinstance(raw_data, str):
                                import json
                                raw_data = json.loads(raw_data)
                            
                            # Merge structured fields from chaos-backend
                            formatted_log.update({
                                'timestamp': raw_data.get('timestamp', formatted_log['fetched_at']),
                                'trace_id': raw_data.get('trace_id'),
                                'service': raw_data.get('service'),
                                'level': raw_data.get('level', log.get('log_level', 'INFO')),
                                'error_type': raw_data.get('error_type'),
                                'class': raw_data.get('class')
                            })
                            formatted_log['message'] = raw_data.get('message', log.get('message', ''))
                        except Exception:
                            # Fallback to original fields if parsing fails
                            pass
                    
                    formatted_logs.append(formatted_log)
                return formatted_logs
        except Exception as e:
            print(f"Failed to get monitor logs: {e}")
            return []

    def get_monitor_metrics(self, monitor_id, hours=24):
        """Get performance metrics for a monitor over time"""
        try:
            with self.db.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Get history with timestamps
                cursor.execute(
                    """SELECT status, latency_ms, created_at
                       FROM monitor_history 
                       WHERE monitor_id = %s 
                       AND created_at >= NOW() - INTERVAL '%s hours'
                       ORDER BY created_at ASC""",
                    (monitor_id, hours)
                )
                history = cursor.fetchall()
                
                metrics = []
                for h in history:
                    timestamp = h['created_at'].isoformat() if isinstance(h['created_at'], datetime) else h['created_at']
                    metrics.append({
                        'timestamp': timestamp,
                        'latency': h['latency_ms'],
                        'status': h['status'],
                        'uptime': 100 if h['status'] == 'UP' else (50 if h['status'] == 'DEGRADED' else 0)
                    })
                
                return metrics
        except Exception as e:
            print(f"Failed to get monitor metrics: {e}")
            return []

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
