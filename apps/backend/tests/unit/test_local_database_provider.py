"""
Tests for local database provider wiring.
"""

import asyncio

from apps.backend.app.routes.v1 import get_dependencies
from apps.backend.infrastructure.db import (
    SQLiteInsightRepository,
    SQLiteMemoryChunkRepository,
    SQLiteReadingContextRepository,
)


def test_default_dependencies_use_sqlite_repositories():
    deps = asyncio.run(get_dependencies())

    assert isinstance(deps["context_repo"], SQLiteReadingContextRepository)
    assert isinstance(deps["memory_repo"], SQLiteMemoryChunkRepository)
    assert isinstance(deps["insight_repo"], SQLiteInsightRepository)
