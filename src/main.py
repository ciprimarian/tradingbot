# src/main.py

import sys
import time

from src.utils.common_imports import get_logger
from src.brokers.alpaca_broker import AlpacaBroker
from src.data.market_data import MarketData
from src.indicators import moving_average
from src.strategies.momentum_strategy import MovingAverageCrossover
from src.risk_management.portfolio_manager import PortfolioManager
from src.config.settings import CONFIG

# Initialize logger
logger = get_logger(__name__)

# ---BOT Configuration---
SYMBOL = CONFIG["trading"]["symbol"]
TIMEFRAME = CONFIG["data"]["timeframe"]
START_DATE = CONFIG["data"]["start_date"]
LIMIT = CONFIG["data"]["limit"]
FAST_SMA = CONFIG['backtest']['strategy_params']['fast_period']
SLOW_SMA = CONFIG['backtest']['strategy_params']['slow_period']
TRADE_QUANTITY = CONFIG["trading"]["trade_quantity"]


def main_bot_loop():
    """Main trading bot loop with proper logging"""
    logger.info("=" * 60)
    logger.info("Starting Live Trading Bot")
    logger.info("=" * 60)
    logger.info(f"Configuration: Symbol={SYMBOL}, Timeframe={TIMEFRAME}")
    logger.info(f"Strategy: SMA Crossover ({FAST_SMA}/{SLOW_SMA})")
    logger.info(f"Trade Quantity: {TRADE_QUANTITY}")

    try:
        broker = AlpacaBroker()
        market_data = MarketData()
        strategy = MovingAverageCrossover(fast_period=FAST_SMA, slow_period=SLOW_SMA)
        portfolio = PortfolioManager(broker)
    except Exception as e:
        logger.critical(f"Failed to initialize trading components: {e}", exc_info=True)
        sys.exit(1)

    logger.info("All components initialized successfully")
    logger.info("Entering main trading loop...")

    while True:
        try:  
            logger.info("-" * 60)
            logger.info(f"Trading cycle started at {time.ctime()}")
            
            # 1. Update our real-time state from the broker 
            logger.info("Updating portfolio state...")
            portfolio.update_portfolio()
            current_qty = portfolio.get_position_qty(SYMBOL)
            in_position = current_qty > 0
            logger.info(f"Current position: {current_qty} shares of {SYMBOL} (in_position={in_position})")

            # 2. Get data and generate signals
            logger.info("Fetching market data and generating signals...")
            df = market_data.get_historical_bars(SYMBOL, TIMEFRAME, start=START_DATE, limit=LIMIT)
            
            if df is None or df.empty:
                logger.error("Failed to fetch market data. Skipping this cycle.")
                time.sleep(60)
                continue
            
            logger.debug(f"Fetched {len(df)} bars of data")
            
            # Calculate indicators
            df = moving_average.calculate_sma(df, FAST_SMA)
            df = moving_average.calculate_sma(df, SLOW_SMA)
            df = strategy.generate_signals(df)

            latest_signal = df['position'].iloc[-1]
            latest_price = df['close'].iloc[-1]
            logger.info(f"Latest signal for {SYMBOL}: {latest_signal} (Price: ${latest_price:.2f})")

            # 3. Execute trades based on signals
            if latest_signal == 1.0 and not in_position:
                logger.warning(f"🟢 BUY SIGNAL DETECTED for {SYMBOL}")
                logger.info(f"Placing BUY order for {TRADE_QUANTITY} shares at ~${latest_price:.2f}")
                
                order = broker.submit_order(symbol=SYMBOL, qty=TRADE_QUANTITY, side="buy")
                if order:
                    logger.info(f"✅ BUY order submitted successfully. Order ID: {order.get('id')}")
                    in_position = True
                else:
                    logger.error("❌ BUY order failed")
                    
            elif latest_signal == -1.0 and in_position:
                logger.warning(f"🔴 SELL SIGNAL DETECTED for {SYMBOL}")
                logger.info(f"Placing SELL order for {current_qty} shares at ~${latest_price:.2f}")
                
                order = broker.submit_order(symbol=SYMBOL, qty=current_qty, side="sell")
                if order:
                    logger.info(f"✅ SELL order submitted successfully. Order ID: {order.get('id')}")
                    in_position = False
                else:
                    logger.error("❌ SELL order failed")
            else:
                logger.info("⏸️  HOLD signal - No action taken")

            logger.info("Waiting for next trading period (24 hours)...")
            time.sleep(86400)

        except KeyboardInterrupt:
            logger.warning("Bot stopped manually by user (KeyboardInterrupt)")
            logger.info("Shutting down gracefully...")
            break
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            logger.info("Restarting loop after 60 seconds...")
            time.sleep(60)

    logger.info("Trading bot shutdown complete")


if __name__ == "__main__":
    main_bot_loop()    