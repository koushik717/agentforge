"""Agent execution engine — orchestrates LLM calls with tool use."""

from __future__ import annotations

import json
import time
from typing import Any, Callable

import structlog

from runtime.llm import LLMMessage, LLMRegistry, LLMResponse, ToolDefinition

logger = structlog.get_logger(__name__)

MAX_TOOL_ITERATIONS = 10


class AgentEngine:
    """Executes agent runs: sends prompts to LLMs, handles tool calls, returns results."""

    def __init__(self, llm_registry: LLMRegistry, tool_registry: dict[str, Any] | None = None) -> None:
        self._llm = llm_registry
        self._tools: dict[str, Any] = tool_registry or {}

    def register_tool(self, name: str, tool: Any) -> None:
        """Register a tool for agent use."""
        self._tools[name] = tool
        logger.info("engine.tool_registered", tool=name)

    def get_tool_definitions(self, tool_names: list[str]) -> list[ToolDefinition]:
        """Get ToolDefinition objects for the requested tools."""
        definitions = []
        for name in tool_names:
            if name in self._tools and hasattr(self._tools[name], "definition"):
                definitions.append(self._tools[name].definition)
        return definitions

    async def execute(
        self,
        *,
        provider: str,
        model: str,
        system_prompt: str,
        user_input: str,
        tool_names: list[str] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Execute an agent with optional tool calling loop.

        1. Send system prompt + user input to LLM
        2. If LLM requests tool calls, execute them and feed results back
        3. Repeat until LLM responds with text (or max iterations)
        4. Return final response
        """
        llm = self._llm.get(provider)
        tool_defs = self.get_tool_definitions(tool_names or [])

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_input),
        ]

        total_tokens = 0
        start_time = time.perf_counter()

        for iteration in range(MAX_TOOL_ITERATIONS):
            logger.info(
                "engine.llm_call",
                provider=provider,
                model=model,
                iteration=iteration,
                message_count=len(messages),
            )

            response = await llm.chat(
                messages=messages,
                model=model,
                tools=tool_defs if tool_defs else None,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            total_tokens += response.tokens_used

            # If no tool calls, check for JSON fallback tool format
            if not response.tool_calls:
                # Check if content is a JSON tool call (fallback from providers that
                # failed formal tool calling)
                parsed_tool = self._parse_json_tool_call(response.content)
                if parsed_tool and tool_defs:
                    tool_name = parsed_tool["tool"]
                    tool_args = parsed_tool.get("args", {})
                    logger.info("engine.json_tool_call", tool=tool_name, args=tool_args)
                    tool_result = await self._execute_tool(tool_name, tool_args)

                    # Feed result back to LLM
                    messages.append(LLMMessage(role="assistant", content=response.content))
                    messages.append(LLMMessage(role="user", content=f"Tool result for {tool_name}:\n{tool_result}\n\nNow provide your final answer based on this information."))
                    total_tokens += response.tokens_used
                    continue

                total_latency = (time.perf_counter() - start_time) * 1000
                response.tokens_used = total_tokens
                response.latency_ms = round(total_latency, 2)
                logger.info(
                    "engine.complete",
                    provider=provider,
                    model=model,
                    iterations=iteration + 1,
                    tokens=total_tokens,
                    latency_ms=response.latency_ms,
                )
                return response

            # Process tool calls
            # Add assistant message with tool calls
            messages.append(LLMMessage(role="assistant", content="", tool_calls=response.tool_calls))

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args_str = tool_call.get("arguments", "{}")

                try:
                    tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                except json.JSONDecodeError:
                    tool_args = {}

                logger.info("engine.tool_call", tool=tool_name, args=tool_args)

                # Execute the tool
                tool_result = await self._execute_tool(tool_name, tool_args)

                # Add tool result as a message
                messages.append(
                    LLMMessage(
                        role="tool",
                        content=str(tool_result),
                        tool_call_id=tool_call.get("id", ""),
                    )
                )

        # Max iterations reached
        total_latency = (time.perf_counter() - start_time) * 1000
        logger.warning("engine.max_iterations_reached", iterations=MAX_TOOL_ITERATIONS)
        return LLMResponse(
            content="I encountered an issue processing your request. Please try again.",
            provider=provider,
            model=model,
            tokens_used=total_tokens,
            latency_ms=round(total_latency, 2),
        )

    def _parse_json_tool_call(self, content: str) -> dict | None:
        """Try to parse a JSON tool call from LLM content.

        Looks for patterns like: {"tool": "web_search", "args": {"query": "..."}}
        """
        if not content:
            return None
        content = content.strip()
        # Try direct JSON parse
        try:
            data = json.loads(content)
            if isinstance(data, dict) and "tool" in data:
                return data
        except json.JSONDecodeError:
            pass
        # Try to extract JSON from markdown code blocks
        import re
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if isinstance(data, dict) and "tool" in data:
                    return data
            except json.JSONDecodeError:
                pass
        return None

    async def _execute_tool(self, tool_name: str, args: dict) -> str:
        """Execute a single tool and return its result as a string."""
        if tool_name not in self._tools:
            return f"Error: Tool '{tool_name}' not found."

        tool = self._tools[tool_name]
        try:
            result = await tool.execute(**args)
            return str(result)
        except Exception as e:
            logger.error("engine.tool_error", tool=tool_name, error=str(e))
            return f"Error executing {tool_name}: {str(e)}"
