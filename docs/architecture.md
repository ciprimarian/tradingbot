# Architecture

Alright, so here's how this whole thing is built. Think of it as a messy but functional tower of trading logic. I'll try to explain it like I would to myself six months from now when I've forgotten why I did everything.

## The Big Picture

This is a multi-agent trading bot. Not the kind where you have a single brain making decisions, but more like a committee of specialists who argue until someone makes a call. Each agent has their own perspective on the market and they all vote on what to do. Sometimes they agree. Sometimes they don't. That's life.

The main flow is dead simple:
1. Fetch market data
2. Ask all the agents what they think
3. Aggregate their opinions
4. Maybe execute a trade if we're confident enough
5. Wait a bit, then do it again

## Core Components

### Agents (src/agents/)

The heart and soul. Each agent is a different lens through which we view the market.

**BaseAgent** - The abstract parent class. Every agent inherits from this. It forces them to implement an `analyze()` method that returns an `AgentSignal`. Each agent has a name and a weight (though I'm not always sure the weights add up to 1.0 and honestly that's fine—controlled chaos).

**TechnicalAnalysisAgent** - Looks at price patterns, moving averages, RSI, all that classic stuff. If the price crosses above SMA or RSI is oversold, it gets excited about buying. Pretty straightforward.

**RiskManagementAgent** - The cautious one. This agent thinks about position sizing, whether we're overexposed, if volatility is too high. It's the one saying "maybe we shouldn't bet the farm on this."

**SimpleSentimentAgent** - Used to analyze news sentiment. Currently might be disabled or have low weight because sentiment analysis can be flaky. But when it works, it reads news headlines and decides if the vibe is bullish or bearish.

**MLPredictionAgent** - Machine learning branch. This one trains models (or uses pre-trained ones) to predict price movements. It's the fancy AI part that makes people think you're doing something cutting-edge. Sometimes it works, sometimes it hallucinates patterns.

**TradingPlannerAgent** - Planning branch. This agent thinks ahead. It considers the current position, the market state, and plans multi-step moves. Like "if we buy now, when would we exit?" It's more strategic than reactive.

**ReasoningAgent** - The philosopher. Uses some reasoning logic (maybe rule-based, maybe symbolic AI) to make sense of contradictory signals. It's supposed to be the tiebreaker when everyone else is confused.

All agents return an `AgentSignal` which has:
- `signal_type`: STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL (enum with values 2, 1, 0, -1, -2)
- `confidence`: float between 0.0 and 1.0
- `reasoning`: a string explaining why
- `metadata`: optional dict for extra info

### AgentCoordinator (src/agents/agent_coordinator.py)

The referee. It collects all the agent signals and mashes them together using one of several aggregation methods:

- **WEIGHTED_AVERAGE**: Each agent's vote is multiplied by its weight. Simple and effective.
- **CONFIDENCE_WEIGHTED**: Like weighted average but also considers how confident each agent is. An agent screaming "I'm 95% sure!" gets more say than one whispering "maybe, like 30%?"
- **MAJORITY_VOTE**: Democracy. Most common signal wins. Confidence is adjusted based on how unified everyone is.
- **UNANIMOUS**: Only acts if everyone agrees. Rarely happens. When it does, it's probably a big deal.

The coordinator also has a `min_confidence_threshold`. If the final aggregated signal doesn't meet that threshold, it returns `None` and we just hold. No FOMO trades.

### Data Layer (src/data/)

**DataManager** - The central hub for all data operations. It fetches historical bars, cleans them (fills missing values, removes outliers), and can save/load datasets in parquet or CSV format.

**MarketData** - Wraps the actual API calls to the broker (Alpaca in our case). Gets you OHLCV bars for whatever symbol and timeframe you want.

**prepare_for_agents()** - A helper method on DataManager that calculates all the indicators the agents need: SMA_20, SMA_50, RSI_14. Basically preprocessing before we hand data to the agents.

There's also stuff like **NewsFeed** and **SentimentData** for grabbing news articles and running sentiment analysis, but those are kind of experimental right now.

### Brokers (src/brokers/)

Abstraction over trading APIs so we can swap brokers without rewriting everything.

**BaseBroker** - The interface. It's currently empty (a placeholder), but ideally it would define methods like `submit_order()`, `get_market_clock()`, `get_account()`, etc.

**AlpacaBroker** - The real implementation. Talks to Alpaca's API. Handles authentication, order submission, fetching positions and account info. If we ever want to add Interactive Brokers or something, we'd implement another broker class.

**PaperTrading** - Simulated trading. No real money at risk. Great for testing without crying over losses.

### Risk Management (src/risk_management/)

**PortfolioManager** - Keeps track of what we own and how much it's worth. Updates positions, calculates total portfolio value, checks if we're in a position for a given symbol.

**PortfolioOptimizer** - The math wizard. Uses things like Kelly Criterion to figure out optimal position sizing based on expected return and volatility. The idea is to not bet too much on any one trade.

**PositionSizer** - Similar to optimizer but simpler. Just calculates how many shares to buy based on risk tolerance and account size.

**RiskCalculator** - Computes metrics like Value at Risk (VaR), max drawdown, Sharpe ratio. Useful for understanding how risky our strategy actually is.

### Indicators (src/indicators/)

All the technical indicator calculations live here. Moving averages, RSI, MACD, Bollinger Bands, ATR, volume indicators, you name it. Each one is a standalone function that takes a DataFrame and spits out the indicator values. Clean and modular.

### Strategies (src/strategies/)

**BaseStrategy** - Abstract class for trading strategies. Each strategy has a `generate_signal()` method.

**MomentumStrategy** - Buys when price is trending up, sells when it reverses. Simple momentum play.

**MeanReversionStrategy** - The opposite. Buys when price dips below average, sells when it spikes above. Bets on things returning to normal.

**MultiAgentStrategy** - The big one. This is where the agent coordinator gets plugged in. Instead of a single rule-based strategy, we let the agent committee decide.

### Backtesting (src/backtest/)

**Backtester** - Runs a strategy against historical data and simulates trades. Tells you how much money you would've made or lost.

**PerformanceAnalyzer** - Crunches the numbers from backtests. Calculates returns, drawdowns, win rate, all the metrics traders care about.

### Configuration (src/config/)

**settings.py** - Loads `trading_config.yaml` and exposes it as `CONFIG`. Everything from which symbol to trade, timeframes, risk limits, API keys (stored in env vars), etc.

**logging.conf** - Logging setup. Where logs go, what level of detail, formatting.

### Main Loop (src/main.py)

The actual bot. Ties everything together.

It initializes all the components: broker, data manager, portfolio, optimizer, agents, and coordinator. Then it enters an infinite loop:

1. Check if the market is open (unless it's crypto/forex which trades 24/7)
2. Update portfolio state
3. Fetch latest market data
4. Prepare indicators
5. Ask agents for their signals via the coordinator
6. If signal is confident enough, calculate position size using optimizer
7. Execute trade (buy or sell)
8. Sleep for a bit (default 60 seconds)
9. Repeat

It handles keyboard interrupts gracefully and logs everything obsessively so you can figure out what went wrong later.

### Dashboard (src/dashboard/)

Web interface for monitoring the bot. Uses Flask and SocketIO for real-time updates. Shows current positions, portfolio value, recent trades, logs, and charts. You can start/stop the bot from the UI.

**BotManager** - Runs the trading bot in a background thread and communicates state back to the web app via WebSockets.

## Data Flow

Here's how data actually moves through the system:

```
Market API (Alpaca) 
    ↓
MarketData.get_historical_bars() 
    ↓
DataManager.get_historical_data() 
    ↓
DataManager.prepare_for_agents() [adds indicators]
    ↓
AgentCoordinator.get_signals() → each agent analyzes data
    ↓
AgentCoordinator.aggregate_signals() → combines agent votes
    ↓
main_bot_loop decides if confidence is high enough
    ↓
PortfolioOptimizer calculates position size
    ↓
AlpacaBroker.submit_order() → executes trade
    ↓
PortfolioManager.update_portfolio() → tracks new position
```

It's a pipeline. Data goes in one end, trades come out the other.

## Design Philosophy

Why did I build it this way? A few reasons:

1. **Modularity** - Each component does one thing. Agents don't talk to brokers. Brokers don't calculate indicators. Clean boundaries.

2. **Extensibility** - Want a new agent? Subclass `BaseAgent` and implement `analyze()`. Done. Want to add a new broker? Implement the interface. Easy.

3. **Testability** - Each piece can be tested in isolation. Mock the broker, feed fake data to agents, verify they spit out the right signals.

4. **Debuggability** - Logs everywhere. Every decision, every calculation, every API call is logged. When things go wrong (and they will), you can trace exactly what happened.

5. **Flexibility** - Multiple aggregation methods, configurable weights, adjustable thresholds. You can tune this thing a million different ways without rewriting code.

## What's Still Broken or Weird

Let me be honest about the rough edges:

- **Agent weights don't always sum to 1.0.** I know that's mathematically weird but it hasn't caused problems yet. The coordinator normalizes things anyway.

- **BaseBroker is empty.** It's supposed to be an interface but I never filled it out. AlpacaBroker just exists on its own. If you add another broker, you'll have to figure out the interface yourself.

- **MultiAgentStrategy is empty.** Yeah. I started it and then just built the logic directly into `main.py` instead. Oops.

- **News sentiment is flaky.** The sentiment analysis agent exists but I don't always use it because news APIs are expensive and the models aren't great. So it's often disabled.

- **No error recovery in the main loop.** If the broker API goes down mid-trade, the bot will retry but might get confused about position state. You should probably check manually.

- **Dashboard has a circular import bug.** There's a `NameError: name 'List' is not defined` in `bot_manager.py`. Need to add `from typing import List` at the top. I keep forgetting to fix that.

## How to Think About This

If you're reading this and trying to extend the bot, here's my advice:

- Start with the agents. That's where the intelligence lives. Everything else is just plumbing.
- Don't overthink the aggregation method. Confidence-weighted works fine. Unanimous is too strict. Weighted average is solid.
- Log more rather than less. Future you will thank present you.
- Test your changes with paper trading first. Real money can wait.
- The optimizer is optional. If you don't trust it, just use a fixed position size.

That's the architecture. It's not perfect, but it works. Most of the time.
