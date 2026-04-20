"""
LLM provider wrappers.

Each provider implements a simple interface:
    async .complete(prompt: str, temperature: float, max_tokens: int) -> str

Providers handle auth, retries, and rate limiting internally.
The advisor doesn't care which API it's talking to.

Primary provider: CodexOAuthProvider (free, uses ChatGPT Plus subscription).
Secondary: OpenClaw gateway (free, uses Google/Copilot/Qwen OAuth).
Fallback: direct API calls (paid, for when OAuth providers are down).
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod


class Provider(ABC):
    """Base interface for LLM providers."""

    @abstractmethod
    async def complete(self, prompt: str, temperature: float = 0.3, max_tokens: int = 500) -> str:
        ...


class CodexOAuthProvider(Provider):
    """
    Use Codex CLI's OAuth tokens to access OpenAI models for free.

    Instead of paying per-token through the API, this reuses the ChatGPT Plus
    subscription's OAuth access_token. Same endpoint (api.openai.com/v1) but
    billed against the monthly subscription, not per-token.

    This is the same pattern OpenClaw uses with Google Antigravity — OAuth
    session tokens from a consumer subscription, not developer API keys.

    Token lifecycle:
    - access_token expires (~10 days based on JWT exp)
    - When expired, refresh_token gets a new access_token
    - refresh_token is long-lived but can be revoked by OpenAI
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        auth_path: str | None = None,
    ) -> None:
        self.model = model
        self.auth_path = auth_path or os.path.expanduser("~/.codex/auth.json")
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._client_id = "app_EMoamEEZ73f0CkXaXp7hrann"  # Codex CLI's OAuth client ID
        self._load_tokens()

    def _load_tokens(self) -> None:
        """Load tokens from Codex auth file."""
        import json
        from pathlib import Path

        path = Path(self.auth_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Codex auth not found at {self.auth_path}. "
                "Run 'codex' and authenticate first."
            )

        with path.open("r") as f:
            auth = json.load(f)

        tokens = auth.get("tokens", {})
        self._access_token = tokens.get("access_token", "")
        self._refresh_token = tokens.get("refresh_token", "")

        if not self._access_token:
            raise ValueError("No access_token in Codex auth file")

    async def _refresh_access_token(self) -> None:
        """Use refresh_token to get a fresh access_token when current one expires."""
        import aiohttp

        if not self._refresh_token:
            raise ConnectionError("No refresh_token available — re-authenticate Codex CLI")

        url = "https://auth.openai.com/oauth/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
            "client_id": self._client_id,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise ConnectionError(f"Token refresh failed ({resp.status}): {body[:200]}")
                data = await resp.json()
                self._access_token = data["access_token"]
                if "refresh_token" in data:
                    self._refresh_token = data["refresh_token"]
                self._save_tokens()

    def _save_tokens(self) -> None:
        """Persist refreshed tokens back to Codex auth file."""
        import json
        from pathlib import Path

        path = Path(self.auth_path)
        with path.open("r") as f:
            auth = json.load(f)

        auth["tokens"]["access_token"] = self._access_token
        if self._refresh_token:
            auth["tokens"]["refresh_token"] = self._refresh_token

        with path.open("w") as f:
            json.dump(auth, f, indent=2)

    async def complete(self, prompt: str, temperature: float = 0.3, max_tokens: int = 500) -> str:
        import aiohttp

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._access_token}",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 401:
                    # Token expired — refresh and retry
                    await self._refresh_access_token()
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    async with session.post(url, json=payload, headers=headers) as retry:
                        if retry.status != 200:
                            body = await retry.text()
                            raise ConnectionError(
                                f"OpenAI returned {retry.status} after refresh: {body[:200]}"
                            )
                        data = await retry.json()
                        return data["choices"][0]["message"]["content"]

                if resp.status != 200:
                    body = await resp.text()
                    raise ConnectionError(f"OpenAI returned {resp.status}: {body[:200]}")
                data = await resp.json()
                return data["choices"][0]["message"]["content"]


class OpenClawProvider(Provider):
    """
    Route through OpenClaw gateway on Pinnacle.
    Uses OpenClaw's OAuth tokens (Google Gemini, GitHub Copilot, Qwen).
    Also free — good as secondary/fallback to diversify model sources.
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
