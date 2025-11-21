# Trading Bot

An algorithmic trading bot that uses multiple AI agents to make trading decisions. Because one flawed strategy is risky, but several flawed strategies arguing with each other? That might actually work.

## What This Thing Is

This is a multi-agent AI trading system. It connects to Alpaca (free brokerage API) and trades stocks, ETFs, or crypto based on what a committee of AI agents decides to do.

Instead of trusting a single strategy, I built several different agents:
- Technical analysis agent (reads charts and indicators)
- Machine learning agent (tries to predict price movements)
- Planning agent (thinks ahead using A* search)
- Risk management agent (stops us from doing stupid things)
- Reasoning agent (makes sense of contradictory signals)

They each analyze the market, vote on what to do, and the system combines their opinions. If enough of them agree with decent confidence, we trade. Otherwise we hold.

It's built for paper trading and learning. If it makes you money, great. If it loses you money, well, that's on you.

## Quick Start

If you just want to see it run:

```bash
# Clone and setup
git clone https://github.com/ciprimarian/tradingbot.git
cd tradingbot
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your Alpaca API keys

# Run
python -m src.main
```

For the full setup process, check out [setup.md](setup.md).

## Documentation

Start here if you're trying to figure out what's going on:

**Getting Started**
- [Setup Guide](setup.md) - Get this running on your machine
  
**Understanding the System**
- [Architecture](architecture.md) - How everything fits together
- [System Architecture](system_architecture.md) - Detailed breakdown
- [Trading Strategies](trading_strategies.md) - What each agent actually does

**Working on It**
- [Development](development.md) - If you want to extend or modify this
- [Troubleshooting](troubleshooting.md) - When things go wrong
- [Deployment](deployment.md) - How to deploy the docs (yeah, meta)

## How It Works

The bot's main loop is pretty straightforward:

1. Check if market is open (crypto trades 24/7 though)
2. Fetch latest market data and calculate indicators
3. Ask each agent what they think we should do
4. Each agent returns BUY/SELL/HOLD with a confidence score
5. Coordinator aggregates everything using confidence weighting
6. If we're confident enough, calculate position size and trade
7. Wait 60 seconds, repeat

Read [architecture.md](architecture.md) if you want all the messy details.

## Current Status

**Works:**
- Fetches real market data from Alpaca
- Runs multiple trading agents with different strategies
- Aggregates signals using various methods
- Executes trades on paper account
- Logs everything obsessively
- Includes backtesting framework

**Rough edges:**
- Some agents more developed than others
- Mean reversion strategy is empty
- Could use more tests

## Safety Notes

Read this part:

- **Start with paper trading** - Default is Alpaca's paper API. Keep it that way.
- **Test extensively** - Run backtests. Paper trade for weeks. Watch what it does.
- **Start small** - If you go live, use tiny positions. Like 1-2 shares.
- **Monitor constantly** - Don't set and forget. Check logs. Watch trades.
- **Markets are unpredictable** - Even good bots lose money when things change.
- **This is experimental** - Built for learning, not production trading.

Don't bet money you can't afford to lose.

## Documentation Versions

This documentation is synced with the repo branches. Each branch has its own version:

- **main** - Stable, production version
- **dev** - Latest development, might be broken
- **data** - Data-focused variant

When this is deployed online, you'll be able to switch between versions to see what's different.

## Contributing

Want to improve this?

1. Fork it
2. Make a branch
3. Do your thing
4. Write tests if you're feeling responsible
5. Submit a PR

Or just fork it and go wild. Code's here to learn from.

## License

Do what you want with it. If it makes money, cool. If it loses money, not my problem. No warranty, no guarantees.

## Why I Built This

Wanted to learn about:
- Algorithmic trading
- Multi-agent AI systems
- Machine learning for time series
- Real-world API integration
- Building something that trades actual money (even if fake money)

Best way to learn is to build something real. This is that thing.

---

Built with coffee, confusion, and way too many Stack Overflow tabs.
