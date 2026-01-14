"""
SurrealDB Implementation of InsightRepository
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

from apps.backend.domains.insight_hub.core.entities import (
    BubbleInsight,
    InsightContext,
    InsightStatus,
    InsightType,
)
from apps.backend.domains.insight_hub.port.repository import InsightRepository
from apps.backend.infrastructure.db.base_repository import BaseSurrealRepository
from apps.backend.infrastructure.db.connection import get_db

logger = structlog.get_logger(__name__)


class SurrealInsightRepository(BaseSurrealRepository[BubbleInsight], InsightRepository):
    """SurrealDB implementation of insight repository."""

    table_name = "insights"

    async def list_by_context(self, reading_context_id: str) -> List[BubbleInsight]:
        """List insights for a reading context."""
        results = await self.query(
            f"SELECT * FROM {self.table_name} "
            f"WHERE reading_context_id = '{reading_context_id}' "
            f"ORDER BY created_at DESC"
        )
        return [self._dict_to_entity(row) for row in results if isinstance(row, dict)]

    async def list_by_user(
        self,
        user_id: str,
        paper_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[BubbleInsight]:
        """List insights for a user."""
        if paper_id:
            sql = (
                f"SELECT * FROM {self.table_name} "
                f"WHERE user_id = '{user_id}' AND paper_id = '{paper_id}' "
                f"ORDER BY created_at DESC LIMIT {limit}"
            )
        else:
            sql = (
                f"SELECT * FROM {self.table_name} "
                f"WHERE user_id = '{user_id}' "
                f"ORDER BY created_at DESC LIMIT {limit}"
            )
        results = await self.query(sql)
        return [self._dict_to_entity(row) for row in results if isinstance(row, dict)]

    async def get_pending_insights(self, reading_context_id: str) -> List[BubbleInsight]:
        """Get insights that are ready to be displayed."""
        status = InsightStatus.GENERATED.value
        results = await self.query(
            f"SELECT * FROM {self.table_name} "
            f"WHERE reading_context_id = '{reading_context_id}' AND status = '{status}' "
            f"ORDER BY created_at DESC"
        )
        return [self._dict_to_entity(row) for row in results if isinstance(row, dict)]

    async def cleanup_old(self, older_than_days: int = 7) -> int:
        """Delete old insights and return count deleted."""
        db = await get_db()
        threshold = datetime.utcnow() - timedelta(days=older_than_days)
        results = await self.query(
            f"SELECT id FROM {self.table_name} WHERE created_at < '{threshold.isoformat()}'"
        )
        if not results:
            return 0

        for row in results:
            if isinstance(row, dict) and "id" in row:
                await db.delete(row["id"])
        return len(results)

    def _entity_to_dict(self, entity: BubbleInsight) -> Dict[str, Any]:
        """Convert entity to dict for storage."""
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

    def _dict_to_entity(self, data: Dict[str, Any]) -> BubbleInsight:
        """Convert dict from storage to entity."""
        context = InsightContext(
            trigger_type=data.get("trigger_type", ""),
            paper_id=data.get("paper_id", ""),
            page_number=data.get("page_number", 0),
        )

        return BubbleInsight(
            id=data.get("id"),
            user_id=data.get("user_id", ""),
            reading_context_id=data.get("reading_context_id", ""),
            insight_type=InsightType(data.get("insight_type", "custom")),
            content=data.get("content", ""),
            confidence=data.get("confidence", 0.0),
            status=InsightStatus(data.get("status", "generating")),
            context=context,
        )

    def _get_entity_id(self, entity: BubbleInsight) -> Optional[str]:
        return entity.id

    def _set_entity_id(self, entity: BubbleInsight, entity_id: Optional[str]) -> None:
        entity.id = entity_id
