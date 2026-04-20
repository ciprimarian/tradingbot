from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(slots=True)
class Bar:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(slots=True)
class Signal:
    symbol: str
    direction: str
    confidence: float
    source: str
    timestamp: datetime
    score: float = 0.0
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OrderIntent:
    symbol: str
    side: str
    quantity: float
    order_type: str
    mode: str
    source: str
    created_at: datetime
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Position:
    symbol: str
    quantity: float
    average_entry: float
    market_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PortfolioSnapshot:
    timestamp: datetime
    cash: float
    equity: float
    buying_power: float = 0.0
    positions: Dict[str, Position] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

