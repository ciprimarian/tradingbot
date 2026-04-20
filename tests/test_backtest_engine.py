"""Tests for the Fuzzi backtest engine."""

from datetime import datetime, timezone

import pytest

from src.fuzzi.backtest.engine import BacktestEngine, BacktestResult
from src.fuzzi.common.models import Bar, Signal


def _make_bars(prices: list[float], base_date: int = 1) -> list[Bar]:
    """Create bars from a list of close prices. Open = prev close, high/low derived."""
    bars = []
    for i, price in enumerate(prices):
        prev_close = prices[i - 1] if i > 0 else price
        bars.append(Bar(
            symbol="TEST",
            timestamp=datetime(2026, 1, base_date + i, tzinfo=timezone.utc),
            open=prev_close,
            high=max(price, prev_close) + 0.5,
            low=min(price, prev_close) - 0.5,
            close=price,
            volume=1_000_000.0,
        ))
    return bars


class AlwaysBuySource:
    """Signal source that always says buy. For testing."""
    name = "always_buy"

    def evaluate(self, symbol: str, bars: list[Bar]) -> Signal | None:
        return Signal(
            symbol=symbol,
            direction="buy",
            confidence=0.9,
            source=self.name,
            timestamp=bars[-1].timestamp,
        )


class NeverBuySource:
    """Signal source that never produces signals."""
    name = "never_buy"

    def evaluate(self, symbol: str, bars: list[Bar]) -> None:
        return None


class TestBacktestEngine:
    def test_no_signals_means_no_trades(self):
        prices = [100.0 + i for i in range(30)]
        bars = _make_bars(prices)
        engine = BacktestEngine(initial_capital=10000)

        result = engine.run(bars=bars, source=NeverBuySource(), symbol="TEST")

        assert result.total_trades == 0
        assert result.final_equity == 10000.0

    def test_rising_market_produces_profit(self):
        # Steadily rising prices: 100, 101, 102, ..., 129
        prices = [100.0 + i for i in range(30)]
        bars = _make_bars(prices)
        engine = BacktestEngine(initial_capital=10000, commission_pct=0.0, slippage_pct=0.0)

        result = engine.run(bars=bars, source=AlwaysBuySource(), symbol="TEST", hold_bars=1)

        assert result.total_trades > 0
        assert result.total_return_pct > 0
        assert result.is_profitable

    def test_falling_market_produces_loss(self):
        # Steadily falling prices: 130, 129, ..., 101
        prices = [130.0 - i for i in range(30)]
        bars = _make_bars(prices)
        engine = BacktestEngine(initial_capital=10000, commission_pct=0.0, slippage_pct=0.0)

        result = engine.run(bars=bars, source=AlwaysBuySource(), symbol="TEST", hold_bars=1)

        assert result.total_trades > 0
        assert result.total_return_pct < 0

    def test_commission_reduces_returns(self):
        prices = [100.0 + i * 0.5 for i in range(30)]
        bars = _make_bars(prices)

        no_cost = BacktestEngine(initial_capital=10000, commission_pct=0.0, slippage_pct=0.0)
        with_cost = BacktestEngine(initial_capital=10000, commission_pct=0.002, slippage_pct=0.001)

        result_free = no_cost.run(bars=bars, source=AlwaysBuySource(), symbol="TEST")
        result_paid = with_cost.run(bars=bars, source=AlwaysBuySource(), symbol="TEST")

        assert result_free.total_return_pct > result_paid.total_return_pct

    def test_equity_curve_length(self):
        prices = [100.0] * 30
        bars = _make_bars(prices)
        engine = BacktestEngine(initial_capital=10000)

        result = engine.run(bars=bars, source=NeverBuySource(), symbol="TEST")

        # Equity curve should have entries for each evaluated bar + initial + final
        assert len(result.equity_curve) > 1

    def test_too_few_bars_returns_empty(self):
        bars = _make_bars([100.0, 101.0])
        engine = BacktestEngine()

        result = engine.run(bars=bars, source=AlwaysBuySource(), symbol="TEST", lookback=20)

        assert result.total_trades == 0

    def test_summary_string(self):
        prices = [100.0 + i for i in range(30)]
        bars = _make_bars(prices)
        engine = BacktestEngine(initial_capital=10000)

        result = engine.run(bars=bars, source=AlwaysBuySource(), symbol="TEST")

        summary = result.summary()
        assert "trades=" in summary
        assert "return=" in summary
        assert "sharpe=" in summary

    def test_max_drawdown_calculated(self):
        # Up then down: should have measurable drawdown
        prices = [100.0 + i for i in range(15)] + [114.0 - i for i in range(15)]
        bars = _make_bars(prices)
        engine = BacktestEngine(initial_capital=10000, commission_pct=0.0, slippage_pct=0.0)

        result = engine.run(bars=bars, source=AlwaysBuySource(), symbol="TEST")

        assert result.max_drawdown_pct > 0
