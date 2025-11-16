# src/agents/base_agent.py

from enum import Enum
from dataclasses import dataclass
from typing import Any, Dict, Optional
from abc import ABC, abstractmethod
import pandas as pd

class SignalType(Enum):
    STRONG_BUY = 2
    BUY = 1
    HOLD = 0
    SELL = -1
    STRONG_SELL = -2


@dataclass
class AgentSignal:
    signal_type: SignalType
    confidence: float # 0.0 to 1.0
    reasoning: str
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> float:
        """Valiudates confidence in between 0 and 1"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
    
    @property
    def weighted_signal(self) -> float:
        """Returns the weighted signal value based on confidence."""
        return self.signal_type.value * self.confidence
    

class BaseAgent:
    '''Base class for trading agents.'''

    def __init__(self, name: str, weight: float = 1.0, config: Optional[Dict] = None):
        self.name = name
        self.weight = weight
        self.config = config or {}

        # Weight validation
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"Weight must be between 0.0 and 1.0, got {self.weight}")
        
    @abstractmethod
    def analyze(self, data: pd.DataFrame, **kwargs) -> AgentSignal:
        """Analyze market data and return an AgentSignal."""
        pass

    def get_info(self) -> Dict[str, Any]:
        """Returns agent information."""
        return {
            "name": self.name,
            "weight": self.weight,
            "type": self.__class__.__name__,
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__} (name={self.name} weight={self.weight})"