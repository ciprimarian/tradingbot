# src/strategies/base_strategy.py

from abc import ABC, abstractmethod

from src.utils.common_imports import pd, get_logger


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    Ensures that any new strategy has a 'generate_signals' method.
    
    Subclasses should initialize self.logger = get_logger(__name__) in __init__
    """
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals from market data.
        
        Args:
            data: DataFrame with OHLCV data and any required indicators
            
        Returns:
            DataFrame with added 'signal' and 'position' columns
        """
        pass