from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.fuzzi.blotter.records import BlotterEntry


class JsonlBlotter:
    """Append-only blotter storage for early Fuzzi runs."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, entry: BlotterEntry) -> None:
        serialized = self._to_jsonable(entry)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(serialized, sort_keys=True) + "\n")

    def _to_jsonable(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if is_dataclass(value):
            return {key: self._to_jsonable(item) for key, item in asdict(value).items()}
        if isinstance(value, dict):
            return {key: self._to_jsonable(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._to_jsonable(item) for item in value]
        if hasattr(value, "value"):
            return getattr(value, "value")
        return value

