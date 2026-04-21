"""
Adversarial tests for NerveTracker.

The existing test_nerve.py covers happy-path behaviour. This file attacks:
- The EWMA math: documented boost/penalty vs actual per-event effect
- Feedback loop correctness: record_win on submission vs actual P&L
- record_rejection asymmetry: policy blocks vs genuine bad calls
- Recovery symmetry: how many wins to undo a loss
- Rapid consecutive events
- strategy nerve isolation from global nerve
"""

from __future__ import annotations

import math
import pytest

from src.fuzzi.nerve.tracker import NerveMood, NerveTracker


# ---------------------------------------------------------------------------
# Batch 5a — EWMA math: documented vs actual per-event effect
# ---------------------------------------------------------------------------

class TestEWMAMath:
    """
    The documented win_boost=0.08 and loss_penalty=0.12 are NOT the actual
    per-event effect due to EWMA smoothing with decay=0.85.

    Actual effect: boost × (1 - decay) = 0.08 × 0.15 = 0.012 per win
                   penalty × (1 - decay) = 0.12 × 0.15 = 0.018 per loss

    These tests document this behaviour precisely. If someone changes the
    decay or boost values, these tests will catch calibration drift.
    """

    def test_single_win_actual_delta(self):
        nerve = NerveTracker(initial_nerve=0.5, decay=0.85, win_boost=0.08)
        before = nerve.state().global_nerve
        nerve.record_win("test", pnl=0.0)
        after = nerve.state().global_nerve
        actual_delta = after - before
        documented_boost = 0.08
        expected_actual = documented_boost * (1 - 0.85)  # 0.012
        assert math.isclose(actual_delta, expected_actual, abs_tol=1e-9), (
            f"actual win delta={actual_delta:.4f}, expected={expected_actual:.4f}. "
            f"Documented win_boost=0.08 but EWMA with decay=0.85 delivers {actual_delta:.4f} per win."
        )

    def test_single_loss_actual_delta(self):
        nerve = NerveTracker(initial_nerve=0.5, decay=0.85, loss_penalty=0.12)
        before = nerve.state().global_nerve
        nerve.record_loss("test", pnl=0.0)
        after = nerve.state().global_nerve
        actual_delta = before - after  # loss makes it smaller
        expected_actual = 0.12 * (1 - 0.85)  # 0.018
        assert math.isclose(actual_delta, expected_actual, abs_tol=1e-9), (
            f"actual loss delta={actual_delta:.4f}, expected={expected_actual:.4f}."
        )

    def test_wins_needed_to_reach_bold(self):
        """Documents how many consecutive wins it takes to go from STEADY to BOLD."""
        nerve = NerveTracker(initial_nerve=0.5, decay=0.85, win_boost=0.08)
        wins = 0
        while nerve.state().global_nerve < 0.8 and wins < 1000:
            nerve.record_win("test", pnl=0.0)
            wins += 1
        assert wins < 1000, "never reached BOLD — nerve system is functionally stuck"
        # Document the count for calibration awareness
        assert wins > 5, (
            f"reached BOLD in only {wins} wins — EWMA smoothing may be misconfigured. "
            f"Expected ~25 wins needed (win_boost=0.08, decay=0.85)."
        )

    def test_losses_needed_to_reach_spooked(self):
        """Documents how many consecutive losses to go from STEADY to SPOOKED."""
        nerve = NerveTracker(initial_nerve=0.5, decay=0.85, loss_penalty=0.12)
        losses = 0
        while nerve.state().global_nerve > 0.25 and losses < 1000:
            nerve.record_loss("test", pnl=0.0)
            losses += 1
        assert losses < 1000, "never reached SPOOKED"
        assert losses > 3, (
            f"reached SPOOKED in only {losses} losses — may be too sensitive."
        )

    def test_asymmetry_documented_ratio_matches_actual(self):
        """
        loss_penalty / win_boost = 0.12 / 0.08 = 1.5x.
        The actual per-event ratio should also be ~1.5x because EWMA scales both equally.
        """
        nerve_win = NerveTracker(initial_nerve=0.5, decay=0.85, win_boost=0.08, loss_penalty=0.12)
        nerve_loss = NerveTracker(initial_nerve=0.5, decay=0.85, win_boost=0.08, loss_penalty=0.12)

        nerve_win.record_win("t", pnl=0.0)
        nerve_loss.record_loss("t", pnl=0.0)

        win_delta = nerve_win.state().global_nerve - 0.5
        loss_delta = 0.5 - nerve_loss.state().global_nerve

        ratio = loss_delta / win_delta if win_delta > 0 else float("inf")
        expected_ratio = 0.12 / 0.08  # 1.5
        assert math.isclose(ratio, expected_ratio, rel_tol=0.01), (
            f"actual loss/win ratio={ratio:.3f}, expected={expected_ratio:.3f}"
        )


# ---------------------------------------------------------------------------
# Batch 5b — Feedback loop correctness
# ---------------------------------------------------------------------------

class TestFeedbackLoop:
    """
    Documents the known problem: record_win fires on seatbelt approval,
    not on realized P&L. These tests verify what currently happens, so
    that once the bug is fixed the tests flag the change.
    """

    def test_record_win_increases_nerve_regardless_of_future_outcome(self):
        """
        Calling record_win always increases nerve even if the trade
        will lose money. This is the documented bug: there is no
        outcome validation before calling record_win.
        """
        nerve = NerveTracker(initial_nerve=0.5)
        before = nerve.state().global_nerve
        nerve.record_win("test")
        after = nerve.state().global_nerve
        assert after > before  # current (broken) behaviour: nerve goes up unconditionally

    def test_record_rejection_decreases_nerve_for_policy_blocks(self):
        """
        Policy rejections (long-only, max positions) call record_rejection.
        This decreases nerve even though the strategy itself wasn't wrong.
        In a strong bull market, all gap-up SELL signals are rejected by policy
        → nerve drops 0.003 per rejection even though strategy logic is sound.
        Documents the bug: seatbelt policy blocks should not affect nerve.
        """
        nerve = NerveTracker(initial_nerve=0.5)
        before = nerve.state().global_nerve

        for _ in range(10):
            nerve.record_rejection("gap_reversion")

        after = nerve.state().global_nerve
        assert after < before, "policy rejections should decrease nerve (current behaviour)"

        # Each rejection moves nerve by 0.02 * (1-0.85) = 0.003
        delta = before - after
        expected_delta = 10 * 0.02 * (1 - 0.85)
        assert math.isclose(delta, expected_delta, rel_tol=0.05), (
            f"10 rejection delta={delta:.4f}, expected≈{expected_delta:.4f}. "
            "BUG: policy blocks are penalising nerve (0.003 per rejection). "
            "In a bull market with many gap-up sell blocks, this suppresses trading."
        )

    def test_rejection_is_much_smaller_penalty_than_a_loss(self):
        """
        record_rejection uses hard-coded 0.02 penalty.
        record_loss uses loss_penalty=0.12.
        So a policy block is 6x less damaging than a zero-P&L loss.
        Documents the current calibration so changes are visible.
        """
        nerve_rej = NerveTracker(initial_nerve=0.5)
        nerve_loss = NerveTracker(initial_nerve=0.5)

        nerve_rej.record_rejection("test")
        nerve_loss.record_loss("test", pnl=0.0)

        rej_delta = 0.5 - nerve_rej.state().global_nerve
        loss_delta = 0.5 - nerve_loss.state().global_nerve

        # rejection=0.003, loss=0.018 → loss is 6x more damaging
        assert loss_delta > rej_delta, (
            f"rejection_delta={rej_delta:.4f}, loss_delta={loss_delta:.4f}. "
            "A zero-P&L loss should penalise more than a policy rejection."
        )
        ratio = loss_delta / rej_delta if rej_delta > 0 else float("inf")
        assert math.isclose(ratio, 6.0, rel_tol=0.05), (
            f"loss/rejection ratio={ratio:.2f}, expected 6.0 (0.12/0.02). "
            "If this changes, the calibration has drifted."
        )


# ---------------------------------------------------------------------------
# Batch 5c — Recovery symmetry
# ---------------------------------------------------------------------------

class TestRecoverySymmetry:
    def test_wins_to_recover_from_one_loss(self):
        """How many wins to exactly undo one loss? Should be > 1 due to asymmetry."""
        nerve = NerveTracker(initial_nerve=0.5, decay=0.85, win_boost=0.08, loss_penalty=0.12)
        nerve.record_loss("test")
        after_loss = nerve.state().global_nerve

        nerve2 = NerveTracker(initial_nerve=after_loss, decay=0.85, win_boost=0.08, loss_penalty=0.12)
        wins = 0
        while nerve2.state().global_nerve < 0.5 and wins < 100:
            nerve2.record_win("test")
            wins += 1

        assert wins > 1, (
            f"recovered from one loss in {wins} win(s) — asymmetry may not be working"
        )
        assert wins <= 10, (
            f"took {wins} wins to recover from one loss — asymmetry may be too harsh"
        )

    def test_floor_prevents_death_spiral(self):
        """After 1000 consecutive losses, nerve should be at floor, not below."""
        nerve = NerveTracker(initial_nerve=0.5, floor=0.1)
        for _ in range(1000):
            nerve.record_loss("test", pnl=-100.0)
        assert nerve.state().global_nerve == pytest.approx(0.1, abs=0.001)

    def test_ceiling_prevents_euphoria_runaway(self):
        """After 1000 wins, nerve should be at ceiling, not above."""
        nerve = NerveTracker(initial_nerve=0.5, ceiling=1.0)
        for _ in range(1000):
            nerve.record_win("test", pnl=100.0)
        assert nerve.state().global_nerve == pytest.approx(1.0, abs=0.001)


# ---------------------------------------------------------------------------
# Batch 5d — Strategy isolation
# ---------------------------------------------------------------------------

class TestStrategyIsolation:
    @pytest.mark.xfail(
        reason=(
            "DESIGN FINDING: global nerve craters when one strategy loses heavily. "
            "5 wins then 20 losses → global nerve=0.185 (SPOOKED). "
            "There is no per-strategy isolation in the global nerve — all events, "
            "regardless of strategy, feed the global pool. "
            "If gap_reversion is losing badly, nerve will suppress trades from "
            "any future strategy added to the pit, even if that strategy is good. "
            "Judgment lane decision: should global nerve be an average of strategy nerves, "
            "or a separate independent signal?"
        ),
        strict=True,
    )
    def test_one_bad_strategy_does_not_crater_global_nerve(self):
        """Per-strategy nerve failing should not destroy global nerve."""
        nerve = NerveTracker(initial_nerve=0.5)

        for _ in range(5):
            nerve.record_win("winner", pnl=20.0)

        for _ in range(20):
            nerve.record_loss("loser", pnl=-5.0)

        state = nerve.state()
        assert state.strategy_nerves["winner"] > state.strategy_nerves["loser"]
        assert state.global_nerve > 0.3, (
            f"global nerve={state.global_nerve:.3f} cratered due to one bad strategy"
        )

    def test_new_strategy_starts_at_neutral(self):
        """A strategy never seen before defaults to 0.5 nerve."""
        nerve = NerveTracker()
        assert nerve.strategy_nerve("brand_new_strategy") == 0.5

    def test_global_nerve_moves_on_every_event(self):
        """Every win/loss/rejection must move global nerve, even for unknown strategy."""
        nerve = NerveTracker(initial_nerve=0.5)
        before = nerve.state().global_nerve
        nerve.record_win("new_strategy_1234")
        assert nerve.state().global_nerve != before

    def test_sizing_multiplier_reflects_global_not_strategy_nerve(self):
        """sizing_multiplier is based on global nerve, not per-strategy."""
        nerve = NerveTracker(initial_nerve=0.5)

        # Crash one strategy's nerve to floor
        for _ in range(50):
            nerve.record_loss("bad_strat", pnl=-50.0)

        # Global should have moved down, sizing multiplier should reflect that
        state = nerve.state()
        assert state.sizing_multiplier < 1.0
        # Per-strategy nerve for bad_strat is very low
        assert state.strategy_nerves.get("bad_strat", 0.5) < 0.3


# ---------------------------------------------------------------------------
# Batch 5e — Sizing multiplier accuracy
# ---------------------------------------------------------------------------

class TestSizingMultiplierAccuracy:
    def test_sizing_multiplier_at_neutral_is_one(self):
        nerve = NerveTracker(initial_nerve=0.5)
        assert math.isclose(nerve.sizing_multiplier, 1.0, abs_tol=0.01)

    def test_sizing_multiplier_at_floor_is_minimum(self):
        nerve = NerveTracker(initial_nerve=0.1, floor=0.1)
        # At nerve=0.1: 0.3 + (0.1 - 0.1) * (0.7 / 0.4) = 0.3
        assert math.isclose(nerve.sizing_multiplier, 0.3, abs_tol=0.01)

    def test_sizing_multiplier_at_ceiling_is_maximum(self):
        nerve = NerveTracker(initial_nerve=1.0, ceiling=1.0)
        # At nerve=1.0: 1.0 + (1.0 - 0.5) * (0.2 / 0.5) = 1.2
        assert math.isclose(nerve.sizing_multiplier, 1.2, abs_tol=0.01)

    def test_sizing_multiplier_monotonically_increases_with_nerve(self):
        """Higher nerve → higher (or equal) sizing multiplier."""
        levels = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        multipliers = [NerveTracker(initial_nerve=n).sizing_multiplier for n in levels]
        for i in range(1, len(multipliers)):
            assert multipliers[i] >= multipliers[i - 1], (
                f"sizing_multiplier decreased from nerve={levels[i-1]} to nerve={levels[i]}: "
                f"{multipliers[i-1]:.3f} → {multipliers[i]:.3f}"
            )

    def test_sizing_multiplier_never_nan(self):
        for initial in [0.1, 0.5, 1.0]:
            nerve = NerveTracker(initial_nerve=initial)
            assert not math.isnan(nerve.sizing_multiplier)
