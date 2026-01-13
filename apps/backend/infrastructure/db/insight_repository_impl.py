"""
SurrealDB Implementation of InsightRepository
"""

from datetime import datetime, timedelta
from typing import List, Optional

import structlog

from apps.backend.domains.insight_hub.core.entities import (
    BubbleInsight,
    InsightStatus,
    InsightType,
)
from apps.backend.domains.insight_hub.port.repository import InsightRepository
from apps.backend.infrastructure.db.connection import get_db

logger = structlog.get_logger(__name__)


class SurrealInsightRepository(InsightRepository):
    """SurrealDB implementation of insight repository"""

    async def save(self, insight: BubbleInsight) -> None:
        """Save an insight"""
        db = await get_db()

        data = self._entity_to_dict(insight)

        if insight.id:
            await db.update("insights", insight.id, data)
        else:
            result = await db.create("insights", data)
            insight.id = result[0]["id"]

    async def get_by_id(self, insight_id: str) -> Optional[BubbleInsight]:
        """Get an insight by ID"""
        db = await get_db()
        result = await db.select("insights", insight_id)
        if result:
            return self._dict_to_entity(result[0])
        return None

    async def list_by_context(
        self, reading_context_id: str
    ) -> List[BubbleInsight]:
        """List insights for a reading context"""
        db = await get_db()
        result = await db.query(
            """
            SELECT * FROM insights
            WHERE reading_context_id = $context_id
            ORDER BY created_at DESC
            """,
            context_id=reading_context_id,
        )
        return [self._dict_to_entity(row) for row in result[0]]

    async def list_by_user(
        self,
        user_id: str,
        paper_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[BubbleInsight]:
        """List insights for a user"""
        db = await get_db()

        if paper_id:
            result = await db.query(
                """
                SELECT * FROM insights
                WHERE user_id = $user_id AND paper_id = $paper_id
                ORDER BY created_at DESC
                LIMIT $limit
                """,
                user_id=user_id,
                paper_id=paper_id,
                limit=limit,
            )
        else:
            result = await db.query(
                """
                SELECT * FROM insights
                WHERE user_id = $user_id
                ORDER BY created_at DESC
                LIMIT $limit
                """,
                user_id=user_id,
                limit=limit,
            )

        return [self._dict_to_entity(row) for row in result[0]]

    async def get_pending_insights(
        self, reading_context_id: str
    ) -> List[BubbleInsight]:
        """Get insights that are ready to be displayed"""
        db = await get_db()
        result = await db.query(
            """
            SELECT * FROM insights
            WHERE reading_context_id = $context_id
            AND status = $status
            ORDER BY created_at DESC
            """,
            context_id=reading_context_id,
            status=InsightStatus.GENERATED.value,
        )
        return [self._dict_to_entity(row) for row in result[0]]

    async def delete(self, insight_id: str) -> None:
        """Delete an insight"""
        db = await get_db()
        await db.delete("insights", insight_id)

    async def cleanup_old(self, older_than_days: int = 7) -> int:
        """Delete old insights and return count deleted"""
        db = await get_db()
        threshold = datetime.utcnow() - timedelta(days=older_than_days)

        result = await db.query(
            """
            SELECT id FROM insights
            WHERE created_at < $threshold
            """,
            threshold=threshold.isoformat(),
        )

        if result and result[0]:
            insight_ids = [row["id"] for row in result[0]]
            for insight_id in insight_ids:
                await db.delete("insights", insight_id)
            return len(insight_ids)
        return 0

    def _entity_to_dict(self, entity: BubbleInsight) -> dict:
        """Convert entity to dict for storage"""
        data = {
            "user_id": entity.user_id,
            "reading_context_id": entity.reading_context_id,
            "insight_type": entity.insight_type.value,
            "content": entity.content,
            "confidence": entity.confidence,
            "status": entity.status.value,
            "paper_id": entity.context.paper_id,
            "page_number": entity.context.page_number,
            "trigger_type": entity.context.trigger_type,
        }
        if entity.id:
            data["id"] = entity.id
        return data

    def _dict_to_entity(self, data: dict) -> BubbleInsight:
        """Convert dict from storage to entity"""
        from apps.backend.domains.insight_hub.core.entities import InsightContext

        insight_type = InsightType(data.get("insight_type", "custom"))
        status = InsightStatus(data.get("status", "generating"))

        context = InsightContext(
            trigger_type=data.get("trigger_type", ""),
            paper_id=data.get("paper_id", ""),
            page_number=data.get("page_number", 0),
        )

        return BubbleInsight(
            id=data.get("id"),
            user_id=data.get("user_id", ""),
            reading_context_id=data.get("reading_context_id", ""),
            insight_type=insight_type,
            content=data.get("content", ""),
            confidence=data.get("confidence", 0.0),
            status=status,
            context=context,
        )
