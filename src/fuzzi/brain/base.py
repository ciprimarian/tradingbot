from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

from src.fuzzi.common.models import Bar, PortfolioSnapshot, Signal


@dataclass(slots=True)
class BrainContext:
    symbol: str
    bars: list[Bar]
    signal: Signal
    nerve: float
    portfolio: PortfolioSnapshot
    sizing_multiplier: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BrainReview:
    approved: bool
    signal: Signal
    reason: str
    source: str
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class Brain(ABC):
    name: str

    @abstractmethod
    def evaluate(self, context: BrainContext) -> BrainReview:
        """Slow-thinking pass over a fast signal."""

