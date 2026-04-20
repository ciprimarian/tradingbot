from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

from src.fuzzi.brain.base import BrainContext, BrainReview


@dataclass(slots=True)
class CouncilVerdict:
    approved: bool
    reason: str
    created_at: datetime
    source: str = "council"
    metadata: Dict[str, Any] = field(default_factory=dict)


class CouncilRule(ABC):
    name: str

    @abstractmethod
    def review(self, context: BrainContext, review: BrainReview) -> CouncilVerdict | None:
        """Return a verdict to intervene, or None to abstain."""


class Council:
    def __init__(self) -> None:
        self.rules: list[CouncilRule] = []

    def register_rule(self, rule: CouncilRule) -> None:
        self.rules.append(rule)

    def deliberate(self, context: BrainContext, review: BrainReview) -> CouncilVerdict:
        for rule in self.rules:
            verdict = rule.review(context, review)
            if verdict is not None:
                return verdict
        return CouncilVerdict(
            approved=review.approved,
            reason="council stands aside",
            created_at=datetime.now(timezone.utc),
            metadata={"rules": len(self.rules)},
        )

