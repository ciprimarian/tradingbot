"""Tests for the Fuzzi nerve system."""

import pytest

from src.fuzzi.nerve.tracker import NerveMood, NerveTracker


class TestNerveTracker:
    def test_starts_at_neutral(self):
        nerve = NerveTracker(initial_nerve=0.5)
        assert nerve.mood == NerveMood.STEADY
        assert nerve.sizing_multiplier == pytest.approx(1.0, abs=0.01)

    def test_wins_increase_nerve(self):
        nerve = NerveTracker(initial_nerve=0.5)
        starting = nerve.state().global_nerve

        nerve.record_win("gap_reversion", pnl=10.0)

        assert nerve.state().global_nerve > starting

    def test_losses_decrease_nerve(self):
        nerve = NerveTracker(initial_nerve=0.5)
        starting = nerve.state().global_nerve

        nerve.record_loss("gap_reversion", pnl=-10.0)

        assert nerve.state().global_nerve < starting

    def test_losses_hit_harder_than_wins(self):
        """Asymmetric: it takes more wins to recover from a loss."""
        nerve_a = NerveTracker(initial_nerve=0.5)
        nerve_b = NerveTracker(initial_nerve=0.5)

        nerve_a.record_win("test", pnl=10.0)
        nerve_b.record_loss("test", pnl=-10.0)

        win_delta = nerve_a.state().global_nerve - 0.5
        loss_delta = 0.5 - nerve_b.state().global_nerve

        # Loss should move nerve more than an equivalent win
        assert loss_delta > win_delta

    def test_nerve_never_below_floor(self):
        nerve = NerveTracker(initial_nerve=0.5, floor=0.1)

        # Spam losses
        for _ in range(100):
            nerve.record_loss("bad_strat", pnl=-50.0)

        assert nerve.state().global_nerve >= 0.1

    def test_nerve_never_above_ceiling(self):
        nerve = NerveTracker(initial_nerve=0.5, ceiling=1.0)

        # Spam wins
        for _ in range(100):
            nerve.record_win("good_strat", pnl=100.0)

        assert nerve.state().global_nerve <= 1.0

    def test_spooked_nerve_reduces_sizing(self):
        nerve = NerveTracker(initial_nerve=0.5)

        # Drive nerve down
        for _ in range(20):
            nerve.record_loss("failing", pnl=-20.0)

        state = nerve.state()
        assert state.sizing_multiplier < 1.0
        assert state.mood in (NerveMood.SPOOKED, NerveMood.CAUTIOUS)

    def test_per_strategy_tracking(self):
        nerve = NerveTracker(initial_nerve=0.5)

        # One strategy wins, another loses
        nerve.record_win("winner", pnl=15.0)
        nerve.record_win("winner", pnl=12.0)
        nerve.record_loss("loser", pnl=-20.0)
        nerve.record_loss("loser", pnl=-18.0)

        assert nerve.strategy_nerve("winner") > nerve.strategy_nerve("loser")

    def test_idle_drift_toward_neutral(self):
        nerve = NerveTracker(initial_nerve=0.8, neutral_drift=0.01)

        # Many idle ticks should drift toward 0.5
        for _ in range(200):
            nerve.tick_idle()

        # Should be closer to 0.5 than where it started
        assert nerve.state().global_nerve < 0.75

    def test_rejection_slightly_decreases_nerve(self):
        nerve = NerveTracker(initial_nerve=0.5)
        before = nerve.state().global_nerve

        nerve.record_rejection("cautious_strat")

        assert nerve.state().global_nerve < before

    def test_state_summary_is_readable(self):
        nerve = NerveTracker(initial_nerve=0.5)
        nerve.record_win("gap_reversion", pnl=5.0)

        summary = nerve.state().summary()

        assert "nerve=" in summary
        assert "sizing=" in summary
        assert "gap_reversion" in summary

    def test_unknown_strategy_defaults_to_neutral(self):
        nerve = NerveTracker(initial_nerve=0.5)
        assert nerve.strategy_nerve("never_seen") == 0.5

    def test_big_loss_penalizes_more_than_small(self):
        nerve_a = NerveTracker(initial_nerve=0.5)
        nerve_b = NerveTracker(initial_nerve=0.5)

        nerve_a.record_loss("test", pnl=-5.0)   # small loss
        nerve_b.record_loss("test", pnl=-100.0)  # big loss

        # Bigger loss should cause more damage
        assert nerve_a.state().global_nerve > nerve_b.state().global_nerve
