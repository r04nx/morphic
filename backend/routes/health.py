"""Health check routes for Morphic backend"""
from datetime import datetime
from flask import jsonify


def register_health_routes(app, db_manager):
    """Register health check routes"""
    
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
