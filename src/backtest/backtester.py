from dataclasses import dataclass
from typing import Optional, Dict, Type

import pandas as pd

from src.strategies.base_strategy import BaseStrategy
from src.strategies.momentum_strategy import MovingAverageCrossover
from src.utils.logger import get_logger

@dataclass
class BacktestResult:
    equity_curve: pd.Series
    returns: pd.Series
    summary: Dict[str, float]

    def plot(self) -> None:
        ax = self.equity_curve.plot(title="Equity Curve", figsize=(10, 6))
        ax.set_xlabel("Date")

    @property
    def metrics(self) -> Dict[str, float]:
        """Dynamically return summary metrics as a dictionary."""
        return{
            k: v for k, v in self.__dict__.items()
            if not isinstance(v, (pd.Series, pd.DataFrame, dict))
        }

class Backtester:
    def __init__(self, data: pd.DataFrame, config: Optional[dict] = None) -> None:
        self.data = data.copy()
        self.config = config or {}
        self.initial_capital = self.config.get("initial_capital", 100_000)
        self.logger = get_logger(__name__)
        
        self.strategy_registry: Dict[str, Type[BaseStrategy]] = {
            "moving_average_crossover": MovingAverageCrossover,
            "momentum": MovingAverageCrossover,  # alis for backward compability
        }

    def run(
        self,
        strategy: Optional[BaseStrategy] = None,
        strategy_name: Optional[str] = None,
        strategy_params: Optional[dict] = None,
    ) ->BacktestResult:
        strategy_instance = strategy or self._build_strategy(strategy_name, strategy_params)
        self.logger.info("Starting backtest with strategy: %s", strategy_instance.__class__.__name__)
        df = strategy_instance.generate_signals(self.data.copy())

        df["returns"] = df["close"].pct_change().fillna(0)
        df["strategy_returns"] = df["returns"] *df["signal"].shift(1).fillna(0)
        equity_curve = (1 + df["strategy_returns"]).cumprod() * self.initial_capital

        summary = {
            "final_equity": float(equity_curve.iloc[-1]),
            "cumulative_return": float(equity_curve.iloc[-1] / self.initial_capital - 1),
            "volatility": float(df["strategy_returns"].std() * (252 ** 0.5)),
            "sharpe": self._compute_sharpe(df["strategy_returns"]),
        }

        return BacktestResult(
            equity_curve=equity_curve,
            returns=df["strategy_returns"],
            summary=summary,
        )
    
    def _build_strategy(
        self,
        strategy_name: Optional[str],
        strategy_params: Optional[dict] = None,
    ) -> BaseStrategy:
        name = strategy_name or self.config.get("strategy", "moving_average_crossover")
        params = strategy_params or self.config.get("strategy_params", {})
        strategy_cls = self.strategy_registry.get(name)
        if strategy_cls is None:
            raise ValueError(f"Strategy '{name}' is not registered.")
        return strategy_cls(**params)
    
    @staticmethod
    def _compute_sharpe(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
        excess_returns = returns - risk_free_rate / 252
        std = excess_returns.std()
        if std == 0:
            return 0.0
        return (excess_returns.mean() / std) * (252 ** 0.5)