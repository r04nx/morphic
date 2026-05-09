#!/usr/bin/env python3
"""
Test script for all database connections in Morphic backend
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_postgres():
    """Test PostgreSQL connection"""
    print("🔍 Testing PostgreSQL Connection...")
    print("-" * 40)
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        # Connect
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            database=os.getenv('POSTGRES_DB', 'morphic'),
            user=os.getenv('POSTGRES_USER', 'morphic_user'),
            password=os.getenv('POSTGRES_PASSWORD', 'morphic_password_2024')
        )
        
        print("✅ PostgreSQL Connection Successful")
        
        # Test basic query
        with conn.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print(f"📊 Version: {version}")
        
        # Test tables
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT table_name, column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                ORDER BY table_name, ordinal_position
            """)
            tables = cursor.fetchall()
            
            print(f"\n📋 Database Schema:")
            current_table = None
            for row in tables:
                if row['table_name'] != current_table:
                    current_table = row['table_name']
                    print(f"\n  📁 Table: {current_table}")
                print(f"    - {row['column_name']}: {row['data_type']}")
        
        # Test sample data
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM incidents")
            incident_count = cursor.fetchone()['count']
            print(f"\n📈 Sample Data:")
            print(f"  - Incidents: {incident_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL Connection Failed: {e}")
        return False

def test_neo4j():
    """Test Neo4j connection"""
    print("\n🔍 Testing Neo4j Connection...")
    print("-" * 40)
    
    try:
        import neo4j
        
        # Connect
        driver = neo4j.GraphDatabase.driver(
            os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            auth=(os.getenv('NEO4J_USER', 'neo4j'), 
                  os.getenv('NEO4J_PASSWORD', 'morphic_neo4j_password_2024'))
        )
        
        print("✅ Neo4j Connection Successful")
        
        # Test basic query
        with driver.session() as session:
            result = session.run("RETURN 'Neo4j working' AS status")
            status = result.single()['status']
            print(f"📊 Status: {status}")
        
        # Test database info
        with driver.session() as session:
            result = session.run("CALL db.info() YIELD name, value RETURN name, value")
            info = {record['name']: record['value'] for record in result}
            print(f"\n📋 Database Info:")
            for key, value in info.items():
                print(f"  - {key}: {value}")
        
        # Test sample data
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as node_count")
            node_count = result.single()['node_count']
            print(f"\n📈 Sample Data:")
            print(f"  - Nodes: {node_count}")
        
        driver.close()
        return True
        
    except Exception as e:
        print(f"❌ Neo4j Connection Failed: {e}")
        return False

def test_redis():
    """Test Redis connection"""
    print("\n🔍 Testing Redis Connection...")
    print("-" * 40)
    
    try:
        import redis
        
        # Connect
        r = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=os.getenv('REDIS_PORT', 6379),
            password=os.getenv('REDIS_PASSWORD', 'morphic_redis_password_2024'),
            decode_responses=True
        )
        
        # Test ping
        r.ping()
        print("✅ Redis Connection Successful")
        
        # Test basic operations
        r.set('test_key', 'test_value', ex=10)
        value = r.get('test_key')
        print(f"📊 SET/GET Test: {value}")
        
        # Test info
        info = r.info()
        print(f"\n📋 Redis Info:")
        print(f"  - Version: {info.get('redis_version')}")
        print(f"  - Used Memory: {info.get('used_memory_human')}")
        print(f"  - Connected Clients: {info.get('connected_clients')}")
        print(f"  - Uptime: {info.get('uptime_in_seconds')} seconds")
        
        # Test sample data
        r.set('morphic:test', json.dumps({
            'timestamp': datetime.now().isoformat(),
            'status': 'working'
        }), ex=300)
        
        test_data = r.get('morphic:test')
        if test_data:
            parsed = json.loads(test_data)
            print(f"\n📈 Sample Data:")
            print(f"  - Test entry: {parsed}")
        
        # Clean up
        r.delete('test_key', 'morphic:test')
        
        r.close()
        return True
        
    except Exception as e:
        print(f"❌ Redis Connection Failed: {e}")
        return False

def test_flask_app():
    """Test Flask app startup"""
    print("\n🔍 Testing Flask Application...")
    print("-" * 40)
    
    try:
        # Import the app
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        # Test imports
        from app import db_manager, init_databases
        print("✅ Flask App Imports Successful")
        
        # Test database initialization
        if init_databases():
            print("✅ Database Initialization Successful")
            
            # Test basic operations
            if db_manager.postgres_conn:
                with db_manager.postgres_conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    print("✅ PostgreSQL Operations Working")
            
            if db_manager.neo4j_driver:
                with db_manager.neo4j_driver.session() as session:
                    session.run("RETURN 1")
                    print("✅ Neo4j Operations Working")
            
            if db_manager.redis_client:
                db_manager.redis_client.ping()
                print("✅ Redis Operations Working")
            
            return True
        else:
            print("❌ Database Initialization Failed")
            return False
        
    except Exception as e:
        print(f"❌ Flask App Test Failed: {e}")
        return False

def test_logai():
    """Test LogAI availability"""
    print("\n🔍 Testing LogAI...")
    print("-" * 40)
    
    try:
        import logai
        print("✅ LogAI Import Successful")
        
        # Test basic functionality
        from logai.information_extraction import log_parser
        from logai.analysis import anomaly_detector
        print("✅ LogAI Modules Available")
        
        return True
        
    except ImportError as e:
        print(f"⚠️ LogAI Not Available: {e}")
        return False
    except Exception as e:
        print(f"❌ LogAI Test Failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Morphic Backend Connection Tests")
    print("=" * 50)
    print(f"📅 Started at: {datetime.now()}")
    print(f"🐍 Python Version: {sys.version}")
    print()
    
    results = {
        'postgres': test_postgres(),
        'neo4j': test_neo4j(),
        'redis': test_redis(),
        'flask': test_flask_app(),
        'logai': test_logai()
    }
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    for service, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {service.upper()}: {'PASS' if status else 'FAIL'}")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print(f"\n📈 Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Backend is ready to use.")
        return 0
    else:
        print("⚠️ Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
