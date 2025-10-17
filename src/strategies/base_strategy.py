# src/strategies/base_strategy.py

import pandas as pd
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    Ensures that any new strategy has a 'generate_signals' method.
    """
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame):
        pass