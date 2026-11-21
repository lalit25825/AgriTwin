from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from agritwin_ai.agents.market.market_intelligence import MarketIntelligenceService
from agritwin_ai.data.market.ogd_provider import OGDMarketDataProvider


def _row(day, district, market, price, state="Maharashtra", commodity="Onion"):
    return {
        "date": day.isoformat(),
        "state": state,
        "district": district,
        "market": market,
        "commodity": commodity,
        "variety": "Red",
        "grade": "FAQ",
        "arrival_quantity": 100,
        "min_price": price - 100,
        "max_price": price + 100,
        "modal_price": price,
        "source": "test fixture",
        "collected_at": "2026-11-20T10:00:00+00:00",
    }


class NoNetworkProvider:
    api_key = None

    def fetch_state(self, state, page_size=1000, max_records=None):
        return []


def test_regional_fallback_includes_all_available_neighbouring_districts(tmp_path):
    today = date.today()
    rows = [
        _row(today - timedelta(days=1), "Dhule", "Dhule APMC", 4200),
        _row(today - timedelta(days=1), "Jalgaon", "Jalgaon APMC", 4400),
        _row(today - timedelta(days=1), "Nandurbar", "Nandurbar APMC", 4100),
    ]
    source = tmp_path / "market_records.csv"
    pd.DataFrame(rows).to_csv(source, index=False)

    service = MarketIntelligenceService(
        data_path=source,
        history_path=tmp_path / "market_live_history.csv",
        provider=NoNetworkProvider(),
        backfill_days=0,
    )
    result = service.get_dashboard("Nashik", "Onion", horizon=3)

    assert result["available"] is True
    assert result["region_match"] == "nearby_districts"
    assert set(result["nearby_districts_considered"]) == {"Dhule", "Jalgaon", "Nandurbar"}
    assert {row["district"] for row in result["mandis"]} == {"Dhule", "Jalgaon", "Nandurbar"}


def test_best_price_ignores_a_stale_higher_quote_when_fresher_quote_exists(tmp_path):
    today = date.today()
    rows = [
        _row(today - timedelta(days=9), "Nashik", "Lasalgaon", 5200),
        _row(today - timedelta(days=1), "Nashik", "Pimpalgaon", 4650),
    ]
    source = tmp_path / "market_records.csv"
    pd.DataFrame(rows).to_csv(source, index=False)

    service = MarketIntelligenceService(
        data_path=source,
        history_path=tmp_path / "market_live_history.csv",
        provider=NoNetworkProvider(),
        backfill_days=0,
    )
    result = service.get_dashboard("Nashik", "Onion", horizon=3)

    assert result["available"] is True
    assert result["summary"]["best_mandi"] == "Pimpalgaon"
    assert result["summary"]["best_modal_price"] == 4650
    assert result["summary"]["best_quote_is_stale"] is False


def test_unrecognised_location_does_not_fall_back_to_unrelated_nationwide_data(tmp_path):
    today = date.today()
    source = tmp_path / "market_records.csv"
    pd.DataFrame([_row(today, "Nashik", "Lasalgaon", 4600)]).to_csv(source, index=False)
    service = MarketIntelligenceService(
        data_path=source,
        history_path=tmp_path / "market_live_history.csv",
        provider=NoNetworkProvider(),
        backfill_days=0,
    )

    result = service.get_dashboard("Unknownville", "Onion", horizon=3)
    assert result["available"] is False
    assert result["region_match"] == "no_regional_match"


def test_short_history_forecast_is_explicitly_low_confidence(tmp_path):
    today = date.today()
    source = tmp_path / "market_records.csv"
    pd.DataFrame([
        _row(today - timedelta(days=1), "Nashik", "Lasalgaon", 4600),
        _row(today, "Nashik", "Lasalgaon", 4700),
    ]).to_csv(source, index=False)
    service = MarketIntelligenceService(
        data_path=source,
        history_path=tmp_path / "market_live_history.csv",
        provider=NoNetworkProvider(),
        backfill_days=0,
    )

    result = service.get_dashboard("Nashik", "Onion", horizon=2)
    assert result["forecast_meta"]["confidence"] == "very_low"
    assert "not a statistically reliable ML forecast" in result["forecast_meta"]["note"]


def test_random_forest_forecast_path_is_backtested_when_sufficient_history_exists():
    days = 110
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=days, freq="D")
    step = range(days)
    history = pd.DataFrame({
        "date": dates,
        "state": "Maharashtra",
        "district": "Nashik",
        "market": "Lasalgaon",
        "commodity": "Onion",
        "variety": None,
        "grade": None,
        "arrival_quantity": [800 + i * 2 for i in step],
        "min_price": [1700 + i * 3 for i in step],
        "max_price": [2100 + i * 3 for i in step],
        "modal_price": [1900 + i * 3 + (i % 7) * 2 for i in step],
    })

    result = MarketIntelligenceService()._forecast(history, horizon=5)
    assert len(result["forecasts"]) == 5
    assert result["confidence"] in {"high", "medium", "low"}
    assert result["history_days"] == days
    assert result["mae"] is not None
    assert result["mape"] is not None


def test_historical_provider_uses_partition_pagination_then_filters_date_range():
    class FakeOGDProvider(OGDMarketDataProvider):
        def __init__(self):
            super().__init__(api_key="test-key", max_retries=1)
            self.params = []

        def _request(self, params=None):
            self.params.append(dict(params or {}))
            return {
                "total": 3,
                "records": [
                    {"arrival_date": "01/10/2026", "state": "Maharashtra", "district": "Nashik", "commodity": "Onion", "market": "Lasalgaon", "variety": "Red", "grade": "FAQ", "arrival": "10", "min_price": "1000", "max_price": "1300", "modal_price": "1200"},
                    {"arrival_date": "15/10/2026", "state": "Maharashtra", "district": "Nashik", "commodity": "Onion", "market": "Lasalgaon", "variety": "Red", "grade": "FAQ", "arrival": "10", "min_price": "1000", "max_price": "1300", "modal_price": "1200"},
                    {"arrival_date": "01/09/2026", "state": "Maharashtra", "district": "Nashik", "commodity": "Onion", "market": "Lasalgaon", "variety": "Red", "grade": "FAQ", "arrival": "10", "min_price": "1000", "max_price": "1300", "modal_price": "1200"},
                ],
            }

    provider = FakeOGDProvider()
    rows = provider.fetch_market_history(
        state="Maharashtra",
        district="Nashik",
        commodity="Onion",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 31),
        limit=9000,
    )

    assert [item["arrival_date"] for item in rows] == ["01/10/2026", "15/10/2026"]
    assert provider.params[0]["filters[state.keyword]"] == "Maharashtra"
    assert provider.params[0]["filters[district.keyword]"] == "Nashik"
    assert provider.params[0]["filters[commodity.keyword]"] == "Onion"
    assert "filters[arrival_date]" not in provider.params[0]


def test_named_mandi_query_does_not_return_every_mandi_in_parent_district(tmp_path):
    today = date.today()
    source = tmp_path / "market_records.csv"
    pd.DataFrame([
        _row(today, "Nashik", "Lasalgaon", 4700),
        _row(today, "Nashik", "Pimpalgaon", 4550),
    ]).to_csv(source, index=False)
    service = MarketIntelligenceService(
        data_path=source,
        history_path=tmp_path / "market_live_history.csv",
        provider=NoNetworkProvider(),
        backfill_days=0,
    )

    result = service.get_dashboard("Lasalgaon", "Onion", horizon=3)
    assert result["region_match"] == "requested_market"
    assert [item["market"] for item in result["mandis"]] == ["Lasalgaon"]


def test_historical_backfill_failure_does_not_hide_successful_current_api_snapshot(tmp_path):
    today = date.today()

    class CurrentSnapshotProvider:
        api_key = "test-key"
        def fetch_state(self, state, page_size=1000, max_records=None):
            return [_row(today, "Nashik", "Lasalgaon", 4700)]
        def fetch_market_history(self, **kwargs):
            raise RuntimeError("history endpoint temporarily unavailable")

    source = tmp_path / "market_records.csv"
    pd.DataFrame(columns=["date", "state", "district", "market", "commodity", "modal_price"]).to_csv(source, index=False)
    service = MarketIntelligenceService(
        data_path=source,
        history_path=tmp_path / "market_live_history.csv",
        provider=CurrentSnapshotProvider(),
        backfill_days=365,
    )
    result = service.get_dashboard("Nashik", "Onion", horizon=3)

    assert result["available"] is True
    assert result["source_status"] == "live_api"
    assert result["freshness"] == "today"
    assert "Historical backfill unavailable" in result["warning"]


def test_stale_local_quote_does_not_hide_fresh_neighbour_price(tmp_path):
    today = date.today()
    source = tmp_path / "market_records.csv"
    pd.DataFrame([
        _row(today - timedelta(days=8), "Nashik", "Lasalgaon", 5200),
        _row(today - timedelta(days=1), "Dhule", "Dhule APMC", 4750),
        _row(today - timedelta(days=1), "Jalgaon", "Jalgaon APMC", 4680),
    ]).to_csv(source, index=False)
    service = MarketIntelligenceService(
        data_path=source,
        history_path=tmp_path / "market_live_history.csv",
        provider=NoNetworkProvider(),
        backfill_days=0,
    )

    result = service.get_dashboard("Nashik", "Onion", horizon=3)
    assert result["region_match"] == "nearby_districts"
    assert result["summary"]["best_mandi"] == "Dhule APMC"
    assert result["summary"]["best_quote_is_stale"] is False
    assert {row["district"] for row in result["mandis"]} == {"Nashik", "Dhule", "Jalgaon"}


def test_neighbour_history_backfill_uses_official_commodity_spelling(tmp_path):
    today = date.today()

    class CapturingProvider:
        api_key = "test-key"
        def __init__(self):
            self.history_args = None
        def fetch_state(self, state, page_size=1000, max_records=None):
            return [_row(today, "Dhule", "Dhule APMC", 4800)]
        def fetch_market_history(self, **kwargs):
            self.history_args = kwargs
            return []

    provider = CapturingProvider()
    source = tmp_path / "market_records.csv"
    pd.DataFrame(columns=["date", "state", "district", "market", "commodity", "modal_price"]).to_csv(source, index=False)
    service = MarketIntelligenceService(
        data_path=source,
        history_path=tmp_path / "market_live_history.csv",
        provider=provider,
        backfill_days=365,
    )
    result = service.get_dashboard("Nashik", "onion", horizon=3)

    assert result["available"] is True
    assert provider.history_args["district"] == "Dhule"
    assert provider.history_args["commodity"] == "Onion"


def test_random_forest_not_selected_before_enough_rows_for_temporal_training():
    days = 65
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=days, freq="D")
    values = range(days)
    history = pd.DataFrame({
        "date": dates,
        "state": "Maharashtra",
        "district": "Nashik",
        "market": "Lasalgaon",
        "commodity": "Onion",
        "variety": None,
        "grade": None,
        "arrival_quantity": [800 + i for i in values],
        "min_price": [1700 + i for i in values],
        "max_price": [2100 + i for i in values],
        "modal_price": [1900 + i + (i % 7) for i in values],
    })
    result = MarketIntelligenceService()._forecast(history, horizon=3)
    assert result["model"] in {"last_observation", "moving_average_7", "damped_linear_trend"}
    assert result["mape"] is None


def test_mandi_comparison_preserves_variety_grade_quote_spread(tmp_path):
    today = date.today()
    rows = [
        _row(today, "Nashik", "Lasalgaon", 4400),
        _row(today, "Nashik", "Lasalgaon", 4600),
    ]
    rows[0]["variety"] = "Red"
    rows[0]["grade"] = "FAQ"
    rows[1]["variety"] = "Pusa"
    rows[1]["grade"] = "Super"
    source = tmp_path / "market_records.csv"
    pd.DataFrame(rows).to_csv(source, index=False)
    service = MarketIntelligenceService(
        data_path=source,
        history_path=tmp_path / "market_live_history.csv",
        provider=NoNetworkProvider(),
        backfill_days=0,
    )

    result = service.get_dashboard("Nashik", "Onion", horizon=3)
    mandi = result["mandis"][0]
    assert mandi["modal_price"] == 4500
    assert mandi["modal_price_spread_low"] == 4400
    assert mandi["modal_price_spread_high"] == 4600
    assert {item["variety"] for item in mandi["quality_quotes"]} == {"Red", "Pusa"}


def test_historical_api_rows_are_not_mislabelled_as_current_live_prices(tmp_path):
    today = date.today()

    class HistoricalOnlyProvider:
        api_key = "test-key"
        def fetch_state(self, state, page_size=1000, max_records=None):
            return []
        def fetch_market_history(self, **kwargs):
            return [_row(today - timedelta(days=1), "Nashik", "Lasalgaon", 4725)]

    source = tmp_path / "market_records.csv"
    pd.DataFrame(columns=["date", "state", "district", "market", "commodity", "modal_price"]).to_csv(source, index=False)
    service = MarketIntelligenceService(
        data_path=source,
        history_path=tmp_path / "market_live_history.csv",
        provider=HistoricalOnlyProvider(),
        backfill_days=365,
    )
    result = service.get_dashboard("Nashik", "Onion", horizon=3)

    assert result["available"] is True
    assert result["source_status"] == "historical_api"
    assert result["freshness"] == "recent"
    assert result["streaming_trades_available"] is False
    assert "no current daily quote" in result["warning"]
