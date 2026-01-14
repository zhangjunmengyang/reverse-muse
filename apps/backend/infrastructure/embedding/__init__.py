"""
Embedding infrastructure module.
"""

from apps.backend.infrastructure.embedding.embedding_service import (
    EmbeddingService,
    get_embedding_service,
)

__all__ = ["EmbeddingService", "get_embedding_service"]
