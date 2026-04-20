from enum import Enum


class RunMode(str, Enum):
    """How Fuzzi is currently operating."""

    PAPER = "paper"
    GHOST = "ghost"
    ASSIST = "assist"
    AUTOPILOT = "autopilot"


class TradingMode(str, Enum):
    """Human control posture over the trading loop."""

    MANUAL = "manual"
    HYBRID = "hybrid"
    AUTO = "auto"

