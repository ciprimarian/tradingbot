"""
Adversarial tests for JsonlBlotter and TradeRunner.

Attacks:
- Concurrent appends (file integrity under rapid writes)
- Malformed / None payloads
- Ghost vs Paper mode routing
- Runner idempotency (same intent twice)
- Blotter file path edge cases
- Entry type coverage
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.fuzzi.blotter.records import BlotterEntry, BlotterEntryType
from src.fuzzi.blotter.store import JsonlBlotter
from src.fuzzi.common.models import OrderIntent, Signal
from src.fuzzi.common.modes import RunMode
from src.fuzzi.config import load_settings
from src.fuzzi.runner.service import RunnerDecision, TradeRunner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dt() -> datetime:
    return datetime.now(timezone.utc)


def _entry(entry_type: BlotterEntryType = BlotterEntryType.NOTE) -> BlotterEntry:
    return BlotterEntry(
        entry_type=entry_type,
        mode=RunMode.PAPER,
        created_at=_dt(),
        source="test",
        payload={"key": "value"},
        notes="test note",
    )


def _intent(symbol: str = "SPY") -> OrderIntent:
    return OrderIntent(
        symbol=symbol,
        side="buy",
        quantity=1.0,
        order_type="market",
        mode="paper",
        source="test",
        created_at=_dt(),
        notes="test intent",
    )


# ---------------------------------------------------------------------------
# Batch 6a — JsonlBlotter file operations
# ---------------------------------------------------------------------------

class TestBlotterFileOps:
    def test_creates_file_on_first_append(self, tmp_path):
        path = tmp_path / "blotter.jsonl"
        assert not path.exists()
        blotter = JsonlBlotter(path)
        blotter.append(_entry())
        assert path.exists()

    def test_creates_parent_directories(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "blotter.jsonl"
        blotter = JsonlBlotter(path)
        blotter.append(_entry())
        assert path.exists()

    def test_appends_are_newline_separated(self, tmp_path):
        path = tmp_path / "b.jsonl"
        blotter = JsonlBlotter(path)
        blotter.append(_entry())
        blotter.append(_entry())
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 2

    def test_each_line_is_valid_json(self, tmp_path):
        path = tmp_path / "b.jsonl"
        blotter = JsonlBlotter(path)
        for _ in range(5):
            blotter.append(_entry())
        for line in path.read_text().strip().splitlines():
            parsed = json.loads(line)
            assert isinstance(parsed, dict)

    def test_multiple_entry_types_all_serialise(self, tmp_path):
        path = tmp_path / "b.jsonl"
        blotter = JsonlBlotter(path)
        for et in BlotterEntryType:
            blotter.append(BlotterEntry(
                entry_type=et, mode=RunMode.PAPER, created_at=_dt(),
                source="test", payload={}, notes="",
            ))
        lines = path.read_text().strip().splitlines()
        assert len(lines) == len(BlotterEntryType)

    def test_datetime_serialises_as_iso_string(self, tmp_path):
        path = tmp_path / "b.jsonl"
        blotter = JsonlBlotter(path)
        blotter.append(_entry())
        data = json.loads(path.read_text().strip())
        assert isinstance(data["created_at"], str)
        # Must be a valid ISO datetime string
        datetime.fromisoformat(data["created_at"])

    def test_enum_values_serialise_as_strings(self, tmp_path):
        path = tmp_path / "b.jsonl"
        blotter = JsonlBlotter(path)
        blotter.append(_entry(BlotterEntryType.SIGNAL))
        data = json.loads(path.read_text().strip())
        assert data["entry_type"] == "signal"
        assert data["mode"] == "paper"

    def test_complex_nested_payload_serialises(self, tmp_path):
        path = tmp_path / "b.jsonl"
        blotter = JsonlBlotter(path)
        entry = BlotterEntry(
            entry_type=BlotterEntryType.TICK,
            mode=RunMode.PAPER,
            created_at=_dt(),
            source="pit",
            payload={"nested": {"key": [1, 2, 3]}, "ts": _dt()},
        )
        blotter.append(entry)
        data = json.loads(path.read_text().strip())
        assert data["payload"]["nested"]["key"] == [1, 2, 3]

    def test_empty_payload_serialises(self, tmp_path):
        path = tmp_path / "b.jsonl"
        blotter = JsonlBlotter(path)
        entry = BlotterEntry(
            entry_type=BlotterEntryType.NOTE,
            mode=RunMode.GHOST,
            created_at=_dt(),
            source="test",
        )
        blotter.append(entry)
        data = json.loads(path.read_text().strip())
        assert data["payload"] == {}

    def test_many_rapid_appends_all_survive(self, tmp_path):
        """Rapid sequential appends must not corrupt the file."""
        path = tmp_path / "b.jsonl"
        blotter = JsonlBlotter(path)
        n = 100
        for i in range(n):
            blotter.append(BlotterEntry(
                entry_type=BlotterEntryType.TICK, mode=RunMode.PAPER,
                created_at=_dt(), source="stress", payload={"i": i},
            ))
        lines = path.read_text().strip().splitlines()
        assert len(lines) == n
        for i, line in enumerate(lines):
            data = json.loads(line)
            assert data["payload"]["i"] == i


# ---------------------------------------------------------------------------
# Batch 6b — TradeRunner mode routing
# ---------------------------------------------------------------------------

class TestRunnerModeRouting:
    def test_paper_mode_returns_simulated_status(self, tmp_path):
        settings = load_settings()
        blotter = JsonlBlotter(tmp_path / "r.jsonl")
        runner = TradeRunner(settings=settings, blotter=blotter)
        decision = runner.submit_intent(_intent())
        assert decision.status == "simulated"
        assert decision.mode == RunMode.PAPER

    def test_paper_mode_logs_order_simulated_entry(self, tmp_path):
        settings = load_settings()
        blotter = JsonlBlotter(tmp_path / "r.jsonl")
        runner = TradeRunner(settings=settings, blotter=blotter)
        runner.submit_intent(_intent("AAPL"))
        lines = (tmp_path / "r.jsonl").read_text().strip().splitlines()
        types = [json.loads(l)["entry_type"] for l in lines]
        assert "order_intent" in types
        assert "order_simulated" in types

    def test_ghost_mode_returns_skipped_status(self, tmp_path):
        settings = load_settings()
        settings.runtime.run_mode = RunMode.GHOST
        blotter = JsonlBlotter(tmp_path / "r.jsonl")
        runner = TradeRunner(settings=settings, blotter=blotter)
        decision = runner.submit_intent(_intent())
        assert decision.status == "skipped"
        assert decision.mode == RunMode.GHOST

    def test_ghost_mode_never_logs_simulated(self, tmp_path):
        settings = load_settings()
        settings.runtime.run_mode = RunMode.GHOST
        blotter = JsonlBlotter(tmp_path / "r.jsonl")
        runner = TradeRunner(settings=settings, blotter=blotter)
        runner.submit_intent(_intent())
        lines = (tmp_path / "r.jsonl").read_text().strip().splitlines()
        types = [json.loads(l)["entry_type"] for l in lines]
        assert "order_simulated" not in types
        assert "order_skipped" in types

    def test_record_signal_logs_signal_entry(self, tmp_path):
        settings = load_settings()
        blotter = JsonlBlotter(tmp_path / "r.jsonl")
        runner = TradeRunner(settings=settings, blotter=blotter)
        signal = Signal(
            symbol="SPY", direction="buy", confidence=0.8,
            source="test", timestamp=_dt(), score=0.03,
        )
        runner.record_signal(signal)
        data = json.loads((tmp_path / "r.jsonl").read_text().strip())
        assert data["entry_type"] == "signal"
        assert data["payload"]["symbol"] == "SPY"
        assert data["payload"]["direction"] == "buy"

    def test_submit_same_intent_twice_logs_two_entries(self, tmp_path):
        """Runner is not idempotent — submitting same intent twice logs two orders."""
        settings = load_settings()
        blotter = JsonlBlotter(tmp_path / "r.jsonl")
        runner = TradeRunner(settings=settings, blotter=blotter)
        intent = _intent("TSLA")
        runner.submit_intent(intent)
        runner.submit_intent(intent)
        lines = (tmp_path / "r.jsonl").read_text().strip().splitlines()
        simulated = [l for l in lines if json.loads(l)["entry_type"] == "order_simulated"]
        assert len(simulated) == 2, (
            "Runner submitted same intent twice → two order_simulated entries. "
            "There is no idempotency guard. The pit must not call submit_intent twice."
        )

    def test_decision_metadata_contains_symbol_and_side(self, tmp_path):
        settings = load_settings()
        blotter = JsonlBlotter(tmp_path / "r.jsonl")
        runner = TradeRunner(settings=settings, blotter=blotter)
        decision = runner.submit_intent(_intent("MSFT"))
        assert decision.metadata.get("symbol") == "MSFT"
        assert decision.metadata.get("side") == "buy"

    def test_decision_created_at_is_recent(self, tmp_path):
        settings = load_settings()
        blotter = JsonlBlotter(tmp_path / "r.jsonl")
        runner = TradeRunner(settings=settings, blotter=blotter)
        before = datetime.now(timezone.utc)
        decision = runner.submit_intent(_intent())
        after = datetime.now(timezone.utc)
        assert before <= decision.created_at <= after
