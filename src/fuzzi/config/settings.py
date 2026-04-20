from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

from src.fuzzi.common.modes import RunMode, TradingMode

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "src" / "config" / "trading_config.yaml"


@dataclass(slots=True)
class BrokerSettings:
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    paper_trading: bool = True
    base_url: str = "https://paper-api.alpaca.markets"


@dataclass(slots=True)
class RuntimeSettings:
    run_mode: RunMode = RunMode.PAPER
    trading_mode: TradingMode = TradingMode.HYBRID
    allow_live_orders: bool = False
    default_symbol: str = "SPY"
    default_timeframe: str = "1Day"
    universe_size: int = 20


@dataclass(slots=True)
class LLMSettings:
    auth_path: str = "~/.codex/auth.json"
    primary_model: str = "gpt-4o"
    fallback_model: str = "gpt-4o-mini"
    max_calls_per_tick: int = 3
    timeout_seconds: int = 30


@dataclass(slots=True)
class RiskSettings:
    max_position_notional: float = 25.0
    max_open_positions: int = 4
    long_only: bool = True
    min_cash_buffer: float = 5.0


@dataclass(slots=True)
class FuzziSettings:
    project_root: Path
    config_path: Path
    broker: BrokerSettings
    runtime: RuntimeSettings
    llm: LLMSettings
    risk: RiskSettings
    raw_config: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_broker_credentials(self) -> bool:
        return bool(self.broker.alpaca_api_key and self.broker.alpaca_secret_key)


def _resolve_base_url(paper_trading: bool) -> str:
    if paper_trading:
        return "https://paper-api.alpaca.markets"
    return "https://api.alpaca.markets"


def _load_yaml_config(config_path: Path) -> Dict[str, Any]:
    if not config_path.exists():
        return {}

    with config_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected mapping in config file: {config_path}")
    return loaded


def load_settings(config_path: Path | None = None) -> FuzziSettings:
    load_dotenv()

    resolved_config_path = config_path or DEFAULT_CONFIG_PATH
    raw_config = _load_yaml_config(resolved_config_path)

    paper_trading = os.getenv("ALPACA_PAPER_TRADING", "true").lower() in {"true", "1", "t"}

    broker = BrokerSettings(
        alpaca_api_key=os.getenv("ALPACA_API_KEY", ""),
        alpaca_secret_key=os.getenv("ALPACA_SECRET_KEY", ""),
        paper_trading=paper_trading,
        base_url=_resolve_base_url(paper_trading),
    )

    trading_config = raw_config.get("trading", {})
    data_config = raw_config.get("data", {})

    runtime = RuntimeSettings(
        run_mode=RunMode.PAPER,
        trading_mode=TradingMode.HYBRID,
        allow_live_orders=False,
        default_symbol=trading_config.get("symbol", "SPY"),
        default_timeframe=data_config.get("timeframe", "1Day"),
        universe_size=20,
    )

    llm = LLMSettings()
    risk = RiskSettings()

    return FuzziSettings(
        project_root=PROJECT_ROOT,
        config_path=resolved_config_path,
        broker=broker,
        runtime=runtime,
        llm=llm,
        risk=risk,
        raw_config=raw_config,
    )
