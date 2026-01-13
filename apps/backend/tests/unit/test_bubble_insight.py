"""
Tests for BubbleInsight domain entity
"""

from apps.backend.domains.insight_hub.core.entities import (
    BubbleInsight,
    InsightStatus,
    InsightType,
)


def test_create_bubble_insight(bubble_insight):
    """Test creating a new bubble insight"""
    assert bubble_insight.user_id == "user_test_123"
    assert bubble_insight.insight_type == InsightType.EXPLANATION
    assert bubble_insight.content == "This is an AI-generated insight"
    assert bubble_insight.confidence == 0.85
    assert bubble_insight.status == InsightStatus.GENERATED


def test_mark_displayed(bubble_insight):
    """Test marking insight as displayed"""
    bubble_insight.mark_displayed()

    assert bubble_insight.status == InsightStatus.DISPLAYED
    assert bubble_insight.displayed_at is not None


def test_mark_dismissed(bubble_insight):
    """Test marking insight as dismissed"""
    bubble_insight.mark_dismissed()

    assert bubble_insight.status == InsightStatus.DISMISSED


def test_mark_pinned(bubble_insight):
    """Test marking insight as pinned"""
    bubble_insight.mark_pinned()

    assert bubble_insight.status == InsightStatus.PINNED


def test_should_display_true(bubble_insight):
    """Test checking if insight should display - true case"""
    assert bubble_insight.should_display(confidence_threshold=0.8)


def test_should_display_false_low_confidence(bubble_insight):
    """Test checking if insight should display - false case (low confidence)"""
    bubble_insight.confidence = 0.7

    assert not bubble_insight.should_display(confidence_threshold=0.8)


def test_should_display_false_wrong_status(bubble_insight):
    """Test checking if insight should display - false case (wrong status)"""
    bubble_insight.status = InsightStatus.DISMISSED

    assert not bubble_insight.should_display(confidence_threshold=0.8)


def test_get_display_content_short(bubble_insight):
    """Test getting display content when content is short"""
    short_content = "Short insight"
    bubble_insight.content = short_content
    bubble_insight.max_display_length = 200

    assert bubble_insight.get_display_content() == short_content


def test_get_display_content_long(bubble_insight):
    """Test getting display content when content is long"""
    long_content = "This is a very long insight that exceeds the maximum display length limit for the bubble component"
    bubble_insight.content = long_content
    bubble_insight.max_display_length = 50

    result = bubble_insight.get_display_content()

    assert len(result) <= 50
    assert result.endswith("...")
