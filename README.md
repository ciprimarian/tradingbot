# Trading Bot - Data Analysis Branch

This branch represents the **data analysis and backtesting phase** of the trading bot project. It's frozen in time as a snapshot of when I was exploring data, testing simple strategies, and building the backtesting infrastructure.

## What This Branch Is

This is NOT the live trading bot with AI agents. That's on `main` and `dev` branches.

This branch is where I:
- Explored market data and learned what it looks like
- Built the data pipeline (fetching, cleaning, storing)
- Implemented basic technical indicators
- Created a simple Moving Average Crossover strategy
- Built the backtesting framework
- Analyzed strategy performance through Jupyter notebooks

Think of this as the research phase. The experimental lab where I figured out what works before building the fancy multi-agent system.

## Branch Purpose

I'm keeping this branch separate because:
1. **Assessment/Portfolio** - Shows the data science and analysis work
2. **Learning Reference** - Documents my progression from simple to complex
3. **Baseline** - A simple working bot before adding AI complexity
4. **Comparison** - Can compare simple SMA strategy vs multi-agent performance

This branch stays frozen while `main` continues to evolve.

## What's Here

### Core Components

**Simple Trading Loop** (`src/main.py`)
- Fetches market data from Alpaca
- Calculates 20/50 day moving average crossover
- Executes trades when fast MA crosses slow MA
- Runs once per day
- That's it. No AI, no agents, just classic technical analysis.

**Data Pipeline** (`src/data/`)
- `MarketData` - Fetches OHLCV bars from Alpaca API
- `DataManager` - Saves/loads data to parquet files
- Clean, simple, works.

**Indicators** (`src/indicators/`)
- Moving averages (SMA)
- That's all for now. Kept it minimal.

**Backtesting** (`src/backtest/`)
- `Backtester` - Runs strategy on historical data
- `PerformanceAnalyzer` - Calculates returns, Sharpe ratio, drawdowns
- Generates reports

**Strategy** (`src/strategies/`)
- `MovingAverageCrossover` - The classic. Buy when fast > slow, sell when fast < slow.

### Jupyter Notebooks

This is where the real work happened. Six notebooks documenting the research process:

1. **01_data_exploration_and_cleaning.ipynb**
   - Loading market data
   - Checking for missing values, outliers
   - Understanding data quality
   - Visualizing price movements

2. **02_feature_engineering.ipynb**
   - Creating technical indicators
   - Testing different indicator parameters
   - Feature selection for potential ML models

3. **03_statistical_analysis_and_validation.ipynb**
   - Testing for stationarity
   - Checking correlations
   - Validating assumptions
   - Statistical tests on returns

4. **research.ipynb**
   - General exploration notebook
   - Quick tests and experiments
   - Scratchpad for ideas

5. **strategy_development.ipynb**
   - Developing the MA crossover strategy
   - Testing different MA periods (10/30, 20/50, 50/200)
   - Visualizing entry/exit points

6. **backtesting.ipynb**
   - Running backtests on different symbols
   - Comparing strategy performance
   - Analyzing what works and what doesn't

## Project Structure

```
tradingbot/ (data branch)
├── src/
│   ├── main.py              # Simple MA crossover bot
│   ├── data/
│   │   ├── market_data.py   # Fetch from Alpaca
│   │   └── data_manager.py  # Save/load data
│   ├── indicators/
│   │   └── moving_average.py  # SMA calculation
│   ├── strategies/
│   │   └── momentum_strategy.py  # MA crossover
│   ├── backtest/
│   │   ├── backtester.py
│   │   └── performance_analyzer.py
│   ├── brokers/
│   │   └── alpaca_broker.py
│   └── config/
│       ├── settings.py
│       └── trading_config.yaml
├── notebooks/            # Research notebooks (6 total)
├── data/                # Stored market data
└── docs/               # This documentation
```

## Quick Start

```bash
# Clone and checkout this branch
git clone https://github.com/ciprimarian/tradingbot.git
cd tradingbot
git checkout data

# Setup environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Add your Alpaca API keys to .env
cp .env.example .env
# Edit .env with your keys

# Run a backtest
python src/backtest/backtester.py

# Or explore in notebooks
jupyter notebook notebooks/
```

## Configuration

Everything is configured in `src/config/trading_config.yaml`:

```yaml
trading:
  symbol: "GLD"           # Gold ETF
  trade_quantity: 1

data:
  timeframe: "1Day"
  start_date: "2024-01-01"
  limit: 1000

backtest:
  initial_capital: 10000
  strategy: "moving_average_crossover"
  strategy_params:
    fast_period: 20
    slow_period: 50
```

## Key Findings

What I learned from this data analysis phase:

### What Worked

- **Data quality is good** - Alpaca provides clean OHLCV data with few gaps
- **Simple strategies can work** - MA crossover isn't magic but it catches trends
- **Backtesting is essential** - No strategy should go live without historical testing
- **GLD is stable** - Gold ETF makes a good test symbol (less volatile than tech stocks)

### What Didn't Work

- **20/50 MA is hit or miss** - Works in trending markets, whipsaws in sideways markets
- **Daily timeframe is slow** - Misses intraday opportunities
- **No risk management** - Need position sizing and stop losses
- **One indicator is limiting** - Need multiple confirmation signals

### What I Should Add Next

This is what led to the multi-agent system on `main` branch:
- Multiple indicators (RSI, MACD, Bollinger Bands)
- Multiple strategies voting together
- Machine learning for pattern recognition
- Better risk management
- Position sizing based on volatility

## Differences from Main Branch

| Feature | Data Branch (Here) | Main Branch |
|---------|-------------------|-------------|
| Strategy | Simple MA Crossover | Multi-agent AI system |
| Agents | None | 5+ specialized agents |
| ML Models | None | Random Forest, potential LSTM |
| Decision Making | Single strategy | Aggregated agent votes |
| Complexity | Low | High |
| Purpose | Research/Learning | Production-ready trading |
| Execution | Daily | Configurable (60s default) |

This branch is the foundation. Main branch is the building.

## Using the Notebooks

The notebooks are the main value of this branch. They show the thought process:

```bash
jupyter notebook notebooks/

# Start with 01_data_exploration_and_cleaning.ipynb
# Then move through 02 and 03
# strategy_development.ipynb shows how the MA strategy was built
# backtesting.ipynb has the performance analysis
```

Each notebook has markdown cells explaining what I was thinking and why I made certain choices.

## Backtesting Results

Summary of MA crossover strategy on GLD (2024 data):

- **Total Return**: Varies by period, typically 5-15% annually
- **Win Rate**: ~55-60% (slightly better than coin flip)
- **Sharpe Ratio**: ~0.8-1.2 (decent risk-adjusted returns)
- **Max Drawdown**: ~10-15% (manageable losses)

Not amazing, but not terrible for a simple strategy. Good enough to build on.

## Moving to Main Branch

If you want the advanced multi-agent trading bot, switch branches:

```bash
git checkout main
```

The main branch has:
- AI agents (ML, Planning, Reasoning)
- Confidence-weighted decision aggregation  
- Real-time trading loop
- Web dashboard
- Much more sophisticated risk management
- Extensive documentation

But it all started here, with simple data analysis and a basic MA crossover.

## Why This Matters

This branch documents the learning process. It shows:
- How to build a trading system from scratch
- The importance of data analysis before strategy development
- How backtesting reveals strategy weaknesses
- The progression from simple to complex

Every complex system starts simple. This is that start.

## Documentation

For this branch specifically:

- **Architecture Diagram** - See `docs/data_branch_architecture.md` for visual overview
- **Notebook Guide** - See `docs/notebooks_guide.md` for how to use the research notebooks
- **Setup** - Same as main branch, see `docs/setup.md`

## License

Same as main project - use it however you want. Learn from it, build on it, or ignore it.

## Contact

This is a learning project snapshot. The real development happens on `main`.

---

**Note**: This branch is frozen for assessment/reference purposes. All new development happens on `main` and `dev` branches.
