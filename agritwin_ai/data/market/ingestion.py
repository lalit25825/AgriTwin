from __future__ import annotations

from datetime import date
from typing import Any

from agritwin_ai.data.market.collector import MarketDataCollector
from agritwin_ai.data.market.repository import MarketRepository
from agritwin_ai.data.market.schema import MarketRecord


class MarketIngestionService:
    """
    End-to-end ingestion service for agricultural market data.

    Provider-specific fetching is handled by MarketDataProvider.
    Normalization is handled by MarketDataCollector.
    Persistence is handled by MarketRepository.
    """

    def __init__(
        self,
        collector: MarketDataCollector,
        repository: MarketRepository,
    ) -> None:
        self.collector = collector
        self.repository = repository

    def ingest_latest(
        self,
        save_raw: bool = True,
    ) -> dict[str, Any]:
        """
        Fetch, normalize, validate, deduplicate and persist the
        latest available market observations.
        """

        records = self.collector.collect_and_normalize_latest(
            save_raw=save_raw,
        )

        inserted = self.repository.save(records)

        return self._build_result(
            records=records,
            inserted=inserted,
        )

    def ingest_range(
        self,
        start_date: date,
        end_date: date,
        save_raw: bool = True,
    ) -> dict[str, Any]:
        """
        Fetch, normalize, validate, deduplicate and persist market
        observations for an inclusive date range.
        """

        raw_records = self.collector.collect_range(
            start_date=start_date,
            end_date=end_date,
            save_raw=save_raw,
        )

        records = self.collector.normalize_records(
            raw_records,
        )

        inserted = self.repository.save(records)

        return self._build_result(
            records=records,
            inserted=inserted,
        )

    @staticmethod
    def _build_result(
        records: list[MarketRecord],
        inserted: int,
    ) -> dict[str, Any]:
        commodities = sorted(
            {
                record.commodity
                for record in records
            }
        )

        markets = sorted(
            {
                record.market
                for record in records
            }
        )

        dates = [
            record.date
            for record in records
        ]

        return {
            "fetched": len(records),
            "inserted": inserted,
            "duplicates": len(records) - inserted,
            "commodities": commodities,
            "markets": markets,
            "date_min": min(dates) if dates else None,
            "date_max": max(dates) if dates else None,
        }