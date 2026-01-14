"""
Insight Hub - Domain Services

Business logic for generating and managing AI insights.
"""

from typing import List

from apps.backend.domains.insight_hub.core.entities import (
    BubbleInsight,
    InsightContext,
    InsightType,
)


class InsightGenerationService:
    """Service for generating insights."""

    def create_insight(
        self,
        user_id: str,
        reading_context_id: str,
        insight_type: InsightType,
        content: str,
        confidence: float,
        context: InsightContext,
    ) -> BubbleInsight:
        """Create a new insight."""
        return BubbleInsight(
            user_id=user_id,
            reading_context_id=reading_context_id,
            insight_type=insight_type,
            content=content,
            confidence=confidence,
            context=context,
        )

    def is_duplicate_insight(
        self,
        new_insight: BubbleInsight,
        existing_insights: List[BubbleInsight],
    ) -> bool:
        """
        Check if the new insight is a duplicate of existing ones.
        For MVP, this is a simple string comparison.
        """
        new_content = new_insight.content.lower()
        return any(
            new_content == existing.content.lower()
            for existing in existing_insights
        )
