"""
Repository factory for selectable database providers.
"""

from apps.backend.app.core.config import get_settings
from apps.backend.domains.insight_hub.port.repository import InsightRepository
from apps.backend.domains.memory_hub.port.repository import MemoryChunkRepository
from apps.backend.domains.reading_hub.port.repository import ReadingContextRepository
from apps.backend.infrastructure.db.insight_repository_impl import SurrealInsightRepository
from apps.backend.infrastructure.db.memory_chunk_repository_impl import (
    SurrealMemoryChunkRepository,
)
from apps.backend.infrastructure.db.reading_context_repository_impl import (
    SurrealReadingContextRepository,
)
from apps.backend.infrastructure.db.sqlite_repository_impl import (
    SQLiteInsightRepository,
    SQLiteMemoryChunkRepository,
    SQLiteReadingContextRepository,
)


def use_surrealdb() -> bool:
    """Return whether the configured repository provider is SurrealDB."""
    return get_settings().database_provider.lower() == "surrealdb"


def create_reading_context_repository() -> ReadingContextRepository:
    if use_surrealdb():
        return SurrealReadingContextRepository()
    return SQLiteReadingContextRepository()


def create_memory_chunk_repository() -> MemoryChunkRepository:
    if use_surrealdb():
        return SurrealMemoryChunkRepository()
    return SQLiteMemoryChunkRepository()


def create_insight_repository() -> InsightRepository:
    if use_surrealdb():
        return SurrealInsightRepository()
    return SQLiteInsightRepository()
