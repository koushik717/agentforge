"""Pydantic models for API request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Health ──────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    """Response schema for the /health endpoint."""

    status: str = "ok"
    version: str = "0.1.0"
    environment: str = "development"
    uptime_seconds: float = 0.0
    db_connected: bool = False
    redis_connected: bool = False


# ── Agents ──────────────────────────────────────────────────────────────────


class AgentCreate(BaseModel):
    """Request body for creating a new agent."""

    name: str = Field(..., min_length=1, max_length=255, examples=["Research Assistant"])
    description: str = Field("", max_length=2000, examples=["An agent that helps with research tasks"])
    system_prompt: str = Field(
        "You are a helpful assistant.",
        max_length=10000,
        examples=["You are a research assistant. Help the user find and summarize information."],
    )
    provider: str = Field("groq", examples=["groq", "gemini", "openai", "ollama"])
    model: str = Field("llama-3.3-70b-versatile", examples=["llama-3.3-70b-versatile"])
    tools: list[str] = Field(default_factory=list, examples=[["web_search", "calculator"]])


class AgentResponse(BaseModel):
    """Response schema for agent data."""

    id: UUID
    name: str
    description: str
    system_prompt: str
    provider: str
    model: str
    tools: list[str]
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    """Response schema for listing agents."""

    agents: list[AgentResponse]
    total: int


# ── Runs ────────────────────────────────────────────────────────────────────


class RunCreate(BaseModel):
    """Request body for creating a new run."""

    agent_id: UUID
    input: str = Field(..., min_length=1, max_length=50000, examples=["What is quantum computing?"])


class RunResponse(BaseModel):
    """Response schema for run data."""

    id: UUID
    agent_id: UUID
    status: str
    input: str
    output: str | None = None
    tokens_used: int = 0
    latency_ms: float = 0.0
    error: str | None = None
    created_at: datetime


class RunListResponse(BaseModel):
    """Response schema for listing runs."""

    runs: list[RunResponse]
    total: int


# ── Generic ─────────────────────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    status_code: int = 500
