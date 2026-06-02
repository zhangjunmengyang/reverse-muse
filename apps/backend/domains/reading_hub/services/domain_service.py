"""
Reading Hub - Domain Services

Business logic for managing reading contexts and triggers.
"""

from typing import List

from apps.backend.domains.reading_hub.core.entities import (
    ReadingContext,
    ReadingPosition,
    UserAction,
)


class ReadingContextService:
    """Service for managing reading context."""

    def create_context(
        self,
        user_id: str,
        paper_id: str,
        session_id: str,
    ) -> ReadingContext:
        """Create a new reading context."""
        return ReadingContext(
            user_id=user_id,
            paper_id=paper_id,
            session_id=session_id,
        )

    def record_action_and_update_position(
        self,
        context: ReadingContext,
        action: UserAction,
    ) -> None:
        """Record a user action and update the reading position."""
        context.add_action(action)
        position = ReadingPosition(
            paper_id=action.reading_position.paper_id,
            page_number=action.reading_position.page_number,
            bbox=action.reading_position.bbox,
            text_snippet=action.reading_position.text_snippet,
        )
        context.update_position(position)

    def record_action(
        self,
        context: ReadingContext,
        action: UserAction,
    ) -> None:
        """Record a user action and keep the current position in sync."""
        self.record_action_and_update_position(context, action)

    def is_session_active(
        self,
        context: ReadingContext,
        timeout_seconds: int = 300,
    ) -> bool:
        """Return whether the reading context has recent activity."""
        return not context.is_stale(timeout_seconds=timeout_seconds)

    def cleanup_stale_contexts(
        self,
        contexts: List[ReadingContext],
        timeout_seconds: int = 300,
    ) -> List[str]:
        """Return stable identifiers for stale contexts."""
        return [
            context.id or context.session_id
            for context in contexts
            if context.is_stale(timeout_seconds=timeout_seconds)
        ]
