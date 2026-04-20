"""
Fuzzi backtest engine.

Replays historical bars through signal sources and seatbelt, simulating
what Fuzzi would have done. Produces performance metrics.

This is NOT the old backtester in src/backtest/. That one tests classic
strategies. This one tests the full Fuzzi pipeline: signal → seatbelt →
runner → blotter, exactly as it would run live.

Key principle: the backtest must be HONEST.
- No lookahead bias (signals only see bars up to "now")
- No survivorship bias (test on full universe, not just winners)
- Proper transaction costs
- Realistic fill assumptions (market orders fill at next bar open, not close)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Protocol

from src.fuzzi.common.models import Bar, PortfolioSnapshot, Position


class SignalSourceProtocol(Protocol):
    """Anything that can evaluate bars and produce a signal."""
    name: str

    def evaluate(self, symbol: str, bars: list[Bar]) -> Any:
        ...


@dataclass(slots=True)
class Trade:
    symbol: str
    side: str  # "buy" or "sell"
    quantity: float
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    return_pct: float
    hold_bars: int
    source: str


@dataclass(slots=True)
class BacktestResult:
    """Complete backtest output with all the metrics that matter."""
    trades: list[Trade]
    equity_curve: list[float]
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    total_trades: int
    avg_hold_bars: float
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_equity: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def expectancy(self) -> float:
        """Average PnL per trade."""
        if not self.trades:
            return 0.0
        return sum(t.pnl for t in self.trades) / len(self.trades)

    @property
    def is_profitable(self) -> bool:
        return self.total_return_pct > 0

    def summary(self) -> str:
        """One-line summary for logs."""
        return (
            f"trades={self.total_trades} "
            f"return={self.total_return_pct:+.2f}% "
            f"sharpe={self.sharpe_ratio:.2f} "
            f"dd={self.max_drawdown_pct:.2f}% "
            f"win={self.win_rate:.0%} "
            f"pf={self.profit_factor:.2f}"
        )


class BacktestEngine:
    """
    Replays bars through a signal source and simulates trading.

    Usage:
        engine = BacktestEngine(initial_capital=10000, commission_pct=0.001)
        result = engine.run(bars=historical_bars, source=gap_reversion, symbol="SPY")
    """

    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission_pct: float = 0.001,  # 0.1% per trade (roundtrip ~0.2%)
        max_position_pct: float = 0.25,  # max 25% of equity per position
        slippage_pct: float = 0.0005,  # 0.05% slippage per fill
    ) -> None:
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.max_position_pct = max_position_pct
        self.slippage_pct = slippage_pct

    def run(
        self,
        bars: list[Bar],
        source: SignalSourceProtocol,
        symbol: str,
        lookback: int = 20,
        hold_bars: int = 1,
    ) -> BacktestResult:
        """
        Run backtest over historical bars.

        Args:
            bars: Historical OHLCV bars, oldest first
            source: Signal source to evaluate
            symbol: Ticker being traded
            lookback: How many bars the signal source needs to see
            hold_bars: How many bars to hold before exiting (for swing)
        """
        if len(bars) < lookback + 2:
            return self._empty_result(bars)

        cash = self.initial_capital
        position: Position | None = None
        trades: list[Trade] = []
        equity_curve: list[float] = [self.initial_capital]
        entry_bar_idx: int = 0

        for i in range(lookback, len(bars) - 1):
            # Signal source only sees bars up to current (no lookahead)
            visible_bars = bars[:i + 1]
            current_bar = bars[i]
            next_bar = bars[i + 1]  # fills happen at next bar open

            current_equity = cash + (
                position.quantity * current_bar.close if position else 0.0
            )
            equity_curve.append(current_equity)

            # If we have a position, check if it's time to exit
            if position is not None:
                bars_held = i - entry_bar_idx
                if bars_held >= hold_bars:
                    # Exit at next bar open with slippage
                    exit_price = next_bar.open * (1 - self.slippage_pct)
                    proceeds = position.quantity * exit_price
                    commission = proceeds * self.commission_pct
                    cash += proceeds - commission

                    pnl = (exit_price - position.average_entry) * position.quantity - (
                        commission + position.average_entry * position.quantity * self.commission_pct
                    )
                    return_pct = pnl / (position.average_entry * position.quantity) * 100

                    trades.append(Trade(
                        symbol=symbol,
                        side="buy",
                        quantity=position.quantity,
                        entry_price=position.average_entry,
                        exit_price=exit_price,
                        entry_time=bars[entry_bar_idx].timestamp,
                        exit_time=next_bar.timestamp,
                        pnl=pnl,
                        return_pct=return_pct,
                        hold_bars=bars_held,
                        source=source.name,
                    ))
                    position = None
                continue  # don't enter while holding

            # No position — check for signal
            signal = source.evaluate(symbol, visible_bars)
            if signal is None:
                continue
            if signal.direction.lower() != "buy":
                continue  # v1: long only

            # Enter at next bar open with slippage
            entry_price = next_bar.open * (1 + self.slippage_pct)
            max_notional = current_equity * self.max_position_pct
            quantity = max_notional / entry_price
            commission = max_notional * self.commission_pct
            cash -= (quantity * entry_price) + commission

            position = Position(
                symbol=symbol,
                quantity=quantity,
                average_entry=entry_price,
            )
            entry_bar_idx = i + 1

        # Close any remaining position at last bar close
        if position is not None:
            last_bar = bars[-1]
            exit_price = last_bar.close
            proceeds = position.quantity * exit_price
            commission = proceeds * self.commission_pct
            cash += proceeds - commission

            pnl = (exit_price - position.average_entry) * position.quantity
            return_pct = pnl / (position.average_entry * position.quantity) * 100

            trades.append(Trade(
                symbol=symbol,
                side="buy",
                quantity=position.quantity,
                entry_price=position.average_entry,
                exit_price=exit_price,
                entry_time=bars[entry_bar_idx].timestamp,
                exit_time=last_bar.timestamp,
                pnl=pnl,
                return_pct=return_pct,
                hold_bars=len(bars) - 1 - entry_bar_idx,
                source=source.name,
            ))

        final_equity = cash
        equity_curve.append(final_equity)

        return self._compute_metrics(trades, equity_curve, bars)

    def _compute_metrics(
        self, trades: list[Trade], equity_curve: list[float], bars: list[Bar]
    ) -> BacktestResult:
        """Calculate all performance metrics from trades and equity curve."""
        total_return = (equity_curve[-1] / self.initial_capital - 1) * 100

        # Sharpe (annualized, assuming daily bars)
        if len(equity_curve) > 2:
            returns = [
                (equity_curve[i] / equity_curve[i - 1]) - 1
                for i in range(1, len(equity_curve))
                if equity_curve[i - 1] > 0
            ]
            if returns:
                avg_ret = sum(returns) / len(returns)
                std_ret = (sum((r - avg_ret) ** 2 for r in returns) / len(returns)) ** 0.5
                sharpe = (avg_ret / std_ret * math.sqrt(252)) if std_ret > 0 else 0.0
            else:
                sharpe = 0.0
        else:
            sharpe = 0.0

        # Max drawdown
        peak = self.initial_capital
        max_dd = 0.0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100
            if dd > max_dd:
                max_dd = dd

        # Win/loss metrics
        winners = [t for t in trades if t.pnl > 0]
        losers = [t for t in trades if t.pnl <= 0]
        win_rate = len(winners) / len(trades) if trades else 0.0
        avg_win = sum(t.pnl for t in winners) / len(winners) if winners else 0.0
        avg_loss = sum(t.pnl for t in losers) / len(losers) if losers else 0.0
        gross_profit = sum(t.pnl for t in winners)
        gross_loss = abs(sum(t.pnl for t in losers))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        avg_hold = sum(t.hold_bars for t in trades) / len(trades) if trades else 0.0

        return BacktestResult(
            trades=trades,
            equity_curve=equity_curve,
            total_return_pct=total_return,
            sharpe_ratio=sharpe,
            max_drawdown_pct=max_dd,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            total_trades=len(trades),
            avg_hold_bars=avg_hold,
            start_date=bars[0].timestamp if bars else datetime.now(timezone.utc),
            end_date=bars[-1].timestamp if bars else datetime.now(timezone.utc),
            initial_capital=self.initial_capital,
            final_equity=equity_curve[-1],
        )

    def _empty_result(self, bars: list[Bar]) -> BacktestResult:
        return BacktestResult(
            trades=[],
            equity_curve=[self.initial_capital],
            total_return_pct=0.0,
            sharpe_ratio=0.0,
            max_drawdown_pct=0.0,
            win_rate=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            profit_factor=0.0,
            total_trades=0,
            avg_hold_bars=0.0,
            start_date=bars[0].timestamp if bars else datetime.now(timezone.utc),
            end_date=bars[-1].timestamp if bars else datetime.now(timezone.utc),
            initial_capital=self.initial_capital,
            final_equity=self.initial_capital,
        )
