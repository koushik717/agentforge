"""API route definitions for AgentForge."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query

from api.models import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    ErrorResponse,
    HealthResponse,
    RunCreate,
    RunListResponse,
    RunResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter()

# ── References set by main.py at startup ────────────────────────────────────
_db = None
_redis = None
_start_time: float = time.time()
_settings = None
_engine = None
_tool_registry = None
_llm_registry = None


def init_routes(db, redis, settings, engine=None, tool_registry=None, llm_registry=None) -> None:
    """Inject dependencies into the routes module."""
    global _db, _redis, _settings, _start_time, _engine, _tool_registry, _llm_registry
    _db = db
    _redis = redis
    _settings = settings
    _engine = engine
    _tool_registry = tool_registry
    _llm_registry = llm_registry
    _start_time = time.time()


# ═══════════════════════════════════════════════════════════════════════════
#  HEALTH
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check() -> HealthResponse:
    """Check API, database, and Redis health."""
    db_ok = await _db.ping() if _db else False
    redis_ok = await _redis.ping() if _redis else False

    return HealthResponse(
        status="ok" if (db_ok and redis_ok) else "degraded",
        version=_settings.app_version if _settings else "0.1.0",
        environment=_settings.environment if _settings else "development",
        uptime_seconds=round(time.time() - _start_time, 2),
        db_connected=db_ok,
        redis_connected=redis_ok,
    )


# ═══════════════════════════════════════════════════════════════════════════
#  SYSTEM INFO
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/tools", tags=["system"])
async def list_tools():
    """List all available tools."""
    if _tool_registry:
        return {"tools": _tool_registry.list_tools()}
    return {"tools": []}


@router.get("/providers", tags=["system"])
async def list_providers():
    """List all registered LLM providers."""
    providers = _llm_registry.list_providers() if _llm_registry else []
    return {"providers": providers}


# ═══════════════════════════════════════════════════════════════════════════
#  AGENTS
# ═══════════════════════════════════════════════════════════════════════════


@router.post("/agents", response_model=AgentResponse, status_code=201, tags=["agents"])
async def create_agent(body: AgentCreate) -> AgentResponse:
    """Create a new agent."""
    logger.info("agent.creating", name=body.name, provider=body.provider)

    row = await _db.fetchrow(
        """
        INSERT INTO agents (name, description, system_prompt, provider, model, tools)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb)
        RETURNING *
        """,
        body.name,
        body.description,
        body.system_prompt,
        body.provider,
        body.model,
        json.dumps(body.tools),
    )

    logger.info("agent.created", agent_id=str(row["id"]))
    return _row_to_agent(row)


@router.get("/agents", response_model=AgentListResponse, tags=["agents"])
async def list_agents(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AgentListResponse:
    """List all agents with pagination."""
    rows = await _db.fetch(
        "SELECT * FROM agents ORDER BY created_at DESC LIMIT $1 OFFSET $2",
        limit,
        offset,
    )
    total = await _db.fetchval("SELECT COUNT(*) FROM agents")

    return AgentListResponse(
        agents=[_row_to_agent(r) for r in rows],
        total=total,
    )


@router.get("/agents/{agent_id}", response_model=AgentResponse, tags=["agents"])
async def get_agent(agent_id: UUID) -> AgentResponse:
    """Get a single agent by ID."""
    row = await _db.fetchrow("SELECT * FROM agents WHERE id = $1", agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _row_to_agent(row)


@router.delete("/agents/{agent_id}", status_code=204, tags=["agents"])
async def delete_agent(agent_id: UUID) -> None:
    """Delete an agent and all its runs."""
    result = await _db.execute("DELETE FROM agents WHERE id = $1", agent_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Agent not found")
    logger.info("agent.deleted", agent_id=str(agent_id))


# ═══════════════════════════════════════════════════════════════════════════
#  RUNS
# ═══════════════════════════════════════════════════════════════════════════


@router.post("/runs", response_model=RunResponse, status_code=201, tags=["runs"])
async def create_run(body: RunCreate) -> RunResponse:
    """Create a new agent run (queues for async execution via worker)."""
    # Verify agent exists
    agent = await _db.fetchrow("SELECT id FROM agents WHERE id = $1", body.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    row = await _db.fetchrow(
        """
        INSERT INTO runs (agent_id, status, input)
        VALUES ($1, 'pending', $2)
        RETURNING *
        """,
        body.agent_id,
        body.input,
    )

    # Publish run event to Redis for worker processing
    if _redis:
        await _redis.publish("agent:runs", json.dumps({"run_id": str(row["id"]), "agent_id": str(body.agent_id)}))

    logger.info("run.created", run_id=str(row["id"]), agent_id=str(body.agent_id))
    return _row_to_run(row)


@router.post("/runs/sync", response_model=RunResponse, tags=["runs"])
async def create_run_sync(body: RunCreate) -> RunResponse:
    """Create and immediately execute an agent run (synchronous)."""
    if not _engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    # Verify agent exists
    agent = await _db.fetchrow("SELECT * FROM agents WHERE id = $1", body.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Create run record
    row = await _db.fetchrow(
        """
        INSERT INTO runs (agent_id, status, input)
        VALUES ($1, 'running', $2)
        RETURNING *
        """,
        body.agent_id,
        body.input,
    )
    run_id = str(row["id"])

    try:
        tools = agent["tools"]
        if isinstance(tools, str):
            tools = json.loads(tools)

        response = await _engine.execute(
            provider=agent["provider"],
            model=agent["model"],
            system_prompt=agent["system_prompt"],
            user_input=body.input,
            tool_names=tools,
        )

        # Update with results
        updated = await _db.fetchrow(
            """
            UPDATE runs
            SET status = 'completed', output = $2, tokens_used = $3, latency_ms = $4
            WHERE id = $1
            RETURNING *
            """,
            run_id,
            response.content,
            response.tokens_used,
            response.latency_ms,
        )

        logger.info("run.completed_sync", run_id=run_id, tokens=response.tokens_used)
        return _row_to_run(updated)

    except Exception as e:
        logger.error("run.failed_sync", run_id=run_id, error=str(e))
        updated = await _db.fetchrow(
            "UPDATE runs SET status = 'failed', error = $2 WHERE id = $1 RETURNING *",
            run_id,
            str(e),
        )
        return _row_to_run(updated)


@router.get("/runs", response_model=RunListResponse, tags=["runs"])
async def list_runs(
    agent_id: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> RunListResponse:
    """List runs, optionally filtered by agent_id."""
    if agent_id:
        rows = await _db.fetch(
            "SELECT * FROM runs WHERE agent_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
            agent_id,
            limit,
            offset,
        )
        total = await _db.fetchval("SELECT COUNT(*) FROM runs WHERE agent_id = $1", agent_id)
    else:
        rows = await _db.fetch(
            "SELECT * FROM runs ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            limit,
            offset,
        )
        total = await _db.fetchval("SELECT COUNT(*) FROM runs")

    return RunListResponse(
        runs=[_row_to_run(r) for r in rows],
        total=total,
    )


@router.get("/runs/{run_id}", response_model=RunResponse, tags=["runs"])
async def get_run(run_id: UUID) -> RunResponse:
    """Get a single run by ID."""
    row = await _db.fetchrow("SELECT * FROM runs WHERE id = $1", run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    return _row_to_run(row)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _row_to_agent(row) -> AgentResponse:
    """Convert an asyncpg Record to an AgentResponse."""
    tools = row["tools"]
    if isinstance(tools, str):
        tools = json.loads(tools)
    return AgentResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        system_prompt=row["system_prompt"],
        provider=row["provider"],
        model=row["model"],
        tools=tools,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_run(row) -> RunResponse:
    """Convert an asyncpg Record to a RunResponse."""
    return RunResponse(
        id=row["id"],
        agent_id=row["agent_id"],
        status=row["status"],
        input=row["input"],
        output=row["output"],
        tokens_used=row["tokens_used"] or 0,
        latency_ms=row["latency_ms"] or 0.0,
        error=row["error"],
        created_at=row["created_at"],
    )
