"""
Application configuration and settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Redis (use 127.0.0.1 for explicit IPv4 on Windows)
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379

    # Ollama Unified VLM
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3-vl:8b"

    # Logging
    log_dir: str = "logs"

    # Allowed CORS origins
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
