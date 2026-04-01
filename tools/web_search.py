"""Web search tool using DuckDuckGo (ddgs)."""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from tools import BaseTool

logger = structlog.get_logger(__name__)


class WebSearchTool(BaseTool):
    """Search the web using DuckDuckGo and return summarized results."""

    name = "web_search"
    description = (
        "Search the web for current information. Use this when the user asks about "
        "recent events, facts you are unsure about, or anything requiring up-to-date data."
    )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up on the web.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 5).",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs) -> str:
        """Execute a web search and return formatted results."""
        query = kwargs.get("query", kwargs.get("key", kwargs.get("search_query", "")))
        max_results = int(kwargs.get("max_results", 5))

        if not query:
            return "Error: No search query provided."

        logger.info("tool.web_search", query=query, max_results=max_results)

        try:
            results = await asyncio.to_thread(self._search, query, max_results)

            if not results:
                return f"No results found for: {query}"

            formatted = []
            for i, r in enumerate(results, 1):
                title = r.get("title", "No title")
                body = r.get("body", r.get("snippet", "No description"))
                href = r.get("href", r.get("link", "Unknown"))
                formatted.append(f"{i}. {title}\n   {body}\n   Source: {href}")

            return f"Search results for '{query}':\n\n" + "\n\n".join(formatted)

        except Exception as e:
            logger.error("tool.web_search_error", error=str(e))
            return f"Search failed: {str(e)}"

    def _search(self, query: str, max_results: int) -> list[dict]:
        """Synchronous search wrapper."""
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
