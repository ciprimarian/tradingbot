# Troubleshooting

So things broke. Welcome to software development. Here's a collection of issues I've hit and how to fix them. Hopefully this saves you some time.

## Dashboard Won't Start

### Error: `NameError: name 'List' is not defined`

Yeah, I know about this one. It's in `src/dashboard/bot_manager.py`.

**The problem:** Missing typing imports at the top of the file.

**The fix:**

Open `src/dashboard/bot_manager.py` and add these imports at the very top:

```python
from typing import List, Dict, Optional, Any
```

Should be right after the other imports. Then the dashboard will start fine.

**Why it happened:** I was being lazy and didn't import the typing hints properly. Type hints are nice for documentation but Python needs the imports to actually use them.

## Installation Issues

### TA-Lib Installation Fails

**Error messages like:**
- `fatal error: ta-lib/ta_libc.h: No such file or directory`
- `error: command 'gcc' failed`
- `Cannot find TA-Lib library`

**The problem:** TA-Lib is not a pure Python package. It's a wrapper around a C library, and that C library needs to be installed separately.

**The fix (Linux/Ubuntu):**

```bash
sudo apt-get update
sudo apt-get install ta-lib
```

Or compile from source:

```bash
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
```

Then install the Python wrapper:

```bash
pip install TA-Lib
```

**The fix (Mac):**

```bash
brew install ta-lib
pip install TA-Lib
```

**The fix (Windows):**

This is trickier. You need to:
1. Download pre-compiled TA-Lib from https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
2. Pick the right wheel file for your Python version
3. Install with `pip install <downloaded_wheel_file.whl>`

Or use WSL and follow the Linux instructions.

## API and Connection Issues

### Error: `ALPACA_API_KEY and ALPACA_SECRET_KEY must be set`

**The problem:** Your `.env` file is missing or not being loaded.

**The fix:**

1. Make sure `.env` file exists in the project root
2. Check that it has the right format:

```
ALPACA_API_KEY="your_key_here"
ALPACA_SECRET_KEY="your_secret_here"
ALPACA_PAPER_TRADING="true"
```

3. No extra spaces, use double quotes
4. Verify `python-dotenv` is installed: `pip install python-dotenv`
5. Try loading it manually in Python shell:

```python
from dotenv import load_dotenv
import os
load_dotenv()
print(os.getenv('ALPACA_API_KEY'))
```

If it prints `None`, the file isn't loading. Check the file path.

### Error: `401 Unauthorized` or `Invalid API credentials`

**The problem:** Your Alpaca API keys are wrong or expired.

**The fix:**

1. Go to your Alpaca account dashboard
2. Regenerate your API keys (they expire or can be revoked)
3. Copy the new keys into `.env`
4. Make sure you're using the paper trading keys if `ALPACA_PAPER_TRADING="true"`
5. Restart the bot

### Error: `No data returned for symbol`

**The problem:** Alpaca doesn't have data for that symbol, or your date range is invalid.

**The fix:**

1. Try a common symbol first like `SPY` or `AAPL`
2. Check your date range in `trading_config.yaml` - don't ask for data from the future or too far in the past
3. Some symbols only have limited history on Alpaca
4. Crypto symbols need `/USD` suffix: `BTC/USD` not just `BTC`
5. Test manually:

```python
from src.data.data_manager import DataManager
dm = DataManager()
df = dm.get_historical_data('SPY', '1Day', '2024-01-01', limit=10)
print(df)
```

If that works but your symbol doesn't, it's the symbol.

### Error: `Market is CLOSED` and bot just waits forever

**The problem:** You're trying to trade stocks outside market hours.

**Not really a problem if:**
- It's actually outside market hours (9:30 AM - 4:00 PM ET, Monday-Friday)
- The bot is correctly waiting for market open
- This is expected behavior

**Workarounds if you want to test:**

1. Trade crypto instead (24/7 markets):
   - Change symbol to `BTC/USD` or `ETH/USD`
   - Bot will skip market hours check for crypto

2. Trade commodities with extended hours:
   - Symbols like `GLD` or `GC` have longer trading windows

3. Run a backtest instead of live trading

4. Mock the market clock in the code (only for testing):
   - In `main.py`, comment out the market hours check
   - Don't do this for real trading

## Runtime Issues

### Bot keeps buying and selling the same stock

**The problem:** The strategy is whipsawing in a choppy market.

**The fix:**

1. Increase the confidence threshold in `main.py`:

```python
coordinator = AgentCoordinator(
    agents=agents,
    min_confidence_threshold=0.7  # higher = fewer trades
)
```

2. Add a minimum holding period check
3. Reduce agent weights for the flaky agents
4. Switch to a different aggregation method (try `UNANIMOUS`)
5. This might just be a bad market for your strategy

### ML Agent always returns HOLD

**The problem:** Model isn't trained or training failed.

**The fix:**

1. Check if the model file exists: `data/processed/ml_model.pkl`
2. If not, the agent will try to auto-train on first run
3. Make sure you have enough historical data (at least 100 bars)
4. Try manually training:

```python
from src.agents.ml_prediction_agent import MLPredictionAgent
from src.data.data_manager import DataManager

agent = MLPredictionAgent()
dm = DataManager()
data = dm.get_historical_data('GLD', '1Day', '2024-01-01', limit=500)
data = dm.prepare_for_agents(data)
agent.train(data)
```

5. Check logs for training errors

### Planning Agent is really slow

**The problem:** A* search with long lookahead takes forever.

**The fix:**

1. Reduce lookahead in agent config:

```python
PlanningAgent(config={"lookahead": 3})  # instead of 5+
```

2. Reduce `max_iterations` in the config
3. Or just reduce the agent's weight so it matters less
4. Planning is computationally expensive, that's the tradeoff

### Memory usage keeps growing

**The problem:** Probably accumulating data in memory without cleanup.

**The fix:**

1. Restart the bot periodically (cron job or systemd timer)
2. Check for data leaks in agents - are they storing all historical data?
3. Limit the amount of historical data fetched (reduce `limit` in config)
4. Clear old log files from `logs/` directory

## Data Issues

### Indicators are all NaN

**The problem:** Not enough data to calculate the indicators.

**The fix:**

Moving averages need at least N bars to calculate:
- SMA(50) needs 50+ bars
- RSI(14) needs 14+ bars

Increase the `limit` in your config:

```yaml
data:
  limit: 1000  # fetch more bars
```

Or check if your data source is returning valid data:

```python
df = data_manager.get_historical_data(...)
print(df.tail())  # should show actual price data
```

### Backtest results look too good to be true

**The problem:** They probably are.

**Possible causes:**

1. **Overfitting** - Strategy is tuned perfectly for the test period but won't work going forward
2. **Look-ahead bias** - Accidentally using future data to make past decisions
3. **Survivorship bias** - Only tested on stocks that survived, not the ones that went to zero
4. **Cherry-picking** - Tested on the one time period where the strategy worked

**The fix:**

1. Test on out-of-sample data (different time period)
2. Test on multiple symbols
3. Test on different market conditions (bull market, bear market, sideways)
4. Reduce complexity and parameters
5. Paper trade for weeks before believing the backtest

If it looks too good, it probably is.

## Logging Issues

### No logs appearing

**The problem:** Logging isn't configured or files aren't being written.

**The fix:**

1. Check if `logs/` directory exists (it should auto-create)
2. Check permissions on the directory
3. Look at `src/config/logging.conf` for log configuration
4. Try logging to console instead:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

5. Check if logs are going to console but not files (might be a file handler issue)

### Log files are huge

**The problem:** Debug logging for everything creates massive files.

**The fix:**

1. Change log level from DEBUG to INFO or WARNING
2. Add log rotation to clean up old logs
3. Delete old log files manually: `rm logs/*.log.old`
4. Consider logging to a database or log aggregation service for production

## Dependency Conflicts

### Conflicting package versions

**Error like:** `ERROR: pip's dependency resolver does not currently take into account all the packages that are installed...`

**The fix:**

1. Nuke your virtual environment and start fresh:

```bash
deactivate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

2. If that doesn't work, install dependencies one at a time and see which one breaks
3. Might need to pin specific versions in `requirements.txt`
4. Check if you're using Python 3.13 - some packages might not have wheels yet, try 3.11

## Performance Issues

### Bot is too slow

**The problem:** Taking too long between trading decisions.

**Causes and fixes:**

1. **API calls are slow** - Alpaca servers might be congested, nothing you can do
2. **ML model is slow** - Reduce model complexity or use a faster algorithm
3. **Too much data** - Reduce the number of historical bars fetched
4. **Planning agent** - Reduce lookahead or disable it
5. **Network latency** - Get better internet or move to cloud near Alpaca servers

Check logs to see where time is spent.

### Bot missed a good trade

**The problem:** Signals arrived too late or confidence threshold prevented action.

**The fix:**

1. Reduce the `CHECK_INTERVAL` in `main.py` (check more frequently)
2. Lower the confidence threshold (more trades but lower quality)
3. This is the nature of algorithmic trading - you'll miss some
4. Consider that you also missed bad trades by being cautious

## Testing and Development

### Tests are failing

**The problem:** Tests are out of sync with code or data issues.

**The fix:**

1. Update the tests to match current code
2. Check if tests are trying to hit real APIs (they shouldn't - use mocks)
3. Make sure test data files exist
4. Run one test at a time to isolate the issue:

```bash
pytest tests/test_agents.py::TestTechnicalAgent::test_analyze -v
```

### Can't reproduce an issue

**The problem:** Random data or timing makes issues non-deterministic.

**The fix:**

1. Set random seeds for reproducibility:

```python
import random
import numpy as np
random.seed(42)
np.random.seed(42)
```

2. Save the exact data that caused the issue
3. Use a debugger and breakpoints
4. Add more logging to capture state
5. Write a test case that reproduces it

## General Debugging Strategy

When something breaks and you don't know why:

1. **Read the error message carefully** - It usually tells you exactly what's wrong
2. **Check the logs** - Look in `logs/trading_bot.log` for details
3. **Isolate the problem** - Can you reproduce it with a minimal test?
4. **Google the error** - Someone else has hit this before
5. **Check your assumptions** - Are you sure the data looks like you think it does?
6. **Add print statements** - Sometimes old school debugging is best
7. **Ask for help** - Describe the problem clearly with error messages and context

## Still Stuck?

If none of this helps:

1. Check if there's an update to the code that fixes it
2. Try the nuclear option: fresh clone, fresh venv, fresh install
3. Verify your Python version matches what I used (3.10 or 3.11)
4. Check if it's a known issue I mentioned in the docs
5. Remember this is experimental software, some things just don't work yet

Good luck. Debugging is half the fun of programming.
