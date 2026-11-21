from datetime import date

from agritwin_ai.data.market.collector import MarketDataCollector
from agritwin_ai.data.market.provider import MarketDataProvider


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
            }
        ]

    def fetch_range(self, start_date, end_date):
        return self.fetch_latest()


def test_collector_fetches_latest():
    collector = MarketDataCollector(
        provider=FakeMarketProvider(),
    )

    records = collector.collect_latest(
        save_raw=False,
    )

    assert len(records) == 1
    assert records[0]["commodity"] == "Onion"


def test_collector_normalizes_latest():
    collector = MarketDataCollector(
        provider=FakeMarketProvider(),
    )

    records = collector.collect_and_normalize_latest(
        save_raw=False,
    )

    assert len(records) == 1
    assert records[0].commodity == "Onion"
    assert records[0].modal_price == 2200


def test_collector_saves_raw_data(tmp_path):
    collector = MarketDataCollector(
        provider=FakeMarketProvider(),
        raw_directory=tmp_path,
    )

    records = collector.collect_latest(
        save_raw=True,
    )

    assert len(records) == 1

    files = list(tmp_path.glob("*.json"))

    assert len(files) == 1
    assert files[0].read_text(encoding="utf-8")


def test_collector_range_validates_dates():
    collector = MarketDataCollector(
        provider=FakeMarketProvider(),
    )

    try:
        collector.collect_range(
            start_date=date(2026, 9, 10),
            end_date=date(2026, 9, 1),
            save_raw=False,
        )
    except ValueError as exc:
        assert "end_date" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for invalid date range."
        )