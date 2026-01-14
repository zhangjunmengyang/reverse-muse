"""
Reading Hub - Repository Ports

Interfaces for reading context persistence.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from apps.backend.domains.reading_hub.core.entities import ReadingContext


class ReadingContextRepository(ABC):
    """Repository interface for reading contexts"""

    @abstractmethod
    async def save(self, context: ReadingContext) -> None:
        """Save a reading context"""
        pass

    @abstractmethod
    async def get_by_id(self, context_id: str) -> Optional[ReadingContext]:
        """Get a reading context by ID"""
        pass

    @abstractmethod
    async def get_active_by_user(
        self, user_id: str, timeout_seconds: int = 300
    ) -> Optional[ReadingContext]:
        """Get active reading context for user"""
        pass

    @abstractmethod
    async def get_by_session(self, session_id: str) -> Optional[ReadingContext]:
        """Get a reading context by session ID"""
        pass

    @abstractmethod
    async def list_by_user(
        self, user_id: str, paper_id: Optional[str] = None
    ) -> List[ReadingContext]:
        """List reading contexts for user"""
        pass

    @abstractmethod
    async def delete(self, context_id: str) -> None:
        """Delete a reading context"""
        pass

    @abstractmethod
    async def cleanup_stale(self, timeout_seconds: int = 300) -> int:
        """Cleanup stale contexts and return count of deleted"""
        pass
