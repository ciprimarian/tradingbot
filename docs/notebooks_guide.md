# Notebooks Guide - Data Branch

The notebooks on this branch tell the story of how I learned to analyze market data and develop trading strategies. They're meant to be read in order, like chapters in a book.

## The Six Notebooks

### 01_data_exploration_and_cleaning.ipynb

**Purpose**: Getting familiar with market data.

**What's inside**:
- Loading OHLCV data from Alpaca
- Understanding the data structure (timestamps, prices, volume)
- Checking for missing values
- Looking for outliers or weird data points
- Visualizing price movements over time
- Basic statistics (mean, std, min, max)

**Why it matters**: You can't trade what you don't understand. This notebook is about understanding the raw material.

**Key findings**:
- Alpaca data is pretty clean
- Some small gaps on holidays (expected)
- Volume spikes on news events
- GLD (gold ETF) is relatively stable

**Run it if**: You want to see how to load and inspect market data, or you're working with a new symbol and want to understand its characteristics.

### 02_feature_engineering.ipynb

**Purpose**: Creating indicators and features from raw price data.

**What's inside**:
- Calculating technical indicators (SMA, potentially RSI, MACD)
- Testing different indicator parameters (SMA 10 vs 20 vs 50)
- Visualizing how indicators relate to price movements
- Feature selection - which indicators actually add value?

**Why it matters**: Raw prices are noisy. Indicators smooth and transform that data into something more useful for decision-making.

**Key findings**:
- SMA 20/50 seems like a good balance for daily data
- Shorter periods (5/10) too noisy
- Longer periods (100/200) too slow
- Volume doesn't add much signal for GLD

**Run it if**: You want to experiment with different indicators or test new indicator parameters before adding them to your strategy.

### 03_statistical_analysis_and_validation.ipynb

**Purpose**: Making sure our data and assumptions make sense.

**What's inside**:
- Testing if returns are stationary (they should be)
- Checking for autocorrelation
- Looking at return distributions (normal? fat tails?)
- Correlation analysis between different symbols
- Validating that our data assumptions hold

**Why it matters**: A lot of trading strategies assume certain statistical properties. Better to verify those assumptions than build on shaky ground.

**Key findings**:
- Returns are roughly stationary (good)
- Distribution has fatter tails than normal (expect rare large moves)
- Some autocorrelation in daily returns (momentum exists)
- GLD has low correlation with SPY (good for diversification)

**Run it if**: You're a stats nerd like me, or you want to verify data properties before trusting a strategy.

### research.ipynb

**Purpose**: General scratchpad for quick experiments.

**What's inside**:
- Whatever I was testing at the moment
- Quick data pulls
- Testing API calls
- Trying out new ideas
- Messy, unstructured exploration

**Why it matters**: Not everything needs to be formal. Sometimes you just need to test something quick.

**Run it if**: You want a sandbox to play around without creating a whole new structured notebook.

### strategy_development.ipynb

**Purpose**: Building and testing the MA crossover strategy.

**What's inside**:
- Implementing the crossover logic
- Testing different MA combinations (10/30, 20/50, 50/200)
- Visualizing entry and exit points on price charts
- Manual walk-through of strategy signals
- Iterating on the logic until it makes sense

**Why it matters**: This is where the actual strategy was born. It shows the thought process of going from "MA crossovers might work" to "here's the exact implementation."

**Key findings**:
- 20/50 crossover catches major trends without too many false signals
- Faster combos (10/30) whipsaw in sideways markets
- Slower combos (50/200) miss too much of the move
- Entry timing is easier than exit timing

**Run it if**: You want to develop a new strategy or understand how the MA crossover was created.

### backtesting.ipynb

**Purpose**: Testing the strategy on historical data to see if it actually works.

**What's inside**:
- Running the backtester with MA crossover strategy
- Testing on different time periods (2023, 2024, full history)
- Testing on different symbols (GLD, SPY, TLT)
- Analyzing performance metrics
- Visualizing equity curves
- Understanding where the strategy wins and loses

**Why it matters**: A strategy that sounds good might perform terribly. Backtesting reveals the truth (or at least historical truth).

**Key findings**:
- MA crossover works better in trending markets
- Choppy/sideways markets kill it
- GLD performance: ~10% annually with reasonable drawdowns
- SPY performance: better in bull markets, worse in volatile periods
- Need better risk management (stop losses)

**Run it if**: You want to test a strategy before risking real money, or you need to evaluate performance objectively.

## How to Use These Notebooks

### First Time Through

Go in order: 01 → 02 → 03 → strategy_development → backtesting

Read the markdown cells. They explain what I was thinking and why.

Run each cell. See the outputs. Understand what each step does.

### When Developing New Strategies

1. Use `research.ipynb` to quickly test ideas
2. Once something looks promising, structure it in `strategy_development.ipynb`
3. Test it thoroughly in `backtesting.ipynb`
4. If it passes backtesting, implement it in `src/strategies/`

### When Analyzing New Symbols

1. Start with `01_data_exploration_and_cleaning.ipynb` - load the new symbol
2. Run through the data quality checks
3. Test your strategy on it in `backtesting.ipynb`
4. See if what worked on GLD works on this new symbol

## Running the Notebooks

```bash
# From project root
cd tradingbot
source venv/bin/activate

# Start Jupyter
jupyter notebook notebooks/

# Or use JupyterLab
jupyter lab notebooks/
```

## Common Workflow Patterns

### Pattern 1: Quick Data Check

```python
# In research.ipynb
from src.data.market_data import MarketData
import matplotlib.pyplot as plt

md = MarketData()
df = md.get_historical_bars('SPY', '1Day', start='2024-01-01', limit=100)

df['close'].plot(figsize=(12, 6))
plt.title('SPY Last 100 Days')
plt.show()

print(df.describe())
```

### Pattern 2: Test Indicator

```python
# In 02_feature_engineering.ipynb
from src.indicators.moving_average import calculate_sma

df = calculate_sma(df, 20)
df = calculate_sma(df, 50)

df[['close', 'sma_20', 'sma_50']].tail(20).plot(figsize=(12, 6))
plt.title('Price with Moving Averages')
plt.show()
```

### Pattern 3: Backtest Strategy

```python
# In backtesting.ipynb
from src.backtest.backtester import Backtester
from src.strategies.momentum_strategy import MovingAverageCrossover

strategy = MovingAverageCrossover(fast_period=20, slow_period=50)
backtester = Backtester(strategy=strategy, initial_capital=10000)

results = backtester.run(df)
print(f"Total Return: {results['total_return']:.2%}")
print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
```

## Tips for Working with These Notebooks

### 1. Start Every Notebook Session With

```python
# Auto-reload modules (so changes in src/ take effect immediately)
%load_ext autoreload
%autoreload 2

import sys
sys.path.append('..')  # Add project root to path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
plt.style.use('seaborn-v0_8-darkgrid')  # Pretty plots
%matplotlib inline
```

### 2. Save Your Outputs

Notebooks save outputs by default. This is good - you can review charts later without re-running everything.

But don't commit giant outputs to git. Clear them before committing:
- Cell → All Output → Clear

### 3. Document Your Thinking

Add markdown cells explaining:
- What you're testing
- Why you chose these parameters
- What you expected vs what you got
- Conclusions

Future you will appreciate it.

### 4. Keep Cells Small

One logical operation per cell. Makes it easier to debug and re-run parts without re-running everything.

### 5. Use Checkpoints

Jupyter auto-saves, but also manually save often (`Ctrl+S`). Notebooks can crash and you'll lose work.

## What's Different from Main Branch

The main branch has a more detailed `docs/notebooks.md` guide that covers the more advanced multi-agent notebooks. This data branch focuses on the basics:

- **Data branch**: 6 notebooks about data analysis and simple strategy development
- **Main branch**: Notebooks about testing AI agents, ML models, and complex strategies

This branch is the foundation. Main branch is the advanced course.

## Transitioning Notebook Work to Code

When you develop something good in a notebook, move it to the codebase:

1. **Extract the logic** from the notebook cells
2. **Add error handling** (notebooks skip this)
3. **Write it as a function or class** in `src/`
4. **Add tests** in `tests/`
5. **Update config** if needed
6. **Document** in README or docs

Example:

**Notebook code**:
```python
df['sma_20'] = df['close'].rolling(20).mean()
```

**Production code** (`src/indicators/moving_average.py`):
```python
def calculate_sma(df, period, column='close', inplace=False):
    """Calculate Simple Moving Average"""
    if not inplace:
        df = df.copy()
    df[f'sma_{period}'] = df[column].rolling(period).mean()
    return df
```

## Learning Path

If you're new to trading or data analysis:

1. **Start with 01** - Understand the data
2. **Then 02** - Learn about indicators
3. **Skip 03 initially** - Stats can wait
4. **Jump to strategy_development** - This is the fun part
5. **Then backtesting** - See if it works
6. **Come back to 03** - Now you'll appreciate the stats

If you're experienced:

1. **Skim 01 and 02** - You know this stuff
2. **Read 03** - Validate assumptions
3. **Focus on strategy_development and backtesting** - The meat

## What I Learned

Going through these notebooks taught me:

- **Data quality matters** - Garbage in, garbage out
- **Simple can work** - MA crossover isn't sophisticated but it's not useless
- **Backtesting is humbling** - Strategies that seem brilliant often aren't
- **Parameters matter** - Small changes (20/50 vs 10/30) make big differences
- **Market regimes exist** - What works in 2023 might not work in 2024

This knowledge fed into building the more sophisticated multi-agent system on main branch.

## Next Steps

After working through these notebooks:

1. Try different indicators in 02
2. Test other strategy ideas in strategy_development
3. Backtest on more symbols and time periods
4. When you find something promising, implement it in `src/`
5. Eventually check out the main branch to see the advanced multi-agent approach

The notebooks are a laboratory. Experiment freely.
