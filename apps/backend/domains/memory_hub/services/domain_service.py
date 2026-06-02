"""
Memory Hub - Domain Services

Business logic for managing memory chunks and retrieval.
"""

from datetime import datetime
from typing import List, Optional

from apps.backend.domains.memory_hub.core.entities import (
    MemoryChunk,
    MemoryMetadata,
    MemorySource,
)


class MemoryChunkService:
    """Service for managing memory chunks."""

    def create_chunk(
        self,
        user_id: str,
        content: str,
        paper_id: str,
        paper_title: str,
        page_number: int,
        source: MemorySource = MemorySource.PDF_TEXT,
        embedding: Optional[List[float]] = None,
    ) -> MemoryChunk:
        """Create a new memory chunk."""
        return MemoryChunk(
            user_id=user_id,
            content=content,
            embedding=embedding,
            metadata=MemoryMetadata(
                paper_id=paper_id,
                paper_title=paper_title,
                page_number=page_number,
                source=source,
            ),
        )

    def update_embedding(
        self,
        chunk: MemoryChunk,
        embedding: List[float],
    ) -> None:
        """Update a chunk vector embedding."""
        chunk.embedding = embedding
        chunk.updated_at = datetime.utcnow()

    def mark_accessed(self, chunk: MemoryChunk) -> None:
        """Mark a chunk as accessed."""
        chunk.mark_accessed()

    def filter_by_paper(
        self,
        chunks: List[MemoryChunk],
        paper_id: str,
    ) -> List[MemoryChunk]:
        """Keep chunks from a specific paper."""
        return [chunk for chunk in chunks if chunk.is_from_same_paper(paper_id)]

    def filter_has_embedding(self, chunks: List[MemoryChunk]) -> List[MemoryChunk]:
        """Keep chunks that have vector embeddings."""
        return [chunk for chunk in chunks if chunk.has_embedding()]

    def get_top_accessed(
        self,
        chunks: List[MemoryChunk],
        limit: int = 5,
    ) -> List[MemoryChunk]:
        """Return the most frequently accessed chunks."""
        return sorted(
            chunks,
            key=lambda chunk: chunk.metadata.access_count,
            reverse=True,
        )[:limit]
