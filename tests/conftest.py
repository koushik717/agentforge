"""Pytest configuration and fixtures for AgentForge tests."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Set test env vars before importing app
os.environ["DATABASE_URL"] = os.environ.get(
    "DATABASE_URL", "postgresql://agentforge:agentforge123@localhost:5433/agentforge"
)
os.environ["REDIS_URL"] = os.environ.get("REDIS_URL", "redis://localhost:6379")
os.environ["ENVIRONMENT"] = "test"
os.environ["GROQ_API_KEY"] = os.environ.get("GROQ_API_KEY", "test_key_not_real")


@pytest_asyncio.fixture
async def client():
    """Create an async test client that properly handles lifespan events."""
    # Clear cached settings so test env vars are picked up
    from api.config import get_settings
    get_settings.cache_clear()

    from main import create_app

    app = create_app()

    # Manually trigger the lifespan context manager
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
