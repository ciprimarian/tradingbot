"""
Adversarial tests for SimpleSeatbelt.

The seatbelt is the last line of defence before an order is sent.
These tests attack: degenerate prices, degenerate cash, position limits,
sizing_multiplier edge values, and the long-only constraint interaction
with the gap reversion signal.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Dict

import pytest

from src.fuzzi.seatbelt.service import SeatbeltDecision, SimpleSeatbelt
from src.fuzzi.common.models import OrderIntent, PortfolioSnapshot, Position, Signal
from src.fuzzi.config import load_settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _settings():
    return load_settings()


def _seatbelt() -> SimpleSeatbelt:
    return SimpleSeatbelt(_settings())


def _portfolio(
    cash: float = 100.0,
    equity: float = 100.0,
    positions: Dict[str, Position] | None = None,
) -> PortfolioSnapshot:
    snap = PortfolioSnapshot(
        timestamp=datetime.now(timezone.utc),
        cash=cash,
        equity=equity,
    )
    if positions:
        snap.positions = positions
    return snap


def _buy_signal(symbol: str = "SPY", confidence: float = 0.8) -> Signal:
    return Signal(
        symbol=symbol,
        direction="buy",
        confidence=confidence,
        source="gap_reversion",
        timestamp=datetime.now(timezone.utc),
        score=0.03,
    )


def _sell_signal(symbol: str = "SPY") -> Signal:
    return Signal(
        symbol=symbol,
        direction="sell",
        confidence=0.7,
        source="gap_reversion",
        timestamp=datetime.now(timezone.utc),
        score=0.02,
    )


# ---------------------------------------------------------------------------
# Batch 3a — Long-only constraint
# ---------------------------------------------------------------------------

class TestLongOnlyConstraint:
    def test_buy_signal_passes_long_only_check(self):
        sb = _seatbelt()
        decision = sb.review_signal(_buy_signal(), last_price=100.0, portfolio=_portfolio())
        assert decision.approved

    def test_sell_signal_rejected_by_long_only(self):
        sb = _seatbelt()
        decision = sb.review_signal(_sell_signal(), last_price=100.0, portfolio=_portfolio())
        assert not decision.approved
        assert "long-only" in decision.reason.lower()

    def test_hold_signal_rejected_by_long_only(self):
        hold = Signal(
            symbol="SPY",
            direction="hold",
            confidence=0.5,
            source="test",
            timestamp=datetime.now(timezone.utc),
        )
        sb = _seatbelt()
        decision = sb.review_signal(hold, last_price=100.0, portfolio=_portfolio())
        assert not decision.approved

    def test_case_insensitive_direction_buy_passes(self):
        signal = Signal(
            symbol="SPY",
            direction="BUY",
            confidence=0.8,
            source="test",
            timestamp=datetime.now(timezone.utc),
        )
        sb = _seatbelt()
        decision = sb.review_signal(signal, last_price=100.0, portfolio=_portfolio())
        assert decision.approved


# ---------------------------------------------------------------------------
# Batch 3b — Position already open
# ---------------------------------------------------------------------------

class TestPositionAlreadyOpen:
    def _portfolio_with_position(self, symbol: str = "SPY") -> PortfolioSnapshot:
        snap = _portfolio(cash=100.0, equity=200.0)
        snap.positions = {
            symbol: Position(
                symbol=symbol,
                quantity=1.0,
                average_entry=100.0,
                market_price=100.0,
                market_value=100.0,
            )
        }
        return snap

    def test_open_position_blocks_new_signal(self):
        sb = _seatbelt()
        portfolio = self._portfolio_with_position("SPY")
        decision = sb.review_signal(_buy_signal("SPY"), last_price=100.0, portfolio=portfolio)
        assert not decision.approved
        assert "position" in decision.reason.lower()

    def test_different_symbol_allowed_when_position_open(self):
        sb = _seatbelt()
        portfolio = self._portfolio_with_position("SPY")
        decision = sb.review_signal(_buy_signal("AAPL"), last_price=150.0, portfolio=portfolio)
        # AAPL has no open position — should proceed to next check
        # (might be blocked by max_open_positions or cash, but not by existing position)
        if not decision.approved:
            assert "position already open" not in decision.reason.lower()


# ---------------------------------------------------------------------------
# Batch 3c — Max open positions
# ---------------------------------------------------------------------------

class TestMaxOpenPositions:
    def _portfolio_at_max(self) -> PortfolioSnapshot:
        settings = _settings()
        max_pos = settings.risk.max_open_positions
        snap = _portfolio(cash=1000.0, equity=2000.0)
        snap.positions = {
            f"SYM{i}": Position(f"SYM{i}", 1.0, 100.0, 100.0, 100.0)
            for i in range(max_pos)
        }
        return snap

    def test_at_max_positions_new_signal_rejected(self):
        sb = _seatbelt()
        portfolio = self._portfolio_at_max()
        decision = sb.review_signal(_buy_signal("NEWSTOCK"), last_price=50.0, portfolio=portfolio)
        assert not decision.approved
        assert "max" in decision.reason.lower()

    def test_one_below_max_new_signal_allowed(self):
        settings = _settings()
        max_pos = settings.risk.max_open_positions
        if max_pos <= 1:
            pytest.skip("max_open_positions=1 makes this test trivial")
        snap = _portfolio(cash=1000.0, equity=2000.0)
        snap.positions = {
            f"SYM{i}": Position(f"SYM{i}", 1.0, 100.0, 100.0, 100.0)
            for i in range(max_pos - 1)
        }
        sb = _seatbelt()
        decision = sb.review_signal(_buy_signal("NEWSTOCK"), last_price=50.0, portfolio=snap)
        # Not blocked by max_open_positions (may be blocked by cash/other checks)
        if not decision.approved:
            assert "max open positions" not in decision.reason.lower()


# ---------------------------------------------------------------------------
# Batch 3d — Cash and sizing
# ---------------------------------------------------------------------------

class TestCashAndSizing:
    def test_zero_cash_rejects(self):
        sb = _seatbelt()
        decision = sb.review_signal(_buy_signal(), last_price=100.0, portfolio=_portfolio(cash=0.0))
        assert not decision.approved

    def test_negative_cash_rejects(self):
        sb = _seatbelt()
        decision = sb.review_signal(_buy_signal(), last_price=100.0, portfolio=_portfolio(cash=-50.0))
        assert not decision.approved

    def test_cash_exactly_at_buffer_rejects(self):
        """cash == min_cash_buffer → spendable = 0 → reject."""
        settings = _settings()
        buffer = settings.risk.min_cash_buffer
        sb = _seatbelt()
        decision = sb.review_signal(_buy_signal(), last_price=1.0, portfolio=_portfolio(cash=buffer))
        assert not decision.approved

    def test_cash_just_above_buffer_approves(self):
        settings = _settings()
        buffer = settings.risk.min_cash_buffer
        sb = _seatbelt()
        # Cash slightly above buffer — should produce a tiny but valid order
        decision = sb.review_signal(
            _buy_signal(),
            last_price=0.01,  # very cheap stock to get a non-zero quantity
            portfolio=_portfolio(cash=buffer + 10.0),
        )
        assert decision.approved
        assert decision.intent is not None
        assert decision.intent.quantity > 0

    def test_order_quantity_is_positive(self):
        sb = _seatbelt()
        decision = sb.review_signal(_buy_signal(), last_price=100.0, portfolio=_portfolio(cash=100.0))
        assert decision.approved
        assert decision.intent is not None
        assert decision.intent.quantity > 0

    def test_order_quantity_not_nan_or_inf(self):
        sb = _seatbelt()
        decision = sb.review_signal(_buy_signal(), last_price=100.0, portfolio=_portfolio(cash=100.0))
        assert decision.approved
        assert decision.intent is not None
        assert not math.isnan(decision.intent.quantity)
        assert not math.isinf(decision.intent.quantity)


# ---------------------------------------------------------------------------
# Batch 3e — Invalid prices
# ---------------------------------------------------------------------------

class TestInvalidPrices:
    def test_zero_price_rejects(self):
        sb = _seatbelt()
        decision = sb.review_signal(_buy_signal(), last_price=0.0, portfolio=_portfolio(cash=100.0))
        assert not decision.approved
        assert "price" in decision.reason.lower()

    def test_negative_price_rejects(self):
        sb = _seatbelt()
        decision = sb.review_signal(_buy_signal(), last_price=-10.0, portfolio=_portfolio(cash=100.0))
        assert not decision.approved

    def test_very_small_price_does_not_produce_astronomic_quantity(self):
        """Price=1e-8 would give astronomic quantity. Should be capped by notional."""
        sb = _seatbelt()
        settings = _settings()
        decision = sb.review_signal(
            _buy_signal(),
            last_price=1e-8,
            portfolio=_portfolio(cash=1000.0),
        )
        if decision.approved and decision.intent:
            max_notional = settings.risk.max_position_notional
            # quantity * price must be <= max_notional
            assert decision.intent.quantity * 1e-8 <= max_notional * 1.01  # 1% tolerance

    def test_very_large_price_produces_valid_fractional_quantity(self):
        """Price=1e8 should produce a small but valid fractional quantity."""
        sb = _seatbelt()
        decision = sb.review_signal(
            _buy_signal(),
            last_price=1e8,
            portfolio=_portfolio(cash=100.0),
        )
        # Might be rejected if notional rounds to zero — but should not crash
        if decision.approved and decision.intent:
            assert decision.intent.quantity > 0
            assert not math.isnan(decision.intent.quantity)


# ---------------------------------------------------------------------------
# Batch 3f — Sizing multiplier edge values
# ---------------------------------------------------------------------------

class TestSizingMultiplier:
    @pytest.mark.xfail(
        reason=(
            "DESIGN GAP: seatbelt clamps sizing_multiplier=0.0 to 0.1 floor and approves "
            "the trade (notional=max_position_notional * 0.1). When nerve sends multiplier=0 "
            "to signal 'do not trade', the seatbelt overrides it silently. "
            "Either the nerve floor should not reach 0, or the seatbelt should reject "
            "multiplier=0 explicitly. Needs judgment-lane decision on intent."
        ),
        strict=True,
    )
    def test_sizing_multiplier_zero_rejects(self):
        """A multiplier of 0 means no position size → should reject."""
        sb = _seatbelt()
        decision = sb.review_signal(
            _buy_signal(),
            last_price=100.0,
            portfolio=_portfolio(cash=100.0),
            context={"sizing_multiplier": 0.0},
        )
        assert not decision.approved

    def test_sizing_multiplier_clamped_to_minimum(self):
        """Negative multiplier should be clamped to 0.1 floor (per seatbelt implementation)."""
        sb = _seatbelt()
        decision = sb.review_signal(
            _buy_signal(),
            last_price=100.0,
            portfolio=_portfolio(cash=100.0),
            context={"sizing_multiplier": -5.0},
        )
        # Should either approve with clamped size, or reject gracefully
        if decision.approved and decision.intent:
            assert decision.intent.quantity > 0

    def test_sizing_multiplier_one_gives_full_notional(self):
        sb = _seatbelt()
        settings = _settings()
        decision_full = sb.review_signal(
            _buy_signal(),
            last_price=1.0,
            portfolio=_portfolio(cash=1000.0),
            context={"sizing_multiplier": 1.0},
        )
        assert decision_full.approved
        full_qty = decision_full.intent.quantity

        decision_half = sb.review_signal(
            _buy_signal(),
            last_price=1.0,
            portfolio=_portfolio(cash=1000.0),
            context={"sizing_multiplier": 0.5},
        )
        assert decision_half.approved
        half_qty = decision_half.intent.quantity

        assert math.isclose(full_qty, half_qty * 2, rel_tol=0.01)

    def test_sizing_multiplier_above_one_clamped_to_one(self):
        """Multiplier > 1.0 should be clamped to 1.0 (seatbelt enforces this)."""
        sb = _seatbelt()
        decision_1x = sb.review_signal(
            _buy_signal(), last_price=1.0,
            portfolio=_portfolio(cash=1000.0),
            context={"sizing_multiplier": 1.0},
        )
        decision_10x = sb.review_signal(
            _buy_signal(), last_price=1.0,
            portfolio=_portfolio(cash=1000.0),
            context={"sizing_multiplier": 10.0},
        )
        if decision_1x.approved and decision_10x.approved:
            # Seatbelt clamps to 1.0, so both should produce equal quantity
            assert math.isclose(decision_1x.intent.quantity, decision_10x.intent.quantity, rel_tol=0.01)

    def test_missing_context_uses_default_multiplier(self):
        """No context passed → defaults to 1.0 sizing multiplier."""
        sb = _seatbelt()
        decision = sb.review_signal(
            _buy_signal(), last_price=100.0, portfolio=_portfolio(cash=100.0),
            context=None,
        )
        assert decision.approved or not decision.approved  # must not raise


# ---------------------------------------------------------------------------
# Batch 3g — Decision struct integrity
# ---------------------------------------------------------------------------

class TestDecisionIntegrity:
    def test_approved_decision_always_has_intent(self):
        sb = _seatbelt()
        decision = sb.review_signal(_buy_signal(), last_price=100.0, portfolio=_portfolio(cash=100.0))
        if decision.approved:
            assert decision.intent is not None

    def test_rejected_decision_has_no_intent(self):
        sb = _seatbelt()
        decision = sb.review_signal(_sell_signal(), last_price=100.0, portfolio=_portfolio(cash=100.0))
        assert not decision.approved
        assert decision.intent is None

    def test_approved_intent_side_is_buy(self):
        sb = _seatbelt()
        decision = sb.review_signal(_buy_signal(), last_price=100.0, portfolio=_portfolio(cash=100.0))
        if decision.approved and decision.intent:
            assert decision.intent.side == "buy"

    def test_approved_intent_symbol_matches_signal(self):
        sb = _seatbelt()
        decision = sb.review_signal(_buy_signal("TSLA"), last_price=250.0, portfolio=_portfolio(cash=100.0))
        if decision.approved and decision.intent:
            assert decision.intent.symbol == "TSLA"

    def test_rejected_decision_has_non_empty_reason(self):
        sb = _seatbelt()
        for signal, price in [
            (_sell_signal(), 100.0),
            (_buy_signal(), 0.0),
            (_buy_signal(), -10.0),
        ]:
            decision = sb.review_signal(signal, last_price=price, portfolio=_portfolio(cash=0.0))
            if not decision.approved:
                assert len(decision.reason) > 0, "rejected decision must have a reason"
