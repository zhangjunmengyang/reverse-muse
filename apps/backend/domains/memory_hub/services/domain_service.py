"""
Memory Hub - Domain Services

Business logic for managing memory chunks and retrieval.
"""

from typing import List, Optional

from apps.backend.domains.memory_hub.core.entities import MemoryChunk, MemorySource


class MemoryChunkService:
    """Service for managing memory chunks"""

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
        """Create a new memory chunk"""
        from apps.backend.domains.memory_hub.core.entities import MemoryMetadata

        metadata = MemoryMetadata(
            paper_id=paper_id,
            paper_title=paper_title,
            page_number=page_number,
            source=source,
        )

        return MemoryChunk(
            user_id=user_id,
            content=content,
            embedding=embedding,
            metadata=metadata,
        )

    def update_embedding(self, chunk: MemoryChunk, embedding: List[float]) -> None:
        """Update the embedding for a chunk"""
        chunk.embedding = embedding

    def mark_accessed(self, chunk: MemoryChunk) -> None:
        """Mark a chunk as accessed (increments access count)"""
        chunk.mark_accessed()

    def filter_by_paper(
        self,
        chunks: List[MemoryChunk],
        paper_id: str,
    ) -> List[MemoryChunk]:
        """Filter chunks by paper ID"""
        return [c for c in chunks if c.is_from_same_paper(paper_id)]

    def filter_has_embedding(self, chunks: List[MemoryChunk]) -> List[MemoryChunk]:
        """Filter chunks that have embeddings"""
        return [c for c in chunks if c.has_embedding()]

    def get_top_accessed(
        self,
        chunks: List[MemoryChunk],
        limit: int = 10,
    ) -> List[MemoryChunk]:
        """Get most frequently accessed chunks"""
        sorted_chunks = sorted(
            chunks, key=lambda c: c.metadata.access_count, reverse=True
        )
        return sorted_chunks[:limit]
