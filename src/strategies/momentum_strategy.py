# src/strategies/momentum_strategy.py

import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy

class MovingAverageCrossover(BaseStrategy):
    """
    A strategy based on the crossoverof 2 simple MA.
    """
    def __init__(self, fast_period: int, slow_period: int):
        if fast_period >= slow_period:
            raise ValueError("Fast period must be less than slow period")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.fast_sma_col = f'sma_{fast_period}'
        self.slow_sma_col = f'sma_{slow_period}'

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        print(f"Generating signals for {self.fast_period}/{self.slow_period} SMA Crossover.")
        if self.fast_sma_col not in data.columns or self.slow_sma_col not in data.columns:
            raise ValueError(f"Data must include {self.fast_sma_col} and {self.slow_sma_col} columns.")
        data['signal'] = np.where(data[self.fast_sma_col] > data[self.slow_sma_col], 1, 0)
        data['position'] = data['signal'].diff()
        print("Signal generation complete")
        return data