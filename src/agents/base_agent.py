# src/agents/base_agent.py

from enum import Enum
from dataclasses import dataclass
from typing import Any, Dict, Optional

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