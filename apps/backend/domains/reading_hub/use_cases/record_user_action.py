"""
Use Case: Record User Action

Orchestrates recording user actions and triggers insight generation.
"""

from typing import List, Optional

from apps.backend.domains.insight_hub.core.entities import BubbleInsight
from apps.backend.domains.insight_hub.use_cases.generate_insight import (
    GenerateInsightUseCase,
)
from apps.backend.domains.memory_hub.core.entities import MemoryChunk
from apps.backend.domains.memory_hub.port.repository import MemoryChunkRepository
from apps.backend.domains.reading_hub.core.entities import (
    ReadingContext,
    UserAction,
)
from apps.backend.domains.reading_hub.port.repository import (
    ReadingContextRepository,
)
from apps.backend.domains.reading_hub.services.domain_service import (
    ReadingContextService,
)


class RecordUserActionUseCase:
    """Use case for recording user actions"""

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
        """Execute use case"""
        # Get context
        if not context_id:
            return None
        context = await self.context_repo.get_by_id(context_id)
        if not context:
            return None

        # Record action
        self.context_service.record_action(context, action)

        # Update position if needed
        self.context_service.update_position(
            context,
            action.reading_position.paper_id,
            action.reading_position.page_number,
            action.reading_position.bbox,
            action.reading_position.text_snippet,
        )

        # Save updated context
        await self.context_repo.save(context)

        # Generate insight if applicable
        # Only generate for specific trigger types
        if action.trigger_type.value in ["selection", "linger"]:
            # Retrieve relevant memories
            query_text = action.selected_text or action.context_text or ""
            if query_text:
                # Note: This is a simplified flow
                # In production, we'd search by embedding
                related_memories = await self.memory_repo.list_by_paper(
                    user_id=context.user_id,
                    paper_id=context.paper_id,
                )

                # Generate insight
                insight = await self.insight_use_case.execute(
                    user_id=context.user_id,
                    context_id=context.id,
                    action=action,
                    related_memories=related_memories,
                )

                return insight

        return None
