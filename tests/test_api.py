"""Integration tests for AgentForge API."""

from __future__ import annotations

import os
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Set test env vars before importing app
os.environ.setdefault("DATABASE_URL", "postgresql://agentforge:agentforge123@localhost:5432/agentforge")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("ENVIRONMENT", "test")


@pytest_asyncio.fixture
async def client():
    """Create an async test client with full app lifespan."""
    from main import create_app

    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    """Root endpoint returns app info."""
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "AgentForge"
    assert "version" in data


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    """Health endpoint returns 200 with db/redis status."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert "db_connected" in data
    assert "redis_connected" in data
    assert "uptime_seconds" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_create_and_get_agent(client: AsyncClient):
    """Create an agent, then retrieve it."""
    create_resp = await client.post(
        "/api/v1/agents",
        json={
            "name": "Test Agent",
            "description": "A test agent for integration tests",
            "system_prompt": "You are a test assistant.",
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "tools": ["web_search"],
        },
    )
    assert create_resp.status_code == 201
    agent = create_resp.json()
    agent_id = agent["id"]
    assert agent["name"] == "Test Agent"
    assert agent["tools"] == ["web_search"]

    # Get by ID
    get_resp = await client.get(f"/api/v1/agents/{agent_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == agent_id

    # List agents
    list_resp = await client.get("/api/v1/agents")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # Cleanup
    del_resp = await client.delete(f"/api/v1/agents/{agent_id}")
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_create_run(client: AsyncClient):
    """Create an agent, then create a run for it."""
    # Create agent first
    agent_resp = await client.post(
        "/api/v1/agents",
        json={"name": "Runner Agent", "description": "Agent for run tests"},
    )
    assert agent_resp.status_code == 201
    agent_id = agent_resp.json()["id"]

    # Create run
    run_resp = await client.post(
        "/api/v1/runs",
        json={"agent_id": agent_id, "input": "What is 2+2?"},
    )
    assert run_resp.status_code == 201
    run = run_resp.json()
    assert run["status"] == "pending"
    assert run["input"] == "What is 2+2?"
    assert run["agent_id"] == agent_id

    # List runs by agent
    list_resp = await client.get(f"/api/v1/runs?agent_id={agent_id}")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # Cleanup
    await client.delete(f"/api/v1/agents/{agent_id}")


@pytest.mark.asyncio
async def test_agent_not_found(client: AsyncClient):
    """Getting a nonexistent agent returns 404."""
    resp = await client.get("/api/v1/agents/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_metrics(client: AsyncClient):
    """Metrics endpoint returns Prometheus format."""
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "agentforge_http_requests_total" in resp.text
