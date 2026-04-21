from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from src.fuzzi.blotter import BlotterEntry, BlotterEntryType, JsonlBlotter
from src.fuzzi.brain import Brain, BrainContext, BrainReview
from src.fuzzi.brain.gate import CouncilGate
from src.fuzzi.common.models import Bar, PortfolioSnapshot
from src.fuzzi.config import FuzziSettings
from src.fuzzi.nerve import NerveTracker
from src.fuzzi.runner import RunnerDecision, TradeRunner
from src.fuzzi.seatbelt import SimpleSeatbelt
from src.fuzzi.signals import SignalSource


class Pit:
    def __init__(
        self,
        settings: FuzziSettings,
        runner: TradeRunner,
        seatbelt: SimpleSeatbelt,
        blotter: JsonlBlotter,
    ) -> None:
        self.settings = settings
        self.runner = runner
        self.seatbelt = seatbelt
        self.blotter = blotter
        self.signal_sources: list[SignalSource] = []
        self.brain: Brain | None = None
        self.council: CouncilGate | None = None
        self.nerve = NerveTracker()
        self.portfolio = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            cash=100.0,
            equity=100.0,
        )
        self._running = False

    def register_source(self, source: SignalSource) -> None:
        self.signal_sources.append(source)

    def mount_brain(self, brain: Brain) -> None:
        self.brain = brain

    def seat_council(self, council: CouncilGate) -> None:
        self.council = council

    async def tick(self, bars: dict[str, list[Bar]]) -> list[RunnerDecision]:
        decisions: list[RunnerDecision] = []

        if not self.signal_sources:
            self._log_tick(symbols=len(bars), signals=0, approvals=0, rejections=0, notes="quiet tape")
            return decisions

        approvals = 0
        rejections = 0
        signals_seen = 0

        for symbol, history in bars.items():
            if not history:
                continue

            for source in self.signal_sources:
                signal = source.evaluate(symbol, history)
                if signal is None:
                    continue

                signals_seen += 1
                self.runner.record_signal(signal)

                sizing_multiplier = self.nerve.sizing_multiplier
                reviewed_signal = signal
                brain_context = BrainContext(
                    symbol=symbol,
                    bars=history,
                    signal=signal,
                    nerve=self.nerve.state().global_nerve,
                    portfolio=self.portfolio,
                    sizing_multiplier=sizing_multiplier,
                )
                brain_review = self._run_brain(brain_context)
                if brain_review is not None:
                    reviewed_signal = brain_review.signal
                    if not brain_review.approved:
                        rejections += 1
                        self.nerve.record_rejection(source.name)
                        self._log_note(source.name, symbol, brain_review.reason)
                        continue

                    council_verdict = self._run_council(brain_context, brain_review)
                    if council_verdict is not None and not council_verdict.approved:
                        rejections += 1
                        self.nerve.record_rejection(source.name)
                        self._log_note(council_verdict.source, symbol, council_verdict.reason)
                        continue

                decision = self.seatbelt.review_signal(
                    signal=reviewed_signal,
                    last_price=history[-1].close,
                    portfolio=self.portfolio,
                    context={"sizing_multiplier": sizing_multiplier, "nerve": self.nerve},
                )

                if not decision.approved or decision.intent is None:
                    rejections += 1
                    self.nerve.record_rejection(source.name)
                    self._log_note(source.name, symbol, decision.reason)
                    continue

                approvals += 1
                runner_decision = self.runner.submit_intent(decision.intent)
                decisions.append(runner_decision)

        self._log_tick(
            symbols=len(bars),
            signals=signals_seen,
            approvals=approvals,
            rejections=rejections,
            notes=self.nerve.state().summary(),
        )
        return decisions

    async def run(self, interval_seconds: int = 60) -> None:
        self._running = True
        while self._running:
            await self.tick({})
            await asyncio.sleep(interval_seconds)

    def stop(self) -> None:
        self._running = False

    def _log_tick(
        self,
        symbols: int,
        signals: int,
        approvals: int,
        rejections: int,
        notes: str,
    ) -> None:
        self.blotter.append(
            BlotterEntry(
                entry_type=BlotterEntryType.TICK,
                mode=self.settings.runtime.run_mode,
                created_at=datetime.now(timezone.utc),
                source="pit",
                payload={
                    "symbols": symbols,
                    "signals": signals,
                    "approvals": approvals,
                    "rejections": rejections,
                    "nerve": self.nerve.state().global_nerve,
                },
                notes=notes,
            )
        )

    def _run_brain(self, context: BrainContext) -> BrainReview | None:
        if self.brain is None:
            return None

        review = self.brain.evaluate(context)
        self.blotter.append(
            BlotterEntry(
                entry_type=BlotterEntryType.BRAIN,
                mode=self.settings.runtime.run_mode,
                created_at=review.created_at,
                source=review.source,
                payload={
                    "symbol": context.symbol,
                    "approved": review.approved,
                    "direction": review.signal.direction,
                    "confidence": review.signal.confidence,
                    "metadata": review.metadata,
                },
                notes=review.reason,
            )
        )
        return review

    def _run_council(self, context: BrainContext, review: BrainReview):
        if self.council is None:
            return None

        verdict = self.council.deliberate(context, review)
        self.blotter.append(
            BlotterEntry(
                entry_type=BlotterEntryType.COUNCIL,
                mode=self.settings.runtime.run_mode,
                created_at=verdict.created_at,
                source=verdict.source,
                payload={
                    "symbol": context.symbol,
                    "approved": verdict.approved,
                    "metadata": verdict.metadata,
                },
                notes=verdict.reason,
            )
        )
        return verdict

    def _log_note(self, source: str, symbol: str, reason: str) -> None:
        self.blotter.append(
            BlotterEntry(
                entry_type=BlotterEntryType.NOTE,
                mode=self.settings.runtime.run_mode,
                created_at=datetime.now(timezone.utc),
                source=source,
                payload={"symbol": symbol, "reason": reason, "nerve": self.nerve.state().global_nerve},
                notes=reason,
            )
        )

    def record_outcome(
        self,
        strategy: str,
        pnl: float,
        *,
        symbol: str | None = None,
        notes: str = "",
    ) -> None:
        if pnl > 0:
            self.nerve.record_win(strategy, pnl=pnl)
            outcome_note = notes or "realized win"
        elif pnl < 0:
            self.nerve.record_loss(strategy, pnl=pnl)
            outcome_note = notes or "realized loss"
        else:
            outcome_note = notes or "flat close"

        self.blotter.append(
            BlotterEntry(
                entry_type=BlotterEntryType.OUTCOME,
                mode=self.settings.runtime.run_mode,
                created_at=datetime.now(timezone.utc),
                source=strategy,
                payload={
                    "symbol": symbol,
                    "pnl": pnl,
                    "nerve": self.nerve.state().global_nerve,
                },
                notes=outcome_note,
            )
        )
