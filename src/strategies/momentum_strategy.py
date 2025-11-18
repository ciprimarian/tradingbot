# src/strategies/momentum_strategy.py

from src.utils.common_imports import pd, np, get_logger
from src.strategies.base_strategy import BaseStrategy

 
class MovingAverageCrossover(BaseStrategy):
    """
    A strategy based on the crossover of 2 simple moving averages.
    Generates BUY signal when fast MA crosses above slow MA.
    Generates SELL signal when fast MA crosses below slow MA.
    """
    
    def __init__(self, fast_period: int, slow_period: int):
        if fast_period >= slow_period:
            raise ValueError("Fast period must be less than slow period")
        
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.fast_sma_col = f'sma_{fast_period}'
        self.slow_sma_col = f'sma_{slow_period}'
        self.logger = get_logger(__name__)
        
        self.logger.info(
            f"MovingAverageCrossover strategy initialized | "
            f"Fast SMA: {fast_period}, Slow SMA: {slow_period}"
        )

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals based on MA crossover"""
        self.logger.debug(f"Generating signals for {self.fast_period}/{self.slow_period} SMA Crossover")
        
        # Validate required columns
        if self.fast_sma_col not in data.columns or self.slow_sma_col not in data.columns:
            error_msg = f"Data must include {self.fast_sma_col} and {self.slow_sma_col} columns"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Generate signals
        data['signal'] = np.where(data[self.fast_sma_col] > data[self.slow_sma_col], 1, 0)
        data['position'] = data['signal'].diff()
        
        # Count signals
        buy_signals = (data['position'] == 1).sum()
        sell_signals = (data['position'] == -1).sum()
        
        self.logger.info(
            f"Signal generation complete | "
            f"BUY signals: {buy_signals}, SELL signals: {sell_signals}"
        )
        self.logger.debug(f"Latest signal: {data['position'].iloc[-1]}")
        
        return data