# Data Branch Architecture

This diagram shows the architecture of the trading bot on the `data` branch - the simple data analysis and backtesting phase.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   Data Branch Trading Bot                    │
│            (Simple MA Crossover Strategy)                     │
└─────────────────────────────────────────────────────────────┘
```

## High-Level Architecture

```
┌──────────────┐
│   main.py    │  ← Entry point, simple trading loop
│  (Main Loop) │
└──────┬───────┘
       │
       ├──────────────┬──────────────┬──────────────┬──────────────┐
       │              │              │              │              │
       ▼              ▼              ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  Broker  │  │   Data   │  │Indicators│  │ Strategy │  │Portfolio │
│  (Alpaca)│  │ Manager  │  │   (SMA)  │  │(MA Cross)│  │ Manager  │
└──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘
      │              │              │              │              │
      │              │              │              │              │
      ▼              ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Services                             │
├──────────────────┬──────────────────┬───────────────────────────┤
│  Alpaca API      │  File Storage     │   Config Files            │
│  (Market Data &  │  (Parquet/CSV)    │   (YAML, .env)            │
│   Trade Exec)    │                   │                           │
└──────────────────┴──────────────────┴───────────────────────────┘
```

## Data Flow

```
1. Fetch Market Data
   ┌────────────┐         ┌─────────────┐         ┌──────────────┐
   │ Alpaca API │────────▶│ MarketData  │────────▶│ DataManager  │
   │            │  OHLCV  │   Client    │  Clean  │  (Storage)   │
   └────────────┘         └─────────────┘         └──────┬───────┘
                                                          │
                                                          ▼
                                                   ┌──────────────┐
                                                   │ Parquet File │
                                                   │ data/*.pq    │
                                                   └──────────────┘

2. Generate Signals
   ┌──────────────┐         ┌─────────────┐         ┌──────────────┐
   │ Price Data   │────────▶│ Calculate   │────────▶│   Strategy   │
   │  (OHLCV)     │         │  SMA 20/50  │  MAs    │ (MA Crossover│
   └──────────────┘         └─────────────┘         └──────┬───────┘
                                                            │
                                                            ▼
                                                     ┌──────────────┐
                                                     │   Signal     │
                                                     │ BUY/SELL/HOLD│
                                                     └──────────────┘

3. Execute Trade
   ┌──────────────┐         ┌─────────────┐         ┌──────────────┐
   │   Signal     │────────▶│ Portfolio   │────────▶│ Alpaca API   │
   │ (BUY/SELL)   │  Check  │  Manager    │  Submit │ (Order Exec) │
   └──────────────┘ Position└─────────────┘  Order  └──────────────┘
```

## Component Details

### Main Loop (src/main.py)

```
┌───────────────────────────────────────────────┐
│           Main Trading Loop                   │
├───────────────────────────────────────────────┤
│                                               │
│  while True:                                  │
│    1. Update portfolio state                  │
│    2. Fetch market data                       │
│    3. Calculate indicators (SMA 20, 50)       │
│    4. Generate signal (crossover logic)       │
│    5. Execute trade if signal triggers        │
│    6. Sleep 24 hours                          │
│    7. Repeat                                  │
│                                               │
│  Error handling:                              │
│    - Catch exceptions, wait 60s, retry        │
│    - Keyboard interrupt for manual stop       │
│                                               │
└───────────────────────────────────────────────┘
```

### Data Layer

```
┌─────────────────────────────────────────────────────────┐
│                    Data Components                       │
├──────────────────────┬──────────────────────────────────┤
│   MarketData         │   DataManager                    │
├──────────────────────┼──────────────────────────────────┤
│ - get_historical_    │ - save_data()                    │
│   bars()             │ - load_data()                    │
│ - Connects to Alpaca │ - Manages storage                │
│ - Returns DataFrame  │ - Parquet/CSV format             │
│                      │ - Stores in data/ dir            │
└──────────────────────┴──────────────────────────────────┘
```

### Indicators

```
┌────────────────────────────────────────┐
│      Technical Indicators               │
├────────────────────────────────────────┤
│  moving_average.py                     │
│                                        │
│  calculate_sma(df, period)             │
│    ├─ Calculates Simple Moving Avg    │
│    ├─ Returns DataFrame with SMA col  │
│    └─ Used for 20-day and 50-day     │
│                                        │
│  That's it for now.                    │
│  More indicators on main branch.       │
└────────────────────────────────────────┘
```

### Strategy

```
┌────────────────────────────────────────────────────┐
│         MovingAverageCrossover Strategy             │
├────────────────────────────────────────────────────┤
│                                                    │
│  Logic:                                            │
│    if SMA_20 > SMA_50:                             │
│        signal = BUY (1)                            │
│    elif SMA_20 < SMA_50:                           │
│        signal = SELL (0)                           │
│                                                    │
│  position = signal.diff()                          │
│    +1 = Entry (buy)                                │
│    -1 = Exit (sell)                                │
│     0 = Hold                                       │
│                                                    │
│  Returns: DataFrame with signal & position cols   │
│                                                    │
└────────────────────────────────────────────────────┘
```

### Backtesting System

```
┌──────────────────────────────────────────────────────────┐
│                  Backtesting Architecture                 │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐         ┌──────────────────────┐      │
│  │  Historical  │────────▶│    Backtester        │      │
│  │     Data     │         │                      │      │
│  └──────────────┘         │ - Simulates trades   │      │
│                           │ - Tracks PnL         │      │
│  ┌──────────────┐         │ - Applies commissions│      │
│  │   Strategy   │────────▶│                      │      │
│  │ (MA Cross)   │         └──────────┬───────────┘      │
│  └──────────────┘                    │                  │
│                                      ▼                  │
│                           ┌──────────────────────┐      │
│                           │ PerformanceAnalyzer  │      │
│                           │                      │      │
│                           │ - Total return       │      │
│                           │ - Sharpe ratio       │      │
│                           │ - Max drawdown       │      │
│                           │ - Win rate           │      │
│                           │ - Trade log          │      │
│                           └──────────────────────┘      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## Jupyter Notebooks Integration

```
┌────────────────────────────────────────────────────────────┐
│               Notebooks Research Pipeline                   │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  01_data_exploration_and_cleaning.ipynb                    │
│    │                                                       │
│    ├──▶ Load data, visualize, check quality               │
│    │                                                       │
│    ▼                                                       │
│  02_feature_engineering.ipynb                              │
│    │                                                       │
│    ├──▶ Create indicators, test parameters                │
│    │                                                       │
│    ▼                                                       │
│  03_statistical_analysis_and_validation.ipynb              │
│    │                                                       │
│    ├──▶ Test assumptions, validate data                   │
│    │                                                       │
│    ▼                                                       │
│  strategy_development.ipynb                                │
│    │                                                       │
│    ├──▶ Develop MA crossover logic                        │
│    │                                                       │
│    ▼                                                       │
│  backtesting.ipynb                                         │
│    │                                                       │
│    └──▶ Test strategy, analyze performance                │
│                                                            │
│  research.ipynb (general scratchpad)                       │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Configuration Flow

```
┌────────────────────────────────────────────────┐
│          Configuration Management               │
├────────────────────────────────────────────────┤
│                                                │
│  .env file                                     │
│    └─▶ ALPACA_API_KEY                          │
│    └─▶ ALPACA_SECRET_KEY                       │
│    └─▶ ALPACA_PAPER_TRADING                    │
│                                                │
│  trading_config.yaml                           │
│    └─▶ trading:                                │
│         ├─ symbol: "GLD"                       │
│         └─ trade_quantity: 1                   │
│    └─▶ data:                                   │
│         ├─ timeframe: "1Day"                   │
│         ├─ start_date: "2024-01-01"            │
│         └─ limit: 1000                         │
│    └─▶ backtest:                               │
│         ├─ initial_capital: 10000              │
│         └─ strategy_params:                    │
│              ├─ fast_period: 20                │
│              └─ slow_period: 50                │
│                                                │
│  settings.py                                   │
│    └─▶ Loads config and exposes as CONFIG dict │
│                                                │
└────────────────────────────────────────────────┘
```

## Execution Timeline

```
Time:   T0          T+1         T+2         T+3         T+4
        │           │           │           │           │
Action: Fetch ────▶ Calc ────▶ Signal ──▶ Execute ──▶ Wait 24h
        Data        SMA         BUY         Order       (Sleep)
        │           │           │           │           │
        │           │           │           │           └──▶ Loop back to T0
        │           │           │           │
Data:   OHLCV ───▶ SMA20 ───▶ +1 ───────▶ BUY GLD
        bars        SMA50       (crossover)  1 share
```

## Key Characteristics

### Simplicity
- One strategy (MA crossover)
- One indicator set (SMA 20/50)
- One symbol at a time
- Daily execution
- No complex decision logic

### Data Focus
- Heavy emphasis on Jupyter notebooks
- Data exploration and validation
- Statistical analysis
- Strategy development through experimentation
- Learning-oriented

### Foundation
- Clean data pipeline
- Solid backtesting framework
- Modular components
- Ready to extend

This simple architecture is the baseline. The main branch builds a multi-agent AI system on top of this foundation.

## Comparison to Main Branch

```
Data Branch:                Main Branch:
┌────────────┐             ┌──────────────────────┐
│   Single   │             │   Multi-Agent        │
│  Strategy  │             │    Committee         │
│ (MA Cross) │             │ (5+ agents voting)   │
└────────────┘             └──────────────────────┘
      │                              │
      ▼                              ▼
  BUY/SELL                  Aggregated Decision
   Signal                   (weighted by confidence)
```

Simple, clear, and effective for learning. That's this branch.
