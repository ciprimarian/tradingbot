"""
Fuzzi nerve system — adaptive confidence tracker.

The nerve represents Fuzzi's confidence in its own recent performance.
It directly affects position sizing: low nerve → smaller trades.

Why this matters:
- Prevents compounding losses during bad streaks
- Automatically scales up when the system is working
- Acts as an implicit regime detector (if nerve keeps dropping,
  the current strategy probably doesn't fit the current market)

Nerve is tracked per-strategy AND globally:
- Per-strategy nerve: affects whether that specific strategy's signals
  get full sizing or reduced sizing
- Global nerve: if ALL strategies are failing, reduce everything

The nerve uses exponential weighted moving average (EWMA):
- Recent events have more impact than old ones
- Smooth, no sudden jumps from single events
- Naturally decays to neutral over time if nothing happens
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict


class NerveMood(str, Enum):
    """Human-readable nerve state for logs."""
    SPOOKED = "spooked"     # < 0.25 — barely trading
    CAUTIOUS = "cautious"   # 0.25 - 0.4
    STEADY = "steady"       # 0.4 - 0.6
    CONFIDENT = "confident" # 0.6 - 0.8
    BOLD = "bold"           # > 0.8 — full aggression


@dataclass(slots=True)
class NerveState:
    """Snapshot of current nerve for logging/blotter."""
    global_nerve: float
    strategy_nerves: Dict[str, float]
    mood: NerveMood
    sizing_multiplier: float
    updated_at: datetime

    def summary(self) -> str:
        strats = ", ".join(f"{k}={v:.2f}" for k, v in self.strategy_nerves.items())
        return f"nerve={self.global_nerve:.2f} ({self.mood.value}) sizing={self.sizing_multiplier:.2f} [{strats}]"


class NerveTracker:
    """
    Tracks system confidence and outputs position sizing adjustments.

    Usage:
        nerve = NerveTracker()
        nerve.record_win("gap_reversion", pnl=12.50)
        nerve.record_loss("gap_reversion", pnl=-8.00)

        state = nerve.state()
        # state.sizing_multiplier → 0.7 (scale down positions)
    """

    def __init__(
        self,
        initial_nerve: float = 0.5,
        decay: float = 0.85,
        win_boost: float = 0.08,
        loss_penalty: float = 0.12,
        floor: float = 0.1,
        ceiling: float = 1.0,
        neutral_drift: float = 0.002,
    ) -> None:
        """
        Args:
            initial_nerve: Starting confidence level
            decay: EWMA decay factor (lower = faster response to recent events)
            win_boost: How much nerve increases on a win
            loss_penalty: How much nerve decreases on a loss (asymmetric — losses hurt more)
            floor: Minimum nerve (never fully stops trading)
            ceiling: Maximum nerve
            neutral_drift: Slow drift toward 0.5 when nothing happens (prevents stale extremes)
        """
        self._global = initial_nerve
        self._strategies: Dict[str, float] = {}
        self._decay = decay
        self._win_boost = win_boost
        self._loss_penalty = loss_penalty
        self._floor = floor
        self._ceiling = ceiling
        self._neutral_drift = neutral_drift
        self._event_count = 0

    def record_win(self, strategy: str, pnl: float = 0.0) -> None:
        """Record a winning trade. Nerve goes up."""
        # Bigger wins give slightly more boost (but capped)
        magnitude_bonus = min(0.03, abs(pnl) / 1000) if pnl > 0 else 0.0
        boost = self._win_boost + magnitude_bonus

        self._global = self._ewma(self._global, self._global + boost)
        self._strategies[strategy] = self._ewma(
            self._strategies.get(strategy, 0.5),
            self._strategies.get(strategy, 0.5) + boost,
        )
        self._clamp_all()
        self._event_count += 1

    def record_loss(self, strategy: str, pnl: float = 0.0) -> None:
        """Record a losing trade. Nerve drops (harder than it rises)."""
        # Bigger losses penalize more
        magnitude_penalty = min(0.05, abs(pnl) / 500) if pnl < 0 else 0.0
        penalty = self._loss_penalty + magnitude_penalty

        self._global = self._ewma(self._global, self._global - penalty)
        self._strategies[strategy] = self._ewma(
            self._strategies.get(strategy, 0.5),
            self._strategies.get(strategy, 0.5) - penalty,
        )
        self._clamp_all()
        self._event_count += 1

    def record_rejection(self, strategy: str) -> None:
        """Seatbelt rejected a signal. Slight nerve decrease (something's off)."""
        self._global = self._ewma(self._global, self._global - 0.02)
        self._strategies[strategy] = self._ewma(
            self._strategies.get(strategy, 0.5),
            self._strategies.get(strategy, 0.5) - 0.02,
        )
        self._clamp_all()

    def tick_idle(self) -> None:
        """Called each tick when nothing happened. Drift toward neutral."""
        self._global += (0.5 - self._global) * self._neutral_drift
        for strat in self._strategies:
            self._strategies[strat] += (0.5 - self._strategies[strat]) * self._neutral_drift
        self._clamp_all()

    def strategy_nerve(self, strategy: str) -> float:
        """Get nerve for a specific strategy. Defaults to 0.5 if unknown."""
        return self._strategies.get(strategy, 0.5)

    @property
    def sizing_multiplier(self) -> float:
        """
        How much to scale position sizes based on current nerve.

        Mapping:
        - nerve 0.1 → multiplier 0.3 (trade at 30% normal size)
        - nerve 0.3 → multiplier 0.6
        - nerve 0.5 → multiplier 1.0 (normal)
        - nerve 0.7 → multiplier 1.0 (no bonus for being confident)
        - nerve 1.0 → multiplier 1.2 (slight bonus at peak confidence)

        Note: we penalize more than we reward. Being spooked shrinks
        positions significantly, but being confident doesn't inflate them much.
        This is intentional — asymmetric risk management.
        """
        if self._global < 0.5:
            # Below neutral: scale down linearly. 0.1→0.3, 0.5→1.0
            return 0.3 + (self._global - 0.1) * (0.7 / 0.4)
        else:
            # Above neutral: very modest increase. 0.5→1.0, 1.0→1.2
            return 1.0 + (self._global - 0.5) * (0.2 / 0.5)

    @property
    def mood(self) -> NerveMood:
        """Current mood based on global nerve level."""
        if self._global < 0.25:
            return NerveMood.SPOOKED
        elif self._global < 0.4:
            return NerveMood.CAUTIOUS
        elif self._global < 0.6:
            return NerveMood.STEADY
        elif self._global < 0.8:
            return NerveMood.CONFIDENT
        else:
            return NerveMood.BOLD

    def state(self) -> NerveState:
        """Full snapshot for logging."""
        return NerveState(
            global_nerve=round(self._global, 4),
            strategy_nerves={k: round(v, 4) for k, v in self._strategies.items()},
            mood=self.mood,
            sizing_multiplier=round(self.sizing_multiplier, 4),
            updated_at=datetime.now(timezone.utc),
        )

    def _ewma(self, current: float, target: float) -> float:
        """Exponential weighted moving average step."""
        return current * self._decay + target * (1 - self._decay)

    def _clamp_all(self) -> None:
        """Enforce floor/ceiling on all values."""
        self._global = max(self._floor, min(self._ceiling, self._global))
        for strat in self._strategies:
            self._strategies[strat] = max(self._floor, min(self._ceiling, self._strategies[strat]))
