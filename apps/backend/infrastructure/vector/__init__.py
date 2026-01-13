"""
Vector Search Infrastructure
"""

from apps.backend.infrastructure.vector.vector_search_service import (
    VectorSearchService,
    get_vector_search_service,
)

__all__ = [
    "VectorSearchService",
    "get_vector_search_service",
]
