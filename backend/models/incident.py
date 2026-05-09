"""Incident model and manager for Morphic backend"""
import json
from datetime import datetime
from psycopg2.extras import RealDictCursor


class IncidentManager:
    """Manages incident operations"""
    
    def __init__(self, db_manager):
        self.db = db_manager

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _safe_commit(self):
        """Commit, rolling back on failure."""
        try:
            self.db.postgres_conn.commit()
        except Exception:
            try:
                self.db.postgres_conn.rollback()
            except Exception:
                pass
            raise

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_incident(self, incident_data):
        """Create a new incident"""
        query = """
        INSERT INTO incidents 
        (trace_id, timestamp, classification, root_cause, blast_radius, 
         impact, confidence_score, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """
        with self.db.get_cursor() as cursor:
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
            incident = dict(cursor.fetchone())

        self._safe_commit()

        # Cache in Redis
        if self.db.redis_client:
            try:
                self.db.redis_client.setex(
                    f"incident:{incident['trace_id']}",
                    3600,
                    json.dumps(incident, default=str)
                )
            except Exception as e:
                print(f"Redis cache write failed (non-fatal): {e}")

        return incident

    def get_incident(self, trace_id):
        """Get incident by trace_id"""
        # Try cache first
        if self.db.redis_client:
            try:
                cached = self.db.redis_client.get(f"incident:{trace_id}")
                if cached:
                    return json.loads(cached)
            except Exception as e:
                print(f"Redis cache read failed (non-fatal): {e}")

        # Query database
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM incidents WHERE trace_id = %s", (trace_id,))
            row = cursor.fetchone()

        if row:
            incident_dict = dict(row)
            if self.db.redis_client:
                try:
                    self.db.redis_client.setex(
                        f"incident:{trace_id}",
                        3600,
                        json.dumps(incident_dict, default=str)
                    )
                except Exception as e:
                    print(f"Redis cache write failed (non-fatal): {e}")
            return incident_dict
        return None

    def list_incidents(self, limit=50, offset=0, blast_radius_filter=None):
        """
        List triaged incidents ordered by severity (CRITICAL first) then recency.

        Args:
            limit: max rows
            offset: pagination offset
            blast_radius_filter: optional str e.g. "HIGH" — return only that severity
        """
        params = []

        # Only rows that have been triaged (blast_radius set)
        where = "WHERE blast_radius IS NOT NULL"

        if blast_radius_filter:
            where += " AND UPPER(blast_radius) = %s"
            params.append(blast_radius_filter.upper().strip())

        query = f"""
        SELECT
            id, trace_id, timestamp, classification, root_cause,
            blast_radius, impact, confidence_score, status,
            created_at, updated_at, service, summary, rca_json
        FROM incidents
        {where}
        ORDER BY
            CASE UPPER(blast_radius)
                WHEN 'CRITICAL' THEN 1
                WHEN 'HIGH'     THEN 2
                WHEN 'MEDIUM'   THEN 3
                WHEN 'LOW'      THEN 4
                ELSE                 5
            END ASC,
            created_at DESC
        LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        with self.db.get_cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        return [dict(row) for row in rows]


    def add_incident_log(self, incident_id, log_data):
        """Add log entry to incident timeline"""
        query = """
        INSERT INTO incident_logs 
        (incident_id, timestamp, service, endpoint, log_level, message, raw_log)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """
        with self.db.get_cursor() as cursor:
            cursor.execute(query, (
                incident_id,
                log_data.get('timestamp', datetime.utcnow()),
                log_data.get('service'),
                log_data.get('endpoint'),
                log_data.get('log_level'),
                log_data.get('message'),
                json.dumps(log_data.get('raw_log', {}))
            ))
            log_entry = dict(cursor.fetchone())

        self._safe_commit()
        return log_entry
