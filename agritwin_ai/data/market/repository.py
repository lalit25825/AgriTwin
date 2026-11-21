from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Iterable

from agritwin_ai.data.market.schema import MarketRecord


class MarketRepository:
    """
    Persistent storage for normalized agricultural market records.

    V1 uses CSV so the dataset remains easy to inspect, debug, and
    feed into pandas/ML pipelines later.
    """

    FIELDNAMES = [
        "date",
        "state",
        "district",
        "market",
        "commodity",
        "variety",
        "grade",
        "arrival_quantity",
        "min_price",
        "max_price",
        "modal_price",
        "source",
        "collected_at",
    ]

    def __init__(
        self,
        path: str | Path = "data/market/processed/market_records.csv",
    ) -> None:
        self.path = Path(path)

    def save(
        self,
        records: Iterable[MarketRecord],
    ) -> int:
        """
        Add records to the repository.

        Existing records with the same observation key are not duplicated.

        Returns the number of newly inserted records.
        """

        incoming = list(records)

        if not incoming:
            return 0

        for record in incoming:
            if not isinstance(record, MarketRecord):
                raise TypeError(
                    "Repository accepts only MarketRecord objects."
                )

        existing = self.load()

        existing_keys = {
            self._record_key(record)
            for record in existing
        }

        new_records = []

        for record in incoming:
            key = self._record_key(record)

            if key in existing_keys:
                continue

            existing_keys.add(key)
            new_records.append(record)

        if not new_records:
            return 0

        all_records = existing + new_records

        self._write(all_records)

        return len(new_records)

    def load(self) -> list[MarketRecord]:
        """
        Load all stored records.
        """

        if not self.path.exists():
            return []

        records: list[MarketRecord] = []

        with self.path.open(
            "r",
            newline="",
            encoding="utf-8",
        ) as file:
            reader = csv.DictReader(file)

            for row in reader:
                records.append(
                    MarketRecord.model_validate(row)
                )

        return records

    def query(
        self,
        commodity: str | None = None,
        market: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[MarketRecord]:
        """
        Query stored records by commodity, market, and date range.
        """

        records = self.load()

        if commodity is not None:
            commodity_normalized = commodity.strip().lower()

            records = [
                record
                for record in records
                if record.commodity.lower()
                == commodity_normalized
            ]

        if market is not None:
            market_normalized = market.strip().lower()

            records = [
                record
                for record in records
                if record.market.lower()
                == market_normalized
            ]

        if start_date is not None:
            records = [
                record
                for record in records
                if record.date >= start_date
            ]

        if end_date is not None:
            records = [
                record
                for record in records
                if record.date <= end_date
            ]

        return sorted(
            records,
            key=lambda record: record.date,
        )

    def count(self) -> int:
        return len(self.load())

    def _write(
        self,
        records: list[MarketRecord],
    ) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=self.FIELDNAMES,
            )

            writer.writeheader()

            for record in records:
                data = record.model_dump(mode="json")

                writer.writerow(
                    {
                        field: data.get(field)
                        for field in self.FIELDNAMES
                    }
                )

    @staticmethod
    def _record_key(
        record: MarketRecord,
    ) -> tuple:
        """
        Unique observation identity.

        Price observations are identified by their date, location,
        commodity, variety, and grade.
        """

        return (
            record.date,
            record.state.strip().lower(),
            (record.district or "").strip().lower(),
            record.market.strip().lower(),
            record.commodity.strip().lower(),
            (record.variety or "").strip().lower(),
            (record.grade or "").strip().lower(),
        )