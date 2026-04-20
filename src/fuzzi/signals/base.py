from __future__ import annotations

from abc import ABC, abstractmethod

from src.fuzzi.common.models import Bar, Signal


class SignalSource(ABC):
    """Interface for anything that produces trading signals."""

    name: str

    @abstractmethod
    def evaluate(self, symbol: str, bars: list[Bar]) -> Signal | None:
        """Analyze bars and optionally produce a signal."""

