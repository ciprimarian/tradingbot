from brokers.alpaca_broker import AlpacaBroker
from data.market_data import MarketData
from indicators import moving_average

def run_connection_test():
    print("Running connection test to Alpaca...")
    broker = AlpacaBroker()
    broker.get_account_info()
    print("Connection test completed.")

def run_data_fetch():
    print("Data fetch test...")
    market_data_handler = MarketData()
    historical_data = market_data_handler.get_historical_bars(
        symbol="TSLA",
        timeframe="1Day",
        start="2025-01-01T00:00:00Z",
        limit=50
    )

    if historical_data is not None:
        print("\n Succesfully fetched historical data")
        print(historical_data.tail())

        #Calculate 20 days SMA
        print("\nCalculate SMA")
        data_with_sma=moving_average.calculate_sma(historical_data, 20)

        #Display SMA
        print("\nData woth @)-day SMA")
        print(data_with_sma.tail())
    else:
        print("\nFailed to fetch.")
    print("Data Fetch Completed")        

if __name__ == "__main__":
    run_connection_test()
    run_data_fetch()