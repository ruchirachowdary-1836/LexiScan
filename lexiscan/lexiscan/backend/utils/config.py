"""
LexiScan — Application Configuration
Loads settings from .env file using pydantic-settings.
"""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "LexiScan"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "dev-secret-key-change-in-production"

    # Database
    DATABASE_URL: str = "postgresql://lexiscan_user:lexiscan_pass@localhost:5432/lexiscan_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Models
    LEGALBERT_MODEL: str = "nlpaueb/legal-bert-base-uncased"
    NER_MODEL: str = "en_core_web_sm"
    MODEL_CACHE_DIR: str = "./data/models"
    MAX_CLAUSE_LENGTH: int = 512
    BATCH_SIZE: int = 8

    # File Storage
    UPLOAD_DIR: str = "./data/uploads"
    MAX_FILE_SIZE_MB: int = 50

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    ALLOWED_ORIGINS: str = "http://localhost:8501,http://localhost:3000"

    # Streamlit
    STREAMLIT_PORT: int = 8501
    API_BASE_URL: str = "http://localhost:8000"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/lexiscan.log"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    @property
    def model_cache_path(self) -> Path:
        p = Path(self.MODEL_CACHE_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def upload_path(self) -> Path:
        p = Path(self.UPLOAD_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
