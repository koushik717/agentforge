"""Background worker that processes agent runs from Redis pub/sub."""

from __future__ import annotations

import asyncio
import json
import signal
import sys
import time

import structlog

from api.config import get_settings
from api.db import Database
from api.db.cache import RedisClient
from observability import configure_logging
from runtime.engine import AgentEngine
from runtime.llm import LLMRegistry
from runtime.llm.providers import GeminiProvider, GroqProvider, OllamaProvider, OpenAIProvider
from tools import ToolRegistry
from tools.calculator import Calculator
from tools.web_search import WebSearchTool

logger = structlog.get_logger(__name__)


class Worker:
    """Consumes run events from Redis and executes agents."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.db: Database | None = None
        self.redis: RedisClient | None = None
        self.engine: AgentEngine | None = None
        self._running = False

    async def start(self) -> None:
        """Initialize connections and start processing."""
        configure_logging(
            log_level=self.settings.log_level,
            json_output=self.settings.environment != "development",
        )
        logger.info("worker.starting")

        # Database
        self.db = Database(
            dsn=self.settings.database_url,
            min_size=1,
            max_size=5,
            timeout=self.settings.db_pool_timeout,
        )
        await self.db.connect()

        # Redis
        self.redis = RedisClient(url=self.settings.redis_url)
        await self.redis.connect()

        # LLM Registry
        llm_registry = LLMRegistry()
        if self.settings.groq_api_key and self.settings.groq_api_key != "your_groq_key_here":
            llm_registry.register(GroqProvider(api_key=self.settings.groq_api_key))
        if self.settings.gemini_api_key and self.settings.gemini_api_key != "your_gemini_key_here":
            llm_registry.register(GeminiProvider(api_key=self.settings.gemini_api_key))
        if self.settings.openai_api_key and self.settings.openai_api_key != "your_openai_key_here":
            llm_registry.register(OpenAIProvider(api_key=self.settings.openai_api_key))
        llm_registry.register(OllamaProvider(base_url=self.settings.ollama_base_url))

        # Tools
        tool_registry = ToolRegistry()
        tool_registry.register(WebSearchTool())
        tool_registry.register(Calculator())

        # Engine
        self.engine = AgentEngine(llm_registry=llm_registry, tool_registry=tool_registry.as_dict())

        # Start consuming
        self._running = True
        logger.info("worker.started", providers=llm_registry.list_providers())
        await self._consume()

    async def _consume(self) -> None:
        """Subscribe to Redis and process run events."""
        import redis.asyncio as aioredis

        client = aioredis.from_url(self.settings.redis_url)
        pubsub = client.pubsub()
        await pubsub.subscribe("agent:runs")

        logger.info("worker.subscribed", channel="agent:runs")

        try:
            while self._running:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "message":
                    data = json.loads(message["data"])
                    run_id = data.get("run_id")
                    agent_id = data.get("agent_id")
                    if run_id and agent_id:
                        asyncio.create_task(self._process_run(run_id, agent_id))
                await asyncio.sleep(0.1)
        finally:
            await pubsub.unsubscribe("agent:runs")
            await client.close()

    async def _process_run(self, run_id: str, agent_id: str) -> None:
        """Process a single agent run."""
        logger.info("worker.processing_run", run_id=run_id, agent_id=agent_id)

        try:
            # Get agent config
            agent = await self.db.fetchrow("SELECT * FROM agents WHERE id = $1", agent_id)
            if not agent:
                logger.error("worker.agent_not_found", agent_id=agent_id)
                return

            # Get run
            run = await self.db.fetchrow("SELECT * FROM runs WHERE id = $1", run_id)
            if not run:
                logger.error("worker.run_not_found", run_id=run_id)
                return

            # Mark as running
            await self.db.execute(
                "UPDATE runs SET status = 'running' WHERE id = $1",
                run_id,
            )

            # Execute
            tools = agent["tools"]
            if isinstance(tools, str):
                tools = json.loads(tools)

            response = await self.engine.execute(
                provider=agent["provider"],
                model=agent["model"],
                system_prompt=agent["system_prompt"],
                user_input=run["input"],
                tool_names=tools,
            )

            # Update run with results
            await self.db.execute(
                """
                UPDATE runs
                SET status = 'completed',
                    output = $2,
                    tokens_used = $3,
                    latency_ms = $4
                WHERE id = $1
                """,
                run_id,
                response.content,
                response.tokens_used,
                response.latency_ms,
            )

            logger.info(
                "worker.run_completed",
                run_id=run_id,
                tokens=response.tokens_used,
                latency_ms=response.latency_ms,
            )

        except Exception as e:
            logger.error("worker.run_failed", run_id=run_id, error=str(e), exc_info=True)
            await self.db.execute(
                "UPDATE runs SET status = 'failed', error = $2 WHERE id = $1",
                run_id,
                str(e),
            )

    async def stop(self) -> None:
        """Graceful shutdown."""
        logger.info("worker.stopping")
        self._running = False
        if self.db:
            await self.db.disconnect()
        if self.redis:
            await self.redis.disconnect()
        logger.info("worker.stopped")


async def run_worker() -> None:
    """Entry point for the worker process."""
    worker = Worker()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(worker.stop()))

    await worker.start()


if __name__ == "__main__":
    asyncio.run(run_worker())
