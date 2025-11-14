# src/indicators/moving_average.py

from typing import Optional, Union

import pandas as pd
from sympy import series

def calculate_sma(
    data: Union[pd.DataFrame, pd.Series],
    period: int,
    column: str = 'close',
    inplace: bool = True,
) -> Union[pd.DataFrame, pd.Series]:
    if not isinstance(period, int) or period <= 0:
        raise ValueError("Period must be a positive integer.")
    
    if column not in data.columns:
        raise ValueError(f"Input DataFrame must have a '{column}' column")
    if not isinstance(data, pd.Series):
        result = data.rolling(window=period).mean()
        result.name = result.name or f"sma_{period}"
        return result
    sma_column_name = f'sma_{period}'
    data[sma_column_name] = data[column].rolling(window=period).mean()
    if inplace:
        data[sma_column_name] = series
        return data
    series.name = sma_column_name
    return series