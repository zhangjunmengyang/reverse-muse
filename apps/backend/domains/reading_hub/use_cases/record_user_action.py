"""
Use Case: Record User Action

Orchestrates recording user actions and triggers insight generation.
"""

from typing import Optional

import structlog

from apps.backend.domains.insight_hub.core.entities import BubbleInsight
from apps.backend.domains.insight_hub.use_cases.generate_insight import (
    GenerateInsightUseCase,
)
from apps.backend.domains.memory_hub.port.repository import MemoryChunkRepository
from apps.backend.domains.reading_hub.core.entities import UserAction
from apps.backend.domains.reading_hub.port.repository import ReadingContextRepository
from apps.backend.domains.reading_hub.services.domain_service import (
    ReadingContextService,
)

INSIGHT_TRIGGERS = {"selection", "linger", "backtrack"}
logger = structlog.get_logger(__name__)


def is_timeout_error(error: Exception) -> bool:
    error_text = str(error).lower()
    return isinstance(error, TimeoutError) or "timeout" in error_text or "timed out" in error_text


class RecordUserActionUseCase:
    """Use case for recording user actions."""

    def __init__(
        self,
        context_repo: ReadingContextRepository,
        context_service: ReadingContextService,
        memory_repo: MemoryChunkRepository,
        insight_use_case: GenerateInsightUseCase,
    ):
        self.context_repo = context_repo
        self.context_service = context_service
        self.memory_repo = memory_repo
        self.insight_use_case = insight_use_case

    async def execute(
        self,
        context_id: Optional[str],
        action: UserAction,
    ) -> Optional[BubbleInsight]:
        """Execute use case."""
        if not context_id:
            return None

        context = await self.context_repo.get_by_id(context_id)
        if not context:
            return None

        # Record action and update position
        self.context_service.record_action_and_update_position(context, action)
        await self.context_repo.save(context)

        # Generate insight if applicable
        if action.trigger_type.value not in INSIGHT_TRIGGERS:
            return None

        query_text = action.selected_text or action.context_text or ""
        if not query_text:
            return None

        related_memories = await self.memory_repo.list_by_paper(
            user_id=context.user_id,
            paper_id=context.paper_id,
        )

        try:
            return await self.insight_use_case.execute(
                user_id=context.user_id,
                context_id=context.id,
                action=action,
                related_memories=related_memories,
            )
        except Exception as error:
            if not is_timeout_error(error):
                raise

            logger.warning(
                "Insight generation timed out; action remains recorded",
                trigger_type=action.trigger_type.value,
                context_id=context_id,
                error=str(error),
            )
            return None
