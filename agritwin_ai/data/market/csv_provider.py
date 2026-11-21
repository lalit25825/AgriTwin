from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from agritwin_ai.data.market.provider import MarketDataProvider


class CSVMarketDataProvider(MarketDataProvider):
    """
    Market-data provider backed by an official CSV export.

    The CSV can come directly from the Government of India OGD
    mandi-price resource or another trusted provider using the
    same market-data concept.

    Provider-specific column names are intentionally not normalized
    here. MarketNormalizer handles that responsibility.
    """

    name = "ogd_csv"

    def __init__(
        self,
        path: str | Path,
    ) -> None:
        self.path = Path(path)

        if not self.path.exists():
            raise FileNotFoundError(
                f"Market CSV not found: {self.path}"
            )

    def _load(self) -> pd.DataFrame:
        dataframe = pd.read_csv(
            self.path,
            low_memory=False,
        )

        if dataframe.empty:
            raise ValueError(
                "Market CSV contains no records."
            )

        return dataframe

    def fetch_latest(self) -> list[dict[str, Any]]:
        dataframe = self._load()

        return dataframe.to_dict(
            orient="records"
        )

    def fetch_range(
        self,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        if end_date < start_date:
            raise ValueError(
                "end_date cannot be earlier than start_date."
            )

        dataframe = self._load()

        date_column = self._find_date_column(
            dataframe
        )

        parsed_dates = pd.to_datetime(
            dataframe[date_column],
            errors="coerce",
        )

        mask = (
            (parsed_dates.dt.date >= start_date)
            & (parsed_dates.dt.date <= end_date)
        )

        filtered = dataframe.loc[mask]

        return filtered.to_dict(
            orient="records"
        )

    def health_check(self) -> bool:
        try:
            dataframe = self._load()

            return not dataframe.empty

        except Exception:
            return False

    @staticmethod
    def _find_date_column(
        dataframe: pd.DataFrame,
    ) -> str:
        candidates = [
            "date",
            "Date",
            "arrival_date",
            "Arrival_Date",
            "price_date",
            "Price_Date",
        ]

        for candidate in candidates:
            if candidate in dataframe.columns:
                return candidate

        raise ValueError(
            "Could not identify a date column in market CSV."
        )