"""PostgreSQL database layer using asyncpg connection pooling."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import asyncpg
import structlog

logger = structlog.get_logger(__name__)

# ── SQL Schema ──────────────────────────────────────────────────────────────

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS agents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    system_prompt TEXT NOT NULL DEFAULT 'You are a helpful assistant.',
    provider    VARCHAR(50) NOT NULL DEFAULT 'groq',
    model       VARCHAR(100) NOT NULL DEFAULT 'llama-3.3-70b-versatile',
    tools       JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS runs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id    UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    status      VARCHAR(20) NOT NULL DEFAULT 'pending',
    input       TEXT NOT NULL,
    output      TEXT,
    tokens_used INTEGER DEFAULT 0,
    latency_ms  DOUBLE PRECISION DEFAULT 0,
    error       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_runs_agent_id ON runs(agent_id);
CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at DESC);
"""


class Database:
    """Async PostgreSQL client backed by an asyncpg connection pool."""

    def __init__(self, dsn: str, *, min_size: int = 2, max_size: int = 10, timeout: float = 30.0) -> None:
        self._dsn = dsn
        self._min_size = min_size
        self._max_size = max_size
        self._timeout = timeout
        self._pool: asyncpg.Pool | None = None

    # ── Lifecycle ───────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Create the connection pool and initialize the schema."""
        logger.info("database.connecting", dsn=self._dsn.split("@")[-1])
        self._pool = await asyncpg.create_pool(
            dsn=self._dsn,
            min_size=self._min_size,
            max_size=self._max_size,
            timeout=self._timeout,
        )
        await self.init_schema()
        logger.info("database.connected")

    async def disconnect(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("database.disconnected")

    async def init_schema(self) -> None:
        """Run the CREATE TABLE statements."""
        async with self._pool.acquire() as conn:
            await conn.execute(_SCHEMA_SQL)
        logger.info("database.schema_initialized")

    # ── Query Helpers ───────────────────────────────────────────────────

    async def execute(self, query: str, *args: Any) -> str:
        """Execute a query and return the status string."""
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        """Fetch multiple rows."""
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args: Any) -> asyncpg.Record | None:
        """Fetch a single row."""
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args: Any) -> Any:
        """Fetch a single value."""
        async with self._pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    # ── Health ──────────────────────────────────────────────────────────

    async def ping(self) -> bool:
        """Return True if the database is reachable."""
        try:
            result = await self.fetchval("SELECT 1")
            return result == 1
        except Exception:
            logger.warning("database.ping_failed", exc_info=True)
            return False

    @property
    def is_connected(self) -> bool:
        return self._pool is not None and not self._pool._closed
