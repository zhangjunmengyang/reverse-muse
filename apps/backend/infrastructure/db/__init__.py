"""
Repository implementations.
"""

from apps.backend.infrastructure.db.base_repository import BaseSurrealRepository
from apps.backend.infrastructure.db.insight_repository_impl import (
    SurrealInsightRepository,
)
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
    close_sqlite_store,
)

__all__ = [
    "BaseSurrealRepository",
    "close_sqlite_store",
    "SQLiteInsightRepository",
    "SQLiteMemoryChunkRepository",
    "SQLiteReadingContextRepository",
    "SurrealInsightRepository",
    "SurrealMemoryChunkRepository",
    "SurrealReadingContextRepository",
]
