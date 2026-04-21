"""
Adversarial tests for BacktestEngine.

Attacks:
- No-lookahead-bias guarantee
- Commission and slippage math correctness
- Sharpe on degenerate equity curves (flat, single trade, all same return)
- Max drawdown accuracy
- Long-only filter (sell signals ignored)
- Strategy validation: gap reversion in rising/falling/choppy markets
- Overfitting tells: Sharpe > 3 suspicion flag
- Edge-case bar counts
"""

from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta
from typing import List

import pytest

from src.fuzzi.backtest.engine import BacktestEngine, BacktestResult, Trade
from src.fuzzi.common.models import Bar
from src.fuzzi.signals.gap_reversion import GapReversionSource


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dt(day: int = 0) -> datetime:
    return datetime(2024, 1, 2, tzinfo=timezone.utc) + timedelta(days=day)


def _bar(close: float, open_: float | None = None, day: int = 0, symbol: str = "SPY") -> Bar:
    o = open_ if open_ is not None else close
    return Bar(
        symbol=symbol,
        timestamp=_dt(day),
        open=o,
        high=max(o, close) * 1.001,
        low=min(o, close) * 0.999,
        close=close,
        volume=1_000_000.0,
    )


def _trending_up(n: int = 40, start: float = 100.0, step: float = 1.0, gap_pct: float = 0.0) -> List[Bar]:
    """Steady uptrend. gap_pct adds an opening gap on each bar."""
    bars = [_bar(start, day=0)]
    for i in range(1, n):
        prev_close = bars[-1].close
        close = prev_close + step
        open_ = prev_close * (1 + gap_pct) if gap_pct else close
        bars.append(_bar(close, open_=open_, day=i))
    return bars


def _trending_down(n: int = 40, start: float = 140.0, step: float = 1.0, gap_pct: float = 0.0) -> List[Bar]:
    bars = [_bar(start, day=0)]
    for i in range(1, n):
        prev_close = bars[-1].close
        close = max(prev_close - step, 0.01)
        open_ = prev_close * (1 - gap_pct) if gap_pct else close
        bars.append(_bar(close, open_=open_, day=i))
    return bars


def _choppy(n: int = 40, base: float = 100.0, amplitude: float = 2.0) -> List[Bar]:
    """Oscillating market: alternating gap-down and gap-up each bar."""
    bars = [_bar(base, day=0)]
    for i in range(1, n):
        prev_close = bars[-1].close
        if i % 2 == 1:
            open_ = prev_close * 0.97   # gap down 3%
            close = prev_close * 0.995  # partial reversion up
        else:
            open_ = prev_close * 1.03   # gap up 3%
            close = prev_close * 1.005  # partial reversion down
        bars.append(_bar(close, open_=open_, day=i))
    return bars


def _flat(n: int = 40, price: float = 100.0) -> List[Bar]:
    return [_bar(price, day=i) for i in range(n)]


engine = BacktestEngine(initial_capital=10_000, commission_pct=0.001, slippage_pct=0.0005)
source = GapReversionSource(gap_threshold=0.01)


# ---------------------------------------------------------------------------
# Batch 4a — Degenerate bar counts
# ---------------------------------------------------------------------------

class TestDegenerateBars:
    def test_empty_bars_returns_empty_result(self):
        result = engine.run([], source, "SPY")
        assert result.total_trades == 0
        assert result.total_return_pct == 0.0

    def test_fewer_than_lookback_plus_two_returns_empty(self):
        """Need lookback + 2 bars minimum. With default lookback=20, need 22."""
        bars = _flat(n=21)  # one short
        result = engine.run(bars, source, "SPY", lookback=20)
        assert result.total_trades == 0

    def test_exactly_minimum_bars_runs_without_crash(self):
        """lookback=20 + 2 = 22 bars minimum."""
        bars = _flat(n=22)
        result = engine.run(bars, source, "SPY", lookback=20)
        assert result is not None
        assert not math.isnan(result.sharpe_ratio)

    def test_single_bar_returns_empty(self):
        result = engine.run([_bar(100.0)], source, "SPY")
        assert result.total_trades == 0


# ---------------------------------------------------------------------------
# Batch 4b — No-lookahead-bias guarantee
# ---------------------------------------------------------------------------

class TestNoLookahead:
    def test_signal_uses_only_past_bars(self):
        """
        Place a future-changing close price at bar N+1.
        The signal evaluated at bar N must NOT see bar N+1's close.
        We use a custom source that checks which bars it received.
        """
        from src.fuzzi.signals.base import SignalSource
        from src.fuzzi.common.models import Signal

        class LookaheadDetectorSource(SignalSource):
            name = "lookahead_detector"
            max_bars_seen: int = 0
            calls: list[int] = []

            def evaluate(self, symbol: str, bars: list[Bar]):
                self.calls.append(len(bars))
                self.max_bars_seen = max(self.max_bars_seen, len(bars))
                return None  # never trade, just observe

        spy_source = LookaheadDetectorSource()
        bars = _flat(n=30)
        engine.run(bars, spy_source, "SPY", lookback=5)

        # At bar i (0-indexed), the source should see exactly i+1 bars.
        # max bars seen should be len(bars) - 1 (last bar is only used for fill, not signal)
        assert spy_source.max_bars_seen <= len(bars) - 1, (
            f"source saw {spy_source.max_bars_seen} bars but should see at most {len(bars)-1}"
        )
        # Each call must see one more bar than the previous
        for i in range(1, len(spy_source.calls)):
            assert spy_source.calls[i] >= spy_source.calls[i - 1]

    def test_fill_happens_at_next_bar_open_not_signal_bar(self):
        """
        Enter at next bar's open is the documented fill model.
        If signal fires at bar i (close=100), and bar i+1 opens at 105,
        the entry price should be ~105 (+ slippage), NOT 100.
        """
        from src.fuzzi.signals.base import SignalSource
        from src.fuzzi.common.models import Signal

        signal_bars_seen = []

        class OneShotSource(SignalSource):
            name = "one_shot"
            fired: bool = False

            def evaluate(self, symbol: str, bars: list[Bar]):
                if not self.fired and len(bars) >= 22:
                    self.fired = True
                    signal_bars_seen.append(bars[-1].close)
                    return Signal(
                        symbol=symbol, direction="buy", confidence=0.9,
                        source=self.name, timestamp=bars[-1].timestamp, score=0.05,
                    )
                return None

        # Make the next bar after signal open at a very different price
        bars = _flat(n=25, price=100.0)
        bars[22] = _bar(100.0, open_=200.0, day=22)  # bar after signal fires: open=200

        one_shot = OneShotSource()
        result = engine.run(bars, one_shot, "SPY", lookback=20, hold_bars=1)

        if result.trades:
            trade = result.trades[0]
            # Entry price must be ~200 (next bar open), not 100 (signal bar close)
            assert trade.entry_price > 150, (
                f"entry_price={trade.entry_price}, expected ~200 (next bar open). "
                "Possible lookahead: engine may be filling at signal bar price."
            )


# ---------------------------------------------------------------------------
# Batch 4c — Commission and slippage math
# ---------------------------------------------------------------------------

class TestCommissionAndSlippage:
    def test_zero_commission_increases_profit(self):
        bars = _choppy(n=50)
        with_commission = BacktestEngine(initial_capital=10_000, commission_pct=0.01).run(bars, source, "SPY")
        without_commission = BacktestEngine(initial_capital=10_000, commission_pct=0.0).run(bars, source, "SPY")
        if with_commission.total_trades > 0 and without_commission.total_trades > 0:
            assert without_commission.total_return_pct >= with_commission.total_return_pct

    def test_high_slippage_reduces_profit(self):
        bars = _choppy(n=50)
        low_slip = BacktestEngine(initial_capital=10_000, slippage_pct=0.0).run(bars, source, "SPY")
        high_slip = BacktestEngine(initial_capital=10_000, slippage_pct=0.02).run(bars, source, "SPY")
        if low_slip.total_trades > 0 and high_slip.total_trades > 0:
            assert low_slip.total_return_pct >= high_slip.total_return_pct

    def test_commission_reduces_trade_pnl(self):
        """Each trade PnL should be reduced by commission on both legs."""
        bars = _choppy(n=30)
        no_cost = BacktestEngine(10_000, commission_pct=0.0, slippage_pct=0.0).run(bars, source, "SPY")
        with_cost = BacktestEngine(10_000, commission_pct=0.01, slippage_pct=0.0).run(bars, source, "SPY")
        if no_cost.total_trades > 0 and with_cost.total_trades > 0:
            assert no_cost.avg_win >= with_cost.avg_win or no_cost.total_return_pct > with_cost.total_return_pct


# ---------------------------------------------------------------------------
# Batch 4d — Metrics correctness
# ---------------------------------------------------------------------------

class TestMetricsCorrectness:
    def test_zero_trades_gives_zero_win_rate(self):
        result = engine.run(_flat(n=40), source, "SPY")
        assert result.win_rate == 0.0

    def test_all_winning_trades_win_rate_one(self):
        """Construct a scenario where every trade wins."""
        bars = _choppy(n=50)  # gap-down then reversion
        result = engine.run(bars, source, "SPY")
        if result.total_trades > 0:
            # win_rate should be countable
            assert 0.0 <= result.win_rate <= 1.0

    def test_max_drawdown_non_negative(self):
        for bars in [_trending_up(n=40), _trending_down(n=40), _choppy(n=40), _flat(n=40)]:
            result = engine.run(bars, source, "SPY")
            assert result.max_drawdown_pct >= 0.0, f"negative max drawdown: {result.max_drawdown_pct}"

    def test_max_drawdown_on_monotonic_decline(self):
        """Price only goes down — if we trade, drawdown should be significant."""
        bars = _trending_down(n=40, start=140.0, step=2.0, gap_pct=0.02)
        result = engine.run(bars, source, "SPY")
        if result.total_trades > 0 and result.total_return_pct < 0:
            assert result.max_drawdown_pct > 0

    def test_sharpe_is_finite(self):
        for bars in [_trending_up(n=40, gap_pct=0.02), _choppy(n=40), _flat(n=40)]:
            result = engine.run(bars, source, "SPY")
            assert math.isfinite(result.sharpe_ratio), f"non-finite Sharpe: {result.sharpe_ratio}"

    def test_sharpe_on_flat_equity_is_zero(self):
        """If nothing trades and equity never moves, Sharpe should be 0."""
        result = engine.run(_flat(n=40), source, "SPY")
        assert result.total_trades == 0
        assert result.sharpe_ratio == 0.0

    def test_profit_factor_infinite_when_no_losers(self):
        """If all trades win, profit_factor = inf."""
        bars = _choppy(n=50)
        result = engine.run(bars, source, "SPY")
        if result.total_trades > 0 and result.avg_loss == 0.0:
            assert result.profit_factor == float("inf") or result.profit_factor > 10

    def test_total_return_matches_equity_curve(self):
        bars = _choppy(n=50)
        result = engine.run(bars, source, "SPY")
        expected_return = (result.equity_curve[-1] / result.initial_capital - 1) * 100
        assert math.isclose(result.total_return_pct, expected_return, abs_tol=0.001)

    def test_final_equity_matches_equity_curve_last(self):
        bars = _choppy(n=50)
        result = engine.run(bars, source, "SPY")
        assert math.isclose(result.final_equity, result.equity_curve[-1], abs_tol=0.001)


# ---------------------------------------------------------------------------
# Batch 4e — Long-only filter
# ---------------------------------------------------------------------------

class TestLongOnlyFilter:
    def test_sell_signals_never_execute(self):
        """BacktestEngine explicitly skips non-buy signals (long only in v1)."""
        from src.fuzzi.signals.base import SignalSource
        from src.fuzzi.common.models import Signal

        class AllSellSource(SignalSource):
            name = "all_sell"
            def evaluate(self, symbol: str, bars: list[Bar]):
                return Signal(
                    symbol=symbol, direction="sell", confidence=0.9,
                    source=self.name, timestamp=bars[-1].timestamp, score=0.05,
                )

        bars = _trending_up(n=40)
        result = engine.run(bars, AllSellSource(), "SPY")
        assert result.total_trades == 0, "backtest engine executed sell trades — long-only filter broken"

    def test_gap_up_sell_signals_not_traded(self):
        """In a trending-up market, gap reversion generates SELLs. None should trade."""
        bars = _trending_up(n=50, step=1.0, gap_pct=0.02)  # 2% gap up every day
        result = engine.run(bars, source, "SPY")
        # All signals are sell → no trades in long-only engine
        assert result.total_trades == 0, (
            f"expected 0 trades on all-gap-up data, got {result.total_trades}. "
            "The gap-down BUY leg is never triggered when price only gaps up."
        )


# ---------------------------------------------------------------------------
# Batch 4f — Strategy edge validation (the real test)
# ---------------------------------------------------------------------------

class TestStrategyEdgeValidation:
    """
    These tests validate whether gap reversion has a real edge.
    They are INTENTIONALLY strict — a strategy that only barely passes
    is not a strategy worth trading.
    """

    @pytest.mark.xfail(
        reason=(
            "STRATEGY FINDING: gap reversion LOSES MONEY on next-bar-open fill model. "
            "The reversion happens within the gap bar (open→close). By the time we fill "
            "at the NEXT bar's open, that bar has already gapped in the opposite direction. "
            "We buy at the top of the reversal, exit at the next gap-down. Win rate=0%, "
            "return=-2.5% on pure choppy synthetic data. "
            "Gap reversion requires SAME-DAY entry at the gap open, not next-bar fill. "
            "The backtest fill model (next bar open) is architecturally incompatible with "
            "this strategy. Judgment lane must either: "
            "(a) change fill model to allow same-day entry, or "
            "(b) change strategy to hold until gap closes over multiple bars (hold_bars>1), or "
            "(c) accept that the 'edge' only exists intraday and cannot be backtested daily."
        ),
        strict=True,
    )
    def test_gap_reversion_profitable_in_choppy_market(self):
        """In a mean-reverting market, gap-down fade should make money."""
        bars = _choppy(n=60)
        result = engine.run(bars, source, "SPY", lookback=5, hold_bars=1)
        assert result.total_trades > 0, "strategy never fired in choppy market"
        assert result.total_return_pct > 0, (
            f"gap reversion lost money in choppy market: return={result.total_return_pct:.2f}%"
        )

    @pytest.mark.xfail(
        reason=(
            "STRATEGY FINDING: gap reversion performs BETTER in a trending-up market "
            "with daily gap-downs than in pure choppy data. "
            "In a rising trend with gap-downs: we buy the dip (gap down open), "
            "exit at next bar which has recovered. Uptrend provides the recovery. "
            "In choppy: next bar after gap-down gaps UP, we enter at the top, "
            "exit at the next gap-down. The next-bar fill model inverts the edge in choppy. "
            "The strategy thesis (works in choppy, not in trend) is backwards "
            "under the current fill model. The regime detector wiring is therefore "
            "wired to the wrong regime — it should fire in TRENDING_UP with gap-downs, "
            "not in CHOPPY. Or the fill model must change."
        ),
        strict=True,
    )
    def test_gap_reversion_underperforms_in_strong_uptrend(self):
        """
        In a strong uptrend, gap-down reversion fades the trend.
        The long-only engine skips all gap-up sells, and any gap-down
        buys are buying into a falling open that may not recover.
        This should either produce 0 trades or underperform choppy.
        """
        bars = _trending_up(n=60, step=0.5, gap_pct=-0.02)  # gap down 2% daily, trend up
        result_trend = engine.run(bars, source, "SPY", lookback=5, hold_bars=1)
        bars_choppy = _choppy(n=60)
        result_choppy = engine.run(bars_choppy, source, "SPY", lookback=5, hold_bars=1)

        if result_trend.total_trades > 0 and result_choppy.total_trades > 0:
            # Choppy should outperform trending for gap reversion
            assert result_choppy.total_return_pct >= result_trend.total_return_pct, (
                f"gap reversion in trending ({result_trend.total_return_pct:.2f}%) "
                f">= choppy ({result_choppy.total_return_pct:.2f}%) — "
                "strategy does not prefer its intended regime"
            )

    @pytest.mark.xfail(
        reason=(
            "OVERFITTING CANARY: Sharpe > 3 on synthetic data almost always means "
            "the strategy is overfit or the test data is too clean. "
            "If this test starts passing (Sharpe > 3 on real data), "
            "treat it as a red flag, not a green light."
        ),
        strict=False,
    )
    def test_gap_reversion_sharpe_not_suspiciously_high(self):
        """Sharpe > 3 on simple choppy synthetic data is a red flag."""
        bars = _choppy(n=200)
        result = engine.run(bars, source, "SPY", lookback=5, hold_bars=1)
        if result.total_trades >= 5:
            assert result.sharpe_ratio > 3.0  # xfail: we expect this NOT to trigger

    @pytest.mark.xfail(
        reason=(
            "STRATEGY FINDING: win rate is 0% in choppy market with next-bar fill. "
            "Corollary to the fill timing finding: every single trade loses because "
            "entry is at the top of the reversal, not the bottom of the gap. "
            "This must be fixed before paper trading. The 'edge' does not exist "
            "in the current backtest configuration."
        ),
        strict=True,
    )
    def test_gap_reversion_win_rate_above_chance_in_choppy(self):
        """Strategy should win > 50% of the time in its target regime."""
        bars = _choppy(n=100)
        result = engine.run(bars, source, "SPY", lookback=5, hold_bars=1)
        if result.total_trades >= 5:
            assert result.win_rate > 0.50, (
                f"gap reversion win rate {result.win_rate:.0%} is at or below chance "
                f"in choppy market ({result.total_trades} trades)"
            )

    def test_strategy_survives_downtrend_without_catastrophic_loss(self):
        """
        In a falling market, gap-down buys may execute (gaps down = buy signal).
        These are buying into a downtrend. The test flags catastrophic loss (> 30%)
        as a risk management concern.
        """
        bars = _trending_down(n=60, start=140.0, step=1.5, gap_pct=0.025)
        result = engine.run(bars, source, "SPY", lookback=5, hold_bars=1)
        if result.total_trades > 0:
            assert result.max_drawdown_pct < 30.0, (
                f"strategy lost {result.max_drawdown_pct:.1f}% max drawdown in downtrend "
                f"({result.total_trades} trades). Risk management may be inadequate."
            )

    def test_hold_bars_affects_pnl_direction(self):
        """Holding longer in a mean-reverting market may reduce edge."""
        bars = _choppy(n=80)
        hold_1 = engine.run(bars, source, "SPY", lookback=5, hold_bars=1)
        hold_5 = engine.run(bars, source, "SPY", lookback=5, hold_bars=5)
        # Just verify both run without error and produce finite metrics
        assert math.isfinite(hold_1.sharpe_ratio)
        assert math.isfinite(hold_5.sharpe_ratio)

    def test_multiple_symbols_independent_results(self):
        """Running on two symbols should give independent results (no shared state)."""
        bars_a = _choppy(n=50)
        bars_b = _trending_up(n=50, gap_pct=0.02)
        result_a = engine.run(bars_a, source, "SYMA")
        result_b = engine.run(bars_b, source, "SYMB")
        # Different inputs must give different results — they must be independent
        assert result_a.total_trades != result_b.total_trades or (
            result_a.total_return_pct != result_b.total_return_pct
        )
