"""
SurrealDB Implementation of ReadingContextRepository
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

from apps.backend.domains.reading_hub.core.entities import (
    ReadingContext,
    ReadingPosition,
)
from apps.backend.domains.reading_hub.port.repository import ReadingContextRepository
from apps.backend.infrastructure.db.base_repository import BaseSurrealRepository

logger = structlog.get_logger(__name__)


class SurrealReadingContextRepository(BaseSurrealRepository[ReadingContext], ReadingContextRepository):
    """SurrealDB implementation of reading context repository."""

    table_name = "reading_contexts"

    async def get_active_by_user(
        self, user_id: str, timeout_seconds: int = 300
    ) -> Optional[ReadingContext]:
        """Get active reading context for user."""
        threshold = datetime.utcnow() - timedelta(seconds=timeout_seconds)
        results = await self.query(
            f"SELECT * FROM {self.table_name} "
            f"WHERE user_id = '{user_id}' AND last_activity_at > '{threshold.isoformat()}' "
            f"ORDER BY last_activity_at DESC LIMIT 1"
        )
        if results:
            return self._dict_to_entity(results[0])
        return None

    async def get_by_session(self, session_id: str) -> Optional[ReadingContext]:
        """Get a reading context by session ID."""
        results = await self.query(
            f"SELECT * FROM {self.table_name} WHERE session_id = '{session_id}' LIMIT 1"
        )
        if results:
            return self._dict_to_entity(results[0])
        return None

    async def list_by_user(
        self, user_id: str, paper_id: Optional[str] = None
    ) -> List[ReadingContext]:
        """List reading contexts for user."""
        if paper_id:
            sql = (
                f"SELECT * FROM {self.table_name} "
                f"WHERE user_id = '{user_id}' AND paper_id = '{paper_id}' "
                f"ORDER BY last_activity_at DESC"
            )
        else:
            sql = (
                f"SELECT * FROM {self.table_name} "
                f"WHERE user_id = '{user_id}' "
                f"ORDER BY last_activity_at DESC"
            )
        results = await self.query(sql)
        return [self._dict_to_entity(row) for row in results if isinstance(row, dict)]

    async def cleanup_stale(self, timeout_seconds: int = 300) -> int:
        """Cleanup stale contexts and return count of deleted."""
        threshold = datetime.utcnow() - timedelta(seconds=timeout_seconds)
        results = await self.query(
            f"SELECT id FROM {self.table_name} WHERE last_activity_at < '{threshold.isoformat()}'"
        )
        if not results:
            return 0

        for row in results:
            if isinstance(row, dict) and "id" in row:
                await self.delete(row["id"])
        return len(results)

    def _entity_to_dict(self, entity: ReadingContext) -> Dict[str, Any]:
        """Convert entity to dict for storage."""
        data = {
            "user_id": entity.user_id,
            "paper_id": entity.paper_id,
            "session_id": entity.session_id,
            "started_at": entity.started_at.isoformat() if entity.started_at else None,
            "last_activity_at": entity.last_activity_at.isoformat() if entity.last_activity_at else None,
            "reading_progress": entity.reading_progress,
        }
        if entity.current_position:
            data["current_position"] = {
                "paper_id": entity.current_position.paper_id,
                "page_number": entity.current_position.page_number,
                "bbox": entity.current_position.bbox,
                "text_snippet": entity.current_position.text_snippet,
            }
        return data

    def _dict_to_entity(self, data: Dict[str, Any]) -> ReadingContext:
        """Convert dict from storage to entity."""
        pos_data = data.get("current_position")
        current_position = None
        if pos_data:
            current_position = ReadingPosition(
                paper_id=pos_data.get("paper_id", ""),
                page_number=pos_data.get("page_number", 0),
                bbox=pos_data.get("bbox"),
                text_snippet=pos_data.get("text_snippet"),
            )

        return ReadingContext(
            id=data.get("id"),
            user_id=data.get("user_id", ""),
            paper_id=data.get("paper_id", ""),
            session_id=data.get("session_id", ""),
            current_position=current_position,
            reading_progress=data.get("reading_progress", 0.0),
        )

    def _get_entity_id(self, entity: ReadingContext) -> Optional[str]:
        return entity.id

    def _set_entity_id(self, entity: ReadingContext, entity_id: Optional[str]) -> None:
        entity.id = entity_id
