# Development Guide

So you want to extend this thing or fix something. Good. Here's how the development workflow works and how to not break everything.

## Development Setup

Beyond the basic setup in the setup guide, if you're going to be developing:

```bash
# Install dev dependencies
pip install pytest pytest-cov black flake8 mypy

# Install in editable mode so code changes are immediate
pip install -e .
```

I haven't created a `setup.py` yet so that last command won't work. But you should add one if you're doing serious development.

## Code Style

I don't have strict style rules but here's what I generally try to follow:

- Use 4 spaces for indentation (not tabs)
- Keep lines under 100 characters when reasonable
- Use descriptive variable names (no single letters unless it's a loop counter)
- Add docstrings to classes and complex functions
- Type hints are nice but I'm inconsistent about using them

Run black for auto-formatting:

```bash
black src/
```

Run flake8 to catch obvious issues:

```bash
flake8 src/ --max-line-length=100
```

I don't enforce these strictly. Code that works beats perfect code that doesn't.

## Project Layout Philosophy

Each directory has a purpose:

- `src/agents/` - Each agent is independent, shouldn't depend on other agents
- `src/brokers/` - Abstraction layer, should be swappable
- `src/data/` - Data fetching and processing, no trading logic
- `src/strategies/` - Classic strategy implementations for backtesting
- `src/risk_management/` - Position sizing and portfolio management
- `src/backtest/` - Backtesting framework, separate from live trading

Keep things modular. If you need functionality from another module, import it cleanly. Don't create circular dependencies.

## Adding a New Agent

This is probably the most common thing you'd want to do. Here's the pattern:

1. Create new file in `src/agents/`, like `my_new_agent.py`

2. Import base classes:

```python
from src.agents.common import BaseAgent, AgentSignal, SignalType
from src.utils.logger import get_logger
import pandas as pd
```

3. Define your agent class:

```python
class MyNewAgent(BaseAgent):
    def __init__(self, name="MyAgent", weight=1.0, config=None):
        super().__init__(name, weight, config)
        self.logger = get_logger(__name__)
        # Your custom initialization here
    
    def analyze(self, data: pd.DataFrame, **kwargs) -> AgentSignal:
        # Your analysis logic here
        # Return an AgentSignal with signal_type, confidence, reasoning
        
        return AgentSignal(
            signal_type=SignalType.BUY,
            confidence=0.7,
            reasoning="Your reasoning here"
        )
```

4. Add it to the coordinator in `src/main.py`:

```python
from src.agents.my_new_agent import MyNewAgent

agents = [
    # ... existing agents ...
    MyNewAgent(name="MyAgent", weight=0.2),
]
```

5. Test it in isolation first:

```python
from src.agents.my_new_agent import MyNewAgent
from src.data.data_manager import DataManager

agent = MyNewAgent()
dm = DataManager()
data = dm.get_historical_data('SPY', '1Day', '2024-01-01', limit=100)
data = dm.prepare_for_agents(data)
signal = agent.analyze(data)
print(signal)
```

## Adding a New Indicator

If you need a technical indicator that's not in the `indicators/` directory:

1. Create or edit a file in `src/indicators/`

2. Follow this pattern:

```python
import pandas as pd
import numpy as np

def calculate_my_indicator(
    df: pd.DataFrame,
    period: int = 14,
    column: str = 'close',
    inplace: bool = False
) -> pd.DataFrame:
    """
    Calculate my custom indicator.
    
    Args:
        df: DataFrame with OHLCV data
        period: Lookback period
        column: Column to calculate on
        inplace: Whether to modify df or return a copy
    
    Returns:
        DataFrame with new column 'my_indicator_{period}'
    """
    if not inplace:
        df = df.copy()
    
    # Your calculation here
    df[f'my_indicator_{period}'] = ...
    
    return df
```

3. Add it to `data_manager.prepare_for_agents()` if all agents should use it

4. Or calculate it in your specific agent if it's specialized

## Writing Tests

I need to write more tests. Here's the pattern when you do:

```python
# tests/test_my_feature.py
import pytest
import pandas as pd
from src.agents.my_agent import MyAgent

def test_my_agent_basic():
    """Test basic functionality"""
    agent = MyAgent()
    
    # Create sample data
    data = pd.DataFrame({
        'close': [100, 101, 102, 103, 104],
        'volume': [1000, 1100, 1200, 1300, 1400]
    })
    
    signal = agent.analyze(data)
    
    assert signal is not None
    assert signal.confidence >= 0.0
    assert signal.confidence <= 1.0

def test_my_agent_edge_cases():
    """Test edge cases"""
    agent = MyAgent()
    
    # Empty data
    empty_df = pd.DataFrame()
    signal = agent.analyze(empty_df)
    assert signal.signal_type == SignalType.HOLD
    
    # Single row
    single_row = pd.DataFrame({'close': [100]})
    signal = agent.analyze(single_row)
    # Should handle gracefully
```

Run tests with:

```bash
pytest tests/ -v
pytest tests/test_my_feature.py -v  # specific file
pytest -k "test_my_agent" -v        # by name pattern
```

## Debugging Tips

### Use the Python debugger

Add this where you want to break:

```python
import pdb; pdb.set_trace()
```

Or use VS Code's debugger with breakpoints.

### Log everything

```python
from src.utils.logger import get_logger
logger = get_logger(__name__)

logger.debug("Detailed info for debugging")
logger.info("General info")
logger.warning("Something weird happened")
logger.error("Something broke")
```

Logs go to `logs/trading_bot.log` by default.

### Test with fake data

Don't always use real API calls when testing. Create fake data:

```python
import pandas as pd
import numpy as np

# Generate fake OHLCV data
dates = pd.date_range('2024-01-01', periods=100, freq='D')
fake_data = pd.DataFrame({
    'timestamp': dates,
    'open': np.random.randn(100).cumsum() + 100,
    'high': np.random.randn(100).cumsum() + 102,
    'low': np.random.randn(100).cumsum() + 98,
    'close': np.random.randn(100).cumsum() + 100,
    'volume': np.random.randint(1000, 10000, 100)
})
```

### Use the notebook

Jupyter notebooks are great for experimentation:

```bash
jupyter notebook notebooks/
```

Test code interactively before integrating it into the main system.

## Git Workflow

How I work with git on this project:

1. Main branch (`main`) is supposed to be stable
2. Development happens on `dev` branch
3. Features get their own branches off `dev`

```bash
# Create feature branch
git checkout dev
git pull origin dev
git checkout -b feature/my-cool-feature

# Make changes, commit often
git add .
git commit -m "descriptive message"

# When done, merge back to dev
git checkout dev
git merge feature/my-cool-feature

# Delete feature branch
git branch -d feature/my-cool-feature
```

Commit messages should be short but descriptive:
- `feat: add new ML agent using LSTM`
- `fix: handle NaN values in RSI calculation`
- `docs: update setup guide with Windows instructions`
- `refactor: simplify coordinator aggregation logic`

## Making Changes to the Core Loop

The main trading loop in `src/main.py` is delicate. If you're modifying it:

1. Test thoroughly in paper trading first
2. Add error handling for edge cases
3. Don't remove the existing error handling and logging
4. Consider what happens if API calls fail mid-execution
5. Make sure the bot can still be stopped with Ctrl+C

## Performance Optimization

If something is slow:

1. Profile it first to find the actual bottleneck:

```python
import time
start = time.time()
# code here
print(f"Took {time.time() - start:.2f} seconds")
```

2. Common bottlenecks:
   - API calls (can't fix, just wait)
   - ML model predictions (reduce complexity or cache)
   - Large DataFrame operations (use vectorized operations)
   - Looping through rows (use pandas built-ins instead)

3. Don't optimize prematurely. Readable code beats fast code until it doesn't.

## Database Integration (Future)

Right now we save data to parquet files. If you want to add a proper database:

1. There's already SQLAlchemy in the dependencies
2. Define models in `src/data/models.py` or similar
3. Create a database manager class
4. Make it optional - file-based should still work
5. Add migrations for schema changes

I haven't done this yet because parquet files work fine for my use case.

## Adding New Brokers

To support a broker other than Alpaca:

1. Create `src/brokers/new_broker.py`
2. Implement the same methods as `AlpacaBroker`:
   - `submit_order()`
   - `get_market_clock()`
   - `get_account()`
   - `get_position()`
   - etc.
3. Make `BaseBroker` an actual abstract base class with these methods
4. Switch broker in config or `main.py`

Should be plug-and-play if you follow the same interface.

## Configuration Management

Config is split between:
- `trading_config.yaml` - Trading parameters, symbols, timeframes
- `.env` - API keys and secrets
- Code constants - Thresholds, weights, etc.

Ideally more stuff should move to config files. But changing code is easier than parsing YAML sometimes.

If you add new config options:
1. Add them to `trading_config.yaml`
2. Update `src/config/settings.py` to load them
3. Document them in the setup guide
4. Provide sensible defaults

## Documentation

When you add features, update the docs:

- User-facing features → README or setup guide
- Architecture changes → architecture doc
- New strategies → trading strategies doc
- Common problems → troubleshooting doc

Write docs like you're explaining to yourself six months from now. That's who will read them.

## Pull Request Checklist

Before submitting a PR (to yourself or others):

- [ ] Code runs without errors
- [ ] Added tests for new functionality
- [ ] Updated relevant documentation
- [ ] Ran linting and formatting
- [ ] Tested in paper trading mode
- [ ] Checked logs for unexpected errors
- [ ] Didn't commit API keys or secrets
- [ ] Commit messages are descriptive

## Development Environment

My setup for reference:
- OS: Linux (Ubuntu)
- Python: 3.11
- Editor: VS Code with Python extension
- Virtual environment: venv
- Terminal: bash

Your mileage may vary on Windows or Mac. Most stuff should work but TA-Lib installation is different.

## Common Development Tasks

### Add a new aggregation method

Edit `src/agents/agent_coordinator.py`:

1. Add enum value to `AggregationMethod`
2. Add method to `AgentCoordinator` class
3. Update `aggregate_signals()` to call it
4. Test it

### Change position sizing logic

Edit `src/risk_management/portfolio_optimizer.py` or create new position sizer. Then update `main.py` to use it.

### Add a new data source

Create new class in `src/data/` that fetches from different API. Make `DataManager` use it based on config.

### Implement a new backtest metric

Edit `src/backtest/performance_analyzer.py`, add calculation method, update the reports.

## Learning Resources

If you want to understand the concepts better:

- **Technical Analysis**: "Technical Analysis of the Financial Markets" by Murphy
- **Machine Learning**: scikit-learn documentation, Andrew Ng's course
- **Algorithmic Trading**: "Advances in Financial Machine Learning" by Lopez de Prado
- **AI Planning**: "Artificial Intelligence: A Modern Approach" by Russell & Norvig
- **Python**: "Fluent Python" by Ramalho

Or just Google stuff and experiment. That's what I did.

## Final Advice

- Start small, test thoroughly
- Paper trade before real money
- Logs are your friend
- When in doubt, add more error handling
- Markets are unpredictable, code defensively
- Have fun with it

Now go build something cool.
