"""
Application Configuration

Uses Pydantic Settings for environment-based configuration.
"""

from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Project info
    project_name: str = "Reverse Muse"
    environment: str = "development"
    debug: bool = False

    # API
    api_v1_prefix: str = "/api/v1"
    host: str = "127.0.0.1"
    port: int = 8001  # Changed from 8000 to avoid conflicts

    # CORS
    cors_origins: List[str] = Field(default=["http://localhost:5173", "http://localhost:3000"])

    # Database (SurrealDB)
    surreal_url: str = Field(default="ws://localhost:8001/rpc", alias="SURREALDB_URL")
    surreal_namespace: str = Field(default="reverse_muse", alias="SURREALDB_NAMESPACE")
    surreal_database: str = Field(default="main", alias="SURREALDB_DATABASE")
    surreal_user: str = Field(default="root", alias="SURREALDB_USER")
    surreal_password: str = Field(default="root", alias="SURREALDB_PASS")

    # File paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent.parent)

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def pdf_dir(self) -> Path:
        return self.data_dir / "pdfs"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    # LLM Configuration
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"

    default_llm_provider: str = "openai"
    default_llm_model: str = "gpt-4o-mini"

    # Embedding
    default_embedding_model: str = "text-embedding-3-small"
    default_embedding_provider: str = "openai"

    # PDF Processing
    chunk_size: int = 500
    chunk_overlap: float = 0.15
    max_pdf_size_mb: int = 50

    # AI Bubble Config
    linger_threshold_seconds: int = 5
    linger_confidence_threshold: float = 0.8
    similarity_threshold: float = 0.85
    max_bubble_length: int = 200

    # Logging
    log_level: str = "INFO"
    log_format: str = "console"  # json or console


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings singleton"""
    return settings
