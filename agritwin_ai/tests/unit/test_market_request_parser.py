import pytest

from agritwin_ai.agents.market.request_parser import (
    MarketRequestParser,
)


def test_parse_onion_lasalgaon():
    parser = MarketRequestParser()

    result = parser.parse(
        "forecast onion prices in Lasalgaon"
    )

    assert result.commodity == "Onion"
    assert result.market == "Lasalgaon"
    assert result.horizon == 7


def test_parse_custom_horizon():
    parser = MarketRequestParser()

    result = parser.parse(
        "predict onion price in Lasalgaon for 14 days"
    )

    assert result.horizon == 14


def test_parse_is_case_insensitive():
    parser = MarketRequestParser()

    result = parser.parse(
        "ONION price at LASALGAON"
    )

    assert result.commodity == "Onion"
    assert result.market == "Lasalgaon"


def test_missing_commodity_rejected():
    parser = MarketRequestParser()

    with pytest.raises(ValueError):
        parser.parse(
            "price forecast for Lasalgaon"
        )


def test_missing_market_rejected():
    parser = MarketRequestParser()

    with pytest.raises(ValueError):
        parser.parse(
            "forecast onion prices"
        )


def test_empty_request_rejected():
    parser = MarketRequestParser()

    with pytest.raises(ValueError):
        parser.parse("")


def test_horizon_cannot_exceed_30_days():
    parser = MarketRequestParser()

    with pytest.raises(ValueError):
        parser.parse(
            "forecast onion price in Lasalgaon for 31 days"
        )

def test_parse_both_markets_when_user_names_an_alternative():
    parser = MarketRequestParser()
    result = parser.parse("onion price in Nashik mandi or Lasangaon mandi")
    assert result.markets == ("Nashik", "Lasalgaon")
    assert result.market == "Nashik"


def test_parse_next_week_and_week_after_as_fourteen_days():
    parser = MarketRequestParser()
    result = parser.parse("forecast onion prices next week and the week after in Lasalgaon")
    assert result.horizon == 14


def test_parse_explicit_forecast_end_date_as_horizon(monkeypatch):
    from datetime import date as real_date

    class FixedDate:
        @classmethod
        def today(cls):
            return real_date(2026, 11, 18)

    monkeypatch.setattr("agritwin_ai.agents.market.request_parser.date", FixedDate)
    parser = MarketRequestParser()
    result = parser.parse("forecast onion price in Nashik up to 25 Nov 2026")
    assert result.horizon == 7
