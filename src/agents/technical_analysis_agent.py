# src/agents/technical_analysis_agent.py

from typing import Dict, Optional
import pandas as pd
import numpy as np

from src.agents.base_agent import BaseAgent, AgentSignal, SignalType

class TechnicalAnalysisAgent(BaseAgent):
    '''Agent that uses technical indicators to generate trading signals.'''

    def __init__(self, name: str = "TechnicalAnalysisAgent", weight: float = 1.0, config: Optional[Dict] = None):
        super().__init__(name, weight, config)

        #Get threshold from config or set defaults
        self.rsi_overbought = self.config.get("rsi_overbought", 70)
        self.rsi_oversold = self.config.get("rsi_oversold", 30)

    def analyze(self, data: pd.DataFrame, **kwargs) -> AgentSignal:
        '''Analyze technical indicators'''
        if data.empty:
            return AgentSignal(
                signal_type=SignalType.HOLD,
                confidence=0.0,
                reasoning="No data provided",
            )
        
        # Get latest data point
        latest = data.iloc[-1]

        #Analyze RSI if available
        if 'rsi_14' in data.columns:
            rsi = latest['rsi_14']
            signal_value, confidence, reasoning = self._analyze_rsi(rsi)

            #Convert to SignalType
            if signal_value > 1.5:
                signal_type = SignalType.STRONG_BUY
            elif signal_value > 0.5:
                signal_type = SignalType.BUY
            elif signal_value < -1.5:
                signal_type = SignalType.STRONG_SELL
            elif signal_value < -0.5:
                signal_type = SignalType.SELL
            else:
                signal_type = SignalType.HOLD

            return AgentSignal(
                signal_type=signal_type,
                confidence=confidence,
                reasoning=reasoning,
            )
        
        return AgentSignal(
            signal_type=SignalType.HOLD,
            confidence=0.0,
            reasoning="No RSI data available",
        )
    
    def _analyze_rsi(self, rsi: float) -> tuple[float, float, str]:
        '''Analyze Rsi value. Returns signal value, confidence, and reasoning.'''
        if pd.isna(rsi):
            return 0.0, 0.0, "RSI value is NaN"
        
        if rsi <= 20:
            return 2.0, 0.9, f"RSI is {rsi}, indicating strong oversold conditions."
        elif rsi <= self.rsi_oversold:
            return 1.0, 0.7, f"RSI is {rsi}, indicating oversold conditions."
        elif rsi >= 80:
            return -2.0, 0.9, f"RSI is {rsi}, indicating strong overbought conditions."
        elif rsi >= self.rsi_overbought:
            return -1.0, 0.7, f"RSI is {rsi}, indicating overbought conditions."
        else:
            return 0.0, 0.5, f"RSI is {rsi}, indicating neutral conditions."