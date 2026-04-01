"""Concrete LLM provider implementations — Groq, Gemini, OpenAI, Ollama."""

from __future__ import annotations

import time
from typing import Any

import structlog

from runtime.llm import LLMMessage, LLMProvider, LLMResponse, ToolDefinition

logger = structlog.get_logger(__name__)


def _messages_to_dicts(messages: list[LLMMessage]) -> list[dict]:
    """Convert LLMMessage list to plain dicts for API calls."""
    result = []
    for m in messages:
        d = {"role": m.role, "content": m.content}
        if m.tool_call_id:
            d["tool_call_id"] = m.tool_call_id
        if m.tool_calls:
            # Convert our simplified format back to OpenAI format
            d["tool_calls"] = [
                {
                    "id": tc.get("id", f"call_{i}"),
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": tc.get("arguments", "{}"),
                    },
                }
                for i, tc in enumerate(m.tool_calls)
            ]
        result.append(d)
    return result


def _tools_to_openai_format(tools: list[ToolDefinition] | None) -> list[dict] | None:
    """Convert ToolDefinition list to OpenAI function-calling format."""
    if not tools:
        return None
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in tools
    ]


def _extract_tool_calls(choice) -> list[dict]:
    """Extract tool calls from an OpenAI-style response choice."""
    tool_calls = []
    msg = choice.message
    if hasattr(msg, "tool_calls") and msg.tool_calls:
        for tc in msg.tool_calls:
            tool_calls.append(
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }
            )
    return tool_calls


# ═══════════════════════════════════════════════════════════════════════════
#  GROQ
# ═══════════════════════════════════════════════════════════════════════════


class GroqProvider(LLMProvider):
    """Groq Cloud provider — blazing-fast inference."""

    provider_name = "groq"

    def __init__(self, api_key: str) -> None:
        from groq import AsyncGroq

        self._client = AsyncGroq(api_key=api_key)

    async def chat(
        self,
        messages: list[LLMMessage],
        model: str,
        *,
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        start = time.perf_counter()

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": _messages_to_dicts(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        openai_tools = _tools_to_openai_format(tools)
        if openai_tools:
            kwargs["tools"] = openai_tools
            kwargs["tool_choice"] = "auto"

        try:
            response = await self._client.chat.completions.create(**kwargs)
        except Exception as e:
            error_str = str(e)
            # Groq sometimes fails tool calling — retry without tools
            if "tool_use_failed" in error_str and openai_tools:
                logger.warning("groq.tool_use_failed_retrying", model=model)
                # Inject tool descriptions into prompt and retry without formal tools
                tool_desc = "\n".join(
                    f"- {t.name}: {t.description}" for t in (tools or [])
                )
                fallback_msgs = list(_messages_to_dicts(messages))
                for msg in fallback_msgs:
                    if msg["role"] == "system":
                        msg["content"] += (
                            f"\n\nYou have access to these tools:\n{tool_desc}\n"
                            "To use a tool, respond ONLY with JSON: "
                            '{"tool": "tool_name", "args": {"key": "value"}}\n'
                            "If you don't need a tool, respond normally."
                        )
                        break
                kwargs.pop("tools", None)
                kwargs.pop("tool_choice", None)
                kwargs["messages"] = fallback_msgs
                response = await self._client.chat.completions.create(**kwargs)
            else:
                raise

        latency = (time.perf_counter() - start) * 1000

        choice = response.choices[0]
        tool_calls = _extract_tool_calls(choice)

        return LLMResponse(
            content=choice.message.content or "",
            provider=self.provider_name,
            model=model,
            tokens_used=response.usage.total_tokens if response.usage else 0,
            latency_ms=round(latency, 2),
            tool_calls=tool_calls,
            raw=response.model_dump() if hasattr(response, "model_dump") else {},
        )

    async def health_check(self) -> bool:
        try:
            resp = await self._client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return bool(resp.choices)
        except Exception:
            return False


# ═══════════════════════════════════════════════════════════════════════════
#  OPENAI
# ═══════════════════════════════════════════════════════════════════════════


class OpenAIProvider(LLMProvider):
    """OpenAI provider (GPT-4o, etc.)."""

    provider_name = "openai"

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        from openai import AsyncOpenAI

        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**kwargs)

    async def chat(
        self,
        messages: list[LLMMessage],
        model: str,
        *,
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        start = time.perf_counter()

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": _messages_to_dicts(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        openai_tools = _tools_to_openai_format(tools)
        if openai_tools:
            kwargs["tools"] = openai_tools
            kwargs["tool_choice"] = "auto"

        response = await self._client.chat.completions.create(**kwargs)
        latency = (time.perf_counter() - start) * 1000

        choice = response.choices[0]
        tool_calls = _extract_tool_calls(choice)

        return LLMResponse(
            content=choice.message.content or "",
            provider=self.provider_name,
            model=model,
            tokens_used=response.usage.total_tokens if response.usage else 0,
            latency_ms=round(latency, 2),
            tool_calls=tool_calls,
            raw=response.model_dump() if hasattr(response, "model_dump") else {},
        )

    async def health_check(self) -> bool:
        try:
            resp = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return bool(resp.choices)
        except Exception:
            return False


# ═══════════════════════════════════════════════════════════════════════════
#  GEMINI (via Google GenAI)
# ═══════════════════════════════════════════════════════════════════════════


class GeminiProvider(LLMProvider):
    """Google Gemini provider."""

    provider_name = "gemini"

    def __init__(self, api_key: str) -> None:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._genai = genai

    async def chat(
        self,
        messages: list[LLMMessage],
        model: str,
        *,
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        import asyncio

        start = time.perf_counter()

        gen_model = self._genai.GenerativeModel(model)

        # Convert messages to Gemini format
        history = []
        prompt = ""
        system_instruction = ""
        for m in messages:
            if m.role == "system":
                system_instruction = m.content
            elif m.role == "user":
                prompt = m.content
                history.append({"role": "user", "parts": [m.content]})
            elif m.role == "assistant":
                history.append({"role": "model", "parts": [m.content]})

        # Use generate_content for simplicity
        full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
        response = await asyncio.to_thread(
            gen_model.generate_content,
            full_prompt,
            generation_config=self._genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        latency = (time.perf_counter() - start) * 1000

        content = ""
        if response.candidates:
            parts = response.candidates[0].content.parts
            content = "".join(p.text for p in parts if hasattr(p, "text"))

        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model=model,
            tokens_used=0,  # Gemini doesn't expose token count the same way
            latency_ms=round(latency, 2),
        )

    async def health_check(self) -> bool:
        try:
            import asyncio

            model = self._genai.GenerativeModel("gemini-2.0-flash")
            resp = await asyncio.to_thread(model.generate_content, "ping")
            return bool(resp.candidates)
        except Exception:
            return False


# ═══════════════════════════════════════════════════════════════════════════
#  OLLAMA (via OpenAI-compatible API)
# ═══════════════════════════════════════════════════════════════════════════


class OllamaProvider(OpenAIProvider):
    """Ollama provider using OpenAI-compatible API."""

    provider_name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434/v1") -> None:
        super().__init__(api_key="ollama", base_url=base_url)

    async def health_check(self) -> bool:
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(self._client.base_url.rstrip("/v1") + "/api/tags", timeout=5.0)
                return resp.status_code == 200
        except Exception:
            return False
