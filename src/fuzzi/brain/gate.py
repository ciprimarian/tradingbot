"""
Council Gate — simple rule-based approval/rejection layer.

This is the lightweight council that the Pit uses for fast pass/fail decisions.
It runs synchronously (no LLM calls) and checks hard rules like:
- Is nerve too low?
- Is this signal from a strategy that's been failing?
- Is it too close to market close?

The full LLM Council (council.py) is the "slow thinking" layer above this.
The Gate is the "fast reflex" layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

from src.fuzzi.brain.base import BrainContext, BrainReview


@dataclass(slots=True)
class CouncilGateVerdict:
    approved: bool
    reason: str
    created_at: datetime
    source: str = "council_gate"
    metadata: Dict[str, Any] = field(default_factory=dict)


class CouncilGateRule(ABC):
    name: str

    @abstractmethod
    def review(self, context: BrainContext, review: BrainReview) -> CouncilGateVerdict | None:
        """Return a verdict to intervene, or None to abstain."""


class CouncilGate:
    """Fast rule-based gate. Runs all rules, first rejection wins."""

    def __init__(self) -> None:
        self.rules: list[CouncilGateRule] = []

    def register_rule(self, rule: CouncilGateRule) -> None:
        self.rules.append(rule)

    def deliberate(self, context: BrainContext, review: BrainReview) -> CouncilGateVerdict:
        for rule in self.rules:
            verdict = rule.review(context, review)
            if verdict is not None:
                return verdict
        return CouncilGateVerdict(
            approved=review.approved,
            reason="gate stands aside",
            created_at=datetime.now(timezone.utc),
            metadata={"rules_checked": len(self.rules)},
        )
