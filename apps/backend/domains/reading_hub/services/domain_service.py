"""
Reading Hub - Domain Services

Business logic for managing reading contexts and triggers.
"""


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
