# src/agents/risk_management_agent.py

import pandas as pd
import numpy as np

from typing import Any, Dict, Optional

from src.agents.base_agent import BaseAgent, AgentSignal, SignalType
from src.utils.logger import get_logger

class RiskManagementAgent(BaseAgent):
    def __init__(self, name: str = "RiskManagementAgent ", weight: float = 1.0, config: Optional[Dict[str, Any]] = None):
        super().__init__(name, weight, config)
        self.max_volatility = self.config.get("max_volatility", 0.03)
        self.lookback_period = self.config.get("lookback_period", 20)

        def analyze(self, data: pd.DataFrame, **kwargs) -> AgentSignal:
            if len(data) < self.lookback_period:
                return AgentSignal(SignalType.HOLD, "Insufficient data for risk analysis.")
            
            #Calculate risk metrics
            volatility = self.calculate_volatility(data)
            drawdown = self.calculate_drawdown(data)

            #Asses each
            vol_signal, vol_conf, vol_reason = self.assess_volatility(volatility)
            dd_signal, dd_conf, dd_reason = self.assess_drawdown(drawdown)

            #Combine *use minumun confidence - most conservative
            avg_signal = (vol_signal + dd_signal) / 2
            min_confidence = min(vol_conf, dd_conf)

            #Convert to SignalType
            # Positive = safe, Negative = risky
            if avg_signal >= 0.3:
               signal_type = SignalType.BUY
            elif avg_signal <= -0.3:
                signal_type = SignalType.SELL
            else:
                signal_type = SignalType.HOLD

            return AgentSignal(
                signal_type=signal_type,
                confidence=min_confidence,
                reasoning=f"Risk: {vol_reason} | {dd_reason}"
            )
        
    def calculate_volatility(self, data: pd.DataFrame) -> float:
        '''Calculate rolling volatility'''
        returns = data['close'].pct_change().dropna()
        recent = returns.tail(self.lookback_period)
        return recent.std()
    
    def calculate_drawdown(self, data: pd.DataFrame) -> float:
        '''Calculate current drawdown'''
        prices = data['close'].tail(self.lookback_period)
        running_max = prices.expanding().max()
        drawdown = (prices - running_max) / running_max
        return abs(drawdown.iloc[-1])
    
    def _assess_volatility(self, vol: float) -> tuple[float, float, str]:
        '''Assess volatility risk'''
        if vol > self.max_volatility * 1.5:
            return -1.5, 0.9, f"High volatility detected: {vol:.2%}"
        elif vol > self.max_volatility:
            return -0.8, 0.7, f"Moderate volatility: {vol:.2%}"
        elif vol > self.max_volatility * 0.5:
            return 1.0, 0.8, f"Acceptable volatility: {vol:.2%}"
        else:
            return 0.3, 0.6, f"Low volatility: {vol:.2%}"
        
    def _assess_drawdown(self, dd: float) -> tuple[float, float, str]:
        '''Assess drawdown risk'''
        if dd > 0.15:
            return -2.0, 0.95, f"Severe drawdown: {dd:.2%}"
        elif dd > 0.10:
            return -1.2, 0.8, f"Moderate drawdown: {dd:.2%}"
        elif dd > 0.03:
            return 0.8, 0.7, f"Acceptable drawdown: {dd:.2%}"
        else:
            return 0.0, 0.5, f"Low drawdown: {dd:.2%}"