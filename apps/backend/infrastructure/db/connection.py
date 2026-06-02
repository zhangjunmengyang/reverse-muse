"""
SurrealDB Connection and Initialization

Provides database connection using HTTP REST API (more reliable than WebSocket).
Based on the pattern from llm-paper-reader project.
"""

import asyncio
import base64
import json
from functools import wraps
from typing import Any, Dict, List, Optional

import aiohttp
import structlog

from apps.backend.app.core.config import get_settings

logger = structlog.get_logger(__name__)


def retry_on_failure(max_retries: int = 3, base_delay: float = 0.5):
    """Retry decorator for database operations"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (asyncio.TimeoutError, aiohttp.ClientError, RuntimeError) as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(base_delay * (2 ** attempt))
                    continue
            raise RuntimeError(f"Operation failed after {max_retries} retries: {last_error}")
        return wrapper
    return decorator


class SurrealDB:
    """SurrealDB async client using HTTP REST API"""

    _session_pool: Dict[str, aiohttp.ClientSession] = {}
    _pool_lock = asyncio.Lock()

    def __init__(self, settings: Optional[Any] = None):
        self.settings = settings or get_settings()
        # Convert ws:// to http://
        url = self.settings.surreal_url
        url = url.replace("wss://", "https://").replace("ws://", "http://")
        self._url = url.replace("/rpc", "")
        self._namespace = self.settings.surreal_namespace
        self._database = self.settings.surreal_database
        self._auth: Optional[tuple[str, str]] = (
            self.settings.surreal_user,
            self.settings.surreal_password,
        )

    @classmethod
    async def get_session(cls, url: str) -> aiohttp.ClientSession:
        """Get or create shared HTTP session"""
        async with cls._pool_lock:
            if url not in cls._session_pool or cls._session_pool[url].closed:
                timeout = aiohttp.ClientTimeout(total=120, connect=30)
                connector = aiohttp.TCPConnector(
                    limit=100,
                    limit_per_host=30,
                    ttl_dns_cache=300,
                )
                cls._session_pool[url] = aiohttp.ClientSession(
                    timeout=timeout,
                    connector=connector,
                    auto_decompress=False,  # Disable auto decompression
                )
                logger.info("Created new database session pool", url=url)
            return cls._session_pool[url]

    async def _get_session(self) -> aiohttp.ClientSession:
        return await self.get_session(self._url)

    @classmethod
    async def close_all_sessions(cls):
        """Close all sessions"""
        async with cls._pool_lock:
            for url, session in cls._session_pool.items():
                if not session.closed:
                    await session.close()
                    logger.info("Closed database session pool", url=url)
            cls._session_pool.clear()

    async def close(self):
        """Close this instance's connection (keep pool)"""
        pass

    def _build_url(self, endpoint: str) -> str:
        return f"{self._url}{endpoint}"

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "text/plain",
            "Accept-Encoding": "identity",  # Disable compression to avoid 'br' decoding issues
            "Surreal-NS": self._namespace,
            "Surreal-DB": self._database,
        }
        if self._auth:
            username, password = self._auth
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        sql: Optional[str] = None,
    ) -> Any:
        """Execute SurrealDB request"""
        session = await self._get_session()
        url = self._build_url(endpoint)
        headers = self._build_headers()

        if method == "POST" and sql:
            logger.debug("SurrealDB request", method=method, sql=sql[:100] if sql else None)

            async with session.post(url, data=sql, headers=headers) as response:
                if response.status >= 500:
                    error_text = await response.text()
                    raise RuntimeError(f"HTTP {response.status}: {error_text}")

                try:
                    data = await response.json()
                except (json.JSONDecodeError, aiohttp.ContentTypeError) as e:
                    error_text = await response.text()
                    logger.error(
                        "SurrealDB JSON parse error",
                        error=str(e),
                        response_text=error_text[:500],
                    )
                    raise RuntimeError(f"SurrealDB response parse error: {e}")

                if response.status >= 400:
                    logger.error("SurrealDB error", status=response.status, data=data)
                    raise RuntimeError(f"SurrealDB error: {data}")

                return data

        async with session.get(url, headers=headers) as response:
            if response.status >= 500:
                error_text = await response.text()
                raise RuntimeError(f"HTTP {response.status}: {error_text}")

            try:
                data = await response.json()
            except (json.JSONDecodeError, aiohttp.ContentTypeError) as e:
                error_text = await response.text()
                logger.error(
                    "SurrealDB JSON parse error",
                    error=str(e),
                    response_text=error_text[:500],
                )
                raise RuntimeError(f"SurrealDB response parse error: {e}")

            if response.status >= 400:
                logger.error("SurrealDB error", status=response.status, data=data)
                raise RuntimeError(f"SurrealDB error: {data}")

            return data

    @retry_on_failure(max_retries=3)
    async def execute(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute SurrealQL query"""
        if params:
            let_statements = []
            for key, value in params.items():
                try:
                    json_value = json.dumps(value, ensure_ascii=False, default=str)
                except (TypeError, ValueError) as e:
                    logger.warning(
                        "Failed to serialize parameter, using string representation",
                        key=key,
                        error=str(e)
                    )
                    json_value = json.dumps(str(value))
                let_statements.append(f"LET ${key} = {json_value};")
            sql = "\n".join(let_statements) + "\n" + sql

        result = await self._request("POST", "/sql", sql=sql)

        logger.debug("SurrealDB raw result", result=str(result)[:500] if result else None)

        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and item.get("status") == "ERR":
                    error_msg = item.get("result", "Unknown database error")
                    raise RuntimeError(f"SurrealDB query error: {error_msg}")

            for item in reversed(result):
                if isinstance(item, dict) and "result" in item:
                    res = item["result"]
                    if res is not None:
                        if isinstance(res, list):
                            return res
                        elif isinstance(res, dict):
                            return [res]
                        elif isinstance(res, str):
                            raise RuntimeError(f"SurrealDB unexpected result: {res}")
                        else:
                            return [res]
            return []

        elif isinstance(result, dict) and "result" in result:
            res = result["result"]
            if isinstance(res, str) and result.get("status") == "ERR":
                raise RuntimeError(f"SurrealDB query error: {res}")
            return res if isinstance(res, list) else [res] if res is not None else []

        return result if isinstance(result, list) else []

    async def query(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Alias for execute - compatibility with old code"""
        return await self.execute(sql, params)

    async def query_one(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Execute query and return single result"""
        results = await self.execute(sql, params)
        if not results:
            return None
        first_result = results[0]
        if isinstance(first_result, dict):
            return first_result
        return {"value": first_result}

    async def create(
        self,
        table: str,
        data: Dict[str, Any],
        id_: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create record"""
        sql = f"CREATE {table}:{id_} CONTENT $data" if id_ else f"CREATE {table} CONTENT $data"
        result = await self.execute(sql, {"data": data})
        if result and len(result) > 0:
            return result[0]
        raise RuntimeError("Failed to create record")

    async def update(
        self,
        record_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update record - record_id should be in format 'table:id'"""
        if not isinstance(record_id, str) or ":" not in record_id:
            raise ValueError(f"Invalid record_id format: {record_id}")

        # Direct update using record ID
        sql = f"UPDATE {record_id} MERGE $data"
        result = await self.execute(sql, {"data": data})
        if result and len(result) > 0:
            return result[0]
        raise RuntimeError("Failed to update record")

    async def delete(self, record_id: str) -> bool:
        """Delete record"""
        if not isinstance(record_id, str) or ":" not in record_id:
            raise ValueError(f"Invalid record_id format: {record_id}")

        table, id_part = record_id.split(":", 1)
        sql = "DELETE type::thing($table, $id)"
        await self.execute(sql, {"table": table, "id": id_part})
        return True

    async def select(
        self,
        table: str,
        where: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        order: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query records"""
        sql = f"SELECT * FROM {table}"
        if where:
            sql += f" WHERE {where}"
        if order:
            sql += f" ORDER BY {order}"
        if limit:
            sql += f" LIMIT {int(limit)}"

        return await self.execute(sql, params)

    async def select_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Query single record by ID"""
        if not isinstance(record_id, str) or ":" not in record_id:
            raise ValueError(f"Invalid record_id format: {record_id}")

        table, id_part = record_id.split(":", 1)
        sql = "SELECT * FROM type::thing($table, $id)"
        return await self.query_one(sql, {"table": table, "id": id_part})


# Global database instance
_db: Optional[SurrealDB] = None
_db_init_lock: Optional[asyncio.Lock] = None


def _get_db_lock() -> asyncio.Lock:
    """Get lock lazily to ensure correct event loop"""
    global _db_init_lock
    if _db_init_lock is None:
        _db_init_lock = asyncio.Lock()
    return _db_init_lock


async def get_db() -> SurrealDB:
    """Get database connection singleton"""
    global _db
    if _db is None:
        lock = _get_db_lock()
        async with lock:
            if _db is None:
                settings = get_settings()
                logger.info("Connecting to SurrealDB", url=settings.surreal_url)
                _db = SurrealDB(settings)
                logger.info("SurrealDB client initialized")
    return _db


async def close_db() -> None:
    """Close database connection"""
    global _db
    await SurrealDB.close_all_sessions()
    _db = None
    logger.info("Closed database connection")


async def initialize_schema() -> None:
    """Initialize database schema"""
    db = await get_db()

    logger.info("Initializing database schema")

    # Create tables (SurrealDB creates them automatically)
    # We define schema through type enforcement

    # Reading Contexts - SCHEMALESS allows flexible field types
    try:
        await db.execute(
            """
            DEFINE TABLE IF NOT EXISTS reading_contexts SCHEMALESS;
            DEFINE FIELD IF NOT EXISTS user_id ON reading_contexts TYPE string;
            DEFINE FIELD IF NOT EXISTS paper_id ON reading_contexts TYPE string;
            DEFINE FIELD IF NOT EXISTS session_id ON reading_contexts TYPE string;
            """
        )
        logger.info("Defined reading_contexts table")
    except Exception as e:
        logger.warning("Failed to define reading_contexts table", error=str(e))

    # Memory Chunks - embedding is optional for MVP (SCHEMALESS allows null)
    try:
        await db.execute(
            """
            DEFINE TABLE IF NOT EXISTS memory_chunks SCHEMALESS;
            DEFINE FIELD IF NOT EXISTS user_id ON memory_chunks TYPE string;
            DEFINE FIELD IF NOT EXISTS content ON memory_chunks TYPE string;
            DEFINE FIELD IF NOT EXISTS paper_id ON memory_chunks TYPE string;
            DEFINE FIELD IF NOT EXISTS paper_title ON memory_chunks TYPE string;
            """
        )
        logger.info("Defined memory_chunks table")
    except Exception as e:
        logger.warning("Failed to define memory_chunks table", error=str(e))

    # Insights
    try:
        await db.execute(
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
