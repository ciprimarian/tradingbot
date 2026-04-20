from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict

from src.fuzzi.common.modes import RunMode


class BlotterEntryType(str, Enum):
    SIGNAL = "signal"
    ORDER_INTENT = "order_intent"
    ORDER_SIMULATED = "order_simulated"
    ORDER_SKIPPED = "order_skipped"
    NOTE = "note"


@dataclass(slots=True)
class BlotterEntry:
    entry_type: BlotterEntryType
    mode: RunMode
    created_at: datetime
    source: str
    payload: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""

