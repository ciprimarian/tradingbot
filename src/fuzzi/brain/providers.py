"""
LLM provider wrappers.

Each provider implements a simple interface:
    async .complete(prompt: str, temperature: float, max_tokens: int) -> str

Providers handle auth, retries, and rate limiting internally.
The advisor doesn't care which API it's talking to.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod


class Provider(ABC):
    """Base interface for LLM providers."""

    @abstractmethod
    async def complete(self, prompt: str, temperature: float = 0.3, max_tokens: int = 500) -> str:
        ...


class AnthropicProvider(Provider):
    """Claude (Opus) via Anthropic API."""

    def __init__(self, api_key: str | None = None, model: str = "claude-opus-4-6") -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model

    async def complete(self, prompt: str, temperature: float = 0.3, max_tokens: int = 500) -> str:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        message = await client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text


class OpenAIProvider(Provider):
    """GPT via OpenAI API."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o") -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model

    async def complete(self, prompt: str, temperature: float = 0.3, max_tokens: int = 500) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key)
        response = await client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""


class GrokProvider(Provider):
    """Grok via xAI API (OpenAI-compatible endpoint)."""

    def __init__(self, api_key: str | None = None, model: str = "grok-3") -> None:
        self.api_key = api_key or os.getenv("XAI_API_KEY", "")
        self.model = model
        self.base_url = "https://api.x.ai/v1"

    async def complete(self, prompt: str, temperature: float = 0.3, max_tokens: int = 500) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        response = await client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""


class MockProvider(Provider):
    """For testing without API calls."""

    def __init__(self, response: str = '{"stance": "hold", "confidence": 0.5, "reasoning": "mock", "flags": []}') -> None:
        self.response = response
        self.call_count = 0
        self.last_prompt: str = ""

    async def complete(self, prompt: str, temperature: float = 0.3, max_tokens: int = 500) -> str:
        self.call_count += 1
        self.last_prompt = prompt
        return self.response
