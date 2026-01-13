"""
SurrealDB Connection and Initialization

Provides database connection and schema initialization.
"""

import asyncio
from typing import Optional

import structlog
from surrealdb import Surreal

from apps.backend.app.core.config import get_settings

logger = structlog.get_logger(__name__)

# Global database connection
_db: Optional[Surreal] = None


async def get_db() -> Surreal:
    """Get database connection singleton"""
    global _db
    if _db is None:
        settings = get_settings()
        logger.info("Connecting to SurrealDB", url=settings.surreal_url)
        _db = Surreal(settings.surreal_url)
        # For newer surrealdb library, we don't call connect explicitly
        # The connection is established when we use it
        logger.info("SurrealDB connection created (will connect on first use)")
    return _db


async def close_db() -> None:
    """Close database connection"""
    global _db
    if _db is not None:
        try:
            # SurrealDB close is synchronous
            _db.close()
        except Exception as e:
            logger.warning("Error closing database connection", error=str(e))
        _db = None
        logger.info("Closed database connection")


async def initialize_schema() -> None:
    """Initialize database schema"""
    db = await get_db()
    settings = get_settings()

    logger.info("Initializing database schema")

    try:
        # Sign in
        await db.signin(
            {
                "user": settings.surreal_user,
                "pass": settings.surreal_password,
            }
        )
        logger.info("Signed in to SurrealDB")
    except Exception as e:
        logger.warning("Sign-in failed, continuing without auth", error=str(e))

    try:
        # Select namespace and database
        await db.use(settings.surreal_namespace, settings.surreal_database)
        logger.info(f"Selected namespace: {settings.surreal_namespace}, database: {settings.surreal_database}")
    except Exception as e:
        logger.warning("Database selection failed, creating...", error=str(e))
        # Try to create namespace and database
        try:
            await db.query(f"USE NAMESPACE {settings.surreal_namespace}")
        except:
            await db.query(f"CREATE NAMESPACE {settings.surreal_namespace}")

        try:
            await db.use(settings.surreal_namespace, settings.surreal_database)
        except:
            await db.query(f"CREATE DATABASE {settings.surreal_database}")

    # Create tables (SurrealDB creates them automatically)
    # We define schema through type enforcement

    # Reading Contexts
    try:
        await db.query(
            """
            DEFINE TABLE IF NOT EXISTS reading_contexts SCHEMALESS;
            DEFINE FIELD IF NOT EXISTS user_id ON reading_contexts TYPE string;
            DEFINE FIELD IF NOT EXISTS paper_id ON reading_contexts TYPE string;
            DEFINE FIELD IF NOT EXISTS session_id ON reading_contexts TYPE string;
            DEFINE FIELD IF NOT EXISTS started_at ON reading_contexts TYPE datetime;
            DEFINE FIELD IF NOT EXISTS last_activity_at ON reading_contexts TYPE datetime;
            """
        )
        logger.info("Defined reading_contexts table")
    except Exception as e:
        logger.warning("Failed to define reading_contexts table", error=str(e))

    # Memory Chunks
    try:
        await db.query(
            """
            DEFINE TABLE IF NOT EXISTS memory_chunks SCHEMALESS;
            DEFINE FIELD IF NOT EXISTS user_id ON memory_chunks TYPE string;
            DEFINE FIELD IF NOT EXISTS content ON memory_chunks TYPE string;
            DEFINE FIELD IF NOT EXISTS embedding ON memory_chunks TYPE array<float>;
            DEFINE FIELD IF NOT EXISTS paper_id ON memory_chunks TYPE string;
            DEFINE FIELD IF NOT EXISTS paper_title ON memory_chunks TYPE string;
            """
        )
        logger.info("Defined memory_chunks table")
    except Exception as e:
        logger.warning("Failed to define memory_chunks table", error=str(e))

    # Insights
    try:
        await db.query(
            """
            DEFINE TABLE IF NOT EXISTS insights SCHEMALESS;
            DEFINE FIELD IF NOT EXISTS user_id ON insights TYPE string;
            DEFINE FIELD IF NOT EXISTS reading_context_id ON insights TYPE string;
            DEFINE FIELD IF NOT EXISTS insight_type ON insights TYPE string;
            DEFINE FIELD IF NOT EXISTS content ON insights TYPE string;
            DEFINE FIELD IF NOT EXISTS confidence ON insights TYPE float;
            DEFINE FIELD IF NOT EXISTS status ON insights TYPE string;
            """
        )
        logger.info("Defined insights table")
    except Exception as e:
        logger.warning("Failed to define insights table", error=str(e))

    logger.info("Database schema initialized successfully")
