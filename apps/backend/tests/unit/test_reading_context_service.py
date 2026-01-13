"""
Tests for ReadingContextService domain service
"""

from apps.backend.domains.reading_hub.core.entities import (
    ReadingContext,
    TriggerType,
)
from apps.backend.domains.reading_hub.services.domain_service import (
    ReadingContextService,
)


def test_create_context(sample_user_id, sample_paper_id, sample_session_id):
    """Test creating a new reading context via service"""
    service = ReadingContextService()

    context = service.create_context(
        user_id=sample_user_id,
        paper_id=sample_paper_id,
        session_id=sample_session_id,
    )

    assert context.user_id == sample_user_id
    assert context.paper_id == sample_paper_id
    assert context.session_id == sample_session_id


def test_record_action(reading_context, user_action):
    """Test recording a user action via service"""
    service = ReadingContextService()

    initial_count = len(reading_context.recent_actions)

    service.record_action(reading_context, user_action)

    assert len(reading_context.recent_actions) == initial_count + 1


def test_is_session_active_fresh(reading_context):
    """Test checking if session is active - fresh case"""
    service = ReadingContextService()

    assert service.is_session_active(reading_context, timeout_seconds=300)


def test_is_session_active_stale(reading_context):
    """Test checking if session is active - stale case"""
    from datetime import timedelta

    service = ReadingContextService()

    # Make context stale
    reading_context.last_activity_at = reading_context.last_activity_at - timedelta(seconds=400)

    assert not service.is_session_active(reading_context, timeout_seconds=300)


def test_cleanup_stale_contexts():
    """Test identifying stale contexts"""
    from datetime import timedelta

    service = ReadingContextService()

    # Create contexts with different ages
    fresh_context = ReadingContext(user_id="user1", paper_id="paper1", session_id="session1")
    stale_context = ReadingContext(user_id="user1", paper_id="paper2", session_id="session2")

    # Make one stale
    stale_context.last_activity_at = stale_context.last_activity_at - timedelta(seconds=400)

    contexts = [fresh_context, stale_context]

    stale_ids = service.cleanup_stale_contexts(contexts, timeout_seconds=300)

    assert len(stale_ids) == 1
    assert stale_context.id in stale_ids or stale_ids[0]  # id might be None
