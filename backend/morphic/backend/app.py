"""
Morphic Backend — Flask Application Entry Point

Starts:
  - Flask API server (CORS-enabled)
  - APScheduler background job (orchestrator pipeline every 30 s)
  - All database connections (PostgreSQL pool, Neo4j driver, Redis client)
"""

import logging
import signal
import sys
from typing import NoReturn

from flask import Flask, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import Config
from utils.logger import setup_logging

# ---------------------------------------------------------------------------
# Bootstrap logging before anything else
# ---------------------------------------------------------------------------
setup_logging("DEBUG" if Config.DEBUG else "INFO")
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    # CORS — allow the React frontend on any origin in dev
    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
        supports_credentials=True,
    )

    # -----------------------------------------------------------------------
    # Register blueprints
    # -----------------------------------------------------------------------
    from routes.incidents import bp as incidents_bp
    from routes.traces    import bp as traces_bp
    from routes.actions   import bp as actions_bp
    from routes.health    import bp as health_bp
    from routes.settings  import bp as settings_bp

    app.register_blueprint(incidents_bp)
    app.register_blueprint(traces_bp)
    app.register_blueprint(actions_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(settings_bp)

    # -----------------------------------------------------------------------
    # Root redirect
    # -----------------------------------------------------------------------
    @app.get("/")
    def root():
        return jsonify({
            "service": "Morphic Backend",
            "version": "1.0.0",
            "docs":    "/api/health",
            "endpoints": [
                "GET  /api/incidents",
                "GET  /api/incidents/<id>",
                "POST /api/incidents/<id>/actions/email",
                "POST /api/incidents/<id>/actions/github-pr",
                "GET  /api/traces/<trace_id>/events",
                "GET  /api/traces/<trace_id>/graph",
                "GET  /api/actions",
                "GET  /api/actions/incident/<incident_id>",
                "GET  /api/health",
                "GET  /api/settings/status",
            ],
        })

    # -----------------------------------------------------------------------
    # Global error handlers
    # -----------------------------------------------------------------------
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def internal_error(e):
        logger.exception("Unhandled 500 error")
        return jsonify({"error": "Internal server error"}), 500

    return app


def _start_scheduler() -> BackgroundScheduler:
    """Start the APScheduler background job for the orchestration pipeline."""
    from agents.orchestrator import run_pipeline

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        run_pipeline,
        trigger=IntervalTrigger(seconds=Config.POLL_INTERVAL_SECONDS),
        id="orchestrator_pipeline",
        name="Morphic Orchestrator Pipeline",
        replace_existing=True,
        max_instances=1,
        coalesce=True,          # skip missed runs instead of queuing
    )
    scheduler.start()
    logger.info(
        "Orchestrator scheduler started — polling every %d seconds",
        Config.POLL_INTERVAL_SECONDS,
    )
    return scheduler


def _warm_up_db() -> None:
    """Eagerly initialise DB connections so failures are surfaced at startup."""
    from db import postgres, redis_client, neo4j_client

    # PostgreSQL
    try:
        postgres.get_pool()
        logger.info("PostgreSQL pool ready")
    except Exception as exc:
        logger.error("PostgreSQL connection failed: %s", exc)

    # Redis
    try:
        ok = redis_client.ping()
        logger.info("Redis ping: %s", "ok" if ok else "FAILED")
    except Exception as exc:
        logger.error("Redis connection failed: %s", exc)

    # Neo4j
    try:
        ok = neo4j_client.ping()
        logger.info("Neo4j connectivity: %s", "ok" if ok else "FAILED")
    except Exception as exc:
        logger.error("Neo4j connection failed: %s", exc)


def _shutdown(scheduler: BackgroundScheduler) -> None:
    logger.info("Shutting down Morphic backend...")
    if scheduler.running:
        scheduler.shutdown(wait=False)
    from db import postgres, neo4j_client
    postgres.close_pool()
    neo4j_client.close_driver()
    logger.info("Shutdown complete")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Log missing config (warn, don't exit)
    missing = Config.validate()
    if missing:
        logger.warning("Missing environment variables: %s", missing)

    # Warm up connections
    _warm_up_db()

    # Create the Flask app
    app = create_app()

    # Start background orchestrator
    scheduler = _start_scheduler()

    # Graceful shutdown on SIGINT / SIGTERM
    def _handle_signal(sig, frame) -> NoReturn:
        _shutdown(scheduler)
        sys.exit(0)

    signal.signal(signal.SIGINT,  _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # Run an initial pipeline cycle immediately so you don't wait 30 s
    logger.info("Running initial pipeline cycle on startup...")
    try:
        from agents.orchestrator import run_pipeline
        run_pipeline()
    except Exception as exc:
        logger.error("Initial pipeline cycle failed: %s", exc)

    logger.info(
        "Starting Morphic backend on %s:%s (debug=%s)",
        Config.HOST,
        Config.PORT,
        Config.DEBUG,
    )
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
        use_reloader=False,   # reloader conflicts with APScheduler background thread
    )
