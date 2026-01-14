"""
Memory Hub - Domain Services

Business logic for managing memory chunks and retrieval.
"""

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
