"""
Fuzzi regime detector — reads the tape and names what it sees.

A regime is the market's "mood":
- TRENDING_UP / TRENDING_DOWN — price is walking in one direction
- CHOPPY — price oscillates, no direction dominates
- CALM — low volatility, small moves, little to trade
- VOLATILE — big moves, but no clean direction (panic / confusion)

Why this matters:
Different strategies work in different regimes. Gap reversion wants CHOPPY
or CALM. A momentum breakout wants TRENDING. If Fuzzi knows the regime,
it knows which edges to trust right now — and which to mute.

The detector is pure: given bars in, regime out. No side effects, no state.
That makes it cheap to call every tick and easy to backtest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List

from src.fuzzi.common.models import Bar


class Regime(str, Enum):
    """The named market moods Fuzzi recognizes."""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    CHOPPY = "choppy"
    CALM = "calm"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"  # too few bars to judge


@dataclass(slots=True)
class RegimeSnapshot:
    """What the detector saw and concluded."""
    regime: Regime
    confidence: float           # 0.0 - 1.0, how sure the detector is
    efficiency_ratio: float     # 0.0 - 1.0, trendiness
    volatility: float           # stdev of returns, as fraction of price
    direction: float            # signed pct change over the window (e.g. +0.03 = +3%)
    lookback: int               # how many bars were used
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, float] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"regime={self.regime.value} conf={self.confidence:.2f} "
            f"eff={self.efficiency_ratio:.2f} vol={self.volatility:.4f} "
            f"dir={self.direction:+.3f}"
        )


class RegimeDetector:
    """
    Classifies the market into one of Fuzzi's regimes.

    Two indicators do the heavy lifting:
      1. Efficiency ratio → trendiness (0=pure chop, 1=pure trend)
      2. Return volatility → energy (small=calm, large=volatile)

    The _classify() method combines them with thresholds — that's where
    Fuzzi's personality lives. Tune it to taste.

    Usage:
        detector = RegimeDetector(lookback=20)
        snapshot = detector.observe(bars)
        if snapshot.regime == Regime.CHOPPY:
            # gap reversion likely to work
            ...
    """

    def __init__(
        self,
        lookback: int = 20,
        trend_threshold: float = 0.5,
        calm_vol_threshold: float = 0.005,
        volatile_vol_threshold: float = 0.02,
    ) -> None:
        """
        Args:
            lookback: How many bars to evaluate. 20 ≈ one trading month of daily bars.
            trend_threshold: Efficiency ratio above this = "trending" (0.5 is a reasonable starting point).
            calm_vol_threshold: Return stdev below this = "calm" (0.5% per bar).
            volatile_vol_threshold: Return stdev above this = "volatile" (2% per bar).
        """
        self.lookback = lookback
        self.trend_threshold = trend_threshold
        self.calm_vol_threshold = calm_vol_threshold
        self.volatile_vol_threshold = volatile_vol_threshold

    def observe(self, bars: List[Bar]) -> RegimeSnapshot:
        """Read the tape and produce a regime snapshot."""
        if len(bars) < self.lookback:
            return RegimeSnapshot(
                regime=Regime.UNKNOWN,
                confidence=0.0,
                efficiency_ratio=0.0,
                volatility=0.0,
                direction=0.0,
                lookback=len(bars),
            )

        window = bars[-self.lookback:]
        closes = [b.close for b in window]

        efficiency_ratio = self._efficiency_ratio(closes)
        volatility = self._return_volatility(closes)
        direction = (closes[-1] - closes[0]) / closes[0] if closes[0] else 0.0

        regime, confidence = self._classify(efficiency_ratio, volatility, direction)

        return RegimeSnapshot(
            regime=regime,
            confidence=confidence,
            efficiency_ratio=efficiency_ratio,
            volatility=volatility,
            direction=direction,
            lookback=len(window),
        )

    def _efficiency_ratio(self, closes: List[float]) -> float:
        """
        Kaufman's efficiency ratio: net move / sum of absolute moves.

        1.0 → every tick went in the same direction (pure trend)
        0.0 → every tick got undone by the next (pure chop)
        """
        if len(closes) < 2:
            return 0.0
        net = abs(closes[-1] - closes[0])
        path = sum(abs(closes[i] - closes[i - 1]) for i in range(1, len(closes)))
        if path == 0:
            return 0.0
        return net / path

    def _return_volatility(self, closes: List[float]) -> float:
        """Stdev of bar-to-bar returns, as a fraction of price."""
        if len(closes) < 2:
            return 0.0
        returns = [
            (closes[i] - closes[i - 1]) / closes[i - 1]
            for i in range(1, len(closes))
            if closes[i - 1]
        ]
        if not returns:
            return 0.0
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        return variance ** 0.5

    def _classify(
        self,
        efficiency_ratio: float,
        volatility: float,
        direction: float,
    ) -> tuple[Regime, float]:
        """
        Turn raw indicators into a named regime and a confidence score.

        Inputs:
            efficiency_ratio: 0.0 (pure chop) to 1.0 (pure trend)
            volatility: stdev of returns as a fraction of price (e.g. 0.01 = 1%)
            direction: signed pct change over window (e.g. +0.03 = +3%)

        Returns:
            (Regime, confidence in [0.0, 1.0])

        Consider the edges:
            - trending + low vol  → confident TRENDING_UP/DOWN
            - trending + high vol → still trend but shakier
            - choppy + low vol    → CALM (nothing happening)
            - choppy + high vol   → VOLATILE (panic / confusion)
            - in-between          → CHOPPY as the default neutral label

        Thresholds to work with (self.*):
            - self.trend_threshold         (trendiness cutoff)
            - self.calm_vol_threshold      (below this = calm)
            - self.volatile_vol_threshold  (above this = volatile)
        """
        # TODO(human): implement the classification logic.
        # Return a (Regime, confidence) tuple.
        raise NotImplementedError("regime classification — see TODO(human)")
