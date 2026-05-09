"""Settings model and manager for Morphic backend"""
import json
from datetime import datetime, timezone
from psycopg2.extras import RealDictCursor


class SettingsManager:
    """Manages system-wide settings and service configurations"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def get_setting(self, key: str, default=None):
        """Get a setting value"""
        try:
            with self.db.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT value FROM settings WHERE key = %s", (key,))
                result = cursor.fetchone()
                if result:
                    return json.loads(result['value'])
                return default
        except Exception as e:
            print(f"Failed to get setting {key}: {e}")
            return default
    
    def set_setting(self, key: str, value):
        """Set a setting value"""
        try:
            with self.db.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """INSERT INTO settings (key, value, updated_at) 
                       VALUES (%s, %s, %s)
                       ON CONFLICT (key) 
                       DO UPDATE SET value = %s, updated_at = %s""",
                    (key, json.dumps(value), datetime.now(timezone.utc), 
                     json.dumps(value), datetime.now(timezone.utc))
                )
                self.db.postgres_conn.commit()
                return True
        except Exception as e:
            self.db.postgres_conn.rollback()
            print(f"Failed to set setting {key}: {e}")
            return False
    
    def get_all_settings(self):
        """Get all settings"""
        try:
            with self.db.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT key, value, updated_at FROM settings ORDER BY key")
                results = cursor.fetchall()
                settings = {}
                for result in results:
                    settings[result['key']] = json.loads(result['value'])
                return settings
        except Exception as e:
            print(f"Failed to get all settings: {e}")
            return {}
    
    def delete_setting(self, key: str):
        """Delete a setting"""
        try:
            with self.db.postgres_conn.cursor() as cursor:
                cursor.execute("DELETE FROM settings WHERE key = %s", (key,))
                self.db.postgres_conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.db.postgres_conn.rollback()
            print(f"Failed to delete setting {key}: {e}")
            return False
