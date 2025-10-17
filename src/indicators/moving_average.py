# src/indicators/moving_average.py

import pandas as pd

def calculate_sma(data: pd.DataFrame, period: int) -> pd.DataFrame:
    print(f"Calculateing {period} SMA")

    if 'close' not in data.columns:
        raise ValueError("Input DataFrame must have a 'close' column")
    if not isinstance(period, int) or period <= 0:
        raise ValueError("Period must be a positive integer.")
    sma_column_name = f'sma_{period}'
    data[sma_column_name] = data['close'].rolling(window=period).mean()

    print ("SMA Calculation complete")
    return data
