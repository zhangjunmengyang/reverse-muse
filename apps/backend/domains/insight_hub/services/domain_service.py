"""
Insight Hub - Domain Services

Business logic for generating and managing AI insights.
"""

from typing import List

from apps.backend.domains.insight_hub.core.entities import (
    BubbleInsight,
    InsightContext,
    InsightStatus,
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
            status=InsightStatus.GENERATED,
        )

    def filter_high_confidence(
        self,
        insights: List[BubbleInsight],
        threshold: float = 0.8,
    ) -> List[BubbleInsight]:
        """Keep insights whose confidence meets the threshold."""
        return [insight for insight in insights if insight.confidence >= threshold]

    def mark_insight_displayed(self, insight: BubbleInsight) -> None:
        """Mark an insight as displayed."""
        insight.mark_displayed()

    def mark_insight_dismissed(self, insight: BubbleInsight) -> None:
        """Mark an insight as dismissed."""
        insight.mark_dismissed()

    def pin_insight(self, insight: BubbleInsight) -> None:
        """Pin an insight for later review."""
        insight.mark_pinned()

    def get_displayable_insights(
        self,
        insights: List[BubbleInsight],
        confidence_threshold: float = 0.8,
    ) -> List[BubbleInsight]:
        """Return insights that are ready and useful enough to display."""
        return [
            insight
            for insight in insights
            if insight.should_display(confidence_threshold=confidence_threshold)
        ]

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
