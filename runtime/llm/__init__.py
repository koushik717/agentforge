"""LLM provider abstraction layer.

Provides a unified interface for calling multiple LLM providers
(Groq, Gemini, OpenAI, Ollama) with automatic fallback support.
"""

from __future__ import annotations

import abc
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class LLMMessage:
    """A single message in a conversation."""

    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_call_id: str | None = None
    tool_calls: list[dict] | None = None


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    provider: str
    model: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    tool_calls: list[dict] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


@dataclass
class ToolDefinition:
    """Definition of a tool the LLM can call."""

    name: str
    description: str
    parameters: dict[str, Any]


class LLMProvider(abc.ABC):
    """Abstract base class for LLM providers."""

    provider_name: str = "base"

    @abc.abstractmethod
    async def chat(
        self,
        messages: list[LLMMessage],
        model: str,
        *,
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send a chat completion request."""
        ...

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is reachable."""
        ...


class LLMRegistry:
    """Registry of available LLM providers."""

    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}

    def register(self, provider: LLMProvider) -> None:
        """Register a provider."""
        self._providers[provider.provider_name] = provider
        logger.info("llm.provider_registered", provider=provider.provider_name)

    def get(self, name: str) -> LLMProvider:
        """Get a provider by name."""
        if name not in self._providers:
            available = list(self._providers.keys())
            raise ValueError(f"Unknown LLM provider '{name}'. Available: {available}")
        return self._providers[name]

    def list_providers(self) -> list[str]:
        """List all registered provider names."""
        return list(self._providers.keys())

    async def health_check_all(self) -> dict[str, bool]:
        """Check health of all providers."""
        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.health_check()
            except Exception:
                results[name] = False
        return results
