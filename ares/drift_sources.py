from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

REQUIRED_DRIFT_COLUMNS = {"id", "model_name", "prediction", "confidence", "timestamp"}


class ProductionDataSource(ABC):
    @abstractmethod
    def fetch_recent_predictions(self, model_name: str, hours: int) -> pd.DataFrame: ...


class LocalFileDataSource(ProductionDataSource):
    def __init__(self, directory: str | Path):
        self.directory = Path(directory)

    def fetch_recent_predictions(self, model_name: str, hours: int) -> pd.DataFrame:
        del hours  # local sample source returns the full file
        path = self.directory / f"{model_name}_predictions.csv"
        if not path.exists():
            raise FileNotFoundError(f"prediction source file not found: {path}")
        df = pd.read_csv(path)
        missing = REQUIRED_DRIFT_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"prediction source file missing required columns: {sorted(missing)}")
        return df