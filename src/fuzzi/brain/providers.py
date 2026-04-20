"""
LLM provider wrappers.

Each provider implements a simple interface:
    async .complete(prompt: str, temperature: float, max_tokens: int) -> str

Providers handle auth, retries, and rate limiting internally.
The advisor doesn't care which API it's talking to.

Primary provider: OpenClaw gateway (free, uses OAuth tokens).
Fallback providers: direct API calls (paid, for when OpenClaw is down).
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod


class Provider(ABC):
    """Base interface for LLM providers."""

    @abstractmethod
    async def complete(self, prompt: str, temperature: float = 0.3, max_tokens: int = 500) -> str:
        ...


class OpenClawProvider(Provider):
    """
    Route through OpenClaw gateway on Pinnacle.

    OpenClaw exposes an OpenAI-compatible API. We specify which model we want
    and OpenClaw handles auth (OAuth tokens, API keys) internally.

    This is FREE — uses existing OAuth connections (Google Gemini, GitHub Copilot,
    Qwen) without burning paid API credits.

    Models available through OpenClaw:
    - google/gemini-2.5-flash (API key, most reliable)
    - github-copilot models
    - qwen models
    - mistral/codestral-latest
    """

    def __init__(
        self,
        model: str = "google/gemini-2.5-flash",
        gateway_url: str | None = None,
        token: str | None = None,
    ) -> None:
        self.model = model
        self.gateway_url = gateway_url or os.getenv(
            "OPENCLAW_GATEWAY_URL", "http://pinnacle:19211"
        )
        self.token = token or os.getenv("OPENCLAW_GATEWAY_TOKEN", "")

    async def complete(self, prompt: str, temperature: float = 0.3, max_tokens: int = 500) -> str:
        import aiohttp

        url = f"{self.gateway_url}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise ConnectionError(f"OpenClaw returned {resp.status}: {body[:200]}")
                data = await resp.json()
                return data["choices"][0]["message"]["content"]


class AnthropicProvider(Provider):
    """Claude (Opus) via Anthropic API. Paid fallback."""

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
    """GPT via OpenAI API. Paid fallback."""

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
    """Grok via xAI API. Paid fallback."""

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
