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
        signals = []
        reasoning_parts = []

        #Analyze RSI if available
        if 'rsi_14' in data.columns:
            rsi_signal, rsi_conf, rsi_reason = self.analyze_rsi(latest['rsi_14'])
            signals.append(rsi_signal, rsi_conf)
            reasoning_parts.append(rsi_reason)

        #MA analysis
        if 'sma_20' in data.columns and 'sma_50' in data.columns:
            ma_signal, ma_conf, ma_reason = self.analyze_moving_averages(
                price=latest['close'],
                sma_20=latest['sma_20'],
                sma_50=latest['sma_50'],
            )
            signals.append(ma_signal, ma_conf)
            reasoning_parts.append(ma_reason)

        #Aggregate signals
        if not signals:
            return AgentSignal(
                signal_type=SignalType.HOLD,
                confidence=0.0,
                reasoning="No indicators available for analysis",
            )
        
        signal_value = sum(s * c for s, c in signals)
        confidence = sum(c for _, c in signals)
        avg_signal = signal_value / len(signals) if signals else 0.0
        avg_confidence = confidence / len(signals) if signals else 0.0

        signal_type = self._value_to_signal_type(avg_signal)

        reasoning = "; ".join(reasoning_parts)

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
            confidence=avg_confidence,
            reasoning=reasoning,
            metadata={
                'indicators_used': len(signals),
                'avg_signal_value': avg_signal,
            }
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
        
    def analyze_moving_averages(self, price: float, sma_20: float, sma_50: float) -> tuple[float, float, str]:
        '''Analyze Moving Average crossover'''
        if any(pd.isna([price, sma_20, sma_50])):
            return 0.0, 0.0, "MA: N/A"
        
        price_above_20 = price > sma_20
        price_above_50 = price > sma_50 
        ma20_above_50 = sma_20 > sma_50

        #Golden Cross: price above both MAs and SMA20 > SMA50
        if price_above_20 and price_above_50 and ma20_above_50:
            return 1.5, 0.8, "MA: Bullish (golden cross)"
        #Death Cross: oposite
        elif not price_above_20 and not price_above_50 and not ma20_above_50:
            return -1.5, 0.8, "MA: Bearish (death cross)"
        elif ma20_above_50:
            return 0.8, 0.6, "MA: Slightly Bullish"
        else:
            return -0.8, 0.6, "MA: Slightly Bearish"