"""Redis client layer for caching and pub/sub."""

from __future__ import annotations

from typing import Any

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger(__name__)


class RedisClient:
    """Async Redis client wrapper with convenience methods."""

    def __init__(self, url: str = "redis://localhost:6379") -> None:
        self._url = url
        self._client: aioredis.Redis | None = None

    # ── Lifecycle ───────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Create the Redis connection."""
        logger.info("redis.connecting", url=self._url)
        self._client = aioredis.from_url(
            self._url,
            encoding="utf-8",
            decode_responses=True,
        )
        # Verify connectivity
        await self._client.ping()
        logger.info("redis.connected")

    async def disconnect(self) -> None:
        """Close the Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("redis.disconnected")

    # ── Key-Value Operations ────────────────────────────────────────────

    async def get(self, key: str) -> str | None:
        """Get a value by key."""
        return await self._client.get(key)

    async def set(self, key: str, value: str, *, ttl: int | None = None) -> None:
        """Set a key-value pair with optional TTL in seconds."""
        if ttl:
            await self._client.setex(key, ttl, value)
        else:
            await self._client.set(key, value)

    async def delete(self, key: str) -> int:
        """Delete a key. Returns the number of keys removed."""
        return await self._client.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        return bool(await self._client.exists(key))

    # ── JSON helpers (store dicts as JSON strings) ──────────────────────

    async def set_json(self, key: str, data: dict, *, ttl: int | None = None) -> None:
        """Serialize a dict to JSON and store it."""
        import json
        await self.set(key, json.dumps(data), ttl=ttl)

    async def get_json(self, key: str) -> dict | None:
        """Retrieve and deserialize a JSON value."""
        import json
        raw = await self.get(key)
        return json.loads(raw) if raw else None

    # ── Pub/Sub (foundation for agent event streams) ────────────────────

    async def publish(self, channel: str, message: str) -> int:
        """Publish a message to a channel."""
        return await self._client.publish(channel, message)

    # ── Health ──────────────────────────────────────────────────────────

    async def ping(self) -> bool:
        """Return True if Redis is reachable."""
        try:
            return await self._client.ping()
        except Exception:
            logger.warning("redis.ping_failed", exc_info=True)
            return False

    @property
    def is_connected(self) -> bool:
        return self._client is not None
