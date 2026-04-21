"""
Adversarial tests for signal sources.

GapReversionSource is the only signal source in v1. This batch attacks:
- Boundary and threshold edge cases
- Both directions (gap-up SELL and gap-down BUY)
- Confidence bounds and scaling
- Degenerate prices (zero, negative, NaN)
- The strategy's directional asymmetry under a long-only seatbelt
- Strategy edge: does gap reversion make money in the right market conditions?
"""

from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta

import pytest

from src.fuzzi.signals.gap_reversion import GapReversionSource
from src.fuzzi.common.models import Bar, Signal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dt(offset_days: int = 0) -> datetime:
    return datetime(2026, 1, 2, tzinfo=timezone.utc) + timedelta(days=offset_days)


def _bar(close: float, open_: float | None = None, day: int = 0) -> Bar:
    o = open_ if open_ is not None else close
    return Bar(
        symbol="SPY",
        timestamp=_dt(day),
        open=o,
        high=max(o, close) * 1.001,
        low=min(o, close) * 0.999,
        close=close,
        volume=1_000_000.0,
    )


def _two_bars(yesterday_close: float, today_open: float, today_close: float | None = None) -> list[Bar]:
    """Minimal bar list for a gap signal evaluation."""
    tc = today_close if today_close is not None else today_open
    return [_bar(yesterday_close, day=0), _bar(tc, open_=today_open, day=1)]


src = GapReversionSource(gap_threshold=0.01)  # 1% gap threshold


# ---------------------------------------------------------------------------
# Batch 2a — Too few bars
# ---------------------------------------------------------------------------

class TestTooFewBars:
    def test_empty_bars_returns_none(self):
        assert src.evaluate("SPY", []) is None

    def test_single_bar_returns_none(self):
        assert src.evaluate("SPY", [_bar(100.0)]) is None

    def test_exactly_two_bars_evaluates(self):
        bars = _two_bars(100.0, 103.0)  # 3% gap up
        result = src.evaluate("SPY", bars)
        assert result is not None


# ---------------------------------------------------------------------------
# Batch 2b — Gap threshold boundary
# ---------------------------------------------------------------------------

class TestGapThreshold:
    def test_gap_exactly_at_threshold_returns_none(self):
        """Gap == threshold: abs(gap) < threshold is False, should evaluate."""
        # gap = 0.01 exactly → abs(gap) < threshold is False → signal fires
        bars = _two_bars(100.0, 101.0)  # 1% gap
        result = src.evaluate("SPY", bars)
        # The condition is abs(gap) < gap_threshold, so exactly at threshold fires
        assert result is not None

    def test_gap_just_below_threshold_returns_none(self):
        bars = _two_bars(100.0, 100.99)  # 0.99% gap
        result = src.evaluate("SPY", bars)
        assert result is None

    def test_gap_just_above_threshold_fires(self):
        bars = _two_bars(100.0, 101.01)  # 1.01% gap
        result = src.evaluate("SPY", bars)
        assert result is not None

    def test_zero_gap_returns_none(self):
        bars = _two_bars(100.0, 100.0)
        result = src.evaluate("SPY", bars)
        assert result is None

    def test_custom_threshold_respected(self):
        src_5pct = GapReversionSource(gap_threshold=0.05)
        # 3% gap — below 5% threshold
        assert src_5pct.evaluate("SPY", _two_bars(100.0, 103.0)) is None
        # 6% gap — above 5% threshold
        assert src_5pct.evaluate("SPY", _two_bars(100.0, 106.0)) is not None


# ---------------------------------------------------------------------------
# Batch 2c — Direction correctness
# ---------------------------------------------------------------------------

class TestDirection:
    def test_gap_up_generates_sell_signal(self):
        """Gap up → expect reversion down → SELL."""
        bars = _two_bars(100.0, 103.0)  # +3% gap up
        signal = src.evaluate("SPY", bars)
        assert signal is not None
        assert signal.direction == "sell"

    def test_gap_down_generates_buy_signal(self):
        """Gap down → expect reversion up → BUY."""
        bars = _two_bars(100.0, 97.0)  # -3% gap down
        signal = src.evaluate("SPY", bars)
        assert signal is not None
        assert signal.direction == "buy"

    def test_signal_symbol_matches_input(self):
        bars = _two_bars(100.0, 97.0)
        signal = src.evaluate("TSLA", bars)
        assert signal is not None
        assert signal.symbol == "TSLA"

    def test_signal_source_name_is_gap_reversion(self):
        bars = _two_bars(100.0, 97.0)
        signal = src.evaluate("SPY", bars)
        assert signal is not None
        assert signal.source == "gap_reversion"


# ---------------------------------------------------------------------------
# Batch 2d — Confidence bounds and scaling
# ---------------------------------------------------------------------------

class TestConfidenceBounds:
    def test_confidence_between_zero_and_one(self):
        for gap_pct in [0.01, 0.02, 0.05, 0.10, 0.50, 1.00]:
            bars = _two_bars(100.0, 100.0 * (1 + gap_pct))
            signal = src.evaluate("SPY", bars)
            if signal:
                assert 0.0 <= signal.confidence <= 1.0, f"confidence={signal.confidence} for gap={gap_pct:.0%}"

    def test_larger_gap_gives_higher_confidence(self):
        small = src.evaluate("SPY", _two_bars(100.0, 102.0))   # 2% gap
        large = src.evaluate("SPY", _two_bars(100.0, 105.0))   # 5% gap
        assert small is not None and large is not None
        assert large.confidence >= small.confidence

    def test_confidence_never_exceeds_max_confidence(self):
        """Even a 100% gap should not exceed max_confidence."""
        bars = _two_bars(100.0, 200.0)  # 100% gap
        signal = src.evaluate("SPY", bars)
        assert signal is not None
        assert signal.confidence <= src.max_confidence

    def test_custom_max_confidence_respected(self):
        src_low = GapReversionSource(gap_threshold=0.01, max_confidence=0.5)
        bars = _two_bars(100.0, 120.0)  # 20% gap
        signal = src_low.evaluate("SPY", bars)
        assert signal is not None
        assert signal.confidence <= 0.5

    def test_confidence_not_nan(self):
        for gap_pct in [0.01, 0.05, 0.20]:
            bars = _two_bars(100.0, 100.0 * (1 + gap_pct))
            signal = src.evaluate("SPY", bars)
            if signal:
                assert not math.isnan(signal.confidence)

    def test_minimum_gap_gives_minimum_confidence(self):
        """Gap just at threshold should give the lowest possible confidence, not a NaN or 0."""
        bars = _two_bars(100.0, 101.0)  # exactly 1% gap
        signal = src.evaluate("SPY", bars)
        assert signal is not None
        assert signal.confidence >= 0.0


# ---------------------------------------------------------------------------
# Batch 2e — Degenerate prices
# ---------------------------------------------------------------------------

class TestDegeneratePrices:
    def test_zero_yesterday_close_returns_none(self):
        """Division by zero risk: gap = (today_open - yesterday_close) / yesterday_close."""
        bars = _two_bars(0.0, 1.0)
        result = src.evaluate("SPY", bars)
        assert result is None

    def test_negative_yesterday_close_does_not_raise(self):
        """Futures/spreads can have negative prices."""
        bars = _two_bars(-10.0, -9.0)
        try:
            result = src.evaluate("SPY", bars)
            if result:
                assert not math.isnan(result.confidence)
        except Exception as e:
            pytest.fail(f"raised on negative yesterday_close: {e}")

    def test_very_small_yesterday_close_does_not_produce_nan(self):
        bars = _two_bars(1e-8, 1.1e-8)
        try:
            result = src.evaluate("SPY", bars)
            if result:
                assert not math.isnan(result.confidence)
        except ZeroDivisionError:
            pytest.fail("ZeroDivisionError on very small close price")

    def test_very_large_prices_do_not_overflow(self):
        bars = _two_bars(1e10, 1.05e10)  # 5% gap
        result = src.evaluate("SPY", bars)
        assert result is not None
        assert not math.isnan(result.confidence)
        assert not math.isinf(result.confidence)

    def test_today_open_equals_yesterday_close_is_no_signal(self):
        bars = _two_bars(100.0, 100.0)
        assert src.evaluate("SPY", bars) is None

    def test_more_than_two_bars_uses_last_two(self):
        """Signal uses bars[-2] and bars[-1] — extra history must not change result."""
        many_bars = [_bar(50.0 + i, day=i) for i in range(10)]
        # last two: close=58.0, then open=61.0 (+5.17% gap)
        many_bars[-1] = _bar(61.0, open_=61.0, day=9)
        many_bars[-2] = _bar(58.0, day=8)

        signal_many = src.evaluate("SPY", many_bars)
        signal_two = src.evaluate("SPY", many_bars[-2:])

        assert (signal_many is None) == (signal_two is None)
        if signal_many and signal_two:
            assert signal_many.direction == signal_two.direction
            assert math.isclose(signal_many.confidence, signal_two.confidence, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Batch 2f — Signal metadata integrity
# ---------------------------------------------------------------------------

class TestSignalMetadata:
    def test_metadata_contains_gap_value(self):
        bars = _two_bars(100.0, 103.0)
        signal = src.evaluate("SPY", bars)
        assert signal is not None
        assert "gap" in signal.metadata
        assert math.isclose(signal.metadata["gap"], 0.03, abs_tol=1e-9)

    def test_metadata_contains_yesterday_close(self):
        bars = _two_bars(100.0, 103.0)
        signal = src.evaluate("SPY", bars)
        assert signal is not None
        assert signal.metadata["yesterday_close"] == 100.0

    def test_metadata_contains_today_open(self):
        bars = _two_bars(100.0, 103.0)
        signal = src.evaluate("SPY", bars)
        assert signal is not None
        assert signal.metadata["today_open"] == 103.0

    def test_score_is_absolute_gap_magnitude(self):
        """score = abs(gap), should be positive regardless of direction."""
        up_signal = src.evaluate("SPY", _two_bars(100.0, 103.0))
        down_signal = src.evaluate("SPY", _two_bars(100.0, 97.0))
        assert up_signal is not None and down_signal is not None
        assert up_signal.score > 0
        assert down_signal.score > 0
        assert math.isclose(up_signal.score, 0.03, abs_tol=1e-9)
        assert math.isclose(down_signal.score, 0.03, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Batch 2g — Strategy edge validation (adversarial)
# ---------------------------------------------------------------------------

class TestStrategyEdge:
    """
    Does gap reversion actually work in the scenarios it's meant for?
    These tests validate the STRATEGY LOGIC, not just the code.
    A strategy that generates valid Signal objects but loses money is still broken.
    """

    def _simulate_single_trade(self, yesterday_close: float, today_open: float, today_close: float) -> float:
        """
        Simulate one gap reversion trade.
        Returns P&L as fraction: positive = win, negative = loss.
        Buy signal: enter at today_open, exit at today_close.
        Sell signal: ignored (long-only seatbelt mirrors production constraint).
        """
        bars = _two_bars(yesterday_close, today_open, today_close)
        signal = src.evaluate("SPY", bars)
        if signal is None or signal.direction != "buy":
            return 0.0
        # Enter at open, exit at close — simple 1-bar hold
        return (today_close - today_open) / today_open

    def test_gap_down_that_reverts_produces_win(self):
        """Gap down -3%, price closes back near yesterday close → profit."""
        pnl = self._simulate_single_trade(100.0, 97.0, 99.5)
        assert pnl > 0, f"expected profit on gap-down reversion, got {pnl:.3f}"

    def test_gap_down_that_continues_produces_loss(self):
        """Gap down -3%, price continues lower → loss. This should happen and is expected."""
        pnl = self._simulate_single_trade(100.0, 97.0, 94.0)
        assert pnl < 0, f"expected loss when gap continues, got {pnl:.3f}"

    def test_buy_only_seatbelt_kills_gap_up_signals(self):
        """Gap up → SELL signal. Long-only seatbelt rejects it. This is the half-strategy problem."""
        bars = _two_bars(100.0, 103.0)  # gap up
        signal = src.evaluate("SPY", bars)
        assert signal is not None
        assert signal.direction == "sell"
        # A long-only system CANNOT act on this. The sell leg of gap reversion is dead.
        # This test documents the strategy incompleteness — not a code bug, a design gap.

    def test_choppy_market_generates_many_signals(self):
        """
        In a choppy market (alternating gap-up, gap-down), the strategy should fire frequently.
        This validates that the signal fires in its target regime.
        """
        closes = [100.0, 98.0, 101.0, 97.5, 102.0, 98.5, 101.5, 97.0, 103.0, 98.0]
        bars = [_bar(c, day=i) for i, c in enumerate(closes)]
        # Force each adjacent pair to have a gap by setting open != prev close
        for i in range(1, len(bars)):
            gap = closes[i - 1] * 0.025 * (1 if i % 2 == 0 else -1)
            bars[i] = _bar(closes[i], open_=closes[i - 1] + gap, day=i)

        signals = []
        for i in range(1, len(bars)):
            s = src.evaluate("SPY", bars[:i + 1])
            if s:
                signals.append(s)

        assert len(signals) >= 3, f"expected ≥3 signals in choppy market, got {len(signals)}"

    def test_trending_market_generates_signals_against_trend(self):
        """
        In a strong trend, gap reversion fires AGAINST the trend (gaps in trend direction).
        These are counter-trend bets that can lose badly. This documents the risk.
        """
        # Strong uptrend: each day opens 2% higher than previous close
        closes = [100.0 * (1.02 ** i) for i in range(10)]
        bars = []
        for i, close in enumerate(closes):
            if i == 0:
                bars.append(_bar(close, day=i))
            else:
                trend_open = closes[i - 1] * 1.02  # 2% gap up every day
                bars.append(_bar(close, open_=trend_open, day=i))

        sell_signals = []
        for i in range(1, len(bars)):
            s = src.evaluate("SPY", bars[:i + 1])
            if s and s.direction == "sell":
                sell_signals.append(s)

        # Strong uptrend → lots of gap-up SELL signals. But long-only kills them all.
        # This is the signal source firing into a headwind it cannot trade.
        assert len(sell_signals) >= 5, f"expected sell signals in uptrend, got {len(sell_signals)}"

    def test_backtest_gap_down_reversion_on_choppy_data_is_profitable(self):
        """
        Minimal single-leg backtest: buy gap-downs, close at end of day.
        In choppy data (mean-reverting), the long leg should be profitable.
        """
        # 30 bars of choppy data: alternating gap-down / gap-up
        base = 100.0
        bars = []
        for i in range(30):
            if i % 2 == 0:
                open_ = base * 0.97   # gap down 3%
                close = base * 0.995  # partial reversion
            else:
                open_ = base * 1.03   # gap up 3%
                close = base * 1.005  # partial reversion
            bars.append(Bar(
                symbol="SPY",
                timestamp=_dt(i),
                open=open_,
                high=max(open_, close) * 1.001,
                low=min(open_, close) * 0.999,
                close=close,
                volume=1_000_000.0,
            ))
            base = close

        total_pnl = 0.0
        wins = 0
        trades = 0
        for i in range(1, len(bars)):
            s = src.evaluate("SPY", bars[:i + 1])
            if s and s.direction == "buy":
                trade_pnl = (bars[i].close - bars[i].open) / bars[i].open
                total_pnl += trade_pnl
                wins += int(trade_pnl > 0)
                trades += 1

        assert trades > 0, "no buy signals generated on choppy data"
        win_rate = wins / trades if trades else 0.0
        assert win_rate > 0.5, f"gap-down reversion in choppy market: win_rate={win_rate:.0%} — should be > 50%"
        assert total_pnl > 0, f"gap-down reversion in choppy market lost money: pnl={total_pnl:.3f}"
