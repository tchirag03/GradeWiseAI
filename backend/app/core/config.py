"""
Application configuration and settings.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    app_name: str = "Sustainable AI Assessment Platform"
    version: str = "1.0.0"
    api_prefix: str = "/api"

    # MongoDB
    mongo_uri: str = "mongodb://localhost:27017"
    db_name: str = "evaluation_db"

    # File uploads
    upload_dir: str = "uploads"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # Mistral OCR API
    mistral_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
