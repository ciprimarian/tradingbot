# src/main.py
# Multi-Agent AI Trading Bot
# Demonstrates 4 AI branches: ML, Planning, Optimization, Reasoning

import sys
import time
from datetime import datetime

from src.utils.common_imports import get_logger
from src.brokers.alpaca_broker import AlpacaBroker
from src.data.data_manager import DataManager

# Original agents
from src.agents.technical_analysis_agent import TechnicalAnalysisAgent
from src.agents.risk_management_agent import RiskManagementAgent
from src.agents.sentiment_analysis_agent import SimpleSentimentAgent

# New AI agents - demonstrating different AI branches
from src.agents.ml_prediction_agent import MLPredictionAgent  # Machine Learning
from src.agents.planning_agent import TradingPlannerAgent  # Planning
from src.agents.reasoning_agent import ReasoningAgent  # Reasoning

from src.agents.agent_coordinator import AgentCoordinator, AggregationMethod
from src.risk_management.portfolio_manager import PortfolioManager
from src.risk_management.portfolio_optimizer import PortfolioOptimizer  # Optimization
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

# Asset types that trade 24/7 (crypto and forex)
ALWAYS_OPEN_ASSETS = ['BTC', 'ETH', 'LTC', 'BCH', 'DOGE', 'SHIB', 'USDT', 'USDC',
                      'BTCUSD', 'ETHUSD', 'EURUSD', 'GBPUSD', 'USDJPY']

# Commodities with extended/24-hour trading (e.g., on Alpaca they may trade nearly 24/5)
# Gold, Silver, and some other commodities on certain platforms
EXTENDED_HOURS_ASSETS = ['GLD', 'SLV', 'GC', 'SI', 'XAU', 'XAG']  # Gold and Silver ETFs/futures


def is_crypto_or_24_7_asset(symbol):
    """Check if the symbol is a 24/7 trading asset (crypto or forex)"""
    symbol_upper = symbol.upper()
    # Check if it's in the known 24/7 assets list
    if symbol_upper in ALWAYS_OPEN_ASSETS:
        return True
    # Check if it contains common crypto/forex patterns
    if 'USD' in symbol_upper and len(symbol_upper) <= 6:  # e.g., BTCUSD, EURUSD
        return True
    return False


def is_extended_hours_asset(symbol):
    """Check if the symbol has extended trading hours (near 24/5 for commodities)"""
    symbol_upper = symbol.upper()
    return symbol_upper in EXTENDED_HOURS_ASSETS


def main_bot_loop():
    """Main trading bot loop using multi-agent system with AI branches"""
    logger.info("=" * 60)
    logger.info("Starting AI Trading Bot - Multi-Agent System")
    logger.info("AI Branches: ML, Planning, Optimization, Reasoning")
    logger.info("=" * 60)
    logger.info(f"Configuration: Symbol={SYMBOL}, Timeframe={TIMEFRAME}")
    logger.info(f"Trade Quantity: {TRADE_QUANTITY}")

    try:
        # Initialize components
        broker = AlpacaBroker()
        data_manager = DataManager()
        portfolio = PortfolioManager(broker)
        
        # Initialize optimizer - demonstrates Optimization branch
        optimizer = PortfolioOptimizer(risk_free_rate=0.02)
        logger.info("Portfolio optimizer initialized (Optimization AI)")
        
        # Initialize agents - mix of old and new
        # Keeping some old ones for stability, adding new AI agents
        agents = [
            TechnicalAnalysisAgent(name="TechnicalAgent", weight=0.25),
            RiskManagementAgent(name="RiskAgent", weight=0.15),
            
            # New AI agents demonstrating different branches
            MLPredictionAgent(name="MLAgent", weight=0.3),  # Machine Learning branch
            TradingPlannerAgent(name="PlannerAgent", weight=0.15),  # Planning branch
            ReasoningAgent(name="ReasoningAgent", weight=0.25),  # Reasoning branch
            
            # Optional: sentiment agent with lower weight
            # SimpleSentimentAgent(name="SentimentAgent", weight=0.1)
        ]
        
        # Create coordinator - aggregates all agent decisions
        coordinator = AgentCoordinator(
            agents=agents,
            aggregation_method=AggregationMethod.CONFIDENCE_WEIGHTED,
            min_confidence_threshold=0.5
        )
        
        logger.info(f"Initialized {len(agents)} agents:")
        for agent in agents:
            logger.info(f"  - {agent.name} (weight={agent.weight})")
        logger.info(f"Aggregation: {AggregationMethod.CONFIDENCE_WEIGHTED.value}")
        logger.info("Note: Weights might not sum to 1.0 - that's intentional chaos!")
        
    except Exception as e:
        logger.critical(f"Failed to initialize trading components: {e}", exc_info=True)
        sys.exit(1)

    logger.info("All components initialized successfully")
    logger.info("Entering main trading loop...")
    
    # Check asset trading hours type
    is_24_7 = is_crypto_or_24_7_asset(SYMBOL)
    is_extended = is_extended_hours_asset(SYMBOL)
    
    if is_24_7:
        logger.info(f"🌐 Asset {SYMBOL} trades 24/7 (Crypto/Forex) - Market hours check DISABLED")
        logger.info(f"Check interval: {CHECK_INTERVAL}s")
    elif is_extended:
        logger.info(f"⏰ Asset {SYMBOL} has extended hours (Commodity) - Trading nearly 24/5")
        logger.info(f"Note: May have brief closures on weekends")
        logger.info(f"Check interval: {CHECK_INTERVAL}s")
    else:
        logger.info(f"📊 Asset {SYMBOL} follows standard market hours - Market hours check ENABLED")
        logger.info(f"Market check interval: {CHECK_INTERVAL}s (open) / {MARKET_CLOSED_CHECK_INTERVAL}s (closed)")

    last_trade_check_time = None  # Track when we last checked for trades
    iteration_count = 0  # just for fun tracking
    
    while True:
        try:  
            iteration_count += 1
            
            # Check if market is open (skip for 24/7 and extended hours assets)
            if not is_24_7 and not is_extended:
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
                logger.info(f"🟢 Market is OPEN | Iteration #{iteration_count} | {current_time}")
                logger.info(f"Market closes at: {next_close}")
                logger.info("=" * 60)
            elif is_24_7:
                # For 24/7 crypto/forex assets
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.info("=" * 60)
                logger.info(f"🌐 24/7 Trading | Iteration #{iteration_count} | {current_time}")
                logger.info("=" * 60)
            else:
                # For extended hours commodities
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.info("=" * 60)
                logger.info(f"⏰ Extended Hours | Iteration #{iteration_count} | {current_time}")
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
            # Pass current position to planning agent (a bit hacky but works)
            logger.info("Querying agents for trading decision...")
            signal = coordinator.decide(df, current_position=1 if in_position else 0)
            
            if signal is None:
                logger.info("No confident signal from agents - HOLD")
            else:
                latest_price = df['close'].iloc[-1]
                logger.info(
                    f"Agent decision: {signal.signal_type.name} "
                    f"(confidence={signal.confidence:.2f}, price=${latest_price:.2f})"
                )
                logger.debug(f"Reasoning: {signal.reasoning}")

                # 4. Position sizing using optimization (Kelly criterion)
                # Demonstrates Optimization branch in action
                if signal.signal_type.value > 0 and not in_position:
                    # Calculate position size using optimizer
                    try:
                        # Estimate expected return and volatility from recent data
                        recent_returns = df['close'].pct_change().tail(20)
                        expected_return = recent_returns.mean() * signal.confidence
                        volatility = recent_returns.std()
                        
                        optimal_position_value = optimizer.optimize_position_size(
                            expected_return=expected_return,
                            volatility=volatility,
                            current_capital=portfolio.portfolio_value,
                            risk_tolerance=0.02  # risk 2% of capital
                        )
                        
                        # Convert to shares (rough calculation)
                        optimal_qty = int(optimal_position_value / latest_price)
                        optimal_qty = max(1, min(optimal_qty, TRADE_QUANTITY))  # cap at configured max
                        
                        logger.info(f"Optimizer suggests position size: {optimal_qty} shares")
                    except Exception as e:
                        logger.warning(f"Optimization failed: {e}, using default quantity")
                        optimal_qty = TRADE_QUANTITY
                else:
                    optimal_qty = TRADE_QUANTITY

                # 5. Execute trades based on agent signals
                signal_value = signal.signal_type.value
                
                # BUY signals (STRONG_BUY=2 or BUY=1)
                if signal_value > 0 and not in_position:
                    logger.warning(f"📈 BUY SIGNAL DETECTED for {SYMBOL}")
                    logger.info(f"Placing BUY order for {optimal_qty} shares at ~${latest_price:.2f}")
                    
                    order = broker.submit_order(symbol=SYMBOL, qty=optimal_qty, side="buy")
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
    logger.info(f"Total iterations: {iteration_count}")


if __name__ == "__main__":
    main_bot_loop()    