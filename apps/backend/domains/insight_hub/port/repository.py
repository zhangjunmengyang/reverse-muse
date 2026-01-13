"""
Insight Hub - Repository Ports

Interfaces for insight persistence.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from apps.backend.domains.insight_hub.core.entities import BubbleInsight


class InsightRepository(ABC):
    """Repository interface for insights"""

    @abstractmethod
    async def save(self, insight: BubbleInsight) -> None:
        """Save an insight"""
        pass

    @abstractmethod
    async def get_by_id(self, insight_id: str) -> Optional[BubbleInsight]:
        """Get an insight by ID"""
        pass

    @abstractmethod
    async def list_by_context(
        self, reading_context_id: str
    ) -> List[BubbleInsight]:
        """List insights for a reading context"""
        pass

    @abstractmethod
    async def list_by_user(
        self,
        user_id: str,
        paper_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[BubbleInsight]:
        """List insights for a user"""
        pass

    @abstractmethod
    async def get_pending_insights(
        self, reading_context_id: str
    ) -> List[BubbleInsight]:
        """Get insights that are ready to be displayed"""
        pass

    @abstractmethod
    async def delete(self, insight_id: str) -> None:
        """Delete an insight"""
        pass

    @abstractmethod
    async def cleanup_old(
        self, older_than_days: int = 7
    ) -> int:
        """Delete old insights and return count deleted"""
        pass
