# Multi-Agent Trading Bot Architecture

This diagram shows the architecture of the trading bot on `main` and `dev` branches - the sophisticated multi-agent AI system.

## System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│              Multi-Agent AI Trading Bot Architecture                      │
│   Demonstrates: ML, Planning, Optimization, Reasoning AI Branches         │
└──────────────────────────────────────────────────────────────────────────┘
```

## High-Level Architecture

```
                         ┌─────────────────┐
                         │   main.py       │
                         │  (Main Loop)    │
                         └────────┬────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   ▼
      ┌──────────────┐   ┌───────────────┐   ┌──────────────┐
      │ Data Layer   │   │ Agent System  │   │ Execution    │
      │              │   │  (Committee)  │   │   Layer      │
      └──────────────┘   └───────────────┘   └──────────────┘
              │                   │                   │
              │                   │                   │
              ▼                   ▼                   ▼
      ┌──────────────┐   ┌───────────────┐   ┌──────────────┐
      │ MarketData   │   │ 5+ Agents     │   │ Broker API   │
      │ + Indicators │   │ Vote & Decide │   │ + Portfolio  │
      └──────────────┘   └───────────────┘   └──────────────┘
```

## Multi-Agent Decision System

```
┌────────────────────────────────────────────────────────────────────────┐
│                      Agent Committee Architecture                       │
└────────────────────────────────────────────────────────────────────────┘

          Market Data (OHLCV + Indicators)
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │      Agent Coordinator                │
        │   (Aggregation & Decision Logic)      │
        └───┬───────────┬───────────┬───────┬───┘
            │           │           │       │
            ▼           ▼           ▼       ▼      
    ┌──────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐   ┌──────────┐
    │Technical │  │    ML    │  │Planning │  │   Risk   │   │Reasoning │
    │ Analysis │  │Prediction│  │ (A*)    │  │Mgmt Agent│   │  Agent   │
    │  Agent   │  │  Agent   │  │ Agent   │  │          │   │          │
    └────┬─────┘  └────┬─────┘  └────┬────┘  └────┬─────┘   └────┬─────┘
         │             │             │            │              │
         │  Signal     │  Signal     │  Signal    │  Signal      │  Signal
         │  BUY(0.7)   │  STRONG_    │  HOLD(0.6) │  BUY(0.5)    │  BUY(0.6)
         │             │  BUY(0.8)   │            │              │
         └─────────────┴─────────────┴────────────┴──────────────┘
                                │
                                ▼
                    ┌──────────────────────┐
                    │ Aggregated Decision  │
                    │ BUY (conf: 0.68)     │
                    └──────────────────────┘
                                │
                                ▼
                    ┌──────────────────────┐
                    │ Position Optimizer   │
                    │ (Kelly Criterion)    │
                    │ → 2 shares optimal   │
                    └──────────────────────┘
                                │
                                ▼
                        Execute Trade
```

## Individual Agent Details

### Technical Analysis Agent

```
┌──────────────────────────────────────────────┐
│      Technical Analysis Agent                 │
├──────────────────────────────────────────────┤
│  Analyzes:                                   │
│    - RSI (14-period)                         │
│      • < 30: Oversold → BUY                  │
│      • > 70: Overbought → SELL               │
│                                              │
│    - Moving Averages (20, 50)                │
│      • Golden Cross → BUY                    │
│      • Death Cross → SELL                    │
│                                              │
│  Output:                                     │
│    Signal: BUY/SELL/HOLD                     │
│    Confidence: 0.0-1.0                       │
│    Reasoning: "RSI oversold, golden cross"   │
│                                              │
│  Weight: 0.25                                │
└──────────────────────────────────────────────┘
```

### ML Prediction Agent (Machine Learning Branch)

```
┌──────────────────────────────────────────────┐
│       ML Prediction Agent                     │
│    (Machine Learning AI Branch)               │
├──────────────────────────────────────────────┤
│  Model: Random Forest Regressor              │
│                                              │
│  Features:                                   │
│    - Returns (5-day, 10-day momentum)        │
│    - Volatility (rolling std)                │
│    - RSI, MA ratios                          │
│    - Volume patterns                         │
│                                              │
│  Process:                                    │
│    1. Feature engineering                    │
│    2. Predict next-period return             │
│    3. Convert prediction to signal:          │
│       • Predict +2%: STRONG_BUY              │
│       • Predict +0.5%: BUY                   │
│       • Predict -2%: STRONG_SELL             │
│                                              │
│  Training:                                   │
│    - Auto-trains on historical data          │
│    - Saves model to disk (pickle)            │
│    - Loads pre-trained if available          │
│                                              │
│  Weight: 0.30 (highest - it's fancy)         │
└──────────────────────────────────────────────┘
```

### Planning Agent (AI Planning Branch)

```
┌──────────────────────────────────────────────┐
│         Planning Agent                        │
│      (AI Planning Branch - A*)                │
├──────────────────────────────────────────────┤
│  Algorithm: A* Search                         │
│                                              │
│  Problem Definition:                         │
│    States: {position, capital, timestamp}    │
│    Actions: {BUY, SELL, HOLD}                │
│    Goal: Maximize capital                    │
│                                              │
│  Heuristic:                                  │
│    Estimates future returns based on         │
│    historical averages                       │
│                                              │
│  Process:                                    │
│    1. Look ahead N periods (default: 5)      │
│    2. Search for optimal action sequence     │
│    3. Return first action in best plan       │
│                                              │
│  Example Plan:                               │
│    BUY → HOLD → HOLD → SELL → HOLD          │
│    ↑                                         │
│    Take this action now                      │
│                                              │
│  Considers:                                  │
│    - Transaction costs                       │
│    - Multi-step consequences                 │
│    - Market trajectory                       │
│                                              │
│  Weight: 0.15                                │
└──────────────────────────────────────────────┘
```

### Risk Management Agent

```
┌──────────────────────────────────────────────┐
│       Risk Management Agent                   │
├──────────────────────────────────────────────┤
│  Monitors:                                   │
│    - Position size limits                    │
│    - Portfolio exposure                      │
│    - Volatility levels                       │
│    - Drawdown thresholds                     │
│                                              │
│  Signals:                                    │
│    - Vetos overly risky trades               │
│    - Reduces confidence if overexposed       │
│    - Suggests position sizing                │
│                                              │
│  Weight: 0.15 (the cautious one)             │
└──────────────────────────────────────────────┘
```

### Reasoning Agent (Symbolic AI Branch)

```
┌──────────────────────────────────────────────┐
│         Reasoning Agent                       │
│      (Symbolic Reasoning AI)                  │
├──────────────────────────────────────────────┤
│  Purpose:                                    │
│    Makes sense of conflicting signals        │
│                                              │
│  Logic Rules:                                │
│    - If RSI oversold BUT trend down          │
│      → Wait for confirmation                 │
│    - If ML predicts up BUT volume low        │
│      → Reduce confidence                     │
│    - If multiple agents disagree             │
│      → Provide tiebreaker logic              │
│                                              │
│  Status: Partially implemented               │
│  (needs more rules)                          │
│                                              │
│  Weight: 0.25                                │
└──────────────────────────────────────────────┘
```

## Agent Coordinator Aggregation Methods

```
┌────────────────────────────────────────────────────────────────┐
│             Aggregation Methods                                 │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  1. WEIGHTED_AVERAGE                                           │
│     signal = Σ(agent.signal × agent.weight) / Σ(weights)      │
│                                                                │
│  2. CONFIDENCE_WEIGHTED (Default)                              │
│     signal = Σ(agent.signal × agent.weight × confidence)      │
│              / Σ(agent.weight × confidence)                    │
│     → Confident agents get more influence                      │
│                                                                │
│  3. MAJORITY_VOTE                                              │
│     signal = most_common(agent_signals)                        │
│     → Democracy in action                                      │
│                                                                │
│  4. UNANIMOUS                                                  │
│     if all_agents_agree:                                       │
│         signal = agreed_signal                                 │
│     else:                                                      │
│         signal = HOLD (conf: 0.3)                              │
│     → Very conservative                                        │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## Data Flow (Complete System)

```
1. Market Data Acquisition
   ┌─────────────┐         ┌──────────────┐         ┌──────────────┐
   │ Alpaca API  │────────▶│ MarketData   │────────▶│ DataManager  │
   │             │  Fetch  │   Client     │  Clean  │              │
   └─────────────┘  Bars   └──────────────┘         └──────┬───────┘
                                                            │
                                                            ▼
                                                     ┌──────────────┐
                                                     │ Add Indicators│
                                                     │ SMA, RSI, etc │
                                                     └──────┬───────┘
                                                            │
2. Agent Analysis                                           │
                                                            ▼
   ┌────────────────────────────────────────────────────────────────┐
   │             Enriched DataFrame with Indicators                 │
   └────────────┬────────────┬────────────┬────────────┬────────────┘
                │            │            │            │
                ▼            ▼            ▼            ▼
          ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
          │Technical│  │   ML    │  │Planning │  │  Risk   │  ...
          │ Agent   │  │ Agent   │  │  Agent  │  │  Agent  │
          └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘
               │            │            │            │
               └────────────┴────────────┴────────────┘
                            │
                            ▼
3. Aggregation       ┌──────────────┐
                     │ Coordinator  │
                     │  Aggregates  │
                     └──────┬───────┘
                            │
                            ▼
               ┌────────────────────────┐
               │  Final Aggregated      │
               │  Signal + Confidence   │
               └────────┬───────────────┘
                        │
                        ▼
4. Position Sizing  ┌──────────────────┐
                    │ Portfolio        │
                    │ Optimizer        │
                    │ (Kelly Criterion)│
                    └────────┬─────────┘
                             │
                             ▼
5. Execution        ┌───────────────────┐
                    │ AlpacaBroker      │
                    │ submit_order()    │
                    └────────┬──────────┘
                             │
                             ▼
                    ┌───────────────────┐
                    │ Trade Executed    │
                    │ Position Updated  │
                    └───────────────────┘
```

## Portfolio Optimization (Optimization AI Branch)

```
┌────────────────────────────────────────────────────────────┐
│           Portfolio Optimizer                               │
│        (Optimization AI Branch)                             │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Kelly Criterion Formula:                                  │
│                                                            │
│    f* = (p × b - q) / b                                    │
│                                                            │
│  Where:                                                    │
│    f* = fraction of capital to risk                        │
│    p = probability of win (from expected return/vol)       │
│    b = odds (potential gain/loss ratio)                    │
│    q = probability of loss (1 - p)                         │
│                                                            │
│  Process:                                                  │
│    1. Estimate expected return (from ML agent)             │
│    2. Calculate volatility (rolling std of returns)        │
│    3. Compute optimal position size                        │
│    4. Cap at max configured size                           │
│                                                            │
│  Example:                                                  │
│    Expected return: +3%                                    │
│    Volatility: 1.5%                                        │
│    Capital: $10,000                                        │
│    Risk tolerance: 2%                                      │
│    → Optimal position: $1,500 (2 shares at $750 each)      │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Main Loop Flow

```
┌────────────────────────────────────────────────────────┐
│            Main Trading Loop (main.py)                  │
├────────────────────────────────────────────────────────┤
│                                                        │
│  while True:                                           │
│                                                        │
│    1. Check Market Status                             │
│       ├─ If stocks: Check if market open              │
│       ├─ If crypto: Always open                       │
│       └─ If closed: Wait and check again              │
│                                                        │
│    2. Update Portfolio State                          │
│       └─ Fetch current positions from broker          │
│                                                        │
│    3. Fetch Market Data                               │
│       ├─ Get historical bars (configurable limit)     │
│       └─ Add indicators (SMA, RSI via DataManager)    │
│                                                        │
│    4. Query All Agents                                │
│       ├─ Each agent analyzes data                     │
│       ├─ Returns AgentSignal (type, confidence,       │
│       │   reasoning)                                  │
│       └─ Coordinator collects all signals             │
│                                                        │
│    5. Aggregate Signals                               │
│       ├─ Apply aggregation method                     │
│       ├─ Calculate final signal + confidence          │
│       └─ Check confidence threshold (min 0.5)         │
│                                                        │
│    6. If Signal Confident:                            │
│       ├─ Calculate position size (optimizer)          │
│       ├─ Submit order to broker                       │
│       └─ Log decision and reasoning                   │
│                                                        │
│    7. Else:                                           │
│       └─ HOLD (no action)                             │
│                                                        │
│    8. Sleep (default: 60 seconds)                     │
│                                                        │
│    9. Loop                                            │
│                                                        │
│  Error Handling:                                      │
│    - Catch exceptions, wait 60s, retry                │
│    - Keyboard interrupt for graceful shutdown         │
│    - Extensive logging at each step                   │
│                                                        │
└────────────────────────────────────────────────────────┘
```

## Configuration Architecture

```
┌────────────────────────────────────────────────────────┐
│          Configuration Management                       │
├────────────────────────────────────────────────────────┤
│                                                        │
│  .env (Environment Variables)                          │
│    ALPACA_API_KEY                                      │
│    ALPACA_SECRET_KEY                                   │
│    ALPACA_BASE_URL                                     │
│         │                                              │
│         ▼                                              │
│  settings.py                                           │
│    Loads env vars                                      │
│    Validates required keys                             │
│         │                                              │
│         ▼                                              │
│  trading_config.yaml                                   │
│    ├─ trading:                                         │
│    │    symbol, quantity                               │
│    ├─ data:                                            │
│    │    timeframe, start_date, limit                   │
│    └─ backtest:                                        │
│         initial_capital, strategy_params               │
│         │                                              │
│         ▼                                              │
│  Agent Configs (in main.py)                            │
│    Agent weights, parameters                           │
│    Aggregation method                                  │
│    Confidence threshold                                │
│                                                        │
└────────────────────────────────────────────────────────┘
```

## Web Dashboard Architecture

```
┌────────────────────────────────────────────────────────┐
│              Web Dashboard (Flask + SocketIO)           │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Browser                                               │
│    │                                                   │
│    ├─▶ HTTP GET /                                      │
│    │   (Web interface)                                 │
│    │                                                   │
│    └─▶ WebSocket Connection                            │
│        (Real-time updates)                             │
│         │                                              │
│         ▼                                              │
│  Flask App (app.py)                                    │
│    ├─ Routes: /, /start, /stop, /status               │
│    └─ SocketIO: Real-time communication               │
│         │                                              │
│         ▼                                              │
│  BotManager                                            │
│    ├─ Runs trading bot in background thread           │
│    ├─ Collects metrics (portfolio value, trades)      │
│    ├─ Emits updates via WebSocket                     │
│    └─ Handles start/stop commands                     │
│         │                                              │
│         ▼                                              │
│  Trading Bot (runs in thread)                          │
│    Same main loop as standalone bot                    │
│                                                        │
└────────────────────────────────────────────────────────┘
```

## System Characteristics

### Modularity
- Each agent is independent
- Coordinator doesn't know agent internals
- Swappable components (brokers, strategies, aggregation methods)

### Extensibility  
- Add new agents by subclassing `BaseAgent`
- Implement `analyze()` method
- Add to coordinator with a weight
- Done

### Intelligence Layers
1. **Technical Analysis** - Classic indicators
2. **Machine Learning** - Pattern recognition
3. **Planning** - Multi-step optimization
4. **Risk Management** - Position sizing and limits
5. **Reasoning** - Conflict resolution

### Safety Features
- Confidence thresholds prevent weak signals
- Risk management agent can veto trades
- Position sizing limits exposure
- Paper trading mode for testing
- Extensive logging for debugging

## Comparison to Data Branch

```
Data Branch:                    Main/Dev Branch:
┌────────────┐                 ┌──────────────────────┐
│  Single    │                 │   5+ Agents          │
│  Strategy  │                 │   Voting System      │
│  (MA Cross)│                 │   ML + Planning      │
└────────────┘                 │   + Optimization     │
     ▼                         └──────────────────────┘
Simple Signal                            ▼
BUY/SELL                       Aggregated Decision
                               (Confidence-weighted)
```

## Key Innovations

1. **Multi-Agent Decision Making** - Wisdom of the crowd
2. **Confidence Weighting** - Not all opinions equal
3. **AI Branch Demonstrations** - ML, Planning, Optimization, Reasoning
4. **Adaptive Position Sizing** - Kelly Criterion optimization
5. **Flexible Aggregation** - Multiple voting methods
6. **Real-time Execution** - 60-second decision loop (configurable)

This architecture represents the evolution from simple rule-based trading (data branch) to sophisticated AI-driven decision-making (main branch).
