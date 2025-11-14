from typing import Union

import pandas as pd
import numpy as np

def calculate_rsi(
    data: Union[pd.Series, pd.DataFrame],
    window: int = 14,
    column: str = 'close',
) -> pd.Series:
    if window <= 0:
        raise ValueError("RSI window must be a positive integer.")
    
    series = data[column] if isinstance(data, pd.Series) else data[column]
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0.0)    
    loss = np.where(delta < 0, -delta, 0.0)

    gain_series = pd.Series(gain, index=series.index).rolling(window=window).mean()
    loss_series = pd.Series(loss, index=series.index).rolling(window=window).mean()

    rs = gain_series / loss_series.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi.name = f'rsi_{window}'
    return rsi.fillna(method='bfill')