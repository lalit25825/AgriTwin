from datetime import date

import pytest

from agritwin_ai.data.market.ogd_provider import (
    OGDMarketDataProvider,
)
from agritwin_ai.data.market.provider import MarketDataProvider


class FakeProvider(MarketDataProvider):
    name = "fake"

    def fetch_latest(self):
        return [{"commodity": "Onion"}]

    def fetch_range(self, start_date, end_date):
        return [
            {
                "commodity": "Onion",
                "date": start_date.isoformat(),
            }
        ]


def test_provider_is_abstract():
    provider = FakeProvider()

    assert provider.name == "fake"
    assert provider.fetch_latest() == [{"commodity": "Onion"}]


def test_provider_range_returns_data():
    provider = FakeProvider()

    result = provider.fetch_range(
        date(2026, 9, 1),
        date(2026, 9, 5),
    )

    assert len(result) == 1
    assert result[0]["commodity"] == "Onion"


def test_ogd_provider_uses_default_endpoint():
    provider = OGDMarketDataProvider(
        api_key="test-key"
    )

    assert provider.endpoint.endswith(
        "9ef84268-d588-465a-a308-a864a43d0070"
    )


def test_ogd_provider_stores_configuration():
    provider = OGDMarketDataProvider(
        endpoint="https://example.com/api",
        api_key="test-key",
        timeout=10,
    )

    assert provider.endpoint == "https://example.com/api"
    assert provider.api_key == "test-key"
    assert provider.timeout == 10


def test_ogd_range_rejects_invalid_dates():
    provider = OGDMarketDataProvider(
        endpoint="https://example.com/api",
    )

    with pytest.raises(ValueError):
        provider.fetch_range(
            date(2026, 9, 10),
            date(2026, 9, 1),
        )


def test_ogd_provider_parses_records(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "records": [
                    {
                        "commodity": "Onion",
                        "modal_price": 2200,
                    }
                ]
            }

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(
        "agritwin_ai.data.market.ogd_provider.requests.get",
        fake_get,
    )

    provider = OGDMarketDataProvider(
        endpoint="https://example.com/api",
    )

    records = provider.fetch_latest()

    assert len(records) == 1
    assert records[0]["commodity"] == "Onion"
    assert records[0]["modal_price"] == 2200


def test_ogd_provider_rejects_missing_records(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": []}

    monkeypatch.setattr(
        "agritwin_ai.data.market.ogd_provider.requests.get",
        lambda *args, **kwargs: FakeResponse(),
    )

    provider = OGDMarketDataProvider(
        endpoint="https://example.com/api",
    )

    with pytest.raises(ValueError):
        provider.fetch_latest()

def test_ogd_provider_fetch_all_paginates():
    provider = OGDMarketDataProvider(
        api_key="test-key"
    )

    responses = [
        {
            "status": "ok",
            "total": 5,
            "records": [
                {"id": 1},
                {"id": 2},
            ],
        },
        {
            "status": "ok",
            "total": 5,
            "records": [
                {"id": 3},
                {"id": 4},
            ],
        },
        {
            "status": "ok",
            "total": 5,
            "records": [
                {"id": 5},
            ],
        },
    ]

    calls = []

    def fake_request(params):
        calls.append(params)
        return responses[len(calls) - 1]

    provider._request = fake_request

    records = provider.fetch_all(
        page_size=2
    )

    assert len(records) == 5
    assert [record["id"] for record in records] == [
        1,
        2,
        3,
        4,
        5,
    ]

    assert calls[0]["offset"] == 0
    assert calls[1]["offset"] == 2
    assert calls[2]["offset"] == 4


def test_ogd_provider_fetch_all_respects_max_records():
    provider = OGDMarketDataProvider(
        api_key="test-key"
    )

    provider._request = lambda params: {
        "status": "ok",
        "total": 10,
        "records": [
            {"id": params["offset"]},
            {"id": params["offset"] + 1},
        ],
    }

    records = provider.fetch_all(
        page_size=2,
        max_records=5,
    )

    assert len(records) == 5


def test_ogd_provider_fetch_all_rejects_invalid_page_size():
    provider = OGDMarketDataProvider(
        api_key="test-key"
    )

    with pytest.raises(ValueError):
        provider.fetch_all(
            page_size=0
        )