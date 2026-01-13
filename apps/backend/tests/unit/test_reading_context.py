"""
Tests for ReadingContext domain entity
"""

from datetime import datetime, timedelta

from apps.backend.domains.reading_hub.core.entities import (
    ReadingContext,
    UserAction,
    ReadingPosition,
    TriggerType,
)


def test_create_reading_context():
    """Test creating a new reading context"""
    context = ReadingContext(
        user_id="user_123",
        paper_id="paper_456",
        session_id="session_789",
    )

    assert context.user_id == "user_123"
    assert context.paper_id == "paper_456"
    assert context.session_id == "session_789"
    assert context.reading_progress == 0.0
    assert len(context.recent_actions) == 0


def test_add_user_action(reading_context, user_action):
    """Test adding a user action to context"""
    initial_count = len(reading_context.recent_actions)

    reading_context.add_action(user_action)

    assert len(reading_context.recent_actions) == initial_count + 1
    assert reading_context.last_activity_at > datetime.utcnow() - timedelta(seconds=1)


def test_add_action_respects_max_history(reading_context):
    """Test that adding actions respects max history limit"""
    max_history = 10

    for i in range(15):
        action = UserAction(
            trigger_type=TriggerType.SELECTION,
            reading_position=ReadingPosition(
                paper_id="paper_1",
                page_number=1,
            ),
        )
        reading_context.add_action(action, max_history=max_history)

    assert len(reading_context.recent_actions) == max_history


def test_update_position(reading_context, reading_position):
    """Test updating reading position"""
    reading_context.update_position(
        paper_id=reading_position.paper_id,
        page_number=reading_position.page_number,
        bbox=reading_position.bbox,
        text_snippet=reading_position.text_snippet,
    )

    assert reading_context.current_position is not None
    assert reading_context.current_position.page_number == reading_position.page_number
    assert reading_context.last_activity_at > datetime.utcnow() - timedelta(seconds=1)


def test_is_stale_fresh_context(reading_context):
    """Test that fresh context is not stale"""
    assert not reading_context.is_stale(timeout_seconds=300)


def test_is_stale_old_context(reading_context):
    """Test that old context is stale"""
    from datetime import datetime, timedelta

    # Manually set last_activity_at to past
    reading_context.last_activity_at = datetime.utcnow() - timedelta(seconds=400)

    assert reading_context.is_stale(timeout_seconds=300)
