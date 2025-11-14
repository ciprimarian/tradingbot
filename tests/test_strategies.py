# tests/test_strategies.py

from src.data.market_data import MarketData
from src.indicators import moving_average
from src.strategies.momentum_strategy import MovingAverageCrossover

def test_data_fetch_and_strategy():
    print("Data fetch test...")
    market_data_handler = MarketData()
    historical_data = market_data_handler.get_historical_bars(
        symbol="TSLA",
        timeframe="1Day",
        start="2025-01-01T00:00:00Z",
        limit=200
    )

    assert historical_data is not None, "Failed to fetch historical data."
    print("\n Succesfully fetched historical data")

    #Calculate 20 days SMA
    print("\nCalculate SMA")
    data_with_fast_sma = moving_average.calculate_sma(historical_data, 5)
    data_with_both_smas = moving_average.calculate_sma(data_with_fast_sma, 20)

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
    
    assert 'position' in signals_df.columns, "Signal generation failed, 'position' column missing."
    print("Data Fetch Completed")
