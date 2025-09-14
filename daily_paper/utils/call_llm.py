import os
import asyncio
import json
import time
import hashlib
import threading
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from openai import OpenAI, AsyncOpenAI


class _ResponseCache:
    """Simple persistent JSONL cache with in-memory index.

    Each line is a JSON object with fields: key, created_at, payload.
    - key: sha256 over normalized inputs
    - created_at: epoch seconds
    - payload: { response_text, usage_info, meta }
    """

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._index: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        try:
            with self.path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        key = obj.get("key")
                        if key:
                            self._index[key] = obj
                    except Exception:
                        continue
        except Exception:
            # If load fails, start with empty index without crashing.
            self._index = {}

    def get(self, key: str, ttl_seconds: Optional[int] = None) -> Optional[Dict[str, Any]]:
        with self._lock:
            obj = self._index.get(key)
            if not obj:
                return None
            created_at = obj.get("created_at", 0)
            if ttl_seconds is not None and created_at:
                if (time.time() - created_at) > ttl_seconds:
                    return None
            return obj.get("payload")

    def set(self, key: str, payload: Dict[str, Any]):
        record = {
            "key": key,
            "created_at": time.time(),
            "payload": payload,
        }
        line = json.dumps(record, ensure_ascii=False)
        with self._lock:
            # Update memory index first
            self._index[key] = record
            # Append to file
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    def compact(self, max_age_seconds: Optional[int] = None):
        """Rewrite file keeping only latest entries, dropping old ones by age if provided."""
        cutoff = None if max_age_seconds is None else time.time() - max_age_seconds
        with self._lock:
            # Keep latest per key, and drop by age
            new_index: Dict[str, Dict[str, Any]] = {}
            for key, rec in self._index.items():
                if cutoff is not None and rec.get("created_at", 0) < cutoff:
                    continue
                new_index[key] = rec
            # Write temp then replace
            tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
            with tmp_path.open("w", encoding="utf-8") as f:
                for rec in new_index.values():
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            tmp_path.replace(self.path)
            self._index = new_index


def _cache_key(base_url: str, model: str, prompt: str, temperature: float) -> str:
    temp = round(float(temperature), 3)
    data = json.dumps({
        "base_url": base_url or "",
        "model": model or "",
        "prompt": prompt,
        "temperature": temp,
    }, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


class LLM:
    """
    LLM 客户端实例封装。

    - 通过构造函数直接实例化
    - 提供同步调用方法
    - 暴露底层 client：instance.llm
    """

    def __init__(
        self,
        llm_base_url: str,
        llm_api_key: str,
        llm_model: str,
        *,
        enable_cache: bool = True,
        cache_path: str = "data/llm_cache.jsonl",
        cache_ttl_seconds: Optional[int] = None,
    ):
        self.base_url = llm_base_url
        self.api_key = llm_api_key
        self.model = llm_model

        # 仅同步 Client
        self.llm: OpenAI = OpenAI(api_key=self.api_key, base_url=self.base_url)
        # Cache
        self._enable_cache = enable_cache
        self._cache_ttl = cache_ttl_seconds
        self._cache = _ResponseCache(cache_path) if enable_cache else None

    # ---- 同步接口 ----
    def chat(self, prompt: str, temperature: float = 0.2, return_usage: bool = False):
        """
        同步调用 LLM（兼容 OpenAI Chat Completions 接口）
        """
        # Try cache first
        if self._enable_cache and self._cache:
            key = _cache_key(self.base_url, self.model, prompt, temperature)
            cached = self._cache.get(key, ttl_seconds=self._cache_ttl)
            if cached is not None:
                resp = cached.get("response_text", "")
                usage = cached.get("usage_info")
                return (resp, usage) if return_usage else resp

        r = self.llm.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )

        response_text = r.choices[0].message.content
        usage_info = {
            "prompt_tokens": r.usage.prompt_tokens if r.usage else 0,
            "completion_tokens": r.usage.completion_tokens if r.usage else 0,
            "total_tokens": r.usage.total_tokens if r.usage else 0,
            "model": self.model,
        }
        # Save to cache
        if self._enable_cache and self._cache:
            key = _cache_key(self.base_url, self.model, prompt, temperature)
            self._cache.set(key, {
                "response_text": response_text,
                "usage_info": usage_info,
            })
        return (response_text, usage_info) if return_usage else response_text

    def chat_with_usage(self, prompt: str, temperature: float = 0.2):
        return self.chat(prompt, temperature=temperature, return_usage=True)

    def clean_cache(self, max_age_seconds: Optional[int] = None):
        """Compact cache file and drop entries older than max_age_seconds."""
        if self._enable_cache and self._cache:
            self._cache.compact(max_age_seconds=max_age_seconds)

class AsyncLLM:
    """
    异步 LLM 客户端实例封装，仅提供 async 接口。
    """

    def __init__(
        self,
        llm_base_url: str,
        llm_api_key: str,
        llm_model: str,
        *,
        enable_cache: bool = True,
        cache_path: str = "data/llm_cache.jsonl",
        cache_ttl_seconds: Optional[int] = None,
    ):
        self.base_url = llm_base_url
        self.api_key = llm_api_key
        self.model = llm_model
        self.async_llm: Optional[AsyncOpenAI] = None
        # Cache (shared path by default with sync cache)
        self._enable_cache = enable_cache
        self._cache_ttl = cache_ttl_seconds
        self._cache = _ResponseCache(cache_path) if enable_cache else None

    def _get_async_client(self) -> AsyncOpenAI:
        if self.async_llm is None:
            self.async_llm = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        return self.async_llm

    async def aclose(self):
        if self.async_llm is not None:
            await self.async_llm.aclose()
            self.async_llm = None

    async def achat(self, prompt: str, temperature: float = 0.2, return_usage: bool = False):
        # Try cache first
        if self._enable_cache and self._cache:
            key = _cache_key(self.base_url, self.model, prompt, temperature)
            cached = self._cache.get(key, ttl_seconds=self._cache_ttl)
            if cached is not None:
                resp = cached.get("response_text", "")
                usage = cached.get("usage_info")
                return (resp, usage) if return_usage else resp

        client = self._get_async_client()
        r = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )

        response_text = r.choices[0].message.content
        usage_info = {
            "prompt_tokens": r.usage.prompt_tokens if r.usage else 0,
            "completion_tokens": r.usage.completion_tokens if r.usage else 0,
            "total_tokens": r.usage.total_tokens if r.usage else 0,
            "model": self.model,
        }
        # Save to cache
        if self._enable_cache and self._cache:
            key = _cache_key(self.base_url, self.model, prompt, temperature)
            self._cache.set(key, {
                "response_text": response_text,
                "usage_info": usage_info,
            })
        return (response_text, usage_info) if return_usage else response_text

    async def achat_with_usage(self, prompt: str, temperature: float = 0.2):
        return await self.achat(prompt, temperature=temperature, return_usage=True)

    def clean_cache(self, max_age_seconds: Optional[int] = None):
        """Compact cache file and drop entries older than max_age_seconds."""
        if self._enable_cache and self._cache:
            self._cache.compact(max_age_seconds=max_age_seconds)


__all__ = [
    "LLM",
    "AsyncLLM",
]


if __name__ == "__main__":
    # 示例：本地快速自测（需先配置环境变量或直接传参创建实例）
    # llm = LLM(os.getenv("LLM_BASE_URL", ""), os.getenv("LLM_API_KEY", ""), os.getenv("LLM_MODEL", ""))
    # print(llm.chat("hello"))
    pass
