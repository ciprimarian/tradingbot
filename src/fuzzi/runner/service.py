from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any

from src.fuzzi.blotter import BlotterEntry, BlotterEntryType, JsonlBlotter
from src.fuzzi.common.models import OrderIntent, Signal
from src.fuzzi.common.modes import RunMode
from src.fuzzi.config import FuzziSettings


@dataclass(slots=True)
class RunnerDecision:
    status: str
    mode: RunMode
    reason: str
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class TradeRunner:
    """Mode-aware order handling for paper and ghost flows."""

    def __init__(self, settings: FuzziSettings, blotter: JsonlBlotter) -> None:
        self.settings = settings
        self.blotter = blotter

    def record_signal(self, signal: Signal) -> None:
        self.blotter.append(
            BlotterEntry(
                entry_type=BlotterEntryType.SIGNAL,
                mode=self.settings.runtime.run_mode,
                created_at=signal.timestamp,
                source=signal.source,
                payload={
                    "symbol": signal.symbol,
                    "direction": signal.direction,
                    "confidence": signal.confidence,
                    "score": signal.score,
                    "metadata": signal.metadata,
                },
                notes=signal.notes,
            )
        )

    def submit_intent(self, intent: OrderIntent) -> RunnerDecision:
        now = datetime.now(timezone.utc)
        self.blotter.append(
            BlotterEntry(
                entry_type=BlotterEntryType.ORDER_INTENT,
                mode=self.settings.runtime.run_mode,
                created_at=now,
                source=intent.source,
                payload={
                    "symbol": intent.symbol,
                    "side": intent.side,
                    "quantity": intent.quantity,
                    "order_type": intent.order_type,
                    "limit_price": intent.limit_price,
                    "stop_price": intent.stop_price,
                    "metadata": intent.metadata,
                },
                notes=intent.notes,
            )
        )

        if self.settings.runtime.run_mode == RunMode.GHOST:
            decision = RunnerDecision(
                status="skipped",
                mode=RunMode.GHOST,
                reason="ghost mode never sends orders",
                created_at=now,
                metadata={"symbol": intent.symbol, "side": intent.side},
            )
            self.blotter.append(
                BlotterEntry(
                    entry_type=BlotterEntryType.ORDER_SKIPPED,
                    mode=decision.mode,
                    created_at=decision.created_at,
                    source=intent.source,
                    payload=decision.metadata,
                    notes=decision.reason,
                )
            )
            return decision

        if self.settings.runtime.run_mode == RunMode.PAPER:
            decision = RunnerDecision(
                status="simulated",
                mode=RunMode.PAPER,
                reason="paper mode records a simulated order only",
                created_at=now,
                metadata={"symbol": intent.symbol, "side": intent.side, "quantity": intent.quantity},
            )
            self.blotter.append(
                BlotterEntry(
                    entry_type=BlotterEntryType.ORDER_SIMULATED,
                    mode=decision.mode,
                    created_at=decision.created_at,
                    source=intent.source,
                    payload=decision.metadata,
                    notes=decision.reason,
                )
            )
            return decision

        decision = RunnerDecision(
            status="blocked",
            mode=self.settings.runtime.run_mode,
            reason="live order routing is not wired yet",
            created_at=now,
            metadata={"symbol": intent.symbol, "side": intent.side},
        )
        self.blotter.append(
            BlotterEntry(
                entry_type=BlotterEntryType.ORDER_SKIPPED,
                mode=decision.mode,
                created_at=decision.created_at,
                source=intent.source,
                payload=decision.metadata,
                notes=decision.reason,
            )
        )
        return decision

