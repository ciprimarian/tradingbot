"""
Adversarial spec: board-model council where vote weight reflects per-verdict reasoning quality.

Current model:  effective_weight = base_weight × adaptive_weight (historical hit rate)
Board model:    effective_weight = base_weight × reasoning_quality (per-verdict argument quality)

The thesis: a board member who shows up with specific data ("gap down 3.2%, RSI 28,
below 200MA, volume 2.1x average") should carry more weight than one who shows up with
a gut feeling ("looks bullish"). Quality of argument — not seniority — drives the outcome.

This file is a spec. Tests marked xfail require three additions to production code:
  1. AdvisorVerdict.reasoning_quality: float | None = None
     — If set: council uses it directly.
     — If None: council auto-scores via _score_reasoning().
  2. Council._score_reasoning(text: str) -> float
     — Heuristic: 0.0–1.0 based on specificity (numbers, indicators, price levels).
  3. Council.rule() uses reasoning_quality in effective weight:
     effective_weight = base_weight × clamp(reasoning_quality, 0.05, 1.0)
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest

from src.fuzzi.brain.advisor import Advisor, AdvisorRole, AdvisorVerdict, Stance
from src.fuzzi.brain.council import Council, DissentPattern, RulingAction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dt() -> datetime:
    return datetime.now(timezone.utc)


def _advisor(name: str, role: AdvisorRole, weight: float = 0.33) -> Advisor:
    return Advisor(name=name, role=role, provider=None, weight=weight)


def _verdict(
    advisor_name: str,
    role: AdvisorRole,
    stance: Stance,
    confidence: float = 0.9,
    reasoning: str = "no reasoning",
    reasoning_quality: float | None = None,
) -> AdvisorVerdict:
    v = AdvisorVerdict(
        advisor_name=advisor_name,
        role=role,
        symbol="SPY",
        stance=stance,
        confidence=confidence,
        reasoning=reasoning,
    )
    if reasoning_quality is not None:
        v.reasoning_quality = reasoning_quality
    return v


def _council(weights: tuple[float, float, float] = (0.33, 0.33, 0.33)) -> Council:
    return Council(
        advisors=[
            _advisor("strategist", AdvisorRole.STRATEGIST, weights[0]),
            _advisor("analyst", AdvisorRole.ANALYST, weights[1]),
            _advisor("scout", AdvisorRole.SCOUT, weights[2]),
        ]
    )


# ---------------------------------------------------------------------------
# Batch B1 — AdvisorVerdict.reasoning_quality field contract
# ---------------------------------------------------------------------------

class TestAdvisorVerdictReasoningQualityField:
    @pytest.mark.xfail(
        reason="spec: AdvisorVerdict.reasoning_quality field does not yet exist",
        strict=True,
    )
    def test_reasoning_quality_field_exists_with_none_default(self):
        """AdvisorVerdict should have a reasoning_quality: float | None field defaulting to None."""
        v = AdvisorVerdict(
            advisor_name="strategist",
            role=AdvisorRole.STRATEGIST,
            symbol="SPY",
            stance=Stance.BUY,
            confidence=0.8,
            reasoning="some reasoning",
        )
        assert hasattr(v, "reasoning_quality")
        assert v.reasoning_quality is None

    @pytest.mark.xfail(
        reason="spec: AdvisorVerdict.reasoning_quality field does not yet exist",
        strict=True,
    )
    def test_reasoning_quality_can_be_set_to_float(self):
        """When set explicitly, reasoning_quality should be stored and retrievable."""
        v = AdvisorVerdict(
            advisor_name="analyst",
            role=AdvisorRole.ANALYST,
            symbol="SPY",
            stance=Stance.BUY,
            confidence=0.8,
            reasoning="RSI 28, below 200MA",
        )
        v.reasoning_quality = 0.75
        assert v.reasoning_quality == 0.75

    @pytest.mark.xfail(
        reason="spec: AdvisorVerdict.reasoning_quality field does not yet exist",
        strict=True,
    )
    def test_reasoning_quality_can_be_set_at_construction(self):
        """reasoning_quality should be accepted as a constructor parameter."""
        v = AdvisorVerdict(
            advisor_name="analyst",
            role=AdvisorRole.ANALYST,
            symbol="SPY",
            stance=Stance.STRONG_BUY,
            confidence=0.9,
            reasoning="gap down 3.2%, RSI 28, volume 2.1x",
            reasoning_quality=0.85,
        )
        assert math.isclose(v.reasoning_quality, 0.85)


# ---------------------------------------------------------------------------
# Batch B2 — Council._score_reasoning heuristic
# ---------------------------------------------------------------------------

class TestReasoningQualityScorer:
    @pytest.mark.xfail(
        reason="spec: Council._score_reasoning does not yet exist",
        strict=True,
    )
    def test_empty_string_scores_minimum(self):
        """Empty reasoning → lowest possible quality, not zero (floor prevents silence)."""
        council = _council()
        score = council._score_reasoning("")
        assert 0.0 < score <= 0.15, f"empty reasoning scored {score}, expected 0 < s <= 0.15"

    @pytest.mark.xfail(
        reason="spec: Council._score_reasoning does not yet exist",
        strict=True,
    )
    def test_none_scores_minimum(self):
        """None reasoning string → minimum score (guard against missing field)."""
        council = _council()
        score = council._score_reasoning(None)
        assert 0.0 < score <= 0.15

    @pytest.mark.xfail(
        reason="spec: Council._score_reasoning does not yet exist",
        strict=True,
    )
    def test_vague_sentiment_scores_low(self):
        """Pure sentiment without data ("looks bullish", "seems good") → low quality."""
        council = _council()
        vague_texts = [
            "looks bullish",
            "seems good to me",
            "I think buy",
            "positive momentum",
            "bearish vibes",
        ]
        for text in vague_texts:
            score = council._score_reasoning(text)
            assert score < 0.35, f"vague reasoning '{text}' scored {score}, expected < 0.35"

    @pytest.mark.xfail(
        reason="spec: Council._score_reasoning does not yet exist",
        strict=True,
    )
    def test_single_indicator_name_boosts_score(self):
        """Mentioning a technical indicator (RSI, MACD, MA) is better than pure sentiment."""
        council = _council()
        vague = council._score_reasoning("looks bullish")
        with_indicator = council._score_reasoning("RSI is oversold")
        assert with_indicator > vague

    @pytest.mark.xfail(
        reason="spec: Council._score_reasoning does not yet exist",
        strict=True,
    )
    def test_percentage_data_point_scores_medium_high(self):
        """A specific percentage ("down 3.2%", "gap of 2.5%") signals quantitative homework."""
        council = _council()
        score = council._score_reasoning("stock gapped down 3.2% at open")
        assert score >= 0.4, f"percentage mention scored {score}, expected >= 0.4"

    @pytest.mark.xfail(
        reason="spec: Council._score_reasoning does not yet exist",
        strict=True,
    )
    def test_rich_multi_indicator_reasoning_scores_high(self):
        """Multiple indicators + numbers + price levels → top-tier quality."""
        council = _council()
        rich = "gap down 3.2%, RSI 28, below 200MA at 415.20, volume 2.1x average — reversion setup"
        score = council._score_reasoning(rich)
        assert score >= 0.7, f"rich reasoning scored {score}, expected >= 0.7"

    @pytest.mark.xfail(
        reason="spec: Council._score_reasoning does not yet exist",
        strict=True,
    )
    def test_score_is_bounded_between_zero_and_one(self):
        """Score must always be in [0, 1] regardless of input content."""
        council = _council()
        inputs = [
            "",
            "a" * 5000,
            "RSI RSI RSI RSI RSI RSI RSI RSI",
            "42.1% 13.2% 99.9% 0.1% 55.5%",
            "buy buy buy buy buy BUY BUY",
        ]
        for text in inputs:
            score = council._score_reasoning(text)
            assert 0.0 <= score <= 1.0, f"score out of range: {score} for '{text[:50]}'"

    @pytest.mark.xfail(
        reason="spec: Council._score_reasoning does not yet exist",
        strict=True,
    )
    def test_score_is_deterministic(self):
        """Same reasoning text must always produce the same score."""
        council = _council()
        text = "gap down 2.8%, RSI 31, volume spike at 1.8x"
        scores = [council._score_reasoning(text) for _ in range(5)]
        assert all(s == scores[0] for s in scores), "score is not deterministic"

    @pytest.mark.xfail(
        reason="spec: Council._score_reasoning does not yet exist",
        strict=True,
    )
    def test_more_specific_data_points_score_higher(self):
        """Monotonic: adding more data references increases quality score."""
        council = _council()
        base = council._score_reasoning("gap down")
        with_pct = council._score_reasoning("gap down 2.8%")
        with_indicator = council._score_reasoning("gap down 2.8%, RSI 31")
        with_more = council._score_reasoning("gap down 2.8%, RSI 31, below 200MA, volume 1.8x")
        assert base < with_pct <= with_indicator <= with_more, (
            f"quality not monotonic: {base:.2f} < {with_pct:.2f} <= {with_indicator:.2f} <= {with_more:.2f}"
        )

    @pytest.mark.xfail(
        reason="spec: Council._score_reasoning does not yet exist",
        strict=True,
    )
    def test_recognised_indicator_names_boost_score(self):
        """Known indicator names (RSI, MACD, ATR, SMA, EMA, Bollinger) each boost quality."""
        council = _council()
        base = council._score_reasoning("price is low")
        indicators = ["RSI", "MACD", "ATR", "SMA", "EMA", "volume", "momentum"]
        for ind in indicators:
            score = council._score_reasoning(f"price is low and {ind} confirms")
            assert score > base, f"indicator '{ind}' did not boost score (base={base:.2f}, got={score:.2f})"

    @pytest.mark.xfail(
        reason="spec: Council._score_reasoning does not yet exist",
        strict=True,
    )
    def test_very_long_vague_text_does_not_inflate_score(self):
        """Padding with words shouldn't substitute for data — quality is about specificity."""
        council = _council()
        vague_long = "I think this is bullish because the market is going up " * 50
        score = council._score_reasoning(vague_long)
        assert score < 0.35, f"long vague text scored {score}, should not reward length alone"

    @pytest.mark.xfail(
        reason="spec: Council._score_reasoning does not yet exist",
        strict=True,
    )
    def test_unicode_and_special_chars_do_not_crash(self):
        """Scoring must not raise on non-ASCII input."""
        council = _council()
        texts = [
            "RSI 28 — bullish ↑ support at €415.00",
            "价格下跌 3.2%",
            "🚀 to the moon — RSI 15",
            "\x00\x01\x02",
        ]
        for text in texts:
            score = council._score_reasoning(text)
            assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# Batch B3 — Council uses reasoning_quality in effective weight
# ---------------------------------------------------------------------------

class TestBoardModelWeighting:
    @pytest.mark.xfail(
        reason="spec: council.rule() does not yet use reasoning_quality in weighting",
        strict=True,
    )
    def test_explicit_high_quality_verdict_outweighs_explicit_low_quality_same_stance(self):
        """
        Two advisors both say BUY with same stance and confidence.
        One has reasoning_quality=0.9, other has reasoning_quality=0.1.
        Their combined normalized score should be closer to the high-quality one's weight.
        """
        council = _council((0.33, 0.33, 0.33))

        high_q = AdvisorVerdict(
            advisor_name="strategist",
            role=AdvisorRole.STRATEGIST,
            symbol="SPY",
            stance=Stance.STRONG_BUY,
            confidence=0.9,
            reasoning="gap down 3.2%, RSI 28, below 200MA, volume 2.1x",
            reasoning_quality=0.9,
        )
        low_q = AdvisorVerdict(
            advisor_name="analyst",
            role=AdvisorRole.ANALYST,
            symbol="SPY",
            stance=Stance.STRONG_BUY,
            confidence=0.9,
            reasoning="looks bullish",
            reasoning_quality=0.1,
        )

        ruling = council.rule([high_q, low_q])
        # Board model: normalized score should be dominated by high_q (0.9 quality × 0.9 confidence)
        # vs low_q (0.1 quality × 0.9 confidence). Effective weight ratio ~9:1.
        # The normalized score should be close to high_q's contribution.
        assert ruling.action == RulingAction.BUY
        # Conviction should be high — dominated by the well-reasoned verdict
        assert ruling.conviction >= 0.5, (
            f"well-reasoned BUY should have high conviction, got {ruling.conviction}"
        )

    @pytest.mark.xfail(
        reason="spec: council.rule() does not yet use reasoning_quality in weighting",
        strict=True,
    )
    def test_specific_dissent_can_reverse_vague_majority(self):
        """
        The critical board-model scenario:
        Two advisors say BUY with vague reasoning (quality=0.1 each).
        One advisor says SELL with specific data (quality=0.95).

        Old model: 2v1 → BUY wins (majority).
        Board model: the specific SELL argument should dominate.

        This tests the core premise: 'whomever got their homework better carries more weight'.
        """
        council = _council((0.33, 0.33, 0.33))

        vague_buy_1 = AdvisorVerdict(
            advisor_name="strategist",
            role=AdvisorRole.STRATEGIST,
            symbol="SPY",
            stance=Stance.BUY,
            confidence=0.9,
            reasoning="looks bullish",
            reasoning_quality=0.1,
        )
        vague_buy_2 = AdvisorVerdict(
            advisor_name="analyst",
            role=AdvisorRole.ANALYST,
            symbol="SPY",
            stance=Stance.BUY,
            confidence=0.9,
            reasoning="trend is up",
            reasoning_quality=0.1,
        )
        specific_sell = AdvisorVerdict(
            advisor_name="scout",
            role=AdvisorRole.SCOUT,
            symbol="SPY",
            stance=Stance.STRONG_SELL,
            confidence=0.9,
            reasoning="head and shoulders confirmed — neckline break at 415.20, RSI 72 (overbought), "
                      "volume declining on last 3 up-days (distribution), ATR expanding = volatility risk",
            reasoning_quality=0.95,
        )

        ruling = council.rule([vague_buy_1, vague_buy_2, specific_sell])
        # Board model: effective weights ~0.033 : 0.033 : 0.314 (quality × base_weight)
        # Specific SELL carries ~82% of the vote → normalized score negative → SELL or HOLD
        assert ruling.action != RulingAction.BUY, (
            f"Board model should not buy when 2 vague BUYs face 1 specific SELL. "
            f"Got action={ruling.action}, conviction={ruling.conviction}"
        )

    @pytest.mark.xfail(
        reason="spec: council.rule() does not yet use reasoning_quality in weighting",
        strict=True,
    )
    def test_vague_unanimous_consensus_beaten_by_single_specific_voice(self):
        """
        Three unanimous vague BUYs vs one explicit high-quality SELL (injected separately).
        The high-quality solo should produce a ruling closer to SELL than the three vague BUYs.

        Tested as: unanimous vague = low conviction, single specific gets high conviction.
        """
        council = _council()
        vague_verdicts = [
            AdvisorVerdict(
                advisor_name=name, role=role, symbol="SPY",
                stance=Stance.BUY, confidence=0.8,
                reasoning="looks ok", reasoning_quality=0.05,
            )
            for name, role in [
                ("strategist", AdvisorRole.STRATEGIST),
                ("analyst", AdvisorRole.ANALYST),
                ("scout", AdvisorRole.SCOUT),
            ]
        ]
        ruling_vague = council.rule(vague_verdicts)

        specific_solo = [AdvisorVerdict(
            advisor_name="strategist",
            role=AdvisorRole.STRATEGIST,
            symbol="SPY",
            stance=Stance.STRONG_BUY,
            confidence=0.9,
            reasoning="gap down 4.1%, RSI 24 (extreme oversold), below lower Bollinger band, "
                      "volume 3.2x average — textbook mean reversion setup",
            reasoning_quality=0.92,
        )]
        ruling_specific = council.rule(specific_solo)
        # Need 2+ active verdicts, so this may hit SPARSE — let's use two:
        # Actually, 1 active verdict → SPARSE in current code. Let me use 2 verdicts,
        # one specific and one neutral abstain-equivalent at very low quality.
        neutral_low = AdvisorVerdict(
            advisor_name="analyst",
            role=AdvisorRole.ANALYST,
            symbol="SPY",
            stance=Stance.HOLD,
            confidence=0.5,
            reasoning="not sure",
            reasoning_quality=0.05,
        )
        ruling_specific = council.rule([specific_solo[0], neutral_low])

        # Specific solo conviction should exceed vague unanimous conviction
        assert ruling_specific.conviction > ruling_vague.conviction, (
            f"specific solo conviction {ruling_specific.conviction:.3f} "
            f"should exceed vague unanimous {ruling_vague.conviction:.3f}"
        )

    @pytest.mark.xfail(
        reason="spec: council.rule() does not yet use reasoning_quality in weighting",
        strict=True,
    )
    def test_equal_quality_verdicts_fall_back_to_confidence(self):
        """When reasoning quality is equal, confidence breaks the tie (same as current model)."""
        council = _council()
        high_conf = AdvisorVerdict(
            advisor_name="strategist",
            role=AdvisorRole.STRATEGIST,
            symbol="SPY",
            stance=Stance.BUY,
            confidence=0.95,
            reasoning="RSI oversold, gap down 2%",
            reasoning_quality=0.6,
        )
        low_conf = AdvisorVerdict(
            advisor_name="analyst",
            role=AdvisorRole.ANALYST,
            symbol="SPY",
            stance=Stance.SELL,
            confidence=0.3,
            reasoning="MACD cross, below support",
            reasoning_quality=0.6,
        )
        ruling = council.rule([high_conf, low_conf])
        # Equal quality → confidence dominates → BUY wins
        assert ruling.action == RulingAction.BUY

    @pytest.mark.xfail(
        reason="spec: council.rule() does not yet use reasoning_quality in weighting",
        strict=True,
    )
    def test_reasoning_quality_zero_makes_verdict_near_silent(self):
        """
        A verdict with reasoning_quality=0.0 (or near-zero) effectively abstains.
        Even if it says STRONG_BUY with 0.99 confidence, it shouldn't dominate.
        """
        council = _council()
        silent = AdvisorVerdict(
            advisor_name="strategist",
            role=AdvisorRole.STRATEGIST,
            symbol="SPY",
            stance=Stance.STRONG_BUY,
            confidence=0.99,
            reasoning="",
            reasoning_quality=0.0,
        )
        loud = AdvisorVerdict(
            advisor_name="analyst",
            role=AdvisorRole.ANALYST,
            symbol="SPY",
            stance=Stance.STRONG_SELL,
            confidence=0.7,
            reasoning="triple top confirmed, RSI 78, volume divergence, ATR spike",
            reasoning_quality=0.85,
        )
        ruling = council.rule([silent, loud])
        # Loud specific SELL should dominate the silent STRONG_BUY
        assert ruling.action != RulingAction.BUY, (
            f"zero-quality BUY should not override specific SELL: got {ruling.action}"
        )

    @pytest.mark.xfail(
        reason="spec: council.rule() does not yet use reasoning_quality in weighting",
        strict=True,
    )
    def test_metadata_includes_per_verdict_reasoning_quality(self):
        """Ruling metadata should expose per-verdict reasoning quality for audit trail."""
        council = _council()
        v1 = AdvisorVerdict(
            advisor_name="strategist",
            role=AdvisorRole.STRATEGIST,
            symbol="SPY",
            stance=Stance.BUY,
            confidence=0.8,
            reasoning="gap down 2.1%, RSI 30",
            reasoning_quality=0.7,
        )
        v2 = AdvisorVerdict(
            advisor_name="analyst",
            role=AdvisorRole.ANALYST,
            symbol="SPY",
            stance=Stance.BUY,
            confidence=0.8,
            reasoning="seems ok",
            reasoning_quality=0.15,
        )
        ruling = council.rule([v1, v2])
        # Metadata should contain quality scores so the pit can log and audit
        assert "reasoning_qualities" in ruling.metadata or "quality_scores" in ruling.metadata, (
            "ruling metadata should expose per-verdict reasoning quality for audit"
        )


# ---------------------------------------------------------------------------
# Batch B4 — Auto-scoring (reasoning_quality=None → use _score_reasoning)
# ---------------------------------------------------------------------------

class TestAutoScoring:
    @pytest.mark.xfail(
        reason="spec: auto-scoring via _score_reasoning not yet wired into council.rule()",
        strict=True,
    )
    def test_none_quality_triggers_auto_score(self):
        """
        When reasoning_quality is None, council calls _score_reasoning(reasoning)
        and uses the result. Two verdicts with same stance but different reasoning
        text should produce different effective weights.
        """
        council = _council()
        specific = AdvisorVerdict(
            advisor_name="strategist",
            role=AdvisorRole.STRATEGIST,
            symbol="SPY",
            stance=Stance.STRONG_BUY,
            confidence=0.9,
            reasoning="gap down 3.2%, RSI 24, below 200MA, volume 2.8x average",
            # reasoning_quality=None (auto)
        )
        vague = AdvisorVerdict(
            advisor_name="analyst",
            role=AdvisorRole.ANALYST,
            symbol="SPY",
            stance=Stance.HOLD,
            confidence=0.9,
            reasoning="meh",
            # reasoning_quality=None (auto)
        )
        # If auto-scoring works, specific reasoning pulls toward BUY despite HOLD opponent
        ruling = council.rule([specific, vague])
        # The specific STRONG_BUY with 0.9 confidence should dominate the vague HOLD
        # even with auto-scoring (not explicit quality)
        assert ruling.action == RulingAction.BUY, (
            f"specific reasoning auto-score should dominate vague HOLD, got {ruling.action}"
        )

    @pytest.mark.xfail(
        reason="spec: auto-scoring via _score_reasoning not yet wired into council.rule()",
        strict=True,
    )
    def test_explicit_quality_overrides_auto_score(self):
        """
        When reasoning_quality is explicitly set, council uses it even if
        _score_reasoning would give a different value.

        Set quality=0.05 on a rich reasoning string → should still get 0.05 effective quality.
        """
        council = _council()
        explicitly_downgraded = AdvisorVerdict(
            advisor_name="strategist",
            role=AdvisorRole.STRATEGIST,
            symbol="SPY",
            stance=Stance.STRONG_BUY,
            confidence=0.99,
            reasoning="gap down 4%, RSI 20, Bollinger lower band, volume 3x, support held at 410",
            reasoning_quality=0.05,  # explicitly overridden to near-zero
        )
        strong_sell = AdvisorVerdict(
            advisor_name="analyst",
            role=AdvisorRole.ANALYST,
            symbol="SPY",
            stance=Stance.STRONG_SELL,
            confidence=0.7,
            reasoning="MACD bearish cross",
            reasoning_quality=0.6,  # modest but far above 0.05
        )
        ruling = council.rule([explicitly_downgraded, strong_sell])
        # Explicit 0.05 quality must override the rich reasoning text
        # effective_weight: strategist = 0.33×0.05=0.0165 vs analyst = 0.33×0.6=0.198
        # Normalized score heavily negative → SELL
        assert ruling.action != RulingAction.BUY, (
            f"explicit low quality must override rich reasoning text. Got {ruling.action}"
        )


# ---------------------------------------------------------------------------
# Batch B5 — Conviction reflects aggregate reasoning quality
# ---------------------------------------------------------------------------

class TestBoardModelConviction:
    @pytest.mark.xfail(
        reason="spec: conviction not yet modulated by reasoning quality",
        strict=True,
    )
    def test_unanimous_vague_has_lower_conviction_than_unanimous_specific(self):
        """
        The current model gives unanimous a 1.1x boost regardless of reasoning quality.
        Board model: unanimous high-quality should beat unanimous vague quality.
        """
        council = _council()
        vague_verdicts = [
            AdvisorVerdict(
                advisor_name=n, role=r, symbol="SPY",
                stance=Stance.BUY, confidence=0.9,
                reasoning="looks good", reasoning_quality=0.08,
            )
            for n, r in [
                ("strategist", AdvisorRole.STRATEGIST),
                ("analyst", AdvisorRole.ANALYST),
                ("scout", AdvisorRole.SCOUT),
            ]
        ]
        specific_verdicts = [
            AdvisorVerdict(
                advisor_name=n, role=r, symbol="SPY",
                stance=Stance.BUY, confidence=0.9,
                reasoning=f"RSI 28, gap down 3%, volume 2x, below 200MA — reversion signal ({n})",
                reasoning_quality=0.85,
            )
            for n, r in [
                ("strategist", AdvisorRole.STRATEGIST),
                ("analyst", AdvisorRole.ANALYST),
                ("scout", AdvisorRole.SCOUT),
            ]
        ]

        ruling_vague = council.rule(vague_verdicts)
        ruling_specific = council.rule(specific_verdicts)

        assert ruling_specific.conviction > ruling_vague.conviction, (
            f"specific unanimous conviction {ruling_specific.conviction:.3f} "
            f"should exceed vague unanimous {ruling_vague.conviction:.3f}"
        )

    @pytest.mark.xfail(
        reason="spec: conviction not yet modulated by reasoning quality",
        strict=True,
    )
    def test_high_quality_majority_has_higher_conviction_than_low_quality_majority(self):
        """2v1 with high-quality reasoning should be more convincing than 2v1 with vague reasoning."""
        council = _council()

        def _two_v_one(quality: float) -> float:
            v1 = AdvisorVerdict(
                advisor_name="strategist", role=AdvisorRole.STRATEGIST,
                symbol="SPY", stance=Stance.BUY, confidence=0.9,
                reasoning="gap down 2.5%, RSI 29" if quality > 0.5 else "looks up",
                reasoning_quality=quality,
            )
            v2 = AdvisorVerdict(
                advisor_name="analyst", role=AdvisorRole.ANALYST,
                symbol="SPY", stance=Stance.BUY, confidence=0.85,
                reasoning="volume 1.9x, below SMA20" if quality > 0.5 else "positive",
                reasoning_quality=quality,
            )
            v3 = AdvisorVerdict(
                advisor_name="scout", role=AdvisorRole.SCOUT,
                symbol="SPY", stance=Stance.SELL, confidence=0.7,
                reasoning="bearish divergence" if quality > 0.5 else "meh",
                reasoning_quality=quality,
            )
            return council.rule([v1, v2, v3]).conviction

        high_conviction = _two_v_one(0.85)
        low_conviction = _two_v_one(0.1)
        assert high_conviction > low_conviction, (
            f"high-quality 2v1 conviction {high_conviction:.3f} should beat "
            f"low-quality 2v1 {low_conviction:.3f}"
        )

    @pytest.mark.xfail(
        reason="spec: conviction not yet modulated by reasoning quality",
        strict=True,
    )
    def test_conviction_bounded_0_to_1_under_board_model(self):
        """Board model must not produce conviction outside [0, 1]."""
        council = _council()
        verdicts = [
            AdvisorVerdict(
                advisor_name=n, role=r, symbol="SPY",
                stance=Stance.STRONG_BUY, confidence=1.0,
                reasoning="perfect setup: RSI 10, gap 8%, volume 10x, all MAs aligned",
                reasoning_quality=1.0,
            )
            for n, r in [
                ("strategist", AdvisorRole.STRATEGIST),
                ("analyst", AdvisorRole.ANALYST),
                ("scout", AdvisorRole.SCOUT),
            ]
        ]
        ruling = council.rule(verdicts)
        assert 0.0 <= ruling.conviction <= 1.0


# ---------------------------------------------------------------------------
# Batch B6 — Board model vs old model comparison (documents the change)
# ---------------------------------------------------------------------------

class TestBoardModelVsOldModel:
    def test_old_model_ignores_reasoning_text_quality(self):
        """
        Documents the current behavior: council.rule() does not score reasoning text.
        The STRATEGIST with rich reasoning and the ANALYST with empty reasoning
        currently receive the same weight (both get advisor.adaptive_weight ≈ base_weight).

        This test PASSES on the old model and should continue to pass even after
        the board model is implemented (as a behavior-change marker).
        """
        council = _council()
        rich = AdvisorVerdict(
            advisor_name="strategist",
            role=AdvisorRole.STRATEGIST,
            symbol="SPY",
            stance=Stance.STRONG_BUY,
            confidence=0.9,
            reasoning="RSI 22, gap down 4.1%, below Bollinger lower band, volume 3x average",
        )
        vague = AdvisorVerdict(
            advisor_name="analyst",
            role=AdvisorRole.ANALYST,
            symbol="SPY",
            stance=Stance.STRONG_BUY,
            confidence=0.9,
            reasoning="",
        )
        # Old model: both have equal weight (0.33 each), equal stance × confidence
        # → unanimous STRONG_BUY → BUY ruling
        ruling = council.rule([rich, vague])
        # This should pass on the old model
        assert ruling.action == RulingAction.BUY

    @pytest.mark.xfail(
        reason="spec: board model not yet implemented — this documents the behavioral delta",
        strict=True,
    )
    def test_board_model_2v1_reversed_when_quality_inverted(self):
        """
        Old model: 2 STRONG_BUY vs 1 STRONG_SELL → BUY (2v1 majority always wins).
        Board model: if the 1 STRONG_SELL has far superior reasoning quality,
        the board should HOLD or SELL.

        This test captures exactly the behavioral gap between the two models.
        """
        council = _council((0.33, 0.33, 0.33))
        verdicts = [
            AdvisorVerdict(
                advisor_name="strategist",
                role=AdvisorRole.STRATEGIST,
                symbol="SPY",
                stance=Stance.STRONG_BUY,
                confidence=0.9,
                reasoning="looks bullish",
                reasoning_quality=0.08,
            ),
            AdvisorVerdict(
                advisor_name="analyst",
                role=AdvisorRole.ANALYST,
                symbol="SPY",
                stance=Stance.STRONG_BUY,
                confidence=0.9,
                reasoning="feels like an up day",
                reasoning_quality=0.08,
            ),
            AdvisorVerdict(
                advisor_name="scout",
                role=AdvisorRole.SCOUT,
                symbol="SPY",
                stance=Stance.STRONG_SELL,
                confidence=0.9,
                reasoning=(
                    "RSI 76 (overbought extreme), MACD negative divergence for 3 bars, "
                    "price 2.3 stddev above 200MA (historically mean-reverts), "
                    "volume shrinking on up-moves (distribution), ATR expanding = exit risk. "
                    "Bear flag forming on 1h chart with measured move target -4.2% from breakdown."
                ),
                reasoning_quality=0.96,
            ),
        ]
        ruling = council.rule(verdicts)
        # Effective weights: BUY×2 = 0.33×0.08×2 = 0.053, SELL = 0.33×0.96 = 0.317
        # SELL outweighs both BUYs combined → action should not be BUY
        assert ruling.action != RulingAction.BUY, (
            f"board model: specific SELL should outweigh 2 vague BUYs. Got {ruling.action}"
        )

    @pytest.mark.xfail(
        reason="spec: board model not yet implemented",
        strict=True,
    )
    def test_board_model_ruling_includes_quality_in_reasoning_string(self):
        """
        The reasoning string on the ruling should reflect that quality weighting occurred.
        E.g., 'council says sell — scout's reasoning (quality: 0.96) dominated'
        """
        council = _council()
        high_q = AdvisorVerdict(
            advisor_name="scout",
            role=AdvisorRole.SCOUT,
            symbol="SPY",
            stance=Stance.STRONG_SELL,
            confidence=0.9,
            reasoning="RSI 77, MACD divergence, volume fade on 3 up-days",
            reasoning_quality=0.88,
        )
        low_q = AdvisorVerdict(
            advisor_name="analyst",
            role=AdvisorRole.ANALYST,
            symbol="SPY",
            stance=Stance.BUY,
            confidence=0.9,
            reasoning="eh",
            reasoning_quality=0.05,
        )
        ruling = council.rule([high_q, low_q])
        # Ruling reasoning should mention quality or the dominant advisor
        assert any(
            word in ruling.reasoning.lower()
            for word in ["quality", "dominated", "scout", "reasoning"]
        ), f"ruling reasoning doesn't reflect quality weighting: '{ruling.reasoning}'"
