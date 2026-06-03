"""
Tests for RecordUserActionUseCase trigger behavior.
"""

from apps.backend.domains.memory_hub.core.entities import MemoryChunk, MemoryMetadata
from apps.backend.domains.reading_hub.core.entities import (
    ReadingContext,
    ReadingPosition,
    TriggerType,
    UserAction,
)
from apps.backend.domains.reading_hub.services.domain_service import ReadingContextService
from apps.backend.domains.reading_hub.use_cases.record_user_action import (
    RecordUserActionUseCase,
)


class StubContextRepository:
    def __init__(self, context: ReadingContext):
        self.context = context
        self.saved = False

    async def get_by_id(self, context_id: str):
        if context_id == self.context.id:
            return self.context
        return None

    async def save(self, context: ReadingContext) -> None:
        self.saved = True
        self.context = context


class StubMemoryRepository:
    async def list_by_paper(self, user_id: str, paper_id: str):
        return [
            MemoryChunk(
                id="chunk_1",
                user_id=user_id,
                content="Prior context about the same concept.",
                metadata=MemoryMetadata(
                    paper_id=paper_id,
                    paper_title="Paper",
                    page_number=1,
                ),
            )
        ]


class StubInsightUseCase:
    def __init__(self):
        self.called = False
        self.action = None

    async def execute(self, **kwargs):
        self.called = True
        self.action = kwargs["action"]
        return None


class TimeoutInsightUseCase:
    async def execute(self, **kwargs):
        raise RuntimeError("Request timed out.")


async def test_backtrack_action_triggers_insight_generation():
    context = ReadingContext(
        id="context_1",
        user_id="user_1",
        paper_id="paper_1",
        session_id="session_1",
    )
    context_repo = StubContextRepository(context)
    insight_use_case = StubInsightUseCase()
    use_case = RecordUserActionUseCase(
        context_repo=context_repo,
        context_service=ReadingContextService(),
        memory_repo=StubMemoryRepository(),
        insight_use_case=insight_use_case,
    )
    action = UserAction(
        trigger_type=TriggerType.BACKTRACK,
        reading_position=ReadingPosition(
            paper_id="paper_1",
            page_number=1,
            text_snippet="This paragraph needed a second look.",
        ),
        selected_text="This paragraph needed a second look.",
        context_text="This paragraph needed a second look.",
    )

    await use_case.execute(context_id="context_1", action=action)

    assert context_repo.saved
    assert insight_use_case.called
    assert insight_use_case.action.trigger_type == TriggerType.BACKTRACK


async def test_insight_timeout_keeps_action_recorded():
    context = ReadingContext(
        id="context_1",
        user_id="user_1",
        paper_id="paper_1",
        session_id="session_1",
    )
    context_repo = StubContextRepository(context)
    use_case = RecordUserActionUseCase(
        context_repo=context_repo,
        context_service=ReadingContextService(),
        memory_repo=StubMemoryRepository(),
        insight_use_case=TimeoutInsightUseCase(),
    )
    action = UserAction(
        trigger_type=TriggerType.SELECTION,
        reading_position=ReadingPosition(
            paper_id="paper_1",
            page_number=1,
            text_snippet="attention",
        ),
        selected_text="attention",
        context_text="attention",
    )

    insight = await use_case.execute(context_id="context_1", action=action)

    assert insight is None
    assert context_repo.saved
    assert context.recent_actions[-1].selected_text == "attention"
