# Trading Strategies

So here's the part where I explain the actual logic behind the trades. The "why are we buying or selling" stuff. This bot has a few different approaches to choosing trades, from dead simple to kind of fancy.

## Philosophy

Before we get into specifics, let me explain my overall thinking here. Trading is hard. Markets are weird and unpredictable. No single strategy works all the time. Some work in trending markets, some in sideways markets, some not at all. 

So instead of betting everything on one approach, I built a multi-agent system where different strategies each get a vote. Some use technical analysis, some use machine learning, some try to plan ahead. They argue with each other and hopefully the wisdom of the crowd prevents us from doing anything too stupid.

That said, here are the individual strategies and how they think.

## Simple Moving Average Crossover

The granddaddy of all trading strategies. Simple, classic, and honestly kind of dumb but it works more often than you'd think.

**The idea:** 
- Calculate two moving averages: a fast one (like 20-day) and a slow one (like 50-day)
- When the fast MA crosses above the slow MA, that's bullish—prices are accelerating up. Buy signal.
- When the fast MA crosses below the slow MA, that's bearish—prices are slowing down. Sell signal.

**Why it works (sometimes):**
Moving averages smooth out noise and show you the trend. When a short-term trend overtakes a longer-term trend, it suggests momentum is shifting. In trending markets this catches the move early.

**Why it fails:**
In choppy, sideways markets it whipsaws you to death. You buy at the top of a range, sell at the bottom, repeat until you're broke. Also it's always lagging—by the time the crossover happens, the move might be half over.

**Implementation:**
Check out `MovingAverageCrossover` in `src/strategies/momentum_strategy.py`. It's like 50 lines of code. I use it in backtesting but not directly in the live bot. The technical analysis agent basically does the same logic though.

## Technical Analysis Agent Strategy

This is the agent version of technical trading. Instead of just one indicator, it looks at multiple and combines them.

**What it checks:**

1. **RSI (Relative Strength Index)** - Measures if something is overbought or oversold
   - RSI < 30: Oversold, might bounce up. Bullish.
   - RSI > 70: Overbought, might drop. Bearish.
   - RSI around 50: Neutral, no strong signal.

2. **Moving Average positions** - Where's the price relative to MAs?
   - Price above both 20 and 50 day MAs, and 20 > 50: Golden cross territory, bullish.
   - Price below both MAs and 20 < 50: Death cross vibes, bearish.
   - Mixed signals: Slightly bullish or bearish depending on setup.

3. **Aggregation** - Average all the signals together
   - Each indicator gets a signal value (-2 to +2) and a confidence (0 to 1)
   - Multiply them together, average across all indicators
   - Convert back to a discrete signal (STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL)

**Why I like it:**
It's conservative. Needs multiple things to agree before taking strong action. Less prone to fake-outs than a single indicator.

**The catch:**
Still suffers in choppy markets. And if all the indicators are lagging (which they are), then combining them doesn't magically make them faster.

**Code:** `TechnicalAnalysisAgent` in `src/agents/technical_analysis_agent.py`

## Machine Learning Prediction Strategy

This is where it gets fancy. Train a model on historical data and let it predict future returns.

**How it works:**

1. **Feature engineering** - Create predictive features from raw price data:
   - Returns over different timeframes (5-day, 10-day momentum)
   - Volatility (rolling standard deviation of returns)
   - Volume patterns
   - Technical indicators (RSI, MA ratios)
   - Price relative to moving averages

2. **The model** - Random Forest Regressor
   - Why Random Forest? It handles non-linear patterns, doesn't overfit too badly, and is relatively fast.
   - Train on past data: X = features, y = next period's return
   - Learns which feature combinations predict up vs down moves

3. **Prediction** - Feed current features into trained model
   - Model outputs expected return (e.g., +0.02 means predicts 2% gain)
   - Convert prediction to signal:
     - Predict > 2% gain → STRONG_BUY
     - Predict 0.5-2% gain → BUY
     - Predict < -2% loss → STRONG_SELL
     - Predict -2% to -0.5% loss → SELL
     - Anything else → HOLD

4. **Confidence scaling** - Bigger predicted moves get higher confidence

**The reality check:**
Yeah, there's some data leakage issues. The features aren't perfectly forward-looking. The model sometimes hallucinates patterns that don't exist. It's trained on limited data so it might not generalize well. But for demonstrating ML concepts it works fine. And honestly in backtests it's not terrible.

**Code:** `MLPredictionAgent` in `src/agents/ml_prediction_agent.py`

## Planning Agent Strategy (A* Search)

The nerdy one. Uses AI planning algorithms to think multiple steps ahead.

**The concept:**
Trading isn't just about the next move, it's about the sequence. If I buy now, when should I sell? If I'm in a position and price is dropping, should I hold or cut losses?

This agent models trading as a state space search problem:
- **State**: Current position (long/cash), capital, timestamp
- **Actions**: BUY, SELL, HOLD
- **Goal**: Maximize capital at the end of the planning horizon

It uses A* search algorithm to find the optimal sequence of actions.

**How A* works here:**

1. Start from current state (e.g., in cash, $10k capital)
2. Generate possible next states (what if we buy? what if we hold?)
3. Estimate cost to goal using heuristic (assumes we'll capture average returns going forward)
4. Expand most promising states first (low cost + low heuristic)
5. When we reach the end of the planning window, we have a plan
6. Execute the first action in the plan

**Why this is cool:**
It considers transaction costs, it thinks about multi-step consequences, it optimizes globally not just locally.

**Why it's sketchy:**
The heuristic is super simplified. It assumes we know future returns (we don't). The planning horizon is short (5 steps by default) because search gets expensive. And honestly the market changes so fast that a perfect plan for 5 days out is useless.

But it demonstrates planning concepts and sometimes catches patterns the reactive agents miss.

**Code:** `TradingPlannerAgent` in `src/agents/planning_agent.py`

## Reasoning Agent Strategy

The philosopher. Uses logical reasoning to make sense of conflicting signals.

This one is less developed honestly. The idea is to have rules like:
- "If RSI is oversold BUT the trend is down, maybe don't buy yet"
- "If ML predicts up BUT volume is declining, be cautious"
- "If we just had a big move, expect mean reversion"

It's supposed to be the tiebreaker when other agents disagree. In practice I haven't fully implemented all the reasoning logic. It's on the TODO list.

**Code:** `ReasoningAgent` in `src/agents/reasoning_agent.py`

## Risk Management Strategy

Not a trading strategy per se, but it affects every trade. The risk management agent doesn't say "buy this" or "sell that", it says "if we're buying, here's how much" and "we shouldn't be risking more than X% on this trade".

**Key concepts:**

1. **Position sizing** - Don't bet too much on any one trade
   - Kelly Criterion: Optimal bet size based on edge and odds
   - Fixed fractional: Always risk 1-2% of capital per trade
   - Volatility-based: Smaller positions in volatile assets

2. **Portfolio limits** - Don't get overexposed
   - Max 30% of portfolio in any one position
   - Max 50% of portfolio deployed at once (keep cash buffer)
   - Never go full margin (that's how you blow up)

3. **Stop losses** - Exit losing trades before they kill you
   - Trailing stops: Lock in profits as price moves up
   - Percentage stops: Exit if down 5% from entry
   - ATR-based stops: Adjust to volatility

**Implementation notes:**
The `PortfolioOptimizer` class calculates optimal position sizes using Kelly Criterion and risk tolerance. The `RiskManagementAgent` checks if we're overexposed and can veto trades if they're too risky.

**Code:** 
- `src/risk_management/portfolio_optimizer.py`
- `src/risk_management/position_sizer.py`
- `src/agents/risk_management_agent.py`

## Multi-Agent Ensemble (The Actual Bot)

Okay so here's how it all comes together. The live bot doesn't use just one strategy. It uses ALL of them (or most of them).

**The setup:**
- Technical Analysis Agent (weight: 0.25)
- Risk Management Agent (weight: 0.15)
- ML Prediction Agent (weight: 0.30) - highest weight because it's fancy
- Planning Agent (weight: 0.15)
- Reasoning Agent (weight: 0.25)

Each agent analyzes the current market data and returns a signal with confidence.

**Aggregation methods:**

I've implemented several ways to combine the votes:

1. **Weighted Average** - Multiply each signal by its agent's weight, sum them up. Simple and works.

2. **Confidence Weighted** - Like weighted average but also multiply by each agent's confidence. So an agent that's very sure gets more influence than one that's wishy-washy. This is what I usually use.

3. **Majority Vote** - Democracy. Most common signal wins. Good for reducing false signals but might miss opportunities.

4. **Unanimous** - Only act if everyone agrees. Super conservative. Rarely triggers but when it does it's probably legit.

**Confidence threshold:**
Even after aggregation, if the final confidence is below 0.5 (configurable), we don't trade. Just hold. This prevents weak signals from causing bad trades.

**Example flow:**
```
Latest data comes in:
- TechnicalAgent: BUY (confidence 0.7) - "RSI oversold, golden cross forming"
- MLAgent: STRONG_BUY (confidence 0.8) - "Model predicts +3% return"
- PlannerAgent: HOLD (confidence 0.6) - "Plan says wait one more period"
- RiskAgent: BUY (confidence 0.5) - "Position size looks okay, volatility acceptable"
- ReasoningAgent: BUY (confidence 0.6) - "Technicals and ML agree, trust them"

Aggregated (confidence-weighted):
- Signal value: ~1.2 (somewhere between BUY and STRONG_BUY)
- Final confidence: ~0.68
- Decision: BUY with decent confidence
```

**Position sizing:**
Once we decide to BUY, the optimizer calculates how much:
- Expected return (from ML agent): +3%
- Volatility: 1.5% daily
- Current capital: $10,000
- Risk tolerance: 2% of capital
- Kelly fraction: Suggests risking ~15% of capital
- Max shares (configured): 5 shares
- Optimal: 2 shares (balancing Kelly with safety)

Then we submit the buy order for 2 shares.

**Code:** `src/agents/agent_coordinator.py` and the main loop in `src/main.py`

## What Actually Works

Okay real talk. After running this in paper trading for a while, here's what I've learned:

**What works:**
- The multi-agent approach catches more good opportunities than any single strategy
- Confidence weighting prevents overtrading on weak signals
- Position sizing saves you from catastrophic losses
- The ML agent is surprisingly decent at catching momentum shifts

**What doesn't work:**
- Mean reversion strategies get crushed in strong trends
- Planning agent is too slow and the market invalidates the plan too fast
- Reasoning agent needs way more rules to be useful
- Any strategy that worked great in backtest gets worse in live trading (overfitting is real)

**What I'd change if I started over:**
- Add a regime detection layer (are we in trending, mean-reverting, or volatile market?)
- Different agent weights for different regimes
- More emphasis on exits—knowing when to sell matters more than when to buy
- Sentiment analysis from social media (if I can find a good free API)
- Incorporate order book data and volume profile

But for now this is what we've got. It's not perfect but it's honest work.

## Testing Your Own Strategies

If you want to add a new strategy:

1. Create a new agent class in `src/agents/` that inherits from `BaseAgent`
2. Implement the `analyze()` method to return an `AgentSignal`
3. Add your agent to the list in `src/main.py` with a weight
4. Run backtests first to make sure it's not completely broken
5. Paper trade for at least a month before risking real money

Or if you're doing classic strategy backtesting:

1. Create a strategy class in `src/strategies/` inheriting from `BaseStrategy`
2. Implement `generate_signals()` to add 'signal' and 'position' columns to the data
3. Run it through the `Backtester` to see historical performance
4. Tweak parameters until it looks good (but beware overfitting)

Either way, test test test. Markets are unforgiving and even the best strategy will eventually fail when conditions change.

Good luck.
