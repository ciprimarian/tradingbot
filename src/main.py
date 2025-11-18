# src/main.py

import sys
import time
from datetime import datetime

from src.utils.common_imports import get_logger
from src.brokers.alpaca_broker import AlpacaBroker
from src.data.data_manager import DataManager
from src.agents.technical_analysis_agent import TechnicalAnalysisAgent
from src.agents.risk_management_agent import RiskManagementAgent
from src.agents.sentiment_analysis_agent import SimpleSentimentAgent
from src.agents.agent_coordinator import AgentCoordinator, AggregationMethod
from src.risk_management.portfolio_manager import PortfolioManager
from src.config.settings import CONFIG

# Initialize logger
logger = get_logger(__name__)

# ---BOT Configuration---
SYMBOL = CONFIG["trading"]["symbol"]
TIMEFRAME = CONFIG["data"]["timeframe"]
START_DATE = CONFIG["data"]["start_date"]
LIMIT = CONFIG["data"]["limit"]
TRADE_QUANTITY = CONFIG["trading"]["trade_quantity"]

# Polling configuration
CHECK_INTERVAL = 60  # Check market status every 60 seconds
MARKET_CLOSED_CHECK_INTERVAL = 300  # Check every 5 minutes when market is closed


def main_bot_loop():
    """Main trading bot loop using multi-agent system"""
    logger.info("=" * 60)
    logger.info("Starting Live Trading Bot (Multi-Agent System)")
    logger.info("=" * 60)
    logger.info(f"Configuration: Symbol={SYMBOL}, Timeframe={TIMEFRAME}")
    logger.info(f"Trade Quantity: {TRADE_QUANTITY}")

    try:
        # Initialize components
        broker = AlpacaBroker()
        data_manager = DataManager()
        portfolio = PortfolioManager(broker)
        
        # Initialize agents
        agents = [
            TechnicalAnalysisAgent(name="TechnicalAgent", weight=0.5),
            RiskManagementAgent(name="RiskAgent", weight=0.3),
            SimpleSentimentAgent(name="SentimentAgent", weight=0.2)
        ]
        
        # Create coordinator
        coordinator = AgentCoordinator(
            agents=agents,
            aggregation_method=AggregationMethod.CONFIDENCE_WEIGHTED,
            min_confidence_threshold=0.5
        )
        
        logger.info(f"Initialized {len(agents)} agents:")
        for agent in agents:
            logger.info(f"  - {agent.name} (weight={agent.weight})")
        logger.info(f"Aggregation: {AggregationMethod.CONFIDENCE_WEIGHTED.value}")
        
    except Exception as e:
        logger.critical(f"Failed to initialize trading components: {e}", exc_info=True)
        sys.exit(1)

    logger.info("All components initialized successfully")
    logger.info("Entering main trading loop...")
    logger.info(f"Market check interval: {CHECK_INTERVAL}s (open) / {MARKET_CLOSED_CHECK_INTERVAL}s (closed)")

    last_trade_check_time = None  # Track when we last checked for trades
    
    while True:
        try:  
            # Check if market is open
            clock = broker.get_market_clock()
            if not clock:
                logger.warning("Failed to get market clock. Retrying in 60 seconds...")
                time.sleep(60)
                continue
            
            is_open = clock.get('is_open', False)
            next_open = clock.get('next_open')
            next_close = clock.get('next_close')
            
            if not is_open:
                logger.info(f"🔴 Market is CLOSED. Next open: {next_open}")
                logger.info(f"Waiting {MARKET_CLOSED_CHECK_INTERVAL} seconds before next check...")
                time.sleep(MARKET_CLOSED_CHECK_INTERVAL)
                continue
            
            # Market is open - log status
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info("=" * 60)
            logger.info(f"🟢 Market is OPEN | Current time: {current_time}")
            logger.info(f"Market closes at: {next_close}")
            logger.info("=" * 60)
            
            # 1. Update portfolio state
            logger.info("Updating portfolio state...")
            portfolio.update_portfolio()
            current_qty = portfolio.get_position_qty(SYMBOL)
            in_position = current_qty > 0
            logger.info(f"Current position: {current_qty} shares of {SYMBOL} (in_position={in_position})")

            # 2. Get data and prepare for agents
            logger.info("Fetching market data and calculating indicators...")
            df = data_manager.get_historical_data(symbol=SYMBOL, timeframe=TIMEFRAME, start_date=START_DATE, limit=LIMIT)
            
            if df is None or df.empty:
                logger.error("Failed to fetch market data. Retrying in 60 seconds...")
                time.sleep(60)
                continue
            
            logger.debug(f"Fetched {len(df)} bars of data")
            
            # Prepare data with indicators
            df = data_manager.prepare_for_agents(df)
            logger.debug("Indicators calculated: sma_20, sma_50, rsi_14")

            # 3. Get agent decision
            logger.info("Querying agents for trading decision...")
            signal = coordinator.decide(df)
            
            if signal is None:
                logger.info("No confident signal from agents - HOLD")
            else:
                latest_price = df['close'].iloc[-1]
                logger.info(
                    f"Agent decision: {signal.signal_type.name} "
                    f"(confidence={signal.confidence:.2f}, price=${latest_price:.2f})"
                )
                logger.debug(f"Reasoning: {signal.reasoning}")

                # 4. Execute trades based on agent signals
                signal_value = signal.signal_type.value
                
                # BUY signals (STRONG_BUY=2 or BUY=1)
                if signal_value > 0 and not in_position:
                    logger.warning(f"📈 BUY SIGNAL DETECTED for {SYMBOL}")
                    logger.info(f"Placing BUY order for {TRADE_QUANTITY} shares at ~${latest_price:.2f}")
                    
                    order = broker.submit_order(symbol=SYMBOL, qty=TRADE_QUANTITY, side="buy")
                    if order:
                        logger.info(f"✅ BUY order submitted successfully. Order ID: {order.get('id')}")
                        in_position = True
                    else:
                        logger.error("❌ BUY order failed")
                        
                # SELL signals (STRONG_SELL=-2 or SELL=-1)
                elif signal_value < 0 and in_position:
                    logger.warning(f"📉 SELL SIGNAL DETECTED for {SYMBOL}")
                    logger.info(f"Placing SELL order for {current_qty} shares at ~${latest_price:.2f}")
                    
                    order = broker.submit_order(symbol=SYMBOL, qty=current_qty, side="sell")
                    if order:
                        logger.info(f"✅ SELL order submitted successfully. Order ID: {order.get('id')}")
                        in_position = False
                    else:
                        logger.error("❌ SELL order failed")
                else:
                    logger.info("⏸️  HOLD signal - No action taken")
            
            # Record this check time
            last_trade_check_time = time.time()

            # Wait before next check (while market is open)
            logger.info(f"Waiting {CHECK_INTERVAL} seconds before next check...")
            time.sleep(CHECK_INTERVAL)

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