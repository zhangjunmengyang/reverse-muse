"""
Tests for InsightGenerationService domain service
"""

from apps.backend.domains.insight_hub.core.entities import (
    BubbleInsight,
    InsightContext,
    InsightType,
)
from apps.backend.domains.insight_hub.services.domain_service import (
    InsightGenerationService,
)


def test_create_insight(sample_user_id):
    """Test creating a new insight via service"""
    service = InsightGenerationService()

    context = InsightContext(
        trigger_type="selection",
        paper_id="paper_1",
        page_number=5,
        selected_text="selected",
    )

    insight = service.create_insight(
        user_id=sample_user_id,
        reading_context_id="context_123",
        insight_type=InsightType.EXPLANATION,
        content="Insight content",
        confidence=0.9,
        context=context,
    )

    assert insight.user_id == sample_user_id
    assert insight.reading_context_id == "context_123"
    assert insight.insight_type == InsightType.EXPLANATION
    assert insight.content == "Insight content"
    assert insight.confidence == 0.9


def test_filter_high_confidence():
    """Test filtering insights by confidence threshold"""
    service = InsightGenerationService()

    insights = [
        BubbleInsight(
            id="1",
            user_id="user1",
            reading_context_id="c1",
            insight_type=InsightType.EXPLANATION,
            content="Insight 1",
            confidence=0.9,
        ),
        BubbleInsight(
            id="2",
            user_id="user1",
            reading_context_id="c1",
            insight_type=InsightType.CONNECTION,
            content="Insight 2",
            confidence=0.7,
        ),
        BubbleInsight(
            id="3",
            user_id="user1",
            reading_context_id="c1",
            insight_type=InsightType.EXPLANATION,
            content="Insight 3",
            confidence=0.85,
        ),
    ]

    filtered = service.filter_high_confidence(insights, threshold=0.8)

    assert len(filtered) == 2
    assert all(i.confidence >= 0.8 for i in filtered)


def test_mark_insight_displayed(bubble_insight):
    """Test marking insight as displayed via service"""
    service = InsightGenerationService()

    service.mark_insight_displayed(bubble_insight)

    assert bubble_insight.status.value == "displayed"


def test_mark_insight_dismissed(bubble_insight):
    """Test marking insight as dismissed via service"""
    service = InsightGenerationService()

    service.mark_insight_dismissed(bubble_insight)

    assert bubble_insight.status.value == "dismissed"


def test_pin_insight(bubble_insight):
    """Test pinning an insight via service"""
    service = InsightGenerationService()

    service.pin_insight(bubble_insight)

    assert bubble_insight.status.value == "pinned"


def test_get_displayable_insights():
    """Test getting insights that should be displayed"""
    service = InsightGenerationService()

    from apps.backend.domains.insight_hub.core.entities import InsightStatus

    insights = [
        BubbleInsight(
            id="1",
            user_id="user1",
            reading_context_id="c1",
            insight_type=InsightType.EXPLANATION,
            content="Displayable",
            confidence=0.9,
            status=InsightStatus.GENERATED,
        ),
        BubbleInsight(
            id="2",
            user_id="user1",
            reading_context_id="c1",
            insight_type=InsightType.CONNECTION,
            content="Low confidence",
            confidence=0.5,
            status=InsightStatus.GENERATED,
        ),
        BubbleInsight(
            id="3",
            user_id="user1",
            reading_context_id="c1",
            insight_type=InsightType.EXPLANATION,
            content="Already displayed",
            confidence=0.9,
            status=InsightStatus.DISPLAYED,
        ),
    ]

    displayable = service.get_displayable_insights(insights, confidence_threshold=0.8)

    assert len(displayable) == 1
    assert displayable[0].content == "Displayable"


def test_is_duplicate_insight():
    """Test checking if insight is duplicate"""
    service = InsightGenerationService()

    from apps.backend.domains.insight_hub.core.entities import InsightStatus

    existing_insights = [
        BubbleInsight(
            id="1",
            user_id="user1",
            reading_context_id="c1",
            insight_type=InsightType.EXPLANATION,
            content="Existing insight",
            confidence=0.9,
            status=InsightStatus.GENERATED,
        ),
    ]

    # Duplicate insight (same content, case insensitive)
    duplicate_insight = BubbleInsight(
        id="2",
        user_id="user1",
        reading_context_id="c1",
        insight_type=InsightType.EXPLANATION,
        content="existing insight",  # Same content, different case
        confidence=0.9,
    )

    assert service.is_duplicate_insight(duplicate_insight, existing_insights)

    # Non-duplicate insight
    new_insight = BubbleInsight(
        id="3",
        user_id="user1",
        reading_context_id="c1",
        insight_type=InsightType.EXPLANATION,
        content="Completely new insight",
        confidence=0.9,
    )

    assert not service.is_duplicate_insight(new_insight, existing_insights)
