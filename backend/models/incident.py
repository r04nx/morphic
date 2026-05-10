"""Incident model and manager for Morphic backend"""
import json
from datetime import datetime
import uuid
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

    def _get_actions(self, incident_id):
        """Fetch remediation actions for an incident."""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, action_type, status, details, started_at, completed_at, created_at
                    FROM remediation_actions
                    WHERE incident_id = %s::uuid
                    ORDER BY created_at DESC
                    """,
                    (str(incident_id),)
                )
                rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            print(f"Failed to fetch actions (non-fatal): {e}")
            return []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_incident(self, incident_data):
        """Create a new incident"""
        query = """
        INSERT INTO incidents 
        (trace_id, timestamp, classification, root_cause, blast_radius, 
         impact, confidence_score, status, service, summary)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                incident_data.get('status', 'active'),
                incident_data.get('service'),
                incident_data.get('summary')
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

    def get_incident(self, incident_id):
        """
        Fetch a single incident by UUID id OR trace_id.
        Also attaches remediation_actions for the incident.
        """
        # Try Redis cache first (keyed by trace_id)
        is_uuid = False
        try:
            uuid.UUID(str(incident_id))
            is_uuid = True
        except ValueError:
            pass

        if not is_uuid and self.db.redis_client:
            try:
                cached = self.db.redis_client.get(f"incident:{incident_id}")
                if cached:
                    return json.loads(cached)
            except Exception as e:
                print(f"Redis cache read failed (non-fatal): {e}")

        # Query DB — try by UUID id first, then by trace_id
        if is_uuid:
            sql = """
                SELECT * FROM incidents WHERE id = %s::uuid
            """
        else:
            sql = """
                SELECT * FROM incidents WHERE trace_id = %s
            """

        with self.db.get_cursor() as cursor:
            cursor.execute(sql, (incident_id,))
            row = cursor.fetchone()

        if not row:
            return None

        incident_dict = dict(row)

        # Attach remediation actions
        incident_dict["actions"] = self._get_actions(incident_dict["id"])

        # Cache by trace_id
        if self.db.redis_client:
            try:
                self.db.redis_client.setex(
                    f"incident:{incident_dict['trace_id']}",
                    3600,
                    json.dumps(incident_dict, default=str)
                )
            except Exception as e:
                print(f"Redis cache write failed (non-fatal): {e}")

        return incident_dict

    def list_incidents(self, limit=50, offset=0, blast_radius_filter=None):
        """List incidents with optional pagination and filtering"""
        params = []
        where = "WHERE blast_radius IS NOT NULL"

        if blast_radius_filter:
            where += " AND UPPER(blast_radius) = %s"
            params.append(blast_radius_filter.upper().strip())

        query = f"""
        SELECT * FROM incidents
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
