"""
SurrealDB Implementation of MemoryChunkRepository
"""

from typing import List, Optional

import structlog

from apps.backend.domains.memory_hub.core.entities import MemoryChunk, MemorySource
from apps.backend.domains.memory_hub.port.repository import MemoryChunkRepository
from apps.backend.infrastructure.db.connection import get_db

logger = structlog.get_logger(__name__)


class SurrealMemoryChunkRepository(MemoryChunkRepository):
    """SurrealDB implementation of memory chunk repository"""

    async def save(self, chunk: MemoryChunk) -> None:
        """Save a memory chunk"""
        db = await get_db()

        data = self._entity_to_dict(chunk)

        if chunk.id:
            await db.update("memory_chunks", chunk.id, data)
        else:
            result = await db.create("memory_chunks", data)
            chunk.id = result[0]["id"]

    async def get_by_id(self, chunk_id: str) -> Optional[MemoryChunk]:
        """Get a memory chunk by ID"""
        db = await get_db()
        result = await db.select("memory_chunks", chunk_id)
        if result:
            return self._dict_to_entity(result[0])
        return None

    async def list_by_user(self, user_id: str) -> List[MemoryChunk]:
        """List all memory chunks for a user"""
        db = await get_db()
        result = await db.query(
            """
            SELECT * FROM memory_chunks
            WHERE user_id = $user_id
            ORDER BY created_at DESC
            """,
            user_id=user_id,
        )
        return [self._dict_to_entity(row) for row in result[0]]

    async def list_by_paper(self, user_id: str, paper_id: str) -> List[MemoryChunk]:
        """List memory chunks for a specific paper"""
        db = await get_db()
        result = await db.query(
            """
            SELECT * FROM memory_chunks
            WHERE user_id = $user_id AND paper_id = $paper_id
            ORDER BY page_number ASC
            """,
            user_id=user_id,
            paper_id=paper_id,
        )
        return [self._dict_to_entity(row) for row in result[0]]

    async def search_similar(
        self,
        query_embedding: List[float],
        user_id: str,
        exclude_paper_id: Optional[str] = None,
        limit: int = 5,
        threshold: float = 0.85,
    ) -> List[MemoryChunk]:
        """
        Search for similar memory chunks by vector similarity.
        Simplified implementation for MVP.
        """
        # For MVP, we'll use a simple query without vector search
        # In production, integrate with vector database like Pinecone or use SurrealDB's vector extension
        db = await get_db()

        query = "SELECT * FROM memory_chunks WHERE user_id = $user_id"
        params = {"user_id": user_id}

        if exclude_paper_id:
            query += " AND paper_id != $exclude_paper_id"
            params["exclude_paper_id"] = exclude_paper_id

        query += f" LIMIT {limit}"

        result = await db.query(query, **params)
        chunks = [self._dict_to_entity(row) for row in result[0]]

        # TODO: Add vector similarity search
        # For now, return the chunks (simulated similarity)
        return chunks

    async def batch_save(self, chunks: List[MemoryChunk]) -> None:
        """Save multiple memory chunks efficiently"""
        for chunk in chunks:
            await self.save(chunk)

    async def delete_by_paper(self, user_id: str, paper_id: str) -> int:
        """Delete all memory chunks for a paper, returns count deleted"""
        db = await get_db()
        result = await db.query(
            """
            SELECT id FROM memory_chunks
            WHERE user_id = $user_id AND paper_id = $paper_id
            """,
            user_id=user_id,
            paper_id=paper_id,
        )

        if result and result[0]:
            chunk_ids = [row["id"] for row in result[0]]
            for chunk_id in chunk_ids:
                await db.delete("memory_chunks", chunk_id)
            return len(chunk_ids)
        return 0

    def _entity_to_dict(self, entity: MemoryChunk) -> dict:
        """Convert entity to dict for storage"""
        data = {
            "user_id": entity.user_id,
            "content": entity.content,
            "embedding": entity.embedding,
            "paper_id": entity.metadata.paper_id,
            "paper_title": entity.metadata.paper_title,
            "page_number": entity.metadata.page_number,
            "source": entity.metadata.source.value,
        }
        if entity.id:
            data["id"] = entity.id
        return data

    def _dict_to_entity(self, data: dict) -> MemoryChunk:
        """Convert dict from storage to entity"""
        from apps.backend.domains.memory_hub.core.entities import MemoryMetadata

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
