# src/main.py
import sys
import time
from src.brokers.alpaca_broker import AlpacaBroker
from src.data.market_data import MarketData
from src.indicators import moving_average
from src.strategies.momentum_strategy import MovingAverageCrossover
from src.risk_management.portfolio_manager import PortfolioManager

# ---BOT Configuration---
SYMBOL = 'TSLA'
TIMEFRAME = "1Day"
FAST_SMA = 5
SLOW_SMA = 20
TRADE_QUANTITY = 1

def main_bot_loop():
   
    print("Starting Live Trading Bot")

    broker = AlpacaBroker()
    market_data = MarketData()
    strategy = MovingAverageCrossover(fast_period=FAST_SMA, slow_period=SLOW_SMA)
    portfolio = PortfolioManager(broker)

    while True:
        try:  
            print("\n................................")
            print(f"Timestamp: {time.ctime()}")
            
            # 1. Update our real-time state from the broker 
            print("updating portfolio state...")
            portfolio.update_portfolio()
            current_qty = portfolio.get_position_qty(SYMBOL)
            in_position = current_qty > 0
            print(f"Current state: Holding {current_qty} shares of {SYMBOL}. (in_position = {in_position})")

            # 2. Get data and generate signals
            print("Fetching data and generating signals...")
            df = market_data.get_historical_bars(SYMBOL, TIMEFRAME, start="2025-01-01T00:00:00Z", limit=200)
            if df is None:
                raise Exception("Could not fetch Market Data")
            
            df = moving_average.calculate_sma(df, FAST_SMA)
            df = moving_average.calculate_sma(df, SLOW_SMA)
            df =strategy.generate_signals(df)

            latest_signal = df['position'].iloc[-1]
            print(f"LAtest saignal for {SYMBOL}: {latest_signal}")

            if latest_signal == 1.0 and not in_position:
                print("Buy signal detected. Placing BUY order for {TRADE_QUANTITY} shares")
                broker.submit_order(symbol=SYMBOL, qty=TRADE_QUANTITY, side="buy")
                in_position = True
            elif latest_signal == -1.0 and in_position:
                print("Sell signal detected. Placing SELL orderfor all {current_qty} shares.")
                broker.submit_order(symbol=SYMBOL, qty=TRADE_QUANTITY, side="sell")
                in_position = False
            else:
                print("HOLD signal, no action taken.")

            print("Waiting for the next trading period...")
            time.sleep(86400) #wait for #24h

        except KeyboardInterrupt:
           print("Bot stopped manually.")
           break
        except Exception as e:
            print(f"An error occured in the main loop: {e}")
            print("Restarting loop{ after 60 sec}")
            time.sleep(60)

if __name__ == "__main__":
        main_bot_loop()    