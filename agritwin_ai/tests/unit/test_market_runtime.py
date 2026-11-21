import numpy as np
import pandas as pd

from agritwin_ai.agents.market.market_runtime import (
    MarketRuntime,
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


def test_runtime_loads_market_data(tmp_path):
    path = tmp_path / "market_records.csv"

    make_dataframe().to_csv(
        path,
        index=False,
    )

    runtime = MarketRuntime(
        data_path=path
    )

    dataframe = runtime.load_data()

    assert len(dataframe) == 80


def test_runtime_executes_market_agent(tmp_path):
    path = tmp_path / "market_records.csv"

    make_dataframe().to_csv(
        path,
        index=False,
    )

    runtime = MarketRuntime(
        data_path=path
    )

    result = runtime.run(
        commodity="Onion",
        market="Lasalgaon",
        horizon=7,
    )

    assert result["agent"] == "market"
    assert len(result["forecast"]) == 7
    assert "decision" in result


def test_runtime_health_check(tmp_path):
    path = tmp_path / "market_records.csv"

    make_dataframe().to_csv(
        path,
        index=False,
    )

    runtime = MarketRuntime(
        data_path=path
    )

    assert runtime.health_check() is True


def test_missing_data_is_reported(tmp_path):
    runtime = MarketRuntime(
        data_path=tmp_path / "missing.csv"
    )

    assert runtime.health_check() is False

def test_runtime_passes_economic_parameters(tmp_path):
    path = tmp_path / "market_records.csv"

    make_dataframe().to_csv(
        path,
        index=False,
    )

    runtime = MarketRuntime(
        data_path=path
    )

    result = runtime.run(
        commodity="Onion",
        market="Lasalgaon",
        horizon=7,
        nearby_market_price=2200,
        transport_cost=50,
        storage_cost=75,
        expected_spoilage_pct=5,
    )

    assert "economics" in result

    assert (
        result["economics"]["nearby_market_price"]
        == 2200
    )

    assert (
        result["economics"]["transport_cost"]
        == 50
    )

    assert (
        result["economics"]["storage_cost"]
        == 75
    )

def test_forecast_requires_distinct_daily_observations(tmp_path):
    path = tmp_path / "market_records.csv"
    pd.DataFrame({
        "date": ["2026-09-09", "2026-09-09", "2026-09-09"],
        "state": ["Maharashtra"] * 3,
        "district": ["Nashik"] * 3,
        "market": ["APMC Lasalgaon", "Lasalgaon(Niphad)", "Lasalgaon(Vinchur)"],
        "commodity": ["Onion"] * 3,
        "modal_price": [2400, 2500, 2600],
        "arrival_quantity": [100, 200, 300],
    }).to_csv(path, index=False)

    runtime = MarketRuntime(data_path=path)
    import pytest
    with pytest.raises(ValueError, match="only 1 distinct daily market observations"):
        runtime.run(commodity="Onion", market="Lasalgaon", horizon=7)
