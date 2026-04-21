"""
Adversarial tests for the Council — degenerate advisor inputs, edge convictions,
veto boundary conditions, and silent failure guards.

These are not happy-path tests. The goal is to find inputs the council
handles silently but wrongly: NaN confidence, extreme weights, name mismatches,
one-advisor quorum, score underflow, etc.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest

from src.fuzzi.brain.advisor import Advisor, AdvisorRole, AdvisorVerdict, Stance, STANCE_SCORES
from src.fuzzi.brain.council import (
    Council,
    CouncilRuling,
    DissentPattern,
    RulingAction,
)
from src.fuzzi.brain.providers import MockProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _advisor(name: str, role: AdvisorRole = AdvisorRole.ANALYST, weight: float = 0.33) -> Advisor:
    return Advisor(name=name, role=role, provider=MockProvider(response="{}"), weight=weight)


def _verdict(
    name: str,
    stance: Stance,
    confidence: float = 0.8,
    role: AdvisorRole = AdvisorRole.ANALYST,
    flags: list[str] | None = None,
) -> AdvisorVerdict:
    return AdvisorVerdict(
        advisor_name=name,
        role=role,
        symbol="SPY",
        stance=stance,
        confidence=confidence,
        reasoning="test",
        flags=flags or [],
    )


def _council(*advisor_names: str) -> Council:
    advisors = [_advisor(n) for n in advisor_names]
    return Council(advisors)


# ---------------------------------------------------------------------------
# Batch 1a — Empty and minimal inputs
# ---------------------------------------------------------------------------

class TestEmptyAndMinimalInputs:
    def test_no_verdicts_holds(self):
        council = _council("opus", "gpt", "grok")
        ruling = council.rule([])
        assert ruling.action == RulingAction.HOLD
        assert ruling.conviction == 0.0
        assert ruling.dissent == DissentPattern.SPARSE

    def test_single_active_verdict_is_sparse(self):
        """One active verdict is insufficient for a ruling."""
        council = _council("opus", "gpt")
        ruling = council.rule([_verdict("opus", Stance.BUY)])
        assert ruling.action == RulingAction.HOLD
        assert ruling.dissent == DissentPattern.SPARSE

    def test_single_abstain_is_sparse(self):
        council = _council("opus")
        ruling = council.rule([_verdict("opus", Stance.ABSTAIN, confidence=0.0)])
        assert ruling.action == RulingAction.HOLD
        assert ruling.dissent == DissentPattern.SPARSE

    def test_zero_advisors_council_holds_on_valid_verdicts(self):
        """Council with no registered advisors — falls back to base weight 0.33."""
        council = Council([])
        verdicts = [_verdict("opus", Stance.BUY), _verdict("gpt", Stance.BUY)]
        ruling = council.rule(verdicts)
        # should not raise; should produce a valid ruling
        assert ruling.action in RulingAction
        assert not math.isnan(ruling.conviction)

    def test_conviction_always_in_range(self):
        """Conviction must always be in [0, 1] regardless of inputs."""
        council = _council("opus", "gpt", "grok")
        for stances in [
            [Stance.STRONG_BUY, Stance.STRONG_BUY, Stance.STRONG_BUY],
            [Stance.STRONG_SELL, Stance.STRONG_SELL, Stance.STRONG_SELL],
            [Stance.STRONG_BUY, Stance.STRONG_SELL, Stance.HOLD],
            [Stance.ABSTAIN, Stance.ABSTAIN, Stance.BUY],
        ]:
            verdicts = [_verdict(n, s) for n, s in zip(["opus", "gpt", "grok"], stances)]
            ruling = council.rule(verdicts)
            assert 0.0 <= ruling.conviction <= 1.0, f"conviction {ruling.conviction} out of range for {stances}"


# ---------------------------------------------------------------------------
# Batch 1b — All abstain
# ---------------------------------------------------------------------------

class TestAllAbstain:
    def test_all_abstain_produces_hold(self):
        council = _council("opus", "gpt", "grok")
        verdicts = [
            _verdict("opus", Stance.ABSTAIN, confidence=0.0),
            _verdict("gpt", Stance.ABSTAIN, confidence=0.0),
            _verdict("grok", Stance.ABSTAIN, confidence=0.0),
        ]
        ruling = council.rule(verdicts)
        assert ruling.action == RulingAction.HOLD
        assert ruling.dissent == DissentPattern.SPARSE

    def test_all_abstain_conviction_zero(self):
        council = _council("opus", "gpt", "grok")
        verdicts = [_verdict(n, Stance.ABSTAIN, confidence=0.0) for n in ["opus", "gpt", "grok"]]
        ruling = council.rule(verdicts)
        assert ruling.conviction == 0.0

    def test_two_abstain_one_strong_buy_is_sparse(self):
        """Majority abstain: too few active for a ruling."""
        council = _council("opus", "gpt", "grok")
        verdicts = [
            _verdict("opus", Stance.ABSTAIN),
            _verdict("gpt", Stance.ABSTAIN),
            _verdict("grok", Stance.STRONG_BUY, confidence=1.0),
        ]
        ruling = council.rule(verdicts)
        assert ruling.action == RulingAction.HOLD
        assert ruling.dissent == DissentPattern.SPARSE

    def test_abstain_with_high_confidence_still_counts_as_abstain(self):
        """Confidence on an ABSTAIN verdict must not contribute to the score."""
        council = _council("opus", "gpt")
        verdicts = [
            _verdict("opus", Stance.ABSTAIN, confidence=1.0),
            _verdict("gpt", Stance.BUY, confidence=0.8),
        ]
        ruling = council.rule(verdicts)
        # Only gpt is active — sparse
        assert ruling.action == RulingAction.HOLD
        assert ruling.dissent == DissentPattern.SPARSE

    def test_abstain_score_property_is_always_zero(self):
        """AdvisorVerdict.score must be 0 for any abstain, regardless of confidence."""
        for confidence in [0.0, 0.5, 1.0]:
            v = _verdict("test", Stance.ABSTAIN, confidence=confidence)
            assert v.score == 0.0, f"ABSTAIN with confidence={confidence} gave score={v.score}"


# ---------------------------------------------------------------------------
# Batch 1c — All extreme (STRONG_BUY / STRONG_SELL)
# ---------------------------------------------------------------------------

class TestAllExtreme:
    def test_all_strong_buy_maximum_conviction(self):
        council = _council("opus", "gpt", "grok")
        verdicts = [_verdict(n, Stance.STRONG_BUY, confidence=1.0) for n in ["opus", "gpt", "grok"]]
        ruling = council.rule(verdicts)
        assert ruling.action == RulingAction.BUY
        assert ruling.dissent == DissentPattern.UNANIMOUS
        assert ruling.conviction > 0.8

    def test_all_strong_sell_produces_sell_ruling(self):
        council = _council("opus", "gpt", "grok")
        verdicts = [_verdict(n, Stance.STRONG_SELL, confidence=1.0) for n in ["opus", "gpt", "grok"]]
        ruling = council.rule(verdicts)
        assert ruling.action == RulingAction.SELL
        assert ruling.dissent == DissentPattern.UNANIMOUS

    def test_strong_buy_vs_strong_sell_deadlock(self):
        council = _council("opus", "gpt")
        verdicts = [
            _verdict("opus", Stance.STRONG_BUY, confidence=1.0),
            _verdict("gpt", Stance.STRONG_SELL, confidence=1.0),
        ]
        ruling = council.rule(verdicts)
        assert ruling.dissent == DissentPattern.DEADLOCK
        assert ruling.should_act is False

    def test_extreme_confidence_does_not_overflow_conviction(self):
        council = _council("opus", "gpt", "grok")
        verdicts = [_verdict(n, Stance.STRONG_BUY, confidence=1.0) for n in ["opus", "gpt", "grok"]]
        ruling = council.rule(verdicts)
        assert ruling.conviction <= 1.0

    @pytest.mark.xfail(
        reason=(
            "BUG: MAJORITY dissent penalty (0.15) is miscalibrated. "
            "2:1 STRONG_BUY vs STRONG_SELL at equal weights normalizes to 0.333, "
            "then 0.333 - 0.15 = 0.183 < threshold 0.4 → HOLD. "
            "A 2:1 unanimous-strength majority should produce a BUY ruling. "
            "Fix: either reduce MAJORITY penalty, raise score weights for 2:1, "
            "or lower conviction_threshold for MAJORITY pattern. Judgment lane to decide."
        ),
        strict=True,
    )
    def test_mixed_extreme_three_advisors_majority(self):
        """2 strong-buy vs 1 strong-sell → MAJORITY, buy ruling."""
        council = _council("opus", "gpt", "grok")
        verdicts = [
            _verdict("opus", Stance.STRONG_BUY, confidence=1.0),
            _verdict("gpt", Stance.STRONG_BUY, confidence=1.0),
            _verdict("grok", Stance.STRONG_SELL, confidence=1.0),
        ]
        ruling = council.rule(verdicts)
        assert ruling.action == RulingAction.BUY
        assert ruling.dissent == DissentPattern.MAJORITY


# ---------------------------------------------------------------------------
# Batch 1d — NaN and out-of-range confidence
# ---------------------------------------------------------------------------

class TestNaNAndOutOfRangeConfidence:
    def test_nan_confidence_does_not_produce_nan_conviction(self):
        """NaN confidence in a verdict must not propagate into conviction."""
        council = _council("opus", "gpt", "grok")
        verdicts = [
            _verdict("opus", Stance.BUY, confidence=float("nan")),
            _verdict("gpt", Stance.BUY, confidence=0.8),
            _verdict("grok", Stance.BUY, confidence=0.7),
        ]
        try:
            ruling = council.rule(verdicts)
            assert not math.isnan(ruling.conviction), "NaN conviction leaked from NaN confidence input"
        except Exception as e:
            pytest.fail(f"council.rule raised on NaN confidence input: {e}")

    def test_confidence_above_one_does_not_overflow(self):
        """confidence=2.0 should not make conviction > 1.0."""
        council = _council("opus", "gpt", "grok")
        verdicts = [
            _verdict("opus", Stance.BUY, confidence=2.0),
            _verdict("gpt", Stance.BUY, confidence=2.0),
            _verdict("grok", Stance.BUY, confidence=2.0),
        ]
        try:
            ruling = council.rule(verdicts)
            assert ruling.conviction <= 1.0
        except Exception as e:
            pytest.fail(f"council.rule raised on confidence=2.0: {e}")

    def test_negative_confidence_does_not_produce_negative_conviction(self):
        council = _council("opus", "gpt", "grok")
        verdicts = [
            _verdict("opus", Stance.BUY, confidence=-0.5),
            _verdict("gpt", Stance.BUY, confidence=-0.5),
            _verdict("grok", Stance.BUY, confidence=-0.5),
        ]
        try:
            ruling = council.rule(verdicts)
            assert ruling.conviction >= 0.0
        except Exception as e:
            pytest.fail(f"council.rule raised on negative confidence: {e}")

    def test_verdict_score_nan_confidence_is_zero_or_finite(self):
        # BUG: AdvisorVerdict.score = STANCE_SCORES[stance] * self.confidence
        # NaN confidence → NaN score → propagates to council weighted sum → NaN conviction.
        # The score property must guard against NaN confidence. Fix: clamp confidence in
        # the score property or in AdvisorVerdict construction. Judgment/compute lane to fix.
        v = AdvisorVerdict(
            advisor_name="test",
            role=AdvisorRole.ANALYST,
            symbol="SPY",
            stance=Stance.BUY,
            confidence=float("nan"),
            reasoning="test",
        )
        score = v.score
        assert not math.isnan(score), f"AdvisorVerdict.score is NaN when confidence is NaN: {score}"


# ---------------------------------------------------------------------------
# Batch 1e — Advisor name mismatches (orphaned verdicts)
# ---------------------------------------------------------------------------

class TestNameMismatches:
    def test_verdict_from_unknown_advisor_uses_fallback_weight(self):
        """Verdict from an advisor not registered in the Council should use 0.33 fallback."""
        council = _council("opus")
        verdicts = [
            _verdict("opus", Stance.BUY, confidence=0.8),
            _verdict("ghost_advisor", Stance.BUY, confidence=0.8),  # not registered
        ]
        try:
            ruling = council.rule(verdicts)
            assert not math.isnan(ruling.conviction)
        except Exception as e:
            pytest.fail(f"council.rule raised on unregistered advisor name: {e}")

    def test_all_verdicts_from_unknown_advisors_does_not_crash(self):
        council = _council("opus", "gpt")
        verdicts = [
            _verdict("X", Stance.BUY, confidence=0.8),
            _verdict("Y", Stance.SELL, confidence=0.8),
        ]
        try:
            ruling = council.rule(verdicts)
            assert ruling is not None
        except Exception as e:
            pytest.fail(f"raised with fully unknown advisors: {e}")

    def test_case_sensitive_name_mismatch_uses_fallback(self):
        """'Opus' vs 'opus' — should not raise, should fall back to 0.33."""
        council = _council("opus", "gpt")
        verdicts = [
            _verdict("Opus", Stance.BUY),  # capital O
            _verdict("GPT", Stance.BUY),   # capital GPT
        ]
        try:
            ruling = council.rule(verdicts)
            assert not math.isnan(ruling.conviction)
        except Exception as e:
            pytest.fail(f"raised on case-mismatched names: {e}")


# ---------------------------------------------------------------------------
# Batch 1f — Strategist veto boundary conditions
# ---------------------------------------------------------------------------

class TestStrategistVeto:
    def _veto_council(self) -> Council:
        return Council(
            advisors=[
                _advisor("strategist", AdvisorRole.STRATEGIST, weight=0.4),
                _advisor("analyst", AdvisorRole.ANALYST, weight=0.3),
                _advisor("scout", AdvisorRole.SCOUT, weight=0.3),
            ],
            strategist_veto_threshold=-0.5,
        )

    def test_strategist_strongly_bearish_while_others_bullish_vetoes(self):
        council = self._veto_council()
        verdicts = [
            _verdict("strategist", Stance.STRONG_SELL, confidence=1.0, role=AdvisorRole.STRATEGIST),
            _verdict("analyst", Stance.BUY, confidence=0.8, role=AdvisorRole.ANALYST),
            _verdict("scout", Stance.BUY, confidence=0.7, role=AdvisorRole.SCOUT),
        ]
        ruling = council.rule(verdicts)
        assert ruling.action == RulingAction.HOLD
        assert "vetoed" in ruling.reasoning

    def test_strategist_weakly_bearish_does_not_veto(self):
        """Strategist score must be below threshold (-0.5) to trigger veto."""
        council = self._veto_council()
        verdicts = [
            _verdict("strategist", Stance.LEAN_SELL, confidence=0.6, role=AdvisorRole.STRATEGIST),
            _verdict("analyst", Stance.BUY, confidence=0.8, role=AdvisorRole.ANALYST),
            _verdict("scout", Stance.BUY, confidence=0.7, role=AdvisorRole.SCOUT),
        ]
        # LEAN_SELL × 0.6 = -0.3 × 0.6 = -0.18, above threshold -0.5 → no veto
        ruling = council.rule(verdicts)
        assert "vetoed" not in ruling.reasoning.lower() or ruling.action != RulingAction.HOLD

    def test_no_strategist_advisor_no_veto(self):
        """Council with no STRATEGIST role can never trigger veto."""
        council = Council(
            advisors=[
                _advisor("a", AdvisorRole.ANALYST),
                _advisor("b", AdvisorRole.ANALYST),
            ]
        )
        verdicts = [
            _verdict("a", Stance.BUY, confidence=0.9),
            _verdict("b", Stance.BUY, confidence=0.9),
        ]
        ruling = council.rule(verdicts)
        assert "vetoed" not in ruling.reasoning

    def test_strategist_abstains_no_veto(self):
        """Abstaining strategist cannot trigger veto — they have no score."""
        council = self._veto_council()
        verdicts = [
            _verdict("strategist", Stance.ABSTAIN, confidence=0.0, role=AdvisorRole.STRATEGIST),
            _verdict("analyst", Stance.BUY, confidence=0.9, role=AdvisorRole.ANALYST),
            _verdict("scout", Stance.BUY, confidence=0.8, role=AdvisorRole.SCOUT),
        ]
        ruling = council.rule(verdicts)
        assert "vetoed" not in ruling.reasoning

    def test_veto_reduces_nerve_adjustment_more_than_hold(self):
        """Vetoed rulings carry a larger negative nerve adjustment than a low-conviction hold."""
        council = self._veto_council()

        vetoed_verdicts = [
            _verdict("strategist", Stance.STRONG_SELL, confidence=1.0, role=AdvisorRole.STRATEGIST),
            _verdict("analyst", Stance.BUY, confidence=0.8),
            _verdict("scout", Stance.BUY, confidence=0.7),
        ]
        low_conv_verdicts = [
            _verdict("strategist", Stance.HOLD, confidence=0.5, role=AdvisorRole.STRATEGIST),
            _verdict("analyst", Stance.LEAN_BUY, confidence=0.2),
            _verdict("scout", Stance.LEAN_SELL, confidence=0.2),
        ]

        vetoed = council.rule(vetoed_verdicts)
        # reset so ruling count doesn't trigger advisor reset
        council2 = self._veto_council()
        low_conv = council2.rule(low_conv_verdicts)

        assert vetoed.nerve_adjustment < low_conv.nerve_adjustment


# ---------------------------------------------------------------------------
# Batch 1g — Social manipulation flag edge cases
# ---------------------------------------------------------------------------

class TestSocialManipulationFlag:
    def test_pump_flag_caps_conviction_at_half(self):
        council = _council("opus", "gpt", "grok")
        verdicts = [
            _verdict("opus", Stance.STRONG_BUY, confidence=1.0),
            _verdict("gpt", Stance.STRONG_BUY, confidence=1.0),
            AdvisorVerdict(
                advisor_name="grok",
                role=AdvisorRole.SCOUT,
                symbol="SPY",
                stance=Stance.STRONG_BUY,
                confidence=1.0,
                reasoning="suspicious pump",
                flags=["pump_risk"],
            ),
        ]
        ruling = council.rule(verdicts)
        assert ruling.conviction <= 0.5

    def test_manipulation_flag_case_insensitive(self):
        council = _council("opus", "gpt", "grok")
        verdicts = [
            _verdict("opus", Stance.STRONG_BUY, confidence=1.0),
            _verdict("gpt", Stance.STRONG_BUY, confidence=1.0),
            AdvisorVerdict(
                advisor_name="grok",
                role=AdvisorRole.SCOUT,
                symbol="SPY",
                stance=Stance.BUY,
                confidence=0.7,
                reasoning="Looks like MANIPULATION",
                flags=["Manipulation_Risk"],  # mixed case
            ),
        ]
        ruling = council.rule(verdicts)
        assert ruling.conviction <= 0.5

    def test_non_scout_manipulation_flag_has_no_effect(self):
        """Only scout flags should trigger the social cap."""
        council = _council("opus", "gpt", "grok")
        verdicts = [
            AdvisorVerdict(
                advisor_name="opus",
                role=AdvisorRole.STRATEGIST,
                symbol="SPY",
                stance=Stance.STRONG_BUY,
                confidence=1.0,
                reasoning="strong trend",
                flags=["pump_risk"],  # strategist flagging it — should not cap
            ),
            _verdict("gpt", Stance.STRONG_BUY, confidence=1.0),
            _verdict("grok", Stance.STRONG_BUY, confidence=1.0),
        ]
        ruling = council.rule(verdicts)
        # With no scout flag, conviction should be high
        assert ruling.conviction > 0.5

    def test_empty_flags_no_cap(self):
        council = _council("opus", "gpt", "grok")
        verdicts = [_verdict(n, Stance.STRONG_BUY, confidence=1.0) for n in ["opus", "gpt", "grok"]]
        ruling = council.rule(verdicts)
        assert ruling.conviction > 0.5


# ---------------------------------------------------------------------------
# Batch 1h — Periodic reset does not corrupt state
# ---------------------------------------------------------------------------

class TestPeriodicReset:
    def test_reset_at_n_rulings_does_not_raise(self):
        """After reset_every_n_trades rulings, advisor track records wipe. No crash."""
        council = Council(
            advisors=[_advisor("opus"), _advisor("gpt")],
            reset_every_n_trades=3,
        )
        verdicts = [_verdict("opus", Stance.BUY), _verdict("gpt", Stance.BUY)]
        for _ in range(5):
            ruling = council.rule(verdicts)
            assert ruling is not None

    def test_conviction_still_valid_after_reset(self):
        council = Council(
            advisors=[_advisor("opus"), _advisor("gpt")],
            reset_every_n_trades=2,
        )
        verdicts = [_verdict("opus", Stance.BUY), _verdict("gpt", Stance.BUY)]
        for _ in range(4):
            ruling = council.rule(verdicts)
            assert 0.0 <= ruling.conviction <= 1.0
            assert not math.isnan(ruling.conviction)

    def test_reset_clears_hit_rate(self):
        advisor = _advisor("opus")
        council = Council(advisors=[advisor, _advisor("gpt")], reset_every_n_trades=2)
        for _ in range(5):
            advisor.record_outcome(True)
        assert advisor.hit_rate is not None
        verdicts = [_verdict("opus", Stance.BUY), _verdict("gpt", Stance.BUY)]
        council.rule(verdicts)
        council.rule(verdicts)
        # After 2 rulings, reset fires — track record wiped
        assert advisor.hit_rate is None


# ---------------------------------------------------------------------------
# Batch 1i — CouncilRuling struct invariants
# ---------------------------------------------------------------------------

class TestRulingInvariants:
    def test_should_act_false_when_hold(self):
        council = _council("opus", "gpt")
        ruling = council.rule([])
        assert ruling.should_act is False

    def test_should_act_false_when_conviction_below_threshold(self):
        """Conviction just below threshold must not trigger action."""
        council = Council(
            advisors=[_advisor("a"), _advisor("b")],
            conviction_threshold=0.4,
        )
        # Produce a split that makes conviction < 0.4
        verdicts = [
            _verdict("a", Stance.LEAN_BUY, confidence=0.3),
            _verdict("b", Stance.LEAN_SELL, confidence=0.3),
        ]
        ruling = council.rule(verdicts)
        if ruling.conviction < 0.4:
            assert ruling.should_act is False

    def test_ruling_action_is_always_valid_enum(self):
        council = _council("opus", "gpt", "grok")
        for stances in [
            [Stance.BUY, Stance.BUY, Stance.BUY],
            [Stance.SELL, Stance.SELL, Stance.SELL],
            [Stance.ABSTAIN, Stance.ABSTAIN, Stance.BUY],
            [Stance.STRONG_BUY, Stance.STRONG_SELL, Stance.HOLD],
        ]:
            verdicts = [_verdict(n, s) for n, s in zip(["opus", "gpt", "grok"], stances)]
            ruling = council.rule(verdicts)
            assert ruling.action in RulingAction

    def test_nerve_adjustment_is_finite(self):
        council = _council("opus", "gpt", "grok")
        for stances in [
            [Stance.BUY, Stance.BUY, Stance.BUY],
            [Stance.ABSTAIN, Stance.ABSTAIN, Stance.ABSTAIN],
            [Stance.STRONG_BUY, Stance.STRONG_SELL, Stance.HOLD],
        ]:
            verdicts = [_verdict(n, s) for n, s in zip(["opus", "gpt", "grok"], stances)]
            ruling = council.rule(verdicts)
            assert math.isfinite(ruling.nerve_adjustment), f"nerve_adjustment not finite: {ruling.nerve_adjustment}"
