from __future__ import annotations

from src.fuzzi.common.models import Bar, Signal
from src.fuzzi.signals.base import SignalSource


class GapReversionSource(SignalSource):
    """
    Overnight gap mean reversion.

    Logic:
    - Compare today's open to yesterday's close
    - If gap > threshold, generate signal expecting reversion
    - Gap up -> SELL signal
    - Gap down -> BUY signal
    """

    name = "gap_reversion"

    def __init__(self, gap_threshold: float = 0.01, max_confidence: float = 0.85) -> None:
        self.gap_threshold = gap_threshold
        self.max_confidence = max_confidence

    def evaluate(self, symbol: str, bars: list[Bar]) -> Signal | None:
        if len(bars) < 2:
            return None

        yesterday = bars[-2]
        today = bars[-1]
        if yesterday.close <= 0:
            return None

        gap = (today.open - yesterday.close) / yesterday.close
        if abs(gap) < self.gap_threshold:
            return None

        gap_strength = min(abs(gap) / self.gap_threshold, 3.0)
        confidence = min(0.5 + (gap_strength - 1.0) * 0.12, self.max_confidence)
        direction = "sell" if gap > 0 else "buy"
        notes = f"gap at {gap:.2%}, fade the stretch"

        return Signal(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            source=self.name,
            timestamp=today.timestamp,
            score=abs(gap),
            notes=notes,
            metadata={
                "gap": gap,
                "gap_threshold": self.gap_threshold,
                "yesterday_close": yesterday.close,
                "today_open": today.open,
            },
        )

