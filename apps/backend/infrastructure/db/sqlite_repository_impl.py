"""
SQLite repository implementations for local development.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from apps.backend.app.core.config import get_settings
from apps.backend.domains.insight_hub.core.entities import (
    BubbleInsight,
    InsightContext,
    InsightStatus,
    InsightType,
)
from apps.backend.domains.insight_hub.port.repository import InsightRepository
from apps.backend.domains.memory_hub.core.entities import (
    MemoryChunk,
    MemoryMetadata,
    MemorySource,
)
from apps.backend.domains.memory_hub.port.repository import MemoryChunkRepository
from apps.backend.domains.reading_hub.core.entities import (
    ReadingContext,
    ReadingPosition,
    TriggerType,
    UserAction,
)
from apps.backend.domains.reading_hub.port.repository import ReadingContextRepository


def _utcnow_iso() -> str:
    return datetime.utcnow().isoformat()


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: Optional[str], default: Any) -> Any:
    if not value:
        return default
    return json.loads(value)


def _id(table: str) -> str:
    return f"{table}:{uuid.uuid4().hex}"


def _position_to_dict(position: ReadingPosition) -> Dict[str, Any]:
    return {
        "paper_id": position.paper_id,
        "page_number": position.page_number,
        "bbox": position.bbox,
        "text_snippet": position.text_snippet,
    }


def _position_from_dict(data: Dict[str, Any]) -> ReadingPosition:
    return ReadingPosition(
        paper_id=data.get("paper_id", ""),
        page_number=data.get("page_number", 0),
        bbox=data.get("bbox"),
        text_snippet=data.get("text_snippet"),
    )


def _action_to_dict(action: UserAction) -> Dict[str, Any]:
    return {
        "trigger_type": action.trigger_type.value,
        "reading_position": _position_to_dict(action.reading_position),
        "selected_text": action.selected_text,
        "context_text": action.context_text,
        "duration_seconds": action.duration_seconds,
        "timestamp": action.timestamp.isoformat() if action.timestamp else _utcnow_iso(),
    }


def _action_from_dict(data: Dict[str, Any]) -> UserAction:
    return UserAction(
        trigger_type=TriggerType(data.get("trigger_type", "selection")),
        reading_position=_position_from_dict(data.get("reading_position", {})),
        selected_text=data.get("selected_text"),
        context_text=data.get("context_text"),
        duration_seconds=data.get("duration_seconds"),
        timestamp=_parse_datetime(data.get("timestamp")) or datetime.utcnow(),
    )


class SQLiteStore:
    """Small SQLite store wrapper shared by local repositories."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS reading_contexts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                paper_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                current_position TEXT,
                recent_actions TEXT NOT NULL,
                started_at TEXT NOT NULL,
                last_activity_at TEXT NOT NULL,
                reading_progress REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_reading_contexts_user_activity
                ON reading_contexts(user_id, last_activity_at DESC);
            CREATE INDEX IF NOT EXISTS idx_reading_contexts_session
                ON reading_contexts(session_id);

            CREATE TABLE IF NOT EXISTS memory_chunks (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding TEXT,
                paper_id TEXT NOT NULL,
                paper_title TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                section TEXT,
                chapter TEXT,
                source TEXT NOT NULL,
                access_count INTEGER NOT NULL,
                last_accessed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                related_chunk_ids TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_memory_chunks_user
                ON memory_chunks(user_id);
            CREATE INDEX IF NOT EXISTS idx_memory_chunks_paper
                ON memory_chunks(user_id, paper_id, page_number);

            CREATE TABLE IF NOT EXISTS insights (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                reading_context_id TEXT NOT NULL,
                insight_type TEXT NOT NULL,
                content TEXT NOT NULL,
                confidence REAL NOT NULL,
                context TEXT NOT NULL,
                status TEXT NOT NULL,
                is_ai_generated INTEGER NOT NULL,
                max_display_length INTEGER NOT NULL,
                display_duration_seconds INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                displayed_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_insights_context
                ON insights(reading_context_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_insights_user
                ON insights(user_id, created_at DESC);
            """
        )
        self.conn.commit()


_sqlite_store: Optional[SQLiteStore] = None


def get_sqlite_store() -> SQLiteStore:
    global _sqlite_store
    if _sqlite_store is None:
        _sqlite_store = SQLiteStore(get_settings().sqlite_db_path)
    return _sqlite_store


def close_sqlite_store() -> None:
    """Close the shared SQLite connection, if it was opened."""
    global _sqlite_store
    if _sqlite_store is not None:
        _sqlite_store.conn.close()
        _sqlite_store = None


class SQLiteReadingContextRepository(ReadingContextRepository):
    """SQLite implementation of reading context persistence."""

    def __init__(self, store: Optional[SQLiteStore] = None):
        self.store = store or get_sqlite_store()

    async def save(self, context: ReadingContext) -> None:
        if not context.id:
            context.id = _id("reading_contexts")
        current_position = (
            _json_dumps(_position_to_dict(context.current_position))
            if context.current_position
            else None
        )
        recent_actions = _json_dumps([_action_to_dict(action) for action in context.recent_actions])
        self.store.conn.execute(
            """
            INSERT INTO reading_contexts (
                id, user_id, paper_id, session_id, current_position, recent_actions,
                started_at, last_activity_at, reading_progress
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                user_id=excluded.user_id,
                paper_id=excluded.paper_id,
                session_id=excluded.session_id,
                current_position=excluded.current_position,
                recent_actions=excluded.recent_actions,
                started_at=excluded.started_at,
                last_activity_at=excluded.last_activity_at,
                reading_progress=excluded.reading_progress
            """,
            (
                context.id,
                context.user_id,
                context.paper_id,
                context.session_id,
                current_position,
                recent_actions,
                context.started_at.isoformat(),
                context.last_activity_at.isoformat(),
                context.reading_progress,
            ),
        )
        self.store.conn.commit()

    async def get_by_id(self, context_id: str) -> Optional[ReadingContext]:
        row = self.store.conn.execute(
            "SELECT * FROM reading_contexts WHERE id = ?",
            (context_id,),
        ).fetchone()
        return self._row_to_entity(row) if row else None

    async def get_active_by_user(
        self,
        user_id: str,
        timeout_seconds: int = 300,
    ) -> Optional[ReadingContext]:
        threshold = datetime.utcnow() - timedelta(seconds=timeout_seconds)
        row = self.store.conn.execute(
            """
            SELECT * FROM reading_contexts
            WHERE user_id = ? AND last_activity_at > ?
            ORDER BY last_activity_at DESC
            LIMIT 1
            """,
            (user_id, threshold.isoformat()),
        ).fetchone()
        return self._row_to_entity(row) if row else None

    async def get_by_session(self, session_id: str) -> Optional[ReadingContext]:
        row = self.store.conn.execute(
            "SELECT * FROM reading_contexts WHERE session_id = ? LIMIT 1",
            (session_id,),
        ).fetchone()
        return self._row_to_entity(row) if row else None

    async def list_by_user(
        self,
        user_id: str,
        paper_id: Optional[str] = None,
    ) -> List[ReadingContext]:
        if paper_id:
            rows = self.store.conn.execute(
                """
                SELECT * FROM reading_contexts
                WHERE user_id = ? AND paper_id = ?
                ORDER BY last_activity_at DESC
                """,
                (user_id, paper_id),
            ).fetchall()
        else:
            rows = self.store.conn.execute(
                """
                SELECT * FROM reading_contexts
                WHERE user_id = ?
                ORDER BY last_activity_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [self._row_to_entity(row) for row in rows]

    async def delete(self, context_id: str) -> None:
        self.store.conn.execute("DELETE FROM reading_contexts WHERE id = ?", (context_id,))
        self.store.conn.commit()

    async def cleanup_stale(self, timeout_seconds: int = 300) -> int:
        threshold = datetime.utcnow() - timedelta(seconds=timeout_seconds)
        cursor = self.store.conn.execute(
            "DELETE FROM reading_contexts WHERE last_activity_at < ?",
            (threshold.isoformat(),),
        )
        self.store.conn.commit()
        return cursor.rowcount

    def _row_to_entity(self, row: sqlite3.Row) -> ReadingContext:
        current_position_data = _json_loads(row["current_position"], None)
        context = ReadingContext(
            id=row["id"],
            user_id=row["user_id"],
            paper_id=row["paper_id"],
            session_id=row["session_id"],
            current_position=(
                _position_from_dict(current_position_data) if current_position_data else None
            ),
            started_at=_parse_datetime(row["started_at"]) or datetime.utcnow(),
            last_activity_at=_parse_datetime(row["last_activity_at"]) or datetime.utcnow(),
            reading_progress=row["reading_progress"],
        )
        context.recent_actions = [
            _action_from_dict(action) for action in _json_loads(row["recent_actions"], [])
        ]
        return context


class SQLiteMemoryChunkRepository(MemoryChunkRepository):
    """SQLite implementation of memory chunk persistence."""

    def __init__(self, store: Optional[SQLiteStore] = None):
        self.store = store or get_sqlite_store()

    async def save(self, chunk: MemoryChunk) -> None:
        if not chunk.id:
            chunk.id = _id("memory_chunks")
        self.store.conn.execute(
            """
            INSERT INTO memory_chunks (
                id, user_id, content, embedding, paper_id, paper_title, page_number,
                section, chapter, source, access_count, last_accessed_at,
                created_at, updated_at, related_chunk_ids
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                user_id=excluded.user_id,
                content=excluded.content,
                embedding=excluded.embedding,
                paper_id=excluded.paper_id,
                paper_title=excluded.paper_title,
                page_number=excluded.page_number,
                section=excluded.section,
                chapter=excluded.chapter,
                source=excluded.source,
                access_count=excluded.access_count,
                last_accessed_at=excluded.last_accessed_at,
                created_at=excluded.created_at,
                updated_at=excluded.updated_at,
                related_chunk_ids=excluded.related_chunk_ids
            """,
            (
                chunk.id,
                chunk.user_id,
                chunk.content,
                _json_dumps(chunk.embedding) if chunk.embedding is not None else None,
                chunk.metadata.paper_id,
                chunk.metadata.paper_title,
                chunk.metadata.page_number,
                chunk.metadata.section,
                chunk.metadata.chapter,
                chunk.metadata.source.value,
                chunk.metadata.access_count,
                chunk.metadata.last_accessed_at.isoformat()
                if chunk.metadata.last_accessed_at
                else None,
                chunk.created_at.isoformat(),
                chunk.updated_at.isoformat(),
                _json_dumps(chunk.related_chunk_ids),
            ),
        )
        self.store.conn.commit()

    async def get_by_id(self, chunk_id: str) -> Optional[MemoryChunk]:
        row = self.store.conn.execute(
            "SELECT * FROM memory_chunks WHERE id = ?",
            (chunk_id,),
        ).fetchone()
        return self._row_to_entity(row) if row else None

    async def list_by_user(self, user_id: str) -> List[MemoryChunk]:
        rows = self.store.conn.execute(
            "SELECT * FROM memory_chunks WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return [self._row_to_entity(row) for row in rows]

    async def list_by_paper(self, user_id: str, paper_id: str) -> List[MemoryChunk]:
        rows = self.store.conn.execute(
            """
            SELECT * FROM memory_chunks
            WHERE user_id = ? AND paper_id = ?
            ORDER BY page_number ASC
            """,
            (user_id, paper_id),
        ).fetchall()
        return [self._row_to_entity(row) for row in rows]

    async def search_similar(
        self,
        query_embedding: List[float],
        user_id: str,
        exclude_paper_id: Optional[str] = None,
        limit: int = 5,
        threshold: float = 0.85,
    ) -> List[Tuple[MemoryChunk, float]]:
        chunks = await self.list_by_user(user_id)
        scored: List[Tuple[MemoryChunk, float]] = []
        for chunk in chunks:
            if exclude_paper_id and chunk.metadata.paper_id == exclude_paper_id:
                continue
            if not chunk.embedding:
                continue
            similarity = self._cosine_similarity(query_embedding, chunk.embedding)
            if similarity >= threshold:
                scored.append((chunk, similarity))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:limit]

    async def batch_save(self, chunks: List[MemoryChunk]) -> None:
        for chunk in chunks:
            await self.save(chunk)

    async def delete_by_paper(self, user_id: str, paper_id: str) -> int:
        cursor = self.store.conn.execute(
            "DELETE FROM memory_chunks WHERE user_id = ? AND paper_id = ?",
            (user_id, paper_id),
        )
        self.store.conn.commit()
        return cursor.rowcount

    async def list_distinct_papers(self) -> List[dict]:
        rows = self.store.conn.execute(
            """
            SELECT paper_id, paper_title, MAX(page_number) AS page_count
            FROM memory_chunks
            GROUP BY paper_id, paper_title
            ORDER BY paper_title ASC
            """
        ).fetchall()
        return [
            {
                "paper_id": row["paper_id"],
                "paper_title": row["paper_title"],
                "page_count": row["page_count"],
            }
            for row in rows
        ]

    def _row_to_entity(self, row: sqlite3.Row) -> MemoryChunk:
        metadata = MemoryMetadata(
            paper_id=row["paper_id"],
            paper_title=row["paper_title"],
            page_number=row["page_number"],
            section=row["section"],
            chapter=row["chapter"],
            source=MemorySource(row["source"]),
            access_count=row["access_count"],
            last_accessed_at=_parse_datetime(row["last_accessed_at"]),
        )
        return MemoryChunk(
            id=row["id"],
            user_id=row["user_id"],
            content=row["content"],
            embedding=_json_loads(row["embedding"], None),
            metadata=metadata,
            created_at=_parse_datetime(row["created_at"]) or datetime.utcnow(),
            updated_at=_parse_datetime(row["updated_at"]) or datetime.utcnow(),
            related_chunk_ids=_json_loads(row["related_chunk_ids"], []),
        )

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)


class SQLiteInsightRepository(InsightRepository):
    """SQLite implementation of insight persistence."""

    def __init__(self, store: Optional[SQLiteStore] = None):
        self.store = store or get_sqlite_store()

    async def save(self, insight: BubbleInsight) -> None:
        if not insight.id:
            insight.id = _id("insights")
        self.store.conn.execute(
            """
            INSERT INTO insights (
                id, user_id, reading_context_id, insight_type, content, confidence,
                context, status, is_ai_generated, max_display_length,
                display_duration_seconds, created_at, updated_at, displayed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                user_id=excluded.user_id,
                reading_context_id=excluded.reading_context_id,
                insight_type=excluded.insight_type,
                content=excluded.content,
                confidence=excluded.confidence,
                context=excluded.context,
                status=excluded.status,
                is_ai_generated=excluded.is_ai_generated,
                max_display_length=excluded.max_display_length,
                display_duration_seconds=excluded.display_duration_seconds,
                created_at=excluded.created_at,
                updated_at=excluded.updated_at,
                displayed_at=excluded.displayed_at
            """,
            (
                insight.id,
                insight.user_id,
                insight.reading_context_id,
                insight.insight_type.value,
                insight.content,
                insight.confidence,
                _json_dumps(self._context_to_dict(insight.context)),
                insight.status.value,
                1 if insight.is_ai_generated else 0,
                insight.max_display_length,
                insight.display_duration_seconds,
                insight.created_at.isoformat(),
                insight.updated_at.isoformat(),
                insight.displayed_at.isoformat() if insight.displayed_at else None,
            ),
        )
        self.store.conn.commit()

    async def get_by_id(self, insight_id: str) -> Optional[BubbleInsight]:
        row = self.store.conn.execute(
            "SELECT * FROM insights WHERE id = ?",
            (insight_id,),
        ).fetchone()
        return self._row_to_entity(row) if row else None

    async def list_by_context(self, reading_context_id: str) -> List[BubbleInsight]:
        rows = self.store.conn.execute(
            """
            SELECT * FROM insights
            WHERE reading_context_id = ?
            ORDER BY created_at DESC
            """,
            (reading_context_id,),
        ).fetchall()
        return [self._row_to_entity(row) for row in rows]

    async def list_by_user(
        self,
        user_id: str,
        paper_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[BubbleInsight]:
        if paper_id:
            rows = self.store.conn.execute(
                """
                SELECT * FROM insights
                WHERE user_id = ? AND json_extract(context, '$.paper_id') = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, paper_id, limit),
            ).fetchall()
        else:
            rows = self.store.conn.execute(
                """
                SELECT * FROM insights
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [self._row_to_entity(row) for row in rows]

    async def get_pending_insights(self, reading_context_id: str) -> List[BubbleInsight]:
        rows = self.store.conn.execute(
            """
            SELECT * FROM insights
            WHERE reading_context_id = ? AND status = ?
            ORDER BY created_at DESC
            """,
            (reading_context_id, InsightStatus.GENERATED.value),
        ).fetchall()
        return [self._row_to_entity(row) for row in rows]

    async def delete(self, insight_id: str) -> None:
        self.store.conn.execute("DELETE FROM insights WHERE id = ?", (insight_id,))
        self.store.conn.commit()

    async def cleanup_old(self, older_than_days: int = 7) -> int:
        threshold = datetime.utcnow() - timedelta(days=older_than_days)
        cursor = self.store.conn.execute(
            "DELETE FROM insights WHERE created_at < ?",
            (threshold.isoformat(),),
        )
        self.store.conn.commit()
        return cursor.rowcount

    def _row_to_entity(self, row: sqlite3.Row) -> BubbleInsight:
        context = self._context_from_dict(_json_loads(row["context"], {}))
        return BubbleInsight(
            id=row["id"],
            user_id=row["user_id"],
            reading_context_id=row["reading_context_id"],
            insight_type=InsightType(row["insight_type"]),
            content=row["content"],
            confidence=row["confidence"],
            context=context,
            status=InsightStatus(row["status"]),
            is_ai_generated=bool(row["is_ai_generated"]),
            max_display_length=row["max_display_length"],
            display_duration_seconds=row["display_duration_seconds"],
            created_at=_parse_datetime(row["created_at"]) or datetime.utcnow(),
            updated_at=_parse_datetime(row["updated_at"]) or datetime.utcnow(),
            displayed_at=_parse_datetime(row["displayed_at"]),
        )

    def _context_to_dict(self, context: InsightContext) -> Dict[str, Any]:
        return {
            "trigger_type": context.trigger_type,
            "paper_id": context.paper_id,
            "page_number": context.page_number,
            "selected_text": context.selected_text,
            "context_text": context.context_text,
            "related_memory_ids": context.related_memory_ids,
            "related_paper_titles": context.related_paper_titles,
        }

    def _context_from_dict(self, data: Dict[str, Any]) -> InsightContext:
        return InsightContext(
            trigger_type=data.get("trigger_type", ""),
            paper_id=data.get("paper_id", ""),
            page_number=data.get("page_number", 0),
            selected_text=data.get("selected_text"),
            context_text=data.get("context_text"),
            related_memory_ids=data.get("related_memory_ids", []),
            related_paper_titles=data.get("related_paper_titles", []),
        )
