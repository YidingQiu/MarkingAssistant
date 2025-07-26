import os
from pathlib import Path

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Core database settings (required)
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    
    # Storage settings (required)
    STORAGE_ENDPOINT: str
    STORAGE_ACCESS_KEY: str
    STORAGE_SECRET_KEY: str
    
    # JWT settings (required)
    JWT_ACCESS_SECRET: str
    JWT_REFRESH_SECRET: str
    
    # Optional development settings
    DEBUG: bool = True
    
    # Celery Configuration (optional)
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_WORKER_LOG_LEVEL: str = "INFO"

    # Redis Configuration (optional)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: str = "6379"
    REDIS_DB: str = "0"
    
    # Database read-only user (optional for development)
    PG_USER_READ: str = "readonly_user"
    PG_PASSWORD_READ: str = "readonly_pass"
    
    # MinIO configuration (optional for development)
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin123"
    MINIO_SERVER_URL: str = "http://localhost:9000"
    
    # pgAdmin configuration (optional for development)
    PGADMIN_EMAIL: str = "admin@example.com"
    PGADMIN_PASSWORD: str = "admin123"

    class Config:
        # Look for env file in project root, even when running from subdirectories
        env_file = os.getenv("ENV_FILE") or str(Path(__file__).parent.parent.parent / "local.env")
        # Allow case-insensitive environment variable names
        case_sensitive = False

settings = Settings()