"""Database connection manager for Morphic backend"""
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
import neo4j
from config.settings import Config


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
                host=Config.POSTGRES_HOST,
                port=Config.POSTGRES_PORT,
                database=Config.POSTGRES_DB,
                user=Config.POSTGRES_USER,
                password=Config.POSTGRES_PASSWORD
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
                Config.NEO4J_URI,
                auth=(Config.NEO4J_USER, Config.NEO4J_PASSWORD)
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
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                password=Config.REDIS_PASSWORD,
                decode_responses=True
            )
            self.redis_client.ping()
            print("✅ Redis connected")
            return True
        except Exception as e:
            print(f"❌ Redis failed: {e}")
            return False
    
    def connect_all(self):
        """Connect to all databases"""
        print("Connecting to databases...")
        success_count = 0
        if self.connect_postgres():
            success_count += 1
        if self.connect_neo4j():
            success_count += 1
        if self.connect_redis():
            success_count += 1
        print(f"Databases connected: {success_count}/3\n")
        return success_count == 3
    
    def close_connections(self):
        """Close all database connections"""
        if self.postgres_conn:
            self.postgres_conn.close()
        if self.neo4j_driver:
            self.neo4j_driver.close()
        if self.redis_client:
            self.redis_client.close()
