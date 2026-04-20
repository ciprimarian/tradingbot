from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

from src.fuzzi.common.models import OrderIntent, PortfolioSnapshot, Signal
from src.fuzzi.config import FuzziSettings


@dataclass(slots=True)
class SeatbeltDecision:
    approved: bool
    reason: str
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    intent: OrderIntent | None = None


class SimpleSeatbelt:
    """First-pass risk rails for small-capital paper and ghost runs."""

    def __init__(self, settings: FuzziSettings) -> None:
        self.settings = settings

    def review_signal(
        self,
        signal: Signal,
        last_price: float,
        portfolio: PortfolioSnapshot,
        context: Dict[str, Any] | None = None,
    ) -> SeatbeltDecision:
        now = datetime.now(timezone.utc)
        context = context or {}
        sizing_multiplier = float(context.get("sizing_multiplier", 1.0))
        sizing_multiplier = max(0.1, min(sizing_multiplier, 1.0))

        if self.settings.risk.long_only and signal.direction.lower() != "buy":
            return SeatbeltDecision(
                approved=False,
                reason="seatbelt is long-only for v1",
                created_at=now,
                metadata={"direction": signal.direction},
            )

        if signal.symbol in portfolio.positions:
            return SeatbeltDecision(
                approved=False,
                reason="position already open for symbol",
                created_at=now,
                metadata={"symbol": signal.symbol},
            )

        if len(portfolio.positions) >= self.settings.risk.max_open_positions:
            return SeatbeltDecision(
                approved=False,
                reason="max open positions reached",
                created_at=now,
                metadata={"max_open_positions": self.settings.risk.max_open_positions},
            )

        spendable_cash = max(portfolio.cash - self.settings.risk.min_cash_buffer, 0.0)
        capped_notional = self.settings.risk.max_position_notional * sizing_multiplier
        notional = min(capped_notional, spendable_cash)
        if notional <= 0:
            return SeatbeltDecision(
                approved=False,
                reason="not enough free cash after buffer",
                created_at=now,
                metadata={
                    "cash": portfolio.cash,
                    "buffer": self.settings.risk.min_cash_buffer,
                    "sizing_multiplier": sizing_multiplier,
                },
            )

        if last_price <= 0:
            return SeatbeltDecision(
                approved=False,
                reason="invalid last price",
                created_at=now,
                metadata={"last_price": last_price},
            )

        quantity = round(notional / last_price, 6)
        if quantity <= 0:
            return SeatbeltDecision(
                approved=False,
                reason="calculated quantity is zero",
                created_at=now,
                metadata={"notional": notional, "last_price": last_price},
            )

        intent = OrderIntent(
            symbol=signal.symbol,
            side="buy",
            quantity=quantity,
            order_type="market",
            mode=self.settings.runtime.run_mode.value,
            source=signal.source,
            created_at=now,
            notes=f"seatbelt-approved notional={notional:.2f}",
            metadata={
                "confidence": signal.confidence,
                "score": signal.score,
                "notional": notional,
                "sizing_multiplier": sizing_multiplier,
            },
        )
        return SeatbeltDecision(
            approved=True,
            reason="approved",
            created_at=now,
            metadata={
                "notional": notional,
                "quantity": quantity,
                "sizing_multiplier": sizing_multiplier,
            },
            intent=intent,
        )
