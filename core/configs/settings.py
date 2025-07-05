import os
from pathlib import Path

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    STORAGE_ENDPOINT: str
    STORAGE_ACCESS_KEY: str
    STORAGE_SECRET_KEY: str
    JWT_ACCESS_SECRET: str
    JWT_REFRESH_SECRET: str
    DEBUG: bool = True

    class Config:
        # Look for env file in project root, even when running from subdirectories
        env_file = os.getenv("ENV_FILE") or str(Path(__file__).parent.parent.parent / "local.env")

settings = Settings()