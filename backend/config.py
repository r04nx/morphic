"""
Morphic Backend Configuration
All secrets are loaded from environment variables — never hardcoded.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "morphic-dev-secret-change-in-prod")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    PORT = int(os.getenv("FLASK_PORT", "5000"))

    # Anthropic / Claude
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    # GitHub
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
    GITHUB_REPO = os.getenv("GITHUB_REPO", "")          # format: owner/repo
    GITHUB_API_BASE = "https://api.github.com"

    # Email / SMTP
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    EMAIL_FROM = os.getenv("EMAIL_FROM", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
    EMAIL_TO = os.getenv("EMAIL_TO", "")

    # PostgreSQL
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://morphic_user:morphic_password_2024@localhost:5432/morphic",
    )

    # Neo4j
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "morphic_neo4j_password_2024")
    NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "morphic")

    # Redis
    REDIS_URL = os.getenv(
        "REDIS_URL", "redis://:morphic_redis_password_2024@localhost:6379"
    )

    # Chaos Backend
    CHAOS_BACKEND_URL = os.getenv(
        "CHAOS_BACKEND_URL", "https://hackathonps-ykxr.onrender.com"
    )
    POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))

    # Dashboard base URL (used in email links)
    DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:3000")

    # Remediation thresholds
    HIGH_CONFIDENCE_THRESHOLD = float(os.getenv("HIGH_CONFIDENCE_THRESHOLD", "0.7"))
    MIN_CONFIDENCE_FOR_PR = float(os.getenv("MIN_CONFIDENCE_FOR_PR", "0.6"))

    @classmethod
    def validate(cls) -> list[str]:
        """Return a list of missing critical config items."""
        missing = []
        if not cls.ANTHROPIC_API_KEY:
            missing.append("ANTHROPIC_API_KEY")
        if not cls.GITHUB_TOKEN:
            missing.append("GITHUB_TOKEN")
        if not cls.EMAIL_FROM:
            missing.append("EMAIL_FROM")
        return missing
