"""Incident model and manager for Morphic backend"""
import json
from datetime import datetime
from psycopg2.extras import RealDictCursor


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
