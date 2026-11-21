from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from agritwin_ai.data.market.normalizer import MarketNormalizer
from agritwin_ai.data.market.provider import MarketDataProvider


class MarketDataCollector:
    """
    Collects raw market data from a provider and optionally persists
    the raw response for reproducibility and debugging.
    """

    def __init__(
        self,
        provider: MarketDataProvider,
        raw_directory: str | Path = "data/market/raw",
        normalizer: MarketNormalizer | None = None,
    ) -> None:
        self.provider = provider
        self.raw_directory = Path(raw_directory)
        self.normalizer = normalizer or MarketNormalizer()

    def collect_latest(
        self,
        save_raw: bool = True,
    ) -> list[dict[str, Any]]:
        records = self.provider.fetch_latest()

        self._validate_records(records)

        if save_raw:
            self._save_raw(
                records=records,
                collection_type="latest",
            )

        return records

    def collect_range(
        self,
        start_date: date,
        end_date: date,
        save_raw: bool = True,
    ) -> list[dict[str, Any]]:
        if end_date < start_date:
            raise ValueError(
                "end_date cannot be earlier than start_date."
            )

        records = self.provider.fetch_range(
            start_date=start_date,
            end_date=end_date,
        )

        self._validate_records(records)

        if save_raw:
            self._save_raw(
                records=records,
                collection_type=(
                    f"{start_date.isoformat()}_"
                    f"{end_date.isoformat()}"
                ),
            )

        return records

    def normalize_records(
        self,
        records: list[dict[str, Any]],
    ):
        normalized_records = []

        for record in records:
            normalized_records.append(
                self.normalizer.normalize(
                    raw_record=record,
                    source=self.provider.name,
                )
            )

        return normalized_records

    def collect_and_normalize_latest(
        self,
        save_raw: bool = True,
    ):
        raw_records = self.collect_latest(
            save_raw=save_raw,
        )

        return self.normalize_records(raw_records)

    def _save_raw(
        self,
        records: list[dict[str, Any]],
        collection_type: str,
    ) -> Path:
        self.raw_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        filename = (
            f"market_{collection_type}_{timestamp}.json"
        )

        path = self.raw_directory / filename

        payload = {
            "provider": self.provider.name,
            "collected_at": datetime.now().isoformat(),
            "record_count": len(records),
            "records": records,
        }

        path.write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

        return path

    @staticmethod
    def _validate_records(
        records: Any,
    ) -> None:
        if not isinstance(records, list):
            raise TypeError(
                "Market provider must return a list of records."
            )

        for index, record in enumerate(records):
            if not isinstance(record, dict):
                raise TypeError(
                    f"Market record at index {index} "
                    "must be a dictionary."
                )