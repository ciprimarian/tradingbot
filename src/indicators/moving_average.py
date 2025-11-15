# src/indicators/moving_average.py

from typing import Union

import pandas as pd

def calculate_sma(
    data: Union[pd.DataFrame, pd.Series],
    period: int,
    column: str = 'close',
    inplace: bool = True,
) -> Union[pd.DataFrame, pd.Series]:
    if not isinstance(period, int) or period <= 0:
        raise ValueError("Period must be a positive integer.")
    
    if isinstance(data, pd.Series):
        series =data
    else:
        if column not in data.columns:
            raise ValueError(f"Input DataFrame must have a '{column}' column")
        series = data[column]
        if isinstance(series, pd.DataFrame):
            if series.shape[1] != 1:
                raise ValueError(f"Column '{column}' is ambiguous; got {series.shape[1]} columns.")
            series = series.iloc[:, 0]

    sma_name = f'sma_{period}'
    sma = series.rolling(window=period, min_periods=1).mean()

    if not inplace:
        return sma

    if isinstance(data, pd.DataFrame):
        data[sma_name] = sma
        return data

    return sma