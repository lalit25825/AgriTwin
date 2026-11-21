from datetime import date

from agritwin_ai.data.market.collector import MarketDataCollector
from agritwin_ai.data.market.ingestion import MarketIngestionService
from agritwin_ai.data.market.provider import MarketDataProvider
from agritwin_ai.data.market.repository import MarketRepository


class FakeMarketProvider(MarketDataProvider):
    name = "fake"

    def fetch_latest(self):
        return [
            {
                "date": "2026-09-08",
                "state": "Maharashtra",
                "district": "Nashik",
                "market": "Lasalgaon",
                "commodity": "Onion",
                "arrival_quantity": "1200",
                "min_price": "1800",
                "max_price": "2400",
                "modal_price": "2200",
            },
            {
                "date": "2026-09-08",
                "state": "Maharashtra",
                "district": "Pune",
                "market": "Pune",
                "commodity": "Potato",
                "arrival_quantity": "800",
                "min_price": "1500",
                "max_price": "2000",
                "modal_price": "1750",
            },
        ]

    def fetch_range(self, start_date, end_date):
        return self.fetch_latest()


def make_service(tmp_path):
    provider = FakeMarketProvider()

    collector = MarketDataCollector(
        provider=provider,
        raw_directory=tmp_path / "raw",
    )

    repository = MarketRepository(
        tmp_path / "processed" / "market_records.csv",
    )

    return MarketIngestionService(
        collector=collector,
        repository=repository,
    )


def test_ingest_latest(tmp_path):
    service = make_service(tmp_path)

    result = service.ingest_latest(
        save_raw=False,
    )

    assert result["fetched"] == 2
    assert result["inserted"] == 2
    assert result["duplicates"] == 0
    assert result["commodities"] == [
        "Onion",
        "Potato",
    ]


def test_ingest_latest_deduplicates(tmp_path):
    service = make_service(tmp_path)

    first = service.ingest_latest(
        save_raw=False,
    )

    second = service.ingest_latest(
        save_raw=False,
    )

    assert first["inserted"] == 2
    assert second["inserted"] == 0
    assert second["duplicates"] == 2


def test_ingest_persists_records(tmp_path):
    service = make_service(tmp_path)

    service.ingest_latest(
        save_raw=False,
    )

    records = service.repository.load()

    assert len(records) == 2
    assert records[0].commodity == "Onion"
    assert records[1].commodity == "Potato"


def test_ingest_returns_date_range(tmp_path):
    service = make_service(tmp_path)

    result = service.ingest_range(
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 8),
        save_raw=False,
    )

    assert result["date_min"] == date(2026, 9, 8)
    assert result["date_max"] == date(2026, 9, 8)