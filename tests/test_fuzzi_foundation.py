from datetime import datetime, timezone
import json

from src.fuzzi.blotter import JsonlBlotter
from src.fuzzi.common.models import OrderIntent, PortfolioSnapshot, Signal
from src.fuzzi.common.modes import RunMode
from src.fuzzi.config import load_settings
from src.fuzzi.runner import TradeRunner
from src.fuzzi.seatbelt import SimpleSeatbelt


def test_load_settings_defaults():
    settings = load_settings()

    assert settings.runtime.run_mode == RunMode.PAPER
    assert settings.runtime.trading_mode.value == "hybrid"
    assert settings.runtime.default_symbol
    assert settings.llm.auth_path == "~/.codex/auth.json"
    assert settings.llm.primary_model == "gpt-4o"
    assert settings.llm.fallback_model == "gpt-4o-mini"
    assert settings.llm.max_calls_per_tick == 3


def test_trade_runner_paper_mode_records_simulated_order(tmp_path):
    blotter = JsonlBlotter(tmp_path / "paper.jsonl")
    settings = load_settings()
    runner = TradeRunner(settings=settings, blotter=blotter)

    signal = Signal(
        symbol="SPY",
        direction="buy",
        confidence=0.72,
        source="test",
        timestamp=datetime.now(timezone.utc),
    )
    runner.record_signal(signal)

    decision = runner.submit_intent(
        OrderIntent(
            symbol="SPY",
            side="buy",
            quantity=1.25,
            order_type="market",
            mode="paper",
            source="test",
            created_at=datetime.now(timezone.utc),
        )
    )

    assert decision.status == "simulated"

    lines = (tmp_path / "paper.jsonl").read_text(encoding="utf-8").strip().splitlines()
    payloads = [json.loads(line) for line in lines]
    assert payloads[0]["entry_type"] == "signal"
    assert payloads[1]["entry_type"] == "order_intent"
    assert payloads[2]["entry_type"] == "order_simulated"


def test_trade_runner_ghost_mode_never_sends_orders(tmp_path):
    blotter = JsonlBlotter(tmp_path / "ghost.jsonl")
    settings = load_settings()
    settings.runtime.run_mode = RunMode.GHOST
    runner = TradeRunner(settings=settings, blotter=blotter)

    decision = runner.submit_intent(
        OrderIntent(
            symbol="QQQ",
            side="buy",
            quantity=10.0,
            order_type="market",
            mode="ghost",
            source="test",
            created_at=datetime.now(timezone.utc),
        )
    )

    assert decision.status == "skipped"
    assert "ghost mode" in decision.reason


def test_simple_seatbelt_approves_fractional_buy():
    settings = load_settings()
    seatbelt = SimpleSeatbelt(settings)

    signal = Signal(
        symbol="SPY",
        direction="buy",
        confidence=0.81,
        source="test",
        timestamp=datetime.now(timezone.utc),
    )
    portfolio = PortfolioSnapshot(
        timestamp=datetime.now(timezone.utc),
        cash=100.0,
        equity=100.0,
    )

    decision = seatbelt.review_signal(signal=signal, last_price=50.0, portfolio=portfolio)

    assert decision.approved is True
    assert decision.intent is not None
    assert decision.intent.quantity == 0.5


def test_simple_seatbelt_rejects_existing_position():
    settings = load_settings()
    seatbelt = SimpleSeatbelt(settings)

    signal = Signal(
        symbol="SPY",
        direction="buy",
        confidence=0.81,
        source="test",
        timestamp=datetime.now(timezone.utc),
    )
    portfolio = PortfolioSnapshot(
        timestamp=datetime.now(timezone.utc),
        cash=100.0,
        equity=100.0,
        positions={
            "SPY": {
                "quantity": 1.0,
            }
        },
    )

    decision = seatbelt.review_signal(signal=signal, last_price=50.0, portfolio=portfolio)

    assert decision.approved is False
    assert "already open" in decision.reason
