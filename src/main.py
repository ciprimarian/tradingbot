from brokers.alpaca_broker import AlpacaBroker
from data.market_data import MarketData
from indicators import moving_average
from strategies.momentum_strategy import MovingAverageCrossover

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

if __name__ == "__main__":
    run_connection_test()
    run_data_fetch_and_strategy()
   