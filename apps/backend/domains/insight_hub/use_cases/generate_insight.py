"""
Use Case: Generate Insight with LLM

Orchestrates the generation of AI insights using LLM service.
"""

from typing import List, Optional, Tuple

from apps.backend.domains.insight_hub.core.entities import (
    BubbleInsight,
    InsightContext,
    InsightType,
)
from apps.backend.domains.insight_hub.port.repository import InsightRepository
from apps.backend.domains.insight_hub.services.domain_service import (
    InsightGenerationService,
)
from apps.backend.infrastructure.llm import get_llm_service
from apps.backend.infrastructure.vector import get_vector_search_service


class GenerateInsightUseCase:
    """Use case for generating AI insights with LLM"""

    def __init__(
        self,
        insight_repo: InsightRepository,
        insight_service: InsightGenerationService,
    ):
        self.insight_repo = insight_repo
        self.insight_service = insight_service

    async def execute(
        self,
        user_id: str,
        context_id: str,
        action: "UserAction",
        related_memories: List["MemoryChunk"],
        confidence_threshold: float = 0.8,
    ) -> Optional[BubbleInsight]:
        """Execute the use case with LLM integration"""

        # Get vector search service
        vector_service = get_vector_search_service()

        # Perform semantic search for related memories
        search_results = await vector_service.search_similar(
            query_text=action.selected_text or action.context_text or "",
            user_id=user_id,
            exclude_paper_id=action.reading_position.paper_id,
        )

        # Use top 5 related memories
        top_memories = [result[0] for result in search_results[:5]]

        # Generate insight using LLM
        try:
            insight_content, confidence = await get_llm_service().generate_insight(
                user_id=user_id,
                selected_text=action.selected_text or "",
                context_text=action.context_text or "",
                related_memories=[
                    {
                        "content": m.content,
                        "paper_title": m.metadata.paper_title,
                    }
                    for m in top_memories
                ],
                reading_position={
                    "paper_id": action.reading_position.paper_id,
                    "page_number": action.reading_position.page_number,
                },
            )
        except Exception as e:
            import structlog

            logger = structlog.get_logger(__name__)
            logger.warning("LLM generation failed, using fallback", error=str(e))
            # Use fallback
            insight_content, confidence = get_llm_service()._generate_mock_insight(
                action.selected_text or "",
                [{"content": m.content, "paper_title": m.metadata.paper_title}
                 for m in top_memories],
            )

        # Check if insight meets threshold
        if confidence < confidence_threshold or not insight_content:
            return None

        # Create insight context
        insight_context = InsightContext(
            trigger_type=action.trigger_type.value,
            paper_id=action.reading_position.paper_id,
            page_number=action.reading_position.page_number,
            selected_text=action.selected_text,
            context_text=action.context_text,
            related_memory_ids=[m.id for m in related_memories if m.id],
            related_paper_titles=[
                m.metadata.paper_title
                for m in related_memories
                if not m.is_from_same_paper(action.reading_position.paper_id)
            ],
        )

        # Determine insight type based on trigger
        insight_type = self._determine_insight_type(action, top_memories)

        # Create insight
        insight = self.insight_service.create_insight(
            user_id=user_id,
            reading_context_id=context_id,
            insight_type=insight_type,
            content=insight_content,
            confidence=confidence,
            context=insight_context,
        )

        # Check for duplicates
        existing_insights = await self.insight_repo.list_by_context(context_id)
        if self.insight_service.is_duplicate_insight(insight, existing_insights):
            import structlog

            logger = structlog.get_logger(__name__)
            logger.info("Skipping duplicate insight")
            return None

        # Save insight
        await self.insight_repo.save(insight)

        return insight

    def _determine_insight_type(
        self, action: "UserAction", related_memories: List["MemoryChunk"]
    ) -> InsightType:
        """Determine insight type based on action and context"""
        if action.trigger_type.value == "selection":
            return InsightType.EXPLANATION

        if related_memories:
            has_relation = any(
                not m.is_from_same_paper(action.reading_position.paper_id)
                for m in related_memories
            )
            if has_relation:
                return InsightType.CONNECTION
            return InsightType.SIMILARITY

        return InsightType.CUSTOM
