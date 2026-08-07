"""AgentConfig — runtime configuration for the multi-agent layer (M1a+).

Dual-track LLM backend: default ``mock`` (deterministic tests); ``openai`` /
``anthropic`` reuse the canonicalization backends (openai/anthropic are base
dependencies, so no extra package is required here).
"""

from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel

from ..canonicalization import (
    AnthropicLLMBackend,
    LLMBackend,
    OpenAILLMBackend,
    _MockLLMBackend,
)


class AgentConfig(BaseModel):
    """Runtime configuration shared by identity/task/runtime layers (M1-M4)."""

    llm_backend: Literal["mock", "openai", "anthropic"] = "mock"
    llm_model: str = "gpt-4o-mini"
    production: bool = False
    lease_ttl_seconds: float = 300.0
    queue_size: int = 1000
    scheduler: Literal["asyncio", "apscheduler"] = "asyncio"
    bus_backend: Literal["local", "redis"] = "local"
    redis_url: str | None = None
    state_path: str | None = None
    diversity_offline: bool = True
    diversity_cache_dir: str | None = None

    @classmethod
    def from_env(cls) -> AgentConfig:
        """Build config from ADL_* environment variables.

        Recognized vars: ADL_LLM_BACKEND, ADL_LLM_MODEL, ADL_AGENT_PRODUCTION,
        ADL_BUS_BACKEND, ADL_REDIS_URL, ADL_AGENT_DIVERSITY_OFFLINE.
        """
        return cls(
            llm_backend=os.getenv("ADL_LLM_BACKEND", "mock"),  # type: ignore[arg-type]
            llm_model=os.getenv("ADL_LLM_MODEL", "gpt-4o-mini"),
            production=os.getenv("ADL_AGENT_PRODUCTION", "0") in ("1", "true", "True"),
            bus_backend=os.getenv("ADL_BUS_BACKEND", "local"),  # type: ignore[arg-type]
            redis_url=os.getenv("ADL_REDIS_URL"),
            diversity_offline=os.getenv("ADL_AGENT_DIVERSITY_OFFLINE", "1")
            in ("1", "true", "True"),
        )

    def build_llm(self) -> LLMBackend:
        """Return an LLM backend per ``llm_backend`` (mock by default)."""
        if self.llm_backend == "openai":
            return OpenAILLMBackend(model=self.llm_model)
        if self.llm_backend == "anthropic":
            return AnthropicLLMBackend()
        return _MockLLMBackend()
