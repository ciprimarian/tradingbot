# Trading Bot

An algorithmic trading bot that uses multiple AI agents to make trading decisions. Because one flawed strategy is risky, but several flawed strategies arguing with each other? That might actually work.

## What This Is

This is a multi-agent AI trading system built in Python. It connects to Alpaca (a brokerage with a free API) and trades stocks, ETFs, or crypto based on what a committee of AI agents decides to do.

Instead of relying on a single trading strategy, I built several different agents:
- Technical analysis agent (reads charts and indicators)
- Machine learning agent (predicts price movements with Random Forest)
- Planning agent (uses A* search to plan multi-step trades)
- Risk management agent (makes sure we don't do anything too stupid)
- Reasoning agent (tries to make sense of conflicting signals)

They each analyze the market, vote on what to do, and the system aggregates their opinions. If enough of them agree with high confidence, we make a trade. Otherwise we hold.

It's designed for paper trading and learning, not for making you rich. Though if it does make you rich, feel free to send me a postcard.

## Current Status

Works on my machine. Probably works on yours too.

Things that work:
- Fetches real market data from Alpaca
- Runs multiple trading agents with different strategies
- Aggregates signals using configurable methods
- Executes trades (on paper account)
- Logs everything obsessively
~~Has a web dashboard for monitoring (when the import bug is fixed)~~
- Includes backtesting framework

Things that are rough:
~~Dashboard has a missing import that crashes it on startup~~
- Some agents are more developed than others
- The mean reversion strategy file is empty
- No automated tests yet (I know, I know)
- Documentation was written at 2am and it shows

## Quick Start

If you just want to see it run:

```bash
# Clone the repo
git clone https://github.com/ciprimarian/tradingbot.git
cd tradingbot

# Set up Python environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template and add your API keys
cp .env.example .env
# Edit .env with your Alpaca API keys

# Run the bot
python -m src.main
```

For detailed setup instructions, see [docs/setup.md](docs/setup.md).

## What You Need

- Python 3.9 or higher
- An Alpaca account (free, sign up at alpaca.markets)
- TA-Lib C library installed
- About 30 minutes to get everything configured

See the setup doc for detailed prerequisites and troubleshooting.

## Project Structure

```
tradingbot/
├── src/               # All the code
│   ├── agents/        # Trading agents (the brains)
│   ├── brokers/       # Broker API wrappers
│   ├── data/          # Data fetching and management
│   ├── strategies/    # Classic trading strategies
│   ├── risk_management/  # Portfolio and risk tools
│   ├── backtest/      # Backtesting engine
│   ├── ~~dashboard/     # Web UI (Flask + SocketIO)~~
│   └── config/        # Configuration files
├── tests/             # Unit tests (need to write more)
├── notebooks/         # Jupyter notebooks for research
├── docs/              # Documentation (start here)
├── data/              # Stored data and models
└── logs/              # Log files
```

## Documentation

I wrote actual documentation that's meant to be read by humans:

**Online:** https://ciprimarian.github.io/tradingbot/

Or read locally:

- **[Setup Guide](docs/setup.md)** - How to get this running on your machine
- **[Architecture](docs/architecture.md)** - How the system is structured and why
- **[Trading Strategies](docs/trading_strategies.md)** - Explanation of each agent's logic

Read these. They're not the usual corporate documentation BS. They're written like I'm explaining this to myself six months from now when I've forgotten everything.

The online docs are also available for dev and data branches if you want to see what's different.

## How It Works (Quick Version)

1. Bot checks if market is open (unless trading crypto which is 24/7)
2. Fetches latest market data and calculates technical indicators
3. Asks each agent "what do you think we should do?"
4. Each agent returns a signal (BUY/SELL/HOLD) with a confidence level
5. Coordinator aggregates all the signals using confidence weighting
6. If the final signal is confident enough, calculate position size
7. Execute the trade through Alpaca
8. Wait 60 seconds, repeat

See [docs/architecture.md](docs/architecture.md) for the detailed version with all the messy details.

## Configuration

Main config file is `src/config/trading_config.yaml`:

```yaml
trading:
  symbol: "GLD"           # What to trade
  trade_quantity: 1       # Max shares per trade

data:
  timeframe: "1Day"       # Candlestick interval
  start_date: "2024-01-01"
  limit: 1000             # Bars to fetch

backtest:
  initial_capital: 10000
  strategy: "moving_average_crossover"
```

Environment variables go in `.env`:
```
ALPACA_API_KEY="your_key"
ALPACA_SECRET_KEY="your_secret"
ALPACA_PAPER_TRADING="true"  # ALWAYS start with paper trading
```

## Backtesting

Before running live (even on paper), backtest your strategy:

```bash
python -m src.backtest.backtester
```

This runs your strategy against historical data and tells you how it would've performed. Useful for catching obviously broken strategies before they lose money.

Results get saved to `data/backtest_results.csv`.


## Web Dashboard (Removed)

The web dashboard has been removed from this repository and is no longer available or supported. All dashboard-related code and instructions have been deleted. Please ignore any references to the dashboard in older documentation or comments.

## Agent Weights and Tuning

You can adjust how much each agent influences the final decision in `src/main.py`:

```python
agents = [
    TechnicalAnalysisAgent(name="TechnicalAgent", weight=0.25),
    MLPredictionAgent(name="MLAgent", weight=0.30),
    TradingPlannerAgent(name="PlannerAgent", weight=0.15),
    # etc
]
```

Higher weight = more influence. They don't have to sum to 1.0 (controlled chaos).

You can also change the aggregation method:
- `CONFIDENCE_WEIGHTED` - Default, balances agent weights and confidence
- `WEIGHTED_AVERAGE` - Just uses agent weights
- `MAJORITY_VOTE` - Most common signal wins
- `UNANIMOUS` - Only acts when all agents agree (very conservative)

## Running Tests

I should write more tests. For now:

```bash
pytest tests/ -v
```

Code coverage report:

```bash
pytest --cov=src --cov-report=html
```

## Known Issues

Things I'm aware of and will fix when I get around to it:

~~1. Dashboard crashes on startup (missing typing imports)~~
2. Mean reversion strategy is not implemented
3. Reasoning agent logic is incomplete
4. No proper error handling in some API calls
5. The ML model sometimes overfits on limited data
6. Planning agent is slow with longer lookahead periods

If you find more issues, that's called "finding opportunities for improvement."

## Safety Notes

Read this part carefully:

- **START WITH PAPER TRADING** - The bot defaults to Alpaca's paper trading API. Keep it that way until you're very confident.
- **Test extensively** - Run backtests. Paper trade for weeks. Watch it make decisions and make sure they make sense.
- **Start small** - When you do go live, use tiny position sizes. Like 1-2 shares max.
- **Monitor constantly** - Don't just set it and forget it. Check the logs. Watch the trades.
- **Markets are unpredictable** - Even the best bot can lose money when conditions change. Have stop losses.
- **This is experimental** - I built this to learn about algorithmic trading and AI. It's not professionally audited trading software.

Don't bet money you can't afford to lose. Seriously.

## Contributing

If you want to improve this:

1. Fork it
2. Create a feature branch
3. Make your changes
4. Write tests (please)
5. Submit a PR

Or just fork it and do your own thing. The code is here for learning.

## Dependencies

Main libraries used:
- `pandas` & `numpy` - Data manipulation
- `scikit-learn` - Machine learning
- `ta-lib` - Technical indicators
- `alpaca-py` - Broker API (through requests)
~~- `flask` & `flask-socketio` - Web dashboard~~
- `pytorch` & `tensorflow` - ML frameworks (for future agents)
- `transformers` - NLP for sentiment analysis

See `requirements.txt` for full list.

## License

Do whatever you want with this code. If it makes you money, great. If it loses you money, that's on you. No warranty, no guarantees, use at your own risk.

## Why I Built This

I wanted to learn about:
- Algorithmic trading strategies
- Multi-agent AI systems
- Machine learning for time series
- AI planning algorithms
- Real-world API integration
- Building something that trades actual money (even if it's fake money)

Figured the best way to learn was to build something real. This is that thing.

If you're learning too, hope this helps. If you're an experienced trader looking at my code and thinking "this kid has no idea what he's doing," you're probably right. But at least I'm trying.

## Contact

If you have questions or found this useful, feel free to reach out. Or don't. The code speaks for itself.

## Acknowledgments

Built with coffee, confusion, and Stack Overflow.

Thanks to:
- Alpaca for the free API
- The Python trading community for all the open source libraries
- Past me for documenting things, making it slightly easier for present me

Now go make something cool.
