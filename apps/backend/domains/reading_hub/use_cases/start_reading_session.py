"""
Use Case: Start Reading Session

Orchestrates the creation of a new reading context.
"""

from typing import Optional

from apps.backend.domains.reading_hub.core.entities import ReadingContext
from apps.backend.domains.reading_hub.port.repository import (
    ReadingContextRepository,
)
from apps.backend.domains.reading_hub.services.domain_service import (
    ReadingContextService,
)


class StartReadingSessionUseCase:
    """Use case for starting a reading session"""

    def __init__(
        self,
        context_repo: ReadingContextRepository,
        context_service: ReadingContextService,
    ):
        self.context_repo = context_repo
        self.context_service = context_service

    async def execute(
        self,
        user_id: str,
        paper_id: str,
        session_id: str,
    ) -> ReadingContext:
        """Execute the use case"""
        # Check if there's an existing active context
        existing_context = await self.context_repo.get_active_by_user(user_id)
        if existing_context and existing_context.paper_id == paper_id:
            # Reuse existing context
            return existing_context

        # Create new context
        context = self.context_service.create_context(
            user_id=user_id,
            paper_id=paper_id,
            session_id=session_id,
        )

        # Save to repository
        await self.context_repo.save(context)

        return context
