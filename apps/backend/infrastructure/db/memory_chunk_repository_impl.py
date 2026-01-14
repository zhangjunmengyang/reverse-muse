"""
SurrealDB Implementation of MemoryChunkRepository
"""

from typing import Any, Dict, List, Optional, Tuple

import structlog

from apps.backend.domains.memory_hub.core.entities import (
    MemoryChunk,
    MemoryMetadata,
    MemorySource,
)
from apps.backend.domains.memory_hub.port.repository import MemoryChunkRepository
from apps.backend.infrastructure.db.base_repository import BaseSurrealRepository
from apps.backend.infrastructure.db.connection import get_db

logger = structlog.get_logger(__name__)


class SurrealMemoryChunkRepository(BaseSurrealRepository[MemoryChunk], MemoryChunkRepository):
    """SurrealDB implementation of memory chunk repository."""

    table_name = "memory_chunks"

    async def list_by_user(self, user_id: str) -> List[MemoryChunk]:
        """List all memory chunks for a user."""
        results = await self.query(
            f"SELECT * FROM {self.table_name} WHERE user_id = '{user_id}'"
        )
        return [self._dict_to_entity(row) for row in results if isinstance(row, dict)]

    async def list_by_paper(self, user_id: str, paper_id: str) -> List[MemoryChunk]:
        """List memory chunks for a specific paper."""
        results = await self.query(
            f"SELECT * FROM {self.table_name} "
            f"WHERE user_id = '{user_id}' AND paper_id = '{paper_id}' "
            f"ORDER BY page_number ASC"
        )
        return [self._dict_to_entity(row) for row in results if isinstance(row, dict)]

    async def search_similar(
        self,
        query_embedding: List[float],
        user_id: str,
        exclude_paper_id: Optional[str] = None,
        limit: int = 5,
        threshold: float = 0.85,
    ) -> List[Tuple[MemoryChunk, float]]:
        """Search for similar memory chunks (simplified for MVP)."""
        if exclude_paper_id:
            sql = (
                f"SELECT * FROM {self.table_name} "
                f"WHERE user_id = '{user_id}' AND paper_id != '{exclude_paper_id}' "
                f"LIMIT {limit}"
            )
        else:
            sql = f"SELECT * FROM {self.table_name} WHERE user_id = '{user_id}' LIMIT {limit}"

        results = await self.query(sql)
        return [
            (self._dict_to_entity(row), 1.0)
            for row in results
            if isinstance(row, dict)
        ]

    async def batch_save(self, chunks: List[MemoryChunk]) -> None:
        """Save multiple memory chunks efficiently."""
        for chunk in chunks:
            await self.save(chunk)

    async def delete_by_paper(self, user_id: str, paper_id: str) -> int:
        """Delete all memory chunks for a paper, returns count deleted."""
        db = await get_db()
        results = await self.query(
            f"SELECT id FROM {self.table_name} "
            f"WHERE user_id = '{user_id}' AND paper_id = '{paper_id}'"
        )
        if not results:
            return 0

        for row in results:
            if isinstance(row, dict) and "id" in row:
                await db.delete(row["id"])
        return len(results)

    def _entity_to_dict(self, entity: MemoryChunk) -> Dict[str, Any]:
        """Convert entity to dict for storage."""
        data = {
            "user_id": entity.user_id,
            "content": entity.content,
            "paper_id": entity.metadata.paper_id,
            "paper_title": entity.metadata.paper_title,
            "page_number": entity.metadata.page_number,
            "source": entity.metadata.source.value,
        }
        if entity.embedding is not None:
            data["embedding"] = entity.embedding
        if entity.id:
            data["id"] = entity.id
        return data

    def _dict_to_entity(self, data: Dict[str, Any]) -> MemoryChunk:
        """Convert dict from storage to entity."""
        metadata = MemoryMetadata(
            paper_id=data.get("paper_id", ""),
            paper_title=data.get("paper_title", ""),
            page_number=data.get("page_number", 0),
            source=MemorySource(data.get("source", "pdf_text")),
        )

        return MemoryChunk(
            id=data.get("id"),
            user_id=data.get("user_id", ""),
            content=data.get("content", ""),
            embedding=data.get("embedding"),
            metadata=metadata,
        )

    def _get_entity_id(self, entity: MemoryChunk) -> Optional[str]:
        return entity.id

    def _set_entity_id(self, entity: MemoryChunk, entity_id: Optional[str]) -> None:
        entity.id = entity_id
