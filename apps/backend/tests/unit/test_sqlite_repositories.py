"""
Tests for SQLite repository implementations.
"""

import asyncio
from datetime import datetime, timedelta

from apps.backend.domains.insight_hub.core.entities import (
    BubbleInsight,
    InsightContext,
    InsightStatus,
    InsightType,
)
from apps.backend.domains.memory_hub.core.entities import MemoryChunk, MemoryMetadata
from apps.backend.domains.reading_hub.core.entities import (
    ReadingContext,
    ReadingPosition,
    TriggerType,
    UserAction,
)
from apps.backend.infrastructure.db.sqlite_repository_impl import (
    SQLiteInsightRepository,
    SQLiteMemoryChunkRepository,
    SQLiteReadingContextRepository,
    SQLiteStore,
)


def test_sqlite_reading_context_repository_round_trips_context(tmp_path):
    async def run_test():
        store = SQLiteStore(tmp_path / "reading.sqlite")
        repo = SQLiteReadingContextRepository(store)

        context = ReadingContext(
            user_id="user_1",
            paper_id="paper_1",
            session_id="session_1",
            current_position=ReadingPosition(
                paper_id="paper_1",
                page_number=2,
                text_snippet="interesting paragraph",
            ),
        )
        context.add_action(
            UserAction(
                trigger_type=TriggerType.SELECTION,
                reading_position=context.current_position,
                selected_text="interesting paragraph",
            )
        )

        await repo.save(context)

        loaded = await repo.get_by_id(context.id or "")
        active = await repo.get_active_by_user("user_1")
        by_session = await repo.get_by_session("session_1")
        listed = await repo.list_by_user("user_1", paper_id="paper_1")

        assert loaded is not None
        assert loaded.current_position is not None
        assert loaded.current_position.page_number == 2
        assert len(loaded.recent_actions) == 1
        assert active and active.id == context.id
        assert by_session and by_session.id == context.id
        assert [item.id for item in listed] == [context.id]

        loaded.last_activity_at = datetime.utcnow() - timedelta(seconds=600)
        await repo.save(loaded)
        assert await repo.cleanup_stale(timeout_seconds=300) == 1
        store.conn.close()

    asyncio.run(run_test())


def test_sqlite_memory_chunk_repository_supports_library_and_similarity(tmp_path):
    async def run_test():
        store = SQLiteStore(tmp_path / "memory.sqlite")
        repo = SQLiteMemoryChunkRepository(store)

        first = MemoryChunk(
            user_id="user_1",
            content="attention improves long-context reasoning",
            embedding=[1.0, 0.0, 0.0],
            metadata=MemoryMetadata(
                paper_id="paper_a",
                paper_title="Attention Paper",
                page_number=1,
            ),
        )
        second = MemoryChunk(
            user_id="user_1",
            content="diffusion models synthesize images",
            embedding=[0.0, 1.0, 0.0],
            metadata=MemoryMetadata(
                paper_id="paper_b",
                paper_title="Diffusion Paper",
                page_number=3,
            ),
        )

        await repo.batch_save([first, second])

        papers = await repo.list_distinct_papers()
        similar = await repo.search_similar(
            query_embedding=[1.0, 0.0, 0.0],
            user_id="user_1",
            threshold=0.9,
        )
        paper_chunks = await repo.list_by_paper("user_1", "paper_a")

        assert {paper["paper_id"] for paper in papers} == {"paper_a", "paper_b"}
        assert paper_chunks[0].content == first.content
        assert similar[0][0].metadata.paper_id == "paper_a"
        assert round(similar[0][1], 6) == 1.0
        assert await repo.delete_by_paper("user_1", "paper_b") == 1
        store.conn.close()

    asyncio.run(run_test())


def test_sqlite_insight_repository_round_trips_status_and_context(tmp_path):
    async def run_test():
        store = SQLiteStore(tmp_path / "insight.sqlite")
        repo = SQLiteInsightRepository(store)
        insight = BubbleInsight(
            user_id="user_1",
            reading_context_id="context_1",
            insight_type=InsightType.CONNECTION,
            content="This links to the prior attention paper.",
            confidence=0.92,
            context=InsightContext(
                trigger_type="selection",
                paper_id="paper_a",
                page_number=4,
                selected_text="attention heads",
                related_memory_ids=["memory_1"],
                related_paper_titles=["Attention Paper"],
            ),
            status=InsightStatus.GENERATED,
        )

        await repo.save(insight)

        loaded = await repo.get_by_id(insight.id or "")
        pending = await repo.get_pending_insights("context_1")
        by_user = await repo.list_by_user("user_1", paper_id="paper_a")

        assert loaded is not None
        assert loaded.context.paper_id == "paper_a"
        assert loaded.status == InsightStatus.GENERATED
        assert [item.id for item in pending] == [insight.id]
        assert [item.id for item in by_user] == [insight.id]

        loaded.mark_displayed()
        await repo.save(loaded)
        assert await repo.get_pending_insights("context_1") == []
        store.conn.close()

    asyncio.run(run_test())
