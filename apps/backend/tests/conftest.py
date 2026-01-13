"""
Test fixtures for unit tests
"""

from datetime import datetime

import pytest

from apps.backend.domains.reading_hub.core.entities import (
    ReadingContext,
    UserAction,
    ReadingPosition,
    TriggerType,
)
from apps.backend.domains.memory_hub.core.entities import (
    MemoryChunk,
    MemoryMetadata,
    MemorySource,
)
from apps.backend.domains.insight_hub.core.entities import (
    BubbleInsight,
    InsightContext,
    InsightType,
    InsightStatus,
)


@pytest.fixture
def sample_user_id():
    """Sample user ID"""
    return "user_test_123"


@pytest.fixture
def sample_paper_id():
    """Sample paper ID"""
    return "paper_test_456"


@pytest.fixture
def sample_session_id():
    """Sample session ID"""
    return "session_test_789"


@pytest.fixture
def reading_position(sample_paper_id):
    """Sample reading position"""
    return ReadingPosition(
        paper_id=sample_paper_id,
        page_number=5,
        bbox={"x": 100, "y": 200, "width": 50, "height": 20},
        text_snippet="sample text snippet",
    )


@pytest.fixture
def user_action(sample_paper_id, reading_position):
    """Sample user action"""
    return UserAction(
        trigger_type=TriggerType.SELECTION,
        reading_position=reading_position,
        selected_text="selected text",
        context_text="context text around selection",
        duration_seconds=None,
    )


@pytest.fixture
def reading_context(sample_user_id, sample_paper_id, sample_session_id):
    """Sample reading context"""
    return ReadingContext(
        id=None,
        user_id=sample_user_id,
        paper_id=sample_paper_id,
        session_id=sample_session_id,
    )


@pytest.fixture
def memory_metadata(sample_paper_id):
    """Sample memory metadata"""
    return MemoryMetadata(
        paper_id=sample_paper_id,
        paper_title="Test Paper Title",
        page_number=5,
        source=MemorySource.PDF_TEXT,
    )


@pytest.fixture
def memory_chunk(sample_user_id, memory_metadata):
    """Sample memory chunk"""
    return MemoryChunk(
        id=None,
        user_id=sample_user_id,
        content="This is a sample memory chunk content",
        embedding=[0.1, 0.2, 0.3],
        metadata=memory_metadata,
    )


@pytest.fixture
def insight_context(sample_paper_id):
    """Sample insight context"""
    return InsightContext(
        trigger_type="selection",
        paper_id=sample_paper_id,
        page_number=5,
        selected_text="selected text",
        context_text="context text",
    )


@pytest.fixture
def bubble_insight(sample_user_id, insight_context):
    """Sample bubble insight"""
    return BubbleInsight(
        id=None,
        user_id=sample_user_id,
        reading_context_id="context_123",
        insight_type=InsightType.EXPLANATION,
        content="This is an AI-generated insight",
        confidence=0.85,
        context=insight_context,
        status=InsightStatus.GENERATED,
    )
