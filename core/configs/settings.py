import os

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_URL: str
    DB_PORT: str
    DEBUG: bool = True

    class Config:
        env_file = os.getenv("ENV_FILE", "local.env")

settings = Settings()