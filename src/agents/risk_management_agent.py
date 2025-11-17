# src/agents/risk_management_agent.py

import pandas as pd
import numpy as np

from typing import Any, Dict, Optional

from src.agents.base_agent import BaseAgent, AgentSignal, SignalType
from src.utils.logger import get_logger

class RiskManagementAgent(BaseAgent):
    '''Agent that analyzes risk metrics to provide trading signals.
    
       This agent analyzes"
       - Volatility (std, ATR)
       - Drawdown
       - VaR (Value at Risk)
       - Position Sizing constraints
       -Market Conditions (e.g. high volatility periods)
       '''
    def __init__(self, name: str = "RiskManagementAgent ", weight: float = 1.0, config: Optional[Dict[str, Any]] = None):
        super().__init__(name, weight, config)
        self.max_volatility = self.config.get("max_volatility", 0.03)
        self.max_drawdown = self.config.get("max_drawdown", 0.1)
        self.var_threshold = self.config.get("var_threshold", 0.05)
        self.lookback_period = self.config.get("lookback_period", 20)

        def analyze(self, data: pd.DataFrame, **kwargs) -> AgentSignal:
            if data.empty or len(data) < self.lookback_period:
                return AgentSignal(
                    signal_type=SignalType.HOLD,
                    confidence=0.0,
                    reasoning="Insufficient data for risk analysis."
                    )
            
            risk_factors = []
            reasoning_parts = []

            # 1. Volatility Analysis
            volatility = self._calculate_volatility(data)
            vol_signal, vol_confidence, vol_reason = self._assess_volatility(volatility)
            risk_factors.append((vol_signal, vol_confidence))
            reasoning_parts.append(vol_reason)
            
            # 2. Drawdown Analysis
            drawdown = self._calculate_drawdown(data)
            dd_signal, dd_confidence, dd_reason = self._assess_drawdown(drawdown)
            risk_factors.append((dd_signal, dd_confidence))
            reasoning_parts.append(dd_reason)
            
            # 3. Value at Risk
            var = self._calculate_var(data)
            var_signal, var_confidence, var_reason = self._assess_var(var)
            risk_factors.append((var_signal, var_confidence))
            reasoning_parts.append(var_reason)
            
            # 4. Volatility Regime
            regime_signal, regime_confidence, regime_reason = self._assess_volatility_regime(data)
            risk_factors.append((regime_signal, regime_confidence))
            reasoning_parts.append(regime_reason)
            
            # Aggregate risk assessment
            # Risk agent uses minimum confidence (most conservative)
            avg_signal = np.mean([s for s, _ in risk_factors])
            min_confidence = min([c for _, c in risk_factors])

            #Convert to SignalType
            # Positive = safe, Negative = risky
            signal_type = self._value_to_signal_type(avg_signal)
        
            reasoning = "Risk Assessment: " + " | ".join(reasoning_parts)

            return AgentSignal(
                signal_type=signal_type,
                confidence=min_confidence,
                reasoning=reasoning,
                metadata={
                    "volatility": volatility,
                    "drawdown": drawdown,
                    "var_95": var,
                    "risk_factors_checked": len(risk_factors)
                }
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