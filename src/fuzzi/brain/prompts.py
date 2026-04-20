"""
Prompt engineering for each advisor role.

Each role gets a different framing of the same data. The strategist sees
risk and regime. The analyst sees numbers and patterns. The scout sees
momentum and crowd behavior.

Prompts are designed to elicit structured JSON responses with:
- stance (strong_buy/buy/lean_buy/hold/lean_sell/sell/strong_sell/abstain)
- confidence (0-1)
- reasoning (short text)
- flags (list of warnings)
"""

from __future__ import annotations

import json
from datetime import datetime

from src.fuzzi.brain.advisor import AdvisorRole
from src.fuzzi.common.models import Bar, PortfolioSnapshot, Signal


class PromptKit:
    """Builds role-appropriate prompts for LLM advisors."""

    @staticmethod
    def build(
        role: AdvisorRole,
        symbol: str,
        bars: list[Bar],
        portfolio: PortfolioSnapshot,
        signals: list[Signal],
        context: str = "",
    ) -> str:
        """Route to the appropriate prompt builder by role."""
        builders = {
            AdvisorRole.STRATEGIST: PromptKit._strategist_prompt,
            AdvisorRole.ANALYST: PromptKit._analyst_prompt,
            AdvisorRole.SCOUT: PromptKit._scout_prompt,
        }
        builder = builders[role]
        return builder(symbol, bars, portfolio, signals, context)

    @staticmethod
    def _format_bars(bars: list[Bar], limit: int = 20) -> str:
        """Format recent bars as a compact table."""
        recent = bars[-limit:] if len(bars) > limit else bars
        lines = ["date|open|high|low|close|volume"]
        for b in recent:
            date_str = b.timestamp.strftime("%Y-%m-%d") if isinstance(b.timestamp, datetime) else str(b.timestamp)
            lines.append(f"{date_str}|{b.open:.2f}|{b.high:.2f}|{b.low:.2f}|{b.close:.2f}|{int(b.volume)}")
        return "\n".join(lines)

    @staticmethod
    def _format_portfolio(portfolio: PortfolioSnapshot) -> str:
        """Compact portfolio summary."""
        parts = [
            f"cash: ${portfolio.cash:.2f}",
            f"equity: ${portfolio.equity:.2f}",
            f"positions: {len(portfolio.positions)}",
        ]
        if portfolio.positions:
            for sym, pos in portfolio.positions.items():
                if hasattr(pos, "unrealized_pnl"):
                    parts.append(f"  {sym}: qty={pos.quantity} pnl={pos.unrealized_pnl:.2f}")
                else:
                    parts.append(f"  {sym}: {pos}")
        return " | ".join(parts[:5])

    @staticmethod
    def _format_signals(signals: list[Signal]) -> str:
        """Compact existing signals."""
        if not signals:
            return "none"
        lines = []
        for s in signals[:5]:
            lines.append(f"{s.source}: {s.direction} conf={s.confidence:.2f}")
        return "; ".join(lines)

    @staticmethod
    def _response_schema() -> str:
        return """Respond ONLY with JSON:
{
  "stance": "strong_buy|buy|lean_buy|hold|lean_sell|sell|strong_sell|abstain",
  "confidence": 0.0 to 1.0,
  "reasoning": "1-2 sentences max",
  "flags": ["optional", "warning", "strings"]
}"""

    @staticmethod
    def _strategist_prompt(
        symbol: str,
        bars: list[Bar],
        portfolio: PortfolioSnapshot,
        signals: list[Signal],
        context: str,
    ) -> str:
        return f"""You are the Strategist for a trading system called Fuzzi.

Your job: assess regime, risk, and whether this is the right time to act.
You think in terms of: what could go wrong? Is the market environment favorable?
Are we overexposed? Is this signal trustworthy or noise?

You have veto power. If you see unacceptable risk, say so clearly.

## Symbol: {symbol}

## Recent price data:
{PromptKit._format_bars(bars)}

## Portfolio state:
{PromptKit._format_portfolio(portfolio)}

## Signals from other sources:
{PromptKit._format_signals(signals)}

## Additional context:
{context or "none"}

## Your assessment:
Consider:
- What regime is this? (trending, ranging, volatile, calm)
- Is this symbol extended or at a reasonable entry?
- Does the portfolio have room for this position?
- What's the risk/reward?
- Are the other signals trustworthy or conflicting?

{PromptKit._response_schema()}"""

    @staticmethod
    def _analyst_prompt(
        symbol: str,
        bars: list[Bar],
        portfolio: PortfolioSnapshot,
        signals: list[Signal],
        context: str,
    ) -> str:
        return f"""You are the Analyst for a trading system called Fuzzi.

Your job: quantitative assessment. Read the price action, identify patterns,
calculate key levels, spot momentum shifts. You deal in numbers and probabilities.

## Symbol: {symbol}

## Recent price data:
{PromptKit._format_bars(bars)}

## Portfolio state:
{PromptKit._format_portfolio(portfolio)}

## Signals from other sources:
{PromptKit._format_signals(signals)}

## Additional context:
{context or "none"}

## Your assessment:
Consider:
- Key support/resistance levels from this data
- Momentum direction and strength
- Volume patterns (accumulation or distribution?)
- Any recognizable chart patterns
- Statistical edge: is the expected move in our favor?

{PromptKit._response_schema()}"""

    @staticmethod
    def _scout_prompt(
        symbol: str,
        bars: list[Bar],
        portfolio: PortfolioSnapshot,
        signals: list[Signal],
        context: str,
    ) -> str:
        return f"""You are the Scout for a trading system called Fuzzi.

Your job: read the room. What's the narrative around this symbol?
Is there unusual attention, hype, fear, or manipulation signals?
You're the contrarian check — when everyone agrees, you get suspicious.

## Symbol: {symbol}

## Recent price data:
{PromptKit._format_bars(bars)}

## Signals from other sources:
{PromptKit._format_signals(signals)}

## Additional context:
{context or "none"}

## Your assessment:
Consider:
- Is this move driven by fundamentals or narrative/hype?
- Are retail traders piling in (potential reversal signal)?
- Any red flags: pump patterns, unusual volume without news, social media campaigns?
- Is the crowd positioned one way? (crowded trades revert)
- Contrarian signal: if everyone is bullish, be cautious

If you detect potential manipulation (pump & dump, coordinated social media),
add "manipulation_risk" or "pump_risk" to your flags array.

{PromptKit._response_schema()}"""
