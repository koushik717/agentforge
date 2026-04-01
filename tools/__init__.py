"""Tool system — base class, registry, and built-in tools."""

from __future__ import annotations

import abc
from typing import Any

import structlog

from runtime.llm import ToolDefinition

logger = structlog.get_logger(__name__)


class BaseTool(abc.ABC):
    """Abstract base class for all agent tools."""

    name: str = "base_tool"
    description: str = "A base tool."

    @property
    def definition(self) -> ToolDefinition:
        """Return the OpenAI function-calling schema for this tool."""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters_schema,
        )

    @property
    @abc.abstractmethod
    def parameters_schema(self) -> dict[str, Any]:
        """JSON Schema for the tool's parameters."""
        ...

    @abc.abstractmethod
    async def execute(self, **kwargs) -> str:
        """Execute the tool and return a string result."""
        ...


class ToolRegistry:
    """Central registry for all available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
        logger.info("tools.registered", tool=tool.name)

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, str]]:
        """List all available tools."""
        return [{"name": t.name, "description": t.description} for t in self._tools.values()]

    def as_dict(self) -> dict[str, BaseTool]:
        """Return the internal dict for engine registration."""
        return dict(self._tools)

    def get_definitions(self, names: list[str]) -> list[ToolDefinition]:
        """Get ToolDefinition objects for the requested tool names."""
        return [self._tools[n].definition for n in names if n in self._tools]
