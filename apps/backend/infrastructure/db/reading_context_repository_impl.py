"""
SurrealDB Implementation of ReadingContextRepository
"""

from typing import List, Optional

import structlog

from apps.backend.domains.reading_hub.core.entities import ReadingContext
from apps.backend.domains.reading_hub.port.repository import (
    ReadingContextRepository,
)
from apps.backend.infrastructure.db.connection import get_db

logger = structlog.get_logger(__name__)


class SurrealReadingContextRepository(ReadingContextRepository):
    """SurrealDB implementation of reading context repository"""

    async def save(self, context: ReadingContext) -> None:
        """Save a reading context"""
        db = await get_db()

        data = self._entity_to_dict(context)

        if context.id:
            # Update existing - SurrealDB uses update
            try:
                await db.update("reading_contexts", context.id, data)
            except Exception as e:
                logger.warning("Update failed, trying merge", error=str(e))
                await db.query(
                    f"UPDATE reading_contexts SET * WHERE id = '{context.id}'",
                    data
                )
        else:
            # Create new
            result = await db.create("reading_contexts", data)
            context.id = result[0]["id"]

    async def get_by_id(self, context_id: str) -> Optional[ReadingContext]:
        """Get a reading context by ID"""
        db = await get_db()
        result = await db.select("reading_contexts", context_id)
        if result:
            return self._dict_to_entity(result[0])
        return None

    async def get_active_by_user(
        self, user_id: str, timeout_seconds: int = 300
    ) -> Optional[ReadingContext]:
        """Get active reading context for user"""
        from datetime import datetime, timedelta

        db = await get_db()
        threshold = datetime.utcnow() - timedelta(seconds=timeout_seconds)

        # Use raw query for better control
        try:
            result = await db.query(
                f"""
                SELECT * FROM reading_contexts
                WHERE user_id = $user_id
                AND last_activity_at > $threshold
                ORDER BY last_activity_at DESC
                LIMIT 1
                """
            )
            result = await db.query(
                f"""
                SELECT * FROM reading_contexts
                WHERE user_id = '{user_id}'
                AND last_activity_at > '{threshold.isoformat()}'
                ORDER BY last_activity_at DESC
                LIMIT 1
                """
            )
            if result and result[0]:
                return self._dict_to_entity(result[0][0])
        except Exception as e:
            logger.warning("Query failed", error=str(e))

        return None

    async def get_by_session(self, session_id: str) -> Optional[ReadingContext]:
        """Get a reading context by session ID"""
        db = await get_db()
        try:
            result = await db.query(
                f"SELECT * FROM reading_contexts WHERE session_id = '{session_id}' LIMIT 1"
            )
            if result and result[0]:
                return self._dict_to_entity(result[0][0])
        except Exception as e:
            logger.warning("Query failed", error=str(e))
        return None

    async def list_by_user(
        self, user_id: str, paper_id: Optional[str] = None
    ) -> List[ReadingContext]:
        """List reading contexts for user"""
        db = await get_db()

        try:
            if paper_id:
                result = await db.query(
                    f"""
                    SELECT * FROM reading_contexts
                    WHERE user_id = '{user_id}' AND paper_id = '{paper_id}'
                    ORDER BY last_activity_at DESC
                    """
                )
            else:
                result = await db.query(
                    f"""
                    SELECT * FROM reading_contexts
                    WHERE user_id = '{user_id}'
                    ORDER BY last_activity_at DESC
                    """
                )

            if result and result[0]:
                return [self._dict_to_entity(row) for row in result[0]]
        except Exception as e:
            logger.warning("Query failed", error=str(e))

        return []

    async def delete(self, context_id: str) -> None:
        """Delete a reading context"""
        db = await get_db()
        try:
            await db.delete("reading_contexts", context_id)
        except Exception as e:
            logger.warning("Delete failed", error=str(e))

    async def cleanup_stale(self, timeout_seconds: int = 300) -> int:
        """Cleanup stale contexts and return count of deleted"""
        from datetime import datetime, timedelta

        db = await get_db()
        threshold = datetime.utcnow() - timedelta(seconds=timeout_seconds)

        try:
            result = await db.query(
                f"""
                SELECT id FROM reading_contexts
                WHERE last_activity_at < '{threshold.isoformat()}'
                """
            )

            if result and result[0]:
                context_ids = [row["id"] for row in result[0]]
                for context_id in context_ids:
                    await self.delete(context_id)
                return len(context_ids)
        except Exception as e:
            logger.warning("Cleanup failed", error=str(e))

        return 0

    def _entity_to_dict(self, entity: ReadingContext) -> dict:
        """Convert entity to dict for storage"""
        # Simplified conversion
        data = {
            "user_id": entity.user_id,
            "paper_id": entity.paper_id,
            "session_id": entity.session_id,
            "started_at": entity.started_at.isoformat() if entity.started_at else None,
            "last_activity_at": (
                entity.last_activity_at.isoformat()
                if entity.last_activity_at
                else None
            ),
            "reading_progress": entity.reading_progress,
        }
        if entity.id:
            data["id"] = entity.id
        if entity.current_position:
            data["current_position"] = {
                "paper_id": entity.current_position.paper_id,
                "page_number": entity.current_position.page_number,
                "bbox": entity.current_position.bbox,
                "text_snippet": entity.current_position.text_snippet,
            }
        return data

    def _dict_to_entity(self, data: dict) -> ReadingContext:
        """Convert dict from storage to entity"""
        from apps.backend.domains.reading_hub.core.entities import ReadingPosition

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
