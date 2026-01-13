"""
Vector Search Service

Provides semantic search functionality for memory chunks.
"""

import re
from typing import List, Optional, Tuple
from difflib import SequenceMatcher

import structlog

from apps.backend.app.core.config import get_settings
from apps.backend.domains.memory_hub.core.entities import MemoryChunk

logger = structlog.get_logger(__name__)


class VectorSearchService:
    """Service for searching related memory chunks"""

    def __init__(self):
        self.settings = get_settings()

    async def search_similar(
        self,
        query_text: str,
        user_id: str,
        exclude_paper_id: Optional[str] = None,
        limit: int = 5,
        threshold: float = 0.85,
    ) -> List[Tuple[MemoryChunk, float]]:
        """
        Search for similar memory chunks.

        Returns list of (chunk, similarity_score) tuples.
        """
        from apps.backend.domains.memory_hub.port.repository import MemoryChunkRepository
        from apps.backend.infrastructure.db import SurrealMemoryChunkRepository

        # Get all chunks for user
        repo = SurrealMemoryChunkRepository()

        # Get chunks to search from
        if exclude_paper_id:
            chunks = await repo.list_by_user(user_id=user_id)
            chunks = [c for c in chunks if not c.is_from_same_paper(exclude_paper_id)]
        else:
            chunks = await repo.list_by_user(user_id=user_id)

        if not chunks:
            logger.warning(f"No chunks found for user {user_id}")
            return []

        # Calculate similarity scores (simplified for MVP)
        results = []
        for chunk in chunks:
            similarity = self._calculate_similarity(query_text, chunk.content)
            if similarity >= threshold:
                results.append((chunk, similarity))

        # Sort by similarity (highest first)
        results.sort(key=lambda x: x[1], reverse=True)

        # Return top N results
        return results[:limit]

    def _calculate_similarity(
        self, query: str, content: str, method: str = "jaccard"
    ) -> float:
        """
        Calculate similarity between query and content.

        Methods: jaccard, cosine (simplified)
        """
        query_words = self._tokenize(query.lower())
        content_words = self._tokenize(content.lower())

        if method == "jaccard":
            # Jaccard similarity
            query_set = set(query_words)
            content_set = set(content_words)

            if not query_set and not content_set:
                return 0.0

            intersection = len(query_set & content_set)
            union = len(query_set | content_set)

            if union == 0:
                return 0.0

            return intersection / union

        else:
            # Simple word overlap ratio
            if not query_words:
                return 0.0

            query_set = set(query_words)
            content_set = set(content_words)

            matches = sum(1 for word in query_words if word in content_set)

            return matches / len(query_words)

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenizer - splits into words"""
        # Remove punctuation and split
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        return [word for word in text.split() if word]

    async def semantic_search(
        self,
        query: str,
        user_id: str,
        exclude_paper_id: Optional[str] = None,
    ) -> List[Tuple[MemoryChunk, float]]:
        """
        Perform semantic search (simplified for MVP).
        """
        # For MVP, use simple text similarity
        # In production, integrate with actual vector embeddings
        return await self.search_similar(
            query_text=query,
            user_id=user_id,
            exclude_paper_id=exclude_paper_id,
            limit=5,
            threshold=0.6,  # Lower threshold for semantic search
        )


# Singleton instance
_vector_search_service: Optional[VectorSearchService] = None


def get_vector_search_service() -> VectorSearchService:
    """Get or create vector search service singleton"""
    global _vector_search_service
    if _vector_search_service is None:
        _vector_search_service = VectorSearchService()
    return _vector_search_service
