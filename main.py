"""AgentForge — Distributed AI Agent Runtime.

Entry point for the FastAPI application.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.routing import Route

from api.config import get_settings
from api.db import Database
from api.db.cache import RedisClient
from api.routes import init_routes, router
from observability import configure_logging, RequestLoggingMiddleware
from observability.metrics import MetricsMiddleware, metrics_endpoint
from runtime.engine import AgentEngine
from runtime.llm import LLMRegistry
from runtime.llm.providers import GeminiProvider, GroqProvider, OllamaProvider, OpenAIProvider
from tools import ToolRegistry
from tools.calculator import Calculator
from tools.web_search import WebSearchTool

logger = structlog.get_logger(__name__)

# ── Globals ─────────────────────────────────────────────────────────────────

db: Database | None = None
redis_client: RedisClient | None = None
engine: AgentEngine | None = None
tool_registry: ToolRegistry | None = None
llm_registry: LLMRegistry | None = None


# ── Lifespan ────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect to Postgres + Redis, init LLM + tools.  Shutdown: disconnect."""
    global db, redis_client, engine, tool_registry, llm_registry
    settings = get_settings()

    # Configure structured logging
    configure_logging(
        log_level=settings.log_level,
        json_output=settings.environment != "development",
    )

    logger.info(
        "app.starting",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )

    # Connect to PostgreSQL
    db = Database(
        dsn=settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
        timeout=settings.db_pool_timeout,
    )
    await db.connect()

    # Connect to Redis
    redis_client = RedisClient(url=settings.redis_url)
    await redis_client.connect()

    # Initialize LLM providers
    llm_registry = LLMRegistry()
    if settings.groq_api_key and settings.groq_api_key != "your_groq_key_here":
        llm_registry.register(GroqProvider(api_key=settings.groq_api_key))
    if settings.gemini_api_key and settings.gemini_api_key != "your_gemini_key_here":
        llm_registry.register(GeminiProvider(api_key=settings.gemini_api_key))
    if settings.openai_api_key and settings.openai_api_key != "your_openai_key_here":
        llm_registry.register(OpenAIProvider(api_key=settings.openai_api_key))
    llm_registry.register(OllamaProvider(base_url=settings.ollama_base_url))

    # Initialize tools
    tool_registry = ToolRegistry()
    tool_registry.register(WebSearchTool())
    tool_registry.register(Calculator())

    # Initialize engine
    engine = AgentEngine(llm_registry=llm_registry, tool_registry=tool_registry.as_dict())

    # Inject dependencies into routes
    init_routes(db, redis_client, settings, engine, tool_registry, llm_registry)

    logger.info(
        "app.started",
        port=settings.port,
        providers=llm_registry.list_providers(),
        tools=[t["name"] for t in tool_registry.list_tools()],
    )

    yield  # ── Application runs here ──

    # Shutdown
    logger.info("app.shutting_down")
    await db.disconnect()
    await redis_client.disconnect()
    logger.info("app.stopped")


# ── App Factory ─────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Production-grade distributed AI agent runtime. "
        "Create, manage, and execute AI agents with multi-provider LLM support, "
        "tool integration, and real-time observability.",
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Middleware (order matters: outermost first) ──────────────────────
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # ── Routes ──────────────────────────────────────────────────────────
    app.include_router(router, prefix="/api/v1")

    # Prometheus metrics at root level
    app.routes.append(Route("/metrics", metrics_endpoint, methods=["GET"]))

    # Root redirect to docs
    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app


# ── Entrypoint ──────────────────────────────────────────────────────────────

app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower(),
    )
