"""LLM client manager that supports multiple named profiles."""

from __future__ import annotations

from typing import Dict, Optional

from daily_paper.config import Config, ResolvedLLMProfile
from daily_paper.utils.call_llm import LLM, AsyncLLM


class LLMManager:
    """Lazily instantiate LLM/AsyncLLM clients based on named profiles."""

    def __init__(self, config: Config):
        self._config = config
        self._llms: Dict[str, LLM] = {}
        self._async_llms: Dict[str, AsyncLLM] = {}

    def get_profile(
        self, name: str = "default", *, fallback: str = "default"
    ) -> ResolvedLLMProfile:
        return self._config.get_llm_profile(name=name, fallback=fallback)

    def get_llm(self, name: str = "default", *, fallback: str = "default") -> LLM:
        if name not in self._llms:
            profile = self.get_profile(name=name, fallback=fallback)
            self._llms[name] = self._create_llm(profile)
        return self._llms[name]

    def get_async_llm(
        self, name: str = "default", *, fallback: str = "default"
    ) -> AsyncLLM:
        if name not in self._async_llms:
            profile = self.get_profile(name=name, fallback=fallback)
            self._async_llms[name] = self._create_async_llm(profile)
        return self._async_llms[name]

    def close_async(self) -> None:
        """Close all async LLM clients if they were created."""

        for name, client in list(self._async_llms.items()):
            try:
                # AsyncLLM exposes a coroutine close method, but here we only
                # clean local references – the caller should await aclose.
                client.clean_cache()
            finally:
                self._async_llms.pop(name, None)

    @staticmethod
    def _create_llm(profile: ResolvedLLMProfile) -> LLM:
        return LLM(
            profile.base_url,
            profile.api_key,
            profile.model,
            enable_cache=profile.enable_cache,
            cache_path=profile.cache_path,
            cache_ttl_seconds=profile.cache_ttl_seconds,
        )

    @staticmethod
    def _create_async_llm(profile: ResolvedLLMProfile) -> AsyncLLM:
        return AsyncLLM(
            profile.base_url,
            profile.api_key,
            profile.model,
            enable_cache=profile.enable_cache,
            cache_path=profile.cache_path,
            cache_ttl_seconds=profile.cache_ttl_seconds,
        )


__all__ = ["LLMManager"]
