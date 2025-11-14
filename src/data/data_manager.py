# src/data/data_manager.py

from pathlib import Path
from typing import Optional

import pandas as pd

from src.config.settings import load_config, PROJECT_ROOT
from src.data.market_data import MarketData
from src.utils.logger import get_Logger

class DataManager:
    """
    Centralized data manager for handling market data operations.
    """

    def __init__(
        self,
        config: Optional[dict] = None,
        storage_path: Optional[Path] = None
    ) -> None:
        self.config = config or load_config()
        self.logger = get_Logger(__name__)
        base_path = storage_path or Path(
            self.config.get("storage", {}).get("base_path", PROJECT_ROOT / "data" / "processed")
        )
        self.storage_format = self.config.get("storage", {}).get("format", "parquet").lower()
        self.storage_path = Path(base_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.market_data = MarketData()

    def get_historical_data(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = 100
    ) -> pd.DataFrame:
        symbol = symbol or self.config["trading"]["symbol"]
        timeframe = timeframe or self.config["data"]["timeframe"]
        start_date = start_date or self.config["data"]["start_date"]
        limit = limit or self.config["data"].get("limit")

        """
        Fetch historical market data for a given symbol and timeframe.
        """

        self.logger.info("Fetching data | symbol=%s, timeframe=%s, start=%s, end=%s, limit=%d", symbol, timeframe, start_date, end_date, limit)
        df = self.market_data.get_historical_bars(symbol=symbol, timeframe=timeframe, start=start_date, end=end_date, limit=limit)
        if df is None or df.empty:
            raise RuntimeError(f"No data returned for {symbol} in the given period.")
        return df
    
    def clean_data(
        self,
        df: pd.DataFrame,
        fill_method: str = "ffill",
        outlier_std_threshold: float = 3.0,
    ) -> pd.DataFrame:
        if df.empty:
            return df

        if fill_method == "ffill":
            df = df.ffill()
        elif fill_method == "bfill":
            df = df.bfill()
        else:
            df = df.fillna(method=fill_method)

        numeric_cols = df.select_dtypes(include="number").columns
        if len(numeric_cols) > 0:
            z_scores = ((df[numeric_cols] - df[numeric_cols].mean()) / df[numeric_cols].std(ddof=0)).abs()
            median_vals = df[numeric_cols].median()
            df.loc[:, numeric_cols] = df[numeric_cols].where(
                z_scores <= outlier_std_threshold, median_vals
            )
        return df

    def save_data(self, df: pd.DataFrame, name: str, fmt: Optional[str] = None) -> Path:
        if df.empty:
            raise ValueError("Cannot save an empty dataframe.")

        fmt = (fmt or self.storage_format).lower()
        path = self._build_path(name, fmt)
        self.logger.info("Saving dataset %s to %s", name, path)

        if fmt == "parquet":
            df.to_parquet(path)
        elif fmt == "csv":
            df.to_csv(path)
        else:
            raise ValueError(f"Unsupported storage format: {fmt}")
        return path

    def load_data(self, name: str, fmt: Optional[str] = None) -> pd.DataFrame:
        fmt = (fmt or self.storage_format).lower()
        path = self._build_path(name, fmt)
        if not path.exists():
            self.logger.warning("No cached dataset found for %s", name)
            return pd.DataFrame()

        self.logger.info("Loading dataset %s from %s", name, path)
        if fmt == "parquet":
            return pd.read_parquet(path)
        if fmt == "csv":
            df = pd.read_csv(path, parse_dates=True, index_col=0)
            return df
        raise ValueError(f"Unsupported storage format: {fmt}")

    def _build_path(self, name: str, fmt: str) -> Path:
        safe_name = name.replace(" ", "_").lower()
        return self.storage_dir / f"{safe_name}.{fmt}"

