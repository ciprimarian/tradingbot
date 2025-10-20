# src/main.py

from brokers.alpaca_broker import AlpacaBroker
from data.market_data import MarketData
from indicators import moving_average
from strategies.momentum_strategy import MovingAverageCrossover
import argparse
import time

# ---BOT Configuration---
SYMBOL = 'TSLA'
TIMEFRAME = "1Day"
FAST_SMA = 5
SLOW_SMA = 20
TRADE_QUANTITY = 1

def run_connection_test():
    print("Running connection test to Alpaca...")
    broker = AlpacaBroker()
    broker.get_account_info()
    print("Connection test completed.")

def run_data_fetch_and_strategy():
    print("Data fetch test...")
    market_data_handler = MarketData()
    historical_data = market_data_handler.get_historical_bars(
        symbol="TSLA",
        timeframe="1Day",
        start="2025-01-01T00:00:00Z",
        limit=200
    )

    if historical_data is not None:
        print("\n Succesfully fetched historical data")
        print(historical_data.tail())

        #Calculate 20 days SMA
        print("\nCalculate SMA")
        data_with_slow_sma=moving_average.calculate_sma(historical_data, 20)
        data_with_both_smas = moving_average.calculate_sma(data_with_slow_sma, 5)

        #Display SMA
        print("\nData woth 20-day SMA")
        print(data_with_both_smas.tail())

        #Run Strategy test
        print("\n-Running Strategy test-")
        strategy = MovingAverageCrossover(fast_period=5, slow_period=20)

        #Generate Signals
        signals_df = strategy.generate_signals(data_with_both_smas)

        #Print results
        print("\nStrategy signals generated:")
        print(signals_df[['close', 'sma_5', 'sma_20', 'signal', 'position']].tail(20))
        
        #Calculate basic performance metrics
        buy_signals = signals_df[signals_df['position'] == 1]
        sel_signals = signals_df[signals_df['position'] == -1]

        print(f"\nTotal buy signals: {len(buy_signals)}")
        print(f"\nTotal sell signals: {len(sel_signals)}")
    else:
        print("\nFailed to fetch.")
    print("Data Fetch Completed")

def main_bot_loop():
   
    print("Starting Live Trading Bot")

    broker = AlpacaBroker()
    market_data = MarketData()
    strategy = MovingAverageCrossover(fast_period=FAST_SMA, slow_period=SLOW_SMA)
    in_position = False

    while True:
        try:  
            print("\n................................")
            print(f"Timestamp: {time.ctime()}")
            df = market_data.get_historical_bars(SYMBOL, TIMEFRAME, start="2025-01-01T00:00:00Z", limit=200)
            if df is None:
                raise Exception("Could not fetch Market Data")
            
            df = moving_average.calculate_sma(df, FAST_SMA)
            df = moving_average.calculate_sma(df, SLOW_SMA)
            df =strategy.generate_signals(df)

            latest_signal = df['position'].iloc[-1]
            print(f"LAtest saignal for {SYMBOL}: {latest_signal}")

            if latest_signal == 1.0 and not in_position:
                print("Buy signal detected. Placing BUY order.")
                broker.submit_order(symbol=SYMBOL, qty=TRADE_QUANTITY, side="buy")
                in_position = True
            elif latest_signal == -1.0 and in_position:
                print("Sell signal detected. Placing SELL order.")
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
    parser = argparse.ArgumentParser(description="Algorithmic trading bot.")
    parser.add_argument(
        "--mode",
        type=str,
        choices=['run_connection_test', 'run_data_fetch_and_strategy', 'main_bot_loop'],
        required=True,
        help="The mode to run the bot in"
    )
    args = parser.parse_args()

    if args.mode == 'run_connection_test':
        run_connection_test()
    elif args.mode == 'run_data_fetch_and_strategy':
        run_data_fetch_and_strategy()
    elif args.mode == 'main_bot_loop':
        main_bot_loop()    