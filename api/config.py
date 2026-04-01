"""AgentForge configuration management via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── LLM Provider Keys ──────────────────────────────────────────────
    groq_api_key: str = ""
    gemini_api_key: str = ""
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434/v1"

    # ── LLM Defaults ──────────────────────────────────────────────────
    default_provider: Literal["groq", "gemini", "openai", "ollama"] = "groq"
    default_model: str = "llama-3.3-70b-versatile"

    # ── Infrastructure ─────────────────────────────────────────────────
    database_url: str = "postgresql://agentforge:agentforge123@localhost:5432/agentforge"
    redis_url: str = "redis://localhost:6379"

    # ── Server ─────────────────────────────────────────────────────────
    environment: Literal["development", "staging", "production"] = "development"
    port: int = 8000
    log_level: str = "INFO"

    # ── Database Pool ──────────────────────────────────────────────────
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10
    db_pool_timeout: float = 30.0

    # ── App Metadata ───────────────────────────────────────────────────
    app_name: str = "AgentForge"
    app_version: str = "0.1.0"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton)."""
    return Settings()
