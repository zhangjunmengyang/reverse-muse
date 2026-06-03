"""
Application Configuration

Uses Pydantic Settings for environment-based configuration.
"""

from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_project_root() -> Path:
    """Return the repository root from this config module path."""
    return Path(__file__).parent.parent.parent.parent.parent


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
    cors_origins: List[str] = Field(default=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ])

    # Database (SurrealDB)
    database_provider: str = Field(default="sqlite", alias="DATABASE_PROVIDER")
    sqlite_path: Optional[Path] = Field(default=None, alias="SQLITE_PATH")
    surreal_url: str = Field(default="ws://localhost:8000/rpc", alias="SURREALDB_URL")
    surreal_namespace: str = Field(default="reverse_muse", alias="SURREALDB_NAMESPACE")
    surreal_database: str = Field(default="main", alias="SURREALDB_DATABASE")
    surreal_user: str = Field(default="root", alias="SURREALDB_USER")
    surreal_password: str = Field(default="root", alias="SURREALDB_PASS")

    # File paths
    # __file__ = apps/backend/app/core/config.py
    # 往上 5 级到达项目根目录: config.py -> core -> app -> backend -> apps -> root
    project_root: Path = Field(default_factory=default_project_root)

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

    @property
    def sqlite_db_path(self) -> Path:
        return self.sqlite_path or self.data_dir / "reverse_muse.sqlite"

    # LLM Configuration
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"

    # Optional OpenAI-compatible LLM override, separate from embeddings.
    llm_api_key: Optional[str] = Field(default=None, alias="LLM_API_KEY")
    llm_base_url: Optional[str] = Field(default=None, alias="LLM_BASE_URL")
    llm_default_headers: Optional[str] = Field(default=None, alias="LLM_DEFAULT_HEADERS")
    maas_user_email: Optional[str] = Field(default=None, alias="MAAS_USER_EMAIL")
    maas_app_id: Optional[str] = Field(default=None, alias="MAAS_APP_ID")

    default_llm_provider: str = "openai"
    default_llm_model: str = "gpt-4o-mini"

    # Embedding
    default_embedding_model: str = "text-embedding-3-small"
    default_embedding_provider: str = "openai"
    embedding_api_key: Optional[str] = Field(default=None, alias="EMBEDDING_API_KEY")
    embedding_base_url: Optional[str] = Field(default=None, alias="EMBEDDING_BASE_URL")
    embedding_dimension: int = Field(default=1536, alias="EMBEDDING_DIMENSION")
    embedding_encoding_format: str = Field(default="float", alias="EMBEDDING_ENCODING_FORMAT")

    # PDF Processing
    chunk_size: int = 500
    chunk_overlap: float = 0.15
    max_pdf_size_mb: int = 50

    # AI Insight Config
    linger_threshold_seconds: int = 5
    confidence_threshold: float = 0.70  # Lowered from 0.85 for more insights
    cross_paper_similarity_threshold: float = 0.65  # Lowered from 0.75
    same_paper_similarity_threshold: float = 0.45  # Lowered from 0.55
    max_insight_length: int = 200
    min_insight_length: int = 30  # Lowered from 50 to allow shorter insights

    # LLM Behavior
    llm_temperature: float = 0.7
    llm_max_tokens: int = Field(default=512, alias="LLM_MAX_TOKENS")
    llm_timeout_seconds: int = Field(default=20, alias="LLM_TIMEOUT_SECONDS")
    base_confidence: float = 0.75  # Raised from 0.7 so more insights pass threshold

    # Logging
    log_level: str = "INFO"
    log_format: str = "console"  # json or console


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings singleton"""
    return settings
