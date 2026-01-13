"""
Memory Hub - Repository Ports

Interfaces for memory chunk persistence and retrieval.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from apps.backend.domains.memory_hub.core.entities import MemoryChunk


class MemoryChunkRepository(ABC):
    """Repository interface for memory chunks"""

    @abstractmethod
    async def save(self, chunk: MemoryChunk) -> None:
        """Save a memory chunk"""
        pass

    @abstractmethod
    async def get_by_id(self, chunk_id: str) -> Optional[MemoryChunk]:
        """Get a memory chunk by ID"""
        pass

    @abstractmethod
    async def list_by_user(self, user_id: str) -> List[MemoryChunk]:
        """List all memory chunks for a user"""
        pass

    @abstractmethod
    async def list_by_paper(self, user_id: str, paper_id: str) -> List[MemoryChunk]:
        """List memory chunks for a specific paper"""
        pass

    @abstractmethod
    async def search_similar(
        self,
        query_embedding: List[float],
        user_id: str,
        exclude_paper_id: Optional[str] = None,
        limit: int = 5,
        threshold: float = 0.85,
    ) -> List[Tuple[MemoryChunk, float]]:
        """
        Search for similar memory chunks by vector similarity.
        Returns chunks sorted by similarity score (highest first).
        """
        pass

    @abstractmethod
    async def batch_save(self, chunks: List[MemoryChunk]) -> None:
        """Save multiple memory chunks efficiently"""
        pass

    @abstractmethod
    async def delete_by_paper(self, user_id: str, paper_id: str) -> int:
        """Delete all memory chunks for a paper, returns count deleted"""
        pass
