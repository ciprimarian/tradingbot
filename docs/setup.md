# Setup

Getting this trading bot running is straightforward if you know your way around Python. If you don't, well, buckle up.

## Prerequisites

Things you need installed on your machine before anything else:

- **Python 3.9+** - Preferably 3.10 or 3.11. The code might work on 3.9 but I haven't tested it thoroughly. Don't use 3.8 or older, some dependencies won't play nice.
- **pip** - Comes with Python usually. If not, install it.
- **virtualenv or venv** - For creating isolated Python environments. You could use conda too if that's your thing.
- **Git** - For cloning the repo and version control.
- **TA-Lib** - This one's annoying. It's a C library for technical analysis. On Linux you can usually `apt-get install ta-lib` or compile from source. On Mac, `brew install ta-lib`. On Windows, good luck. There are pre-compiled wheels floating around on the internet.

Optional but recommended:
- **Docker** - If you want to run everything in containers. I started a `docker-compose.yml` but never finished it.
- **PostgreSQL** - If you plan to store historical data in a database instead of flat files. Not required for basic operation.

## Installation

### 1. Clone the repo

```bash
git clone <your-repo-url> tradingbot
cd tradingbot
```

Replace `<your-repo-url>` with wherever you're hosting this.

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt now.

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This will take a while. There's a lot of stuff: pandas, numpy, scikit-learn, TensorFlow, PyTorch, transformers for NLP, CCXT for crypto exchanges, etc. Not all of it is strictly necessary if you're just testing, but I included everything I might use.

If the TA-Lib install fails, you need to install the C library first (see Prerequisites above).

### 4. Set up environment variables

Create a `.env` file in the project root. Here's what mine looks like:

```
ALPACA_BASE_URL="https://paper-api.alpaca.markets"
ALPACA_API_KEY="your_alpaca_api_key_here"
ALPACA_SECRET_KEY="your_alpaca_secret_key_here"
```

**IMPORTANT:** Don't commit this file to git. It's already in `.gitignore` but double-check. These are your API credentials.

How to get Alpaca keys:
1. Go to https://alpaca.markets/
2. Sign up for a free account
3. Use paper trading (fake money) to start
4. Generate API keys from the Alpaca website
5. Paste them into `.env`

The `ALPACA_BASE_URL` is the paper trading endpoint. When you're ready for real money (scary), change it to `https://api.alpaca.markets`. But seriously, test thoroughly with paper trading first.

### 5. Configure the bot

Edit `src/config/trading_config.yaml` to set your trading preferences:

```yaml
trading:
  symbol: "GLD"  # What you want to trade. GLD is a gold ETF.
  trade_quantity: 1  # How many shares per trade
  
data:
  timeframe: "1Day"  # Candlestick timeframe: 1Min, 5Min, 1Hour, 1Day, etc.
  start_date: "2024-01-01"  # How far back to fetch historical data
  limit: 1000  # Max number of bars to fetch
```

For testing, I recommend:
- A stable ETF like `GLD` or `SPY` (not volatile penny stocks)
- Small `trade_quantity` like 1 or 2
- Longer `timeframe` like `1Day` so you're not constantly trading

### 6. Test the setup

Let's make sure everything is wired up correctly.

```bash
python -c "from src.config.settings import CONFIG; print(CONFIG)"
```

If that prints out a config dictionary without errors, you're good.

Try fetching some data:

```bash
python -c "from src.data.data_manager import DataManager; dm = DataManager(); df = dm.get_historical_data('GLD', '1Day', '2024-01-01', limit=10); print(df.head())"
```

This should print out 10 rows of OHLCV data for GLD. If you get an API error, check your Alpaca keys.

## Running the Bot

### Manual mode

Just run the main script:

```bash
python -m src.main
```

You'll see a ton of logs. The bot will:
1. Check if the market is open
2. Fetch data and analyze it
3. Make trading decisions
4. Execute trades (on paper account)
5. Sleep for 60 seconds
6. Repeat

Press `Ctrl+C` to stop it gracefully.


### Dashboard (Removed)

The web dashboard and all related code have been removed from this repository. Please ignore any references to it in older documentation or comments.

## Project Structure Quick Tour

Here's where everything lives:

```
tradingbot/
├── src/
│   ├── main.py              # Main bot loop, start here
│   ├── agents/              # All the trading agents
│   ├── brokers/             # Broker API wrappers (Alpaca, etc.)
│   ├── data/                # Data fetching and management
│   ├── indicators/          # Technical indicators (SMA, RSI, etc.)
│   ├── strategies/          # Trading strategies
│   ├── risk_management/     # Portfolio management, position sizing
│   ├── backtest/            # Backtesting engine
│   ├── ~~dashboard/           # Web UI~~
│   ├── config/              # Configuration files
│   └── utils/               # Helper functions, logging
├── data/                    # Stored data (parquet/CSV files)
├── logs/                    # Log files
├── notebooks/               # Jupyter notebooks for research
├── tests/                   # Unit tests
├── docs/                    # Documentation (you are here)
├── requirements.txt         # Python dependencies
└── .env                     # API keys (not in git)
```

## Common Issues

### "ModuleNotFoundError: No module named 'talib'"

You didn't install TA-Lib properly. It's not a pure Python package, it needs the C library. See Prerequisites.

### "ALPACA_API_KEY and ALPACA_SECRET_KEY must be set"

Your `.env` file is missing or not being loaded. Make sure it's in the project root and contains the keys. Also check that `python-dotenv` is installed.

### "Market is CLOSED"

The bot detected the market isn't open. If you're trading stocks/ETFs, they only trade during US market hours (9:30am-4pm ET, Mon-Fri). The bot will wait until the market reopens.

If you're testing and don't want to wait, either:
- Switch to a crypto symbol (like `BTCUSD`) which trades 24/7
- Mock the market clock in the code
- Run a backtest instead of live trading

### "No data returned for symbol"

Alpaca might not have data for that symbol, or your date range is off. Try a common symbol like `SPY` or `AAPL` and a recent date range.


### Dashboard Troubleshooting (Removed)

The dashboard is no longer part of this project. All related troubleshooting steps have been removed.

## Backtesting (Testing Without Real Money)

Before running the bot live (even on paper), you probably want to backtest your strategy on historical data.

```bash
python -m src.backtest.backtester
```

This runs your strategy against past data and shows you how it would've performed. Adjust parameters in `trading_config.yaml` under the `backtest` section.

Check the results in `data/backtest_results.csv` or whatever output file it generates.

## Next Steps

Once you have the bot running:

1. **Monitor it closely.** Even in paper trading, you want to make sure it's behaving as expected.
2. **Check the logs.** They're in the `logs/` directory. Read them to understand what the agents are deciding and why.
3. **Tune the agents.** Adjust their weights in `src/main.py`. Try different aggregation methods in the coordinator.
4. **Add your own agent.** Subclass `BaseAgent` and implement your own analysis logic. See the existing agents for examples.
5. **Backtest extensively.** Test on different time periods, different symbols, different market conditions. Don't trust a strategy that only works in a bull market.
6. **Paper trade for weeks.** Seriously. Don't rush to real money. Let it run on paper for at least a month and watch how it performs.

## Going Live (Real Money)

When you're finally ready to use real money:

1. Change `ALPACA_BASE_URL` in `.env` to `https://api.alpaca.markets`
2. Generate new API keys from Alpaca's live trading dashboard
3. Start with a very small amount of capital
4. Keep `trade_quantity` low
5. Monitor obsessively for the first week
6. Be prepared to shut it down if it does something stupid

And remember: this is experimental software written by someone (me) who is not a professional trader or a financial advisor. Use at your own risk. Don't bet money you can't afford to lose.

## Troubleshooting Tips

If something breaks:
- Read the error message carefully
- Check the logs in `logs/trading_bot.log`
- Verify your API keys and network connection
- Try the failing operation manually in a Python shell to isolate the issue
- Google the error (seriously, half of programming is Googling errors)
- Check if the broker API is down (Alpaca has status pages)

If all else fails, blow away your `venv`, recreate it, reinstall dependencies, and try again. Sometimes that's faster than debugging dependency hell.

Good luck.
