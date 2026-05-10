"""Configuration settings for Morphic backend"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration class"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'morphic_development_secret_key_2024')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True') == 'True'
    
    # PostgreSQL
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'morphic')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'morphic_user')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'morphic_password_2024')
    DATABASE_URL = os.getenv('DATABASE_URL', f'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}')
    
    # Neo4j
    NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'morphic_neo4j_password_2024')
    NEO4J_DATABASE = os.getenv('NEO4J_DATABASE', 'morphic')
    
    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = os.getenv('REDIS_PORT', '6379')
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'morphic_redis_password_2024')
    REDIS_URL = os.getenv('REDIS_URL', f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}')
    
    # GitHub
    GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')
    
    # External Services
    LOG_API_URL = os.getenv('LOG_API_URL', 'https://hackathonps-ykxr.onrender.com/logs')

    # Dashboard
    DASHBOARD_URL = os.getenv('DASHBOARD_URL', 'http://localhost:8081')

    # GitHub
    GITHUB_TOKEN    = os.getenv('GITHUB_TOKEN', '')
    GITHUB_REPO     = os.getenv('GITHUB_REPO', '')       # format: owner/repo
    GITHUB_API_BASE = os.getenv('GITHUB_API_BASE', 'https://api.github.com')

    # Email / SMTP
    EMAIL_FROM     = os.getenv('EMAIL_FROM', '')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
    EMAIL_TO       = os.getenv('EMAIL_TO', '')
    SMTP_HOST      = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT      = int(os.getenv('SMTP_PORT', '587'))

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID   = os.getenv('TELEGRAM_CHAT_ID', '')

    # LLM Provider
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'openrouter')

    # OpenRouter
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    OPENROUTER_BASE_URL = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
    OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'meta-llama/llama-3.1-8b-instruct:free')
    OPENROUTER_HTTP_REFERER = os.getenv('OPENROUTER_HTTP_REFERER')
    OPENROUTER_TITLE = os.getenv('OPENROUTER_TITLE', 'Morphic')

    # Ollama
    OLLAMA_API_KEY = os.getenv('OLLAMA_API_KEY')
    OLLAMA_HOST = os.getenv('OLLAMA_HOST')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'deepseek-v4-flash:cloud')
    
    # LogAI
    LOGAI_CACHE_DIR = os.getenv('LOGAI_CACHE_DIR', '/tmp/logai_cache')
    LOGAI_MODEL_DIR = os.getenv('LOGAI_MODEL_DIR', '/tmp/logai_models')
    LOGAI_NLTK_DATA = os.getenv('LOGAI_NLTK_DATA', '/tmp/nltk_data')
    
    # Monitoring
    MONITOR_CHECK_INTERVAL = int(os.getenv('MONITOR_CHECK_INTERVAL', '30'))
