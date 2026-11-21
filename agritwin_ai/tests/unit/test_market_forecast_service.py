import numpy as np
import pandas as pd
import pytest

from agritwin_ai.models.market.forecast_service import (
    MarketForecastService,
)


def make_dataframe(rows=80):
    dates = pd.date_range(
        "2026-01-01",
        periods=rows,
        freq="D",
    )

    prices = (
        1800
        + np.arange(rows) * 2
        + np.sin(np.arange(rows)) * 10
    )

    return pd.DataFrame(
        {
            "date": dates,
            "state": ["Maharashtra"] * rows,
            "district": ["Nashik"] * rows,
            "market": ["Lasalgaon"] * rows,
            "commodity": ["Onion"] * rows,
            "modal_price": prices,
            "arrival_quantity": (
                1000 + np.arange(rows) * 3
            ),
        }
    )


def test_forecast_returns_requested_horizon():
    dataframe = make_dataframe()

    service = MarketForecastService()

    result = service.forecast(
        dataframe=dataframe,
        commodity="Onion",
        market="Lasalgaon",
        horizon=7,
    )

    assert result["commodity"] == "Onion"
    assert result["market"] == "Lasalgaon"

    assert len(
        result["forecasts"]
    ) == 7


def test_forecast_dates_are_sequential():
    dataframe = make_dataframe()

    service = MarketForecastService()

    result = service.forecast(
        dataframe=dataframe,
        commodity="Onion",
        market="Lasalgaon",
        horizon=7,
    )

    dates = [
        item["date"]
        for item in result["forecasts"]
    ]

    assert dates == sorted(dates)

    assert dates[0] > result[
        "last_observed_date"
    ]


def test_forecast_contains_prices():
    dataframe = make_dataframe()

    service = MarketForecastService()

    result = service.forecast(
        dataframe=dataframe,
        commodity="Onion",
        market="Lasalgaon",
        horizon=5,
    )

    for item in result["forecasts"]:
        assert "predicted_price" in item
        assert np.isfinite(
            item["predicted_price"]
        )


def test_missing_market_history_is_rejected():
    dataframe = make_dataframe()

    service = MarketForecastService()

    with pytest.raises(ValueError):
        service.forecast(
            dataframe=dataframe,
            commodity="Tomato",
            market="Lasalgaon",
            horizon=7,
        )


def test_invalid_horizon_is_rejected():
    dataframe = make_dataframe()

    service = MarketForecastService()

    with pytest.raises(ValueError):
        service.forecast(
            dataframe=dataframe,
            commodity="Onion",
            market="Lasalgaon",
            horizon=0,
        )


def test_short_history_is_rejected():
    dataframe = make_dataframe(
        rows=20
    )

    service = MarketForecastService()

    with pytest.raises(ValueError):
        service.forecast(
            dataframe=dataframe,
            commodity="Onion",
            market="Lasalgaon",
            horizon=7,
        )