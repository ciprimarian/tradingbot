"""Tests for the Fuzzi brain layer — advisors, council, and consensus."""

import asyncio
import json
from datetime import datetime, timezone

import pytest

from src.fuzzi.brain.advisor import Advisor, AdvisorRole, AdvisorVerdict, Stance
from src.fuzzi.brain.council import Council, CouncilRuling, DissentPattern, RulingAction
from src.fuzzi.brain.providers import MockProvider
from src.fuzzi.common.models import Bar, PortfolioSnapshot, Signal


def _make_bars(n: int = 10, base_price: float = 100.0) -> list[Bar]:
    """Generate synthetic bars."""
    bars = []
    for i in range(n):
        price = base_price + i * 0.5
        bars.append(Bar(
            symbol="SPY",
            timestamp=datetime(2026, 4, 1 + i, tzinfo=timezone.utc),
            open=price,
            high=price + 1.0,
            low=price - 0.5,
            close=price + 0.3,
            volume=1_000_000.0 + i * 10000,
        ))
    return bars


def _make_portfolio(cash: float = 100.0) -> PortfolioSnapshot:
    return PortfolioSnapshot(
        timestamp=datetime.now(timezone.utc),
        cash=cash,
        equity=cash,
    )


def _make_advisor(name: str, role: AdvisorRole, response: str, weight: float = 0.33) -> Advisor:
    provider = MockProvider(response=response)
    return Advisor(name=name, role=role, provider=provider, weight=weight)


class TestAdvisor:
    def test_advisor_parses_valid_json_response(self):
        response = json.dumps({
            "stance": "buy",
            "confidence": 0.8,
            "reasoning": "momentum is strong",
            "flags": [],
        })
        advisor = _make_advisor("opus", AdvisorRole.STRATEGIST, response)

        verdict = asyncio.run(advisor.consult(
            symbol="SPY",
            bars=_make_bars(),
            portfolio=_make_portfolio(),
            signals=[],
        ))

        assert verdict.stance == Stance.BUY
        assert verdict.confidence == 0.8
        assert "momentum" in verdict.reasoning
        assert verdict.advisor_name == "opus"

    def test_advisor_handles_markdown_wrapped_json(self):
        response = "```json\n" + json.dumps({
            "stance": "sell",
            "confidence": 0.6,
            "reasoning": "overextended",
            "flags": ["extended_move"],
        }) + "\n```"
        advisor = _make_advisor("gpt", AdvisorRole.ANALYST, response)

        verdict = asyncio.run(advisor.consult(
            symbol="QQQ",
            bars=_make_bars(),
            portfolio=_make_portfolio(),
            signals=[],
        ))

        assert verdict.stance == Stance.SELL
        assert verdict.confidence == 0.6

    def test_advisor_abstains_on_garbage_response(self):
        advisor = _make_advisor("grok", AdvisorRole.SCOUT, "lol idk man just buy it")

        verdict = asyncio.run(advisor.consult(
            symbol="SPY",
            bars=_make_bars(),
            portfolio=_make_portfolio(),
            signals=[],
        ))

        assert verdict.stance == Stance.ABSTAIN
        assert verdict.confidence == 0.0
        assert "parse_error" in verdict.flags

    def test_advisor_abstains_on_provider_error(self):
        class BrokenProvider:
            async def complete(self, **kwargs):
                raise ConnectionError("API down")

        advisor = Advisor(
            name="broken",
            role=AdvisorRole.ANALYST,
            provider=BrokenProvider(),
        )

        verdict = asyncio.run(advisor.consult(
            symbol="SPY",
            bars=_make_bars(),
            portfolio=_make_portfolio(),
            signals=[],
        ))

        assert verdict.stance == Stance.ABSTAIN
        assert "provider_error" in verdict.flags

    def test_advisor_tracks_hit_rate(self):
        advisor = _make_advisor("opus", AdvisorRole.STRATEGIST, "{}")

        advisor.record_outcome(True)
        advisor.record_outcome(True)
        advisor.record_outcome(False)

        assert advisor.hit_rate == pytest.approx(2 / 3, rel=0.01)

    def test_adaptive_weight_scales_with_accuracy(self):
        advisor = _make_advisor("opus", AdvisorRole.STRATEGIST, "{}", weight=0.4)

        # Perfect track record → 1.5x weight
        for _ in range(10):
            advisor.record_outcome(True)
        assert advisor.adaptive_weight == pytest.approx(0.4 * 1.5)

        # Reset with 50% accuracy → 1.0x weight
        advisor._track_record = [True, False] * 5
        assert advisor.adaptive_weight == pytest.approx(0.4 * 1.0)


class TestCouncil:
    def _make_verdict(self, name: str, role: AdvisorRole, stance: Stance, confidence: float) -> AdvisorVerdict:
        return AdvisorVerdict(
            advisor_name=name,
            role=role,
            symbol="SPY",
            stance=stance,
            confidence=confidence,
            reasoning="test",
        )

    def test_unanimous_buy_produces_high_conviction(self):
        advisors = [
            _make_advisor("opus", AdvisorRole.STRATEGIST, "{}"),
            _make_advisor("gpt", AdvisorRole.ANALYST, "{}"),
            _make_advisor("grok", AdvisorRole.SCOUT, "{}"),
        ]
        council = Council(advisors)

        verdicts = [
            self._make_verdict("opus", AdvisorRole.STRATEGIST, Stance.BUY, 0.8),
            self._make_verdict("gpt", AdvisorRole.ANALYST, Stance.BUY, 0.7),
            self._make_verdict("grok", AdvisorRole.SCOUT, Stance.BUY, 0.75),
        ]

        ruling = council.rule(verdicts)

        assert ruling.action == RulingAction.BUY
        assert ruling.dissent == DissentPattern.UNANIMOUS
        assert ruling.conviction > 0.5
        assert ruling.should_act is True

    def test_strategist_veto_forces_hold(self):
        advisors = [
            _make_advisor("opus", AdvisorRole.STRATEGIST, "{}", weight=0.4),
            _make_advisor("gpt", AdvisorRole.ANALYST, "{}", weight=0.3),
            _make_advisor("grok", AdvisorRole.SCOUT, "{}", weight=0.3),
        ]
        council = Council(advisors)

        verdicts = [
            self._make_verdict("opus", AdvisorRole.STRATEGIST, Stance.STRONG_SELL, 0.9),
            self._make_verdict("gpt", AdvisorRole.ANALYST, Stance.BUY, 0.7),
            self._make_verdict("grok", AdvisorRole.SCOUT, Stance.BUY, 0.6),
        ]

        ruling = council.rule(verdicts)

        assert ruling.action == RulingAction.HOLD
        assert "vetoed" in ruling.reasoning

    def test_deadlock_produces_hold(self):
        advisors = [
            _make_advisor("opus", AdvisorRole.STRATEGIST, "{}"),
            _make_advisor("gpt", AdvisorRole.ANALYST, "{}"),
        ]
        council = Council(advisors)

        verdicts = [
            self._make_verdict("opus", AdvisorRole.STRATEGIST, Stance.BUY, 0.7),
            self._make_verdict("gpt", AdvisorRole.ANALYST, Stance.SELL, 0.7),
        ]

        ruling = council.rule(verdicts)

        # With equal opposing forces, conviction should be near zero
        assert ruling.conviction < 0.4
        assert ruling.should_act is False

    def test_social_manipulation_flag_caps_conviction(self):
        advisors = [
            _make_advisor("opus", AdvisorRole.STRATEGIST, "{}"),
            _make_advisor("gpt", AdvisorRole.ANALYST, "{}"),
            _make_advisor("grok", AdvisorRole.SCOUT, "{}"),
        ]
        council = Council(advisors)

        verdicts = [
            self._make_verdict("opus", AdvisorRole.STRATEGIST, Stance.BUY, 0.9),
            self._make_verdict("gpt", AdvisorRole.ANALYST, Stance.STRONG_BUY, 0.95),
            AdvisorVerdict(
                advisor_name="grok",
                role=AdvisorRole.SCOUT,
                symbol="SPY",
                stance=Stance.BUY,
                confidence=0.6,
                reasoning="social momentum but suspicious",
                flags=["pump_risk"],
            ),
        ]

        ruling = council.rule(verdicts)

        # Even with strong buy consensus, pump flag caps conviction
        assert ruling.conviction <= 0.5

    def test_all_abstain_produces_sparse_hold(self):
        advisors = [
            _make_advisor("opus", AdvisorRole.STRATEGIST, "{}"),
            _make_advisor("gpt", AdvisorRole.ANALYST, "{}"),
        ]
        council = Council(advisors)

        verdicts = [
            self._make_verdict("opus", AdvisorRole.STRATEGIST, Stance.ABSTAIN, 0.0),
            self._make_verdict("gpt", AdvisorRole.ANALYST, Stance.ABSTAIN, 0.0),
        ]

        ruling = council.rule(verdicts)

        assert ruling.action == RulingAction.HOLD
        assert ruling.dissent == DissentPattern.SPARSE

    def test_empty_verdicts_hold(self):
        council = Council([])
        ruling = council.rule([])

        assert ruling.action == RulingAction.HOLD
        assert ruling.conviction == 0.0
