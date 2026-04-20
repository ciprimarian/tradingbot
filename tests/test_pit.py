from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from src.fuzzi.blotter import JsonlBlotter
from src.fuzzi.brain import Brain, BrainContext, BrainReview
from src.fuzzi.brain.gate import CouncilGate, CouncilGateRule, CouncilGateVerdict
from src.fuzzi.common.models import Bar, PortfolioSnapshot, Signal
from src.fuzzi.common.modes import RunMode
from src.fuzzi.config import load_settings
from src.fuzzi.pit import Pit
from src.fuzzi.runner import TradeRunner
from src.fuzzi.seatbelt import SimpleSeatbelt
from src.fuzzi.signals import GapReversionSource, SignalSource


class FixedSignalSource(SignalSource):
    name = "fixed"

    def __init__(self, signal: Signal | None) -> None:
        self.signal = signal

    def evaluate(self, symbol: str, bars: list[Bar]) -> Signal | None:
        return self.signal


class OverrideBrain(Brain):
    name = "override_brain"

    def __init__(self, direction: str, approved: bool = True, reason: str = "brain greenlights") -> None:
        self.direction = direction
        self.approved = approved
        self.reason = reason

    def evaluate(self, context: BrainContext) -> BrainReview:
        reviewed_signal = Signal(
            symbol=context.signal.symbol,
            direction=self.direction,
            confidence=context.signal.confidence,
            source=context.signal.source,
            timestamp=context.signal.timestamp,
            score=context.signal.score,
            notes=context.signal.notes,
            metadata=dict(context.signal.metadata),
        )
        reviewed_signal.metadata["brain_override"] = self.direction
        return BrainReview(
            approved=self.approved,
            signal=reviewed_signal,
            reason=self.reason,
            source=self.name,
            created_at=datetime.now(timezone.utc),
            metadata={"override": self.direction},
        )


class DirectionBlockRule(CouncilGateRule):
    name = "no_shorts"

    def __init__(self, blocked_direction: str) -> None:
        self.blocked_direction = blocked_direction

    def review(self, context: BrainContext, review: BrainReview) -> CouncilGateVerdict | None:
        if review.signal.direction == self.blocked_direction:
            return CouncilGateVerdict(
                approved=False,
                reason=f"council blocks {self.blocked_direction}",
                created_at=datetime.now(timezone.utc),
                source=self.name,
                metadata={"direction": self.blocked_direction},
            )
        return None


def _bar_series(symbol: str, yesterday_close: float, today_open: float, today_close: float) -> list[Bar]:
    now = datetime.now(timezone.utc)
    return [
        Bar(
            symbol=symbol,
            timestamp=now - timedelta(days=1),
            open=yesterday_close,
            high=yesterday_close,
            low=yesterday_close,
            close=yesterday_close,
            volume=1000,
        ),
        Bar(
            symbol=symbol,
            timestamp=now,
            open=today_open,
            high=max(today_open, today_close),
            low=min(today_open, today_close),
            close=today_close,
            volume=1500,
        ),
    ]


def test_pit_tick_with_no_signal_sources_returns_empty_decisions(tmp_path):
    settings = load_settings()
    blotter = JsonlBlotter(tmp_path / "pit.jsonl")
    runner = TradeRunner(settings=settings, blotter=blotter)
    seatbelt = SimpleSeatbelt(settings)
    pit = Pit(settings=settings, runner=runner, seatbelt=seatbelt, blotter=blotter)

    decisions = __import__("asyncio").run(pit.tick({}))

    assert decisions == []
    payload = json.loads((tmp_path / "pit.jsonl").read_text(encoding="utf-8").strip())
    assert payload["entry_type"] == "tick"
    assert payload["notes"] == "quiet tape"


def test_pit_gap_signal_flows_through_seatbelt_and_runner(tmp_path):
    settings = load_settings()
    blotter = JsonlBlotter(tmp_path / "pit.jsonl")
    runner = TradeRunner(settings=settings, blotter=blotter)
    seatbelt = SimpleSeatbelt(settings)
    pit = Pit(settings=settings, runner=runner, seatbelt=seatbelt, blotter=blotter)
    pit.register_source(GapReversionSource(gap_threshold=0.01))

    bars = {"SPY": _bar_series("SPY", yesterday_close=100.0, today_open=98.0, today_close=99.0)}
    decisions = __import__("asyncio").run(pit.tick(bars))

    assert len(decisions) == 1
    assert decisions[0].status == "simulated"

    lines = (tmp_path / "pit.jsonl").read_text(encoding="utf-8").strip().splitlines()
    payloads = [json.loads(line) for line in lines]
    assert payloads[0]["entry_type"] == "signal"
    assert payloads[1]["entry_type"] == "order_intent"
    assert payloads[2]["entry_type"] == "order_simulated"
    assert payloads[-1]["entry_type"] == "tick"


def test_nerve_moves_with_rejections_and_approvals(tmp_path):
    settings = load_settings()
    blotter = JsonlBlotter(tmp_path / "pit.jsonl")
    runner = TradeRunner(settings=settings, blotter=blotter)
    seatbelt = SimpleSeatbelt(settings)
    pit = Pit(settings=settings, runner=runner, seatbelt=seatbelt, blotter=blotter)

    rejection_signal = Signal(
        symbol="SPY",
        direction="sell",
        confidence=0.6,
        source="fixed",
        timestamp=datetime.now(timezone.utc),
    )
    pit.register_source(FixedSignalSource(rejection_signal))
    __import__("asyncio").run(pit.tick({"SPY": _bar_series("SPY", 100.0, 100.0, 100.0)}))
    assert pit.nerve == 0.45

    pit.signal_sources.clear()
    approval_signal = Signal(
        symbol="SPY",
        direction="buy",
        confidence=0.6,
        source="fixed",
        timestamp=datetime.now(timezone.utc),
    )
    pit.register_source(FixedSignalSource(approval_signal))
    __import__("asyncio").run(pit.tick({"SPY": _bar_series("SPY", 100.0, 100.0, 100.0)}))
    assert pit.nerve == 0.48


def test_low_nerve_halves_position_sizing(tmp_path):
    settings = load_settings()
    blotter = JsonlBlotter(tmp_path / "pit.jsonl")
    runner = TradeRunner(settings=settings, blotter=blotter)
    seatbelt = SimpleSeatbelt(settings)
    pit = Pit(settings=settings, runner=runner, seatbelt=seatbelt, blotter=blotter)
    pit.nerve = 0.25
    pit.portfolio = PortfolioSnapshot(
        timestamp=datetime.now(timezone.utc),
        cash=100.0,
        equity=100.0,
    )

    signal = Signal(
        symbol="SPY",
        direction="buy",
        confidence=0.7,
        source="fixed",
        timestamp=datetime.now(timezone.utc),
    )
    pit.register_source(FixedSignalSource(signal))

    __import__("asyncio").run(pit.tick({"SPY": _bar_series("SPY", 100.0, 100.0, 50.0)}))

    lines = (tmp_path / "pit.jsonl").read_text(encoding="utf-8").strip().splitlines()
    payloads = [json.loads(line) for line in lines]
    order_payload = next(item for item in payloads if item["entry_type"] == "order_intent")
    assert order_payload["payload"]["quantity"] == 0.25


def test_brain_can_override_signal_before_seatbelt(tmp_path):
    settings = load_settings()
    blotter = JsonlBlotter(tmp_path / "pit.jsonl")
    runner = TradeRunner(settings=settings, blotter=blotter)
    seatbelt = SimpleSeatbelt(settings)
    pit = Pit(settings=settings, runner=runner, seatbelt=seatbelt, blotter=blotter)
    pit.mount_brain(OverrideBrain(direction="buy"))
    pit.register_source(FixedSignalSource(
        Signal(
            symbol="SPY",
            direction="sell",
            confidence=0.6,
            source="fixed",
            timestamp=datetime.now(timezone.utc),
        )
    ))

    decisions = __import__("asyncio").run(pit.tick({"SPY": _bar_series("SPY", 100.0, 100.0, 100.0)}))

    assert len(decisions) == 1
    lines = (tmp_path / "pit.jsonl").read_text(encoding="utf-8").strip().splitlines()
    payloads = [json.loads(line) for line in lines]
    brain_payload = next(item for item in payloads if item["entry_type"] == "brain")
    assert brain_payload["payload"]["direction"] == "buy"


def test_council_can_veto_brain_approved_signal(tmp_path):
    settings = load_settings()
    blotter = JsonlBlotter(tmp_path / "pit.jsonl")
    runner = TradeRunner(settings=settings, blotter=blotter)
    seatbelt = SimpleSeatbelt(settings)
    pit = Pit(settings=settings, runner=runner, seatbelt=seatbelt, blotter=blotter)
    pit.mount_brain(OverrideBrain(direction="buy"))
    council = CouncilGate()
    council.register_rule(DirectionBlockRule(blocked_direction="buy"))
    pit.seat_council(council)
    pit.register_source(FixedSignalSource(
        Signal(
            symbol="SPY",
            direction="buy",
            confidence=0.6,
            source="fixed",
            timestamp=datetime.now(timezone.utc),
        )
    ))

    decisions = __import__("asyncio").run(pit.tick({"SPY": _bar_series("SPY", 100.0, 100.0, 100.0)}))

    assert decisions == []
    assert pit.nerve == 0.45
    lines = (tmp_path / "pit.jsonl").read_text(encoding="utf-8").strip().splitlines()
    payloads = [json.loads(line) for line in lines]
    assert any(item["entry_type"] == "council" for item in payloads)
