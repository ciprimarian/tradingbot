"""
Individual LLM advisor.

Each advisor wraps one LLM provider (Opus, GPT, Grok) and has a distinct
personality/role. Advisors don't make trades — they produce verdicts that
the Council aggregates.

The key insight: each model sees the same market data but is prompted to
focus on different aspects. Opus reasons about risk and regime. GPT
analyzes fundamentals and patterns. Grok reads the room (social, narrative).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from src.fuzzi.common.models import Bar, PortfolioSnapshot, Signal


class AdvisorRole(str, Enum):
    STRATEGIST = "strategist"  # Opus — regime, risk, multi-step reasoning
    ANALYST = "analyst"  # GPT — fundamentals, patterns, quantitative
    SCOUT = "scout"  # Grok — social sentiment, narrative, contrarian


class Stance(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    LEAN_BUY = "lean_buy"
    HOLD = "hold"
    LEAN_SELL = "lean_sell"
    SELL = "sell"
    STRONG_SELL = "strong_sell"
    ABSTAIN = "abstain"  # advisor doesn't have enough info


STANCE_SCORES = {
    Stance.STRONG_BUY: 1.0,
    Stance.BUY: 0.7,
    Stance.LEAN_BUY: 0.3,
    Stance.HOLD: 0.0,
    Stance.LEAN_SELL: -0.3,
    Stance.SELL: -0.7,
    Stance.STRONG_SELL: -1.0,
    Stance.ABSTAIN: 0.0,
}


@dataclass(slots=True)
class AdvisorVerdict:
    advisor_name: str
    role: AdvisorRole
    symbol: str
    stance: Stance
    confidence: float  # 0-1, how sure the advisor is
    reasoning: str  # short explanation
    flags: list[str] = field(default_factory=list)  # warnings, edge cases
    latency_ms: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_response: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def score(self) -> float:
        """Weighted score: stance direction × confidence. Abstain always 0."""
        if self.stance == Stance.ABSTAIN:
            return 0.0
        return STANCE_SCORES[self.stance] * self.confidence


class Advisor:
    """
    One LLM advisor with a specific role and personality.

    Usage:
        opus = Advisor(
            name="opus",
            role=AdvisorRole.STRATEGIST,
            provider=SomeProvider(),  # anything with a .complete(prompt) method
            weight=0.4,
        )
        verdict = await opus.consult(symbol, bars, portfolio, context)
    """

    def __init__(
        self,
        name: str,
        role: AdvisorRole,
        provider: Any,  # duck-typed: needs async .complete(prompt: str) -> str
        weight: float = 0.33,
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> None:
        self.name = name
        self.role = role
        self.provider = provider
        self.weight = weight
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._track_record: list[bool] = []  # recent correct/incorrect calls

    async def consult(
        self,
        symbol: str,
        bars: list[Bar],
        portfolio: PortfolioSnapshot,
        signals: list[Signal],
        context: str = "",
    ) -> AdvisorVerdict:
        """
        Ask this advisor for its take on a symbol.

        Builds a role-appropriate prompt, calls the LLM, parses the response
        into a structured verdict.
        """
        from src.fuzzi.brain.prompts import PromptKit

        prompt = PromptKit.build(
            role=self.role,
            symbol=symbol,
            bars=bars,
            portfolio=portfolio,
            signals=signals,
            context=context,
        )

        start = time.monotonic()
        try:
            raw = await self.provider.complete(
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            latency_ms = int((time.monotonic() - start) * 1000)
        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            return AdvisorVerdict(
                advisor_name=self.name,
                role=self.role,
                symbol=symbol,
                stance=Stance.ABSTAIN,
                confidence=0.0,
                reasoning=f"provider error: {exc}",
                flags=["provider_error"],
                latency_ms=latency_ms,
            )

        return self._parse_response(raw, symbol, latency_ms)

    def _parse_response(self, raw: str, symbol: str, latency_ms: int) -> AdvisorVerdict:
        """
        Parse LLM response into a verdict.

        Expects JSON with: stance, confidence, reasoning, flags (optional).
        Falls back to ABSTAIN if response is unparseable — never crash on bad output.
        """
        try:
            # Try to extract JSON from response (models sometimes wrap in markdown)
            cleaned = raw.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()

            data = json.loads(cleaned)

            stance_raw = data.get("stance", "abstain").lower().strip()
            try:
                stance = Stance(stance_raw)
            except ValueError:
                stance = Stance.ABSTAIN

            confidence = max(0.0, min(1.0, float(data.get("confidence", 0.5))))
            reasoning = str(data.get("reasoning", "no reasoning provided"))[:500]
            flags = data.get("flags", [])
            if not isinstance(flags, list):
                flags = []

            return AdvisorVerdict(
                advisor_name=self.name,
                role=self.role,
                symbol=symbol,
                stance=stance,
                confidence=confidence,
                reasoning=reasoning,
                flags=[str(f) for f in flags],
                latency_ms=latency_ms,
                raw_response=raw[:2000],
                metadata=data.get("metadata", {}),
            )

        except (json.JSONDecodeError, KeyError, TypeError):
            return AdvisorVerdict(
                advisor_name=self.name,
                role=self.role,
                symbol=symbol,
                stance=Stance.ABSTAIN,
                confidence=0.0,
                reasoning=f"couldn't parse response",
                flags=["parse_error"],
                latency_ms=latency_ms,
                raw_response=raw[:2000],
            )

    def record_outcome(self, was_correct: bool) -> None:
        """Track whether this advisor's last call was right. Feeds adaptive weighting."""
        self._track_record.append(was_correct)
        if len(self._track_record) > 50:
            self._track_record = self._track_record[-50:]

    def reset_track_record(self) -> None:
        """Periodic reset — forces advisor to re-earn trust from scratch."""
        self._track_record = []

    @property
    def hit_rate(self) -> Optional[float]:
        """
        Recent accuracy using exponential weighting.
        Recent outcomes matter more than old ones — a win 2 trades ago
        counts more than a win 20 trades ago. Decay factor 0.9.
        Returns None if no track record yet.
        """
        if not self._track_record:
            return None
        decay = 0.9
        weighted_sum = 0.0
        weight_total = 0.0
        for i, correct in enumerate(reversed(self._track_record)):
            w = decay ** i
            weighted_sum += correct * w
            weight_total += w
        return weighted_sum / weight_total if weight_total > 0 else None

    @property
    def adaptive_weight(self) -> float:
        """
        Weight adjusted by track record, with hard caps to prevent
        any single advisor from dominating or being silenced.

        - Floor: 0.5x base weight (always has a voice)
        - Cap: 1.5x base weight (never takes over)
        - No track record: base weight (must earn trust)
        """
        rate = self.hit_rate
        if rate is None:
            return self.weight
        # 50% accuracy → 0.5x, 75% → 1.0x, 100% → 1.5x
        multiplier = max(0.5, min(1.5, 0.5 + rate))
        return self.weight * multiplier
