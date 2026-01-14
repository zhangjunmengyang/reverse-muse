"""
Base Repository Implementation for SurrealDB

Provides common CRUD patterns for all repository implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar

import structlog

from apps.backend.infrastructure.db.connection import get_db

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class BaseSurrealRepository(ABC, Generic[T]):
    """Base class for SurrealDB repository implementations."""

    table_name: str = ""

    async def save(self, entity: T) -> None:
        """Save an entity to the database."""
        db = await get_db()
        data = self._entity_to_dict(entity)
        entity_id = self._get_entity_id(entity)

        try:
            if entity_id:
                await db.update(entity_id, data)
            else:
                result = await db.create(self.table_name, data)
                if result and isinstance(result, dict):
                    self._set_entity_id(entity, result.get("id"))
                logger.debug(f"{self.table_name} entity saved", entity_id=self._get_entity_id(entity))
        except Exception as e:
            logger.error("Save failed", error=str(e), error_type=type(e).__name__)
            raise

    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get an entity by ID."""
        db = await get_db()
        result = await db.select_by_id(entity_id)
        if result:
            return self._dict_to_entity(result)
        return None

    async def delete(self, entity_id: str) -> None:
        """Delete an entity by ID."""
        db = await get_db()
        try:
            await db.delete(entity_id)
        except Exception as e:
            logger.warning("Delete failed", error=str(e))

    async def query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute a raw query and return results."""
        db = await get_db()
        try:
            return await db.query(sql)
        except Exception as e:
            logger.warning("Query failed", error=str(e))
            return []

    @abstractmethod
    def _entity_to_dict(self, entity: T) -> Dict[str, Any]:
        """Convert entity to dictionary for storage."""
        pass

    @abstractmethod
    def _dict_to_entity(self, data: Dict[str, Any]) -> T:
        """Convert dictionary from storage to entity."""
        pass

    @abstractmethod
    def _get_entity_id(self, entity: T) -> Optional[str]:
        """Get the ID from an entity."""
        pass

    @abstractmethod
    def _set_entity_id(self, entity: T, entity_id: Optional[str]) -> None:
        """Set the ID on an entity."""
        pass
