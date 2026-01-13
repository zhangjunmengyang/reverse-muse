"""
Reading Hub - Domain Services

Business logic for managing reading contexts and triggers.
"""

from typing import List, Optional

from apps.backend.domains.reading_hub.core.entities import (
    ReadingContext,
    UserAction,
)


class ReadingContextService:
    """Service for managing reading context"""

    def create_context(
        self,
        user_id: str,
        paper_id: str,
        session_id: str,
    ) -> ReadingContext:
        """Create a new reading context"""
        return ReadingContext(
            user_id=user_id,
            paper_id=paper_id,
            session_id=session_id,
        )

    def record_action(
        self,
        context: ReadingContext,
        action: UserAction,
    ) -> None:
        """Record a user action in the context"""
        context.add_action(action)

    def update_position(
        self,
        context: ReadingContext,
        paper_id: str,
        page_number: int,
        bbox: Optional[dict] = None,
        text_snippet: Optional[str] = None,
    ) -> None:
        """Update current reading position"""
        from apps.backend.domains.reading_hub.core.entities import ReadingPosition

        position = ReadingPosition(
            paper_id=paper_id,
            page_number=page_number,
            bbox=bbox,
            text_snippet=text_snippet,
        )
        context.update_position(position)

    def is_session_active(self, context: ReadingContext, timeout_seconds: int = 300) -> bool:
        """Check if the reading session is still active"""
        return not context.is_stale(timeout_seconds)

    def cleanup_stale_contexts(
        self,
        contexts: List[ReadingContext],
        timeout_seconds: int = 300,
    ) -> List[str]:
        """Identify and return IDs of stale contexts"""
        stale_ids = []
        for context in contexts:
            if context.is_stale(timeout_seconds):
                stale_ids.append(context.id)
        return stale_ids
