import numpy as np
import pandas as pd
import pytest

from agritwin_ai.data.market.profiler import (
    MarketDataProfiler,
)


def make_dataframe(rows=20):
    dates = pd.date_range(
        "2026-01-01",
        periods=rows,
        freq="D",
    )

    return pd.DataFrame(
        {
            "date": dates,
            "state": ["Maharashtra"] * rows,
            "district": ["Nashik"] * rows,
            "market": ["Lasalgaon"] * rows,
            "commodity": ["Onion"] * rows,
            "arrival_quantity": (
                1000 + np.arange(rows) * 10
            ),
            "min_price": (
                1700 + np.arange(rows)
            ),
            "max_price": (
                1900 + np.arange(rows)
            ),
            "modal_price": (
                1800 + np.arange(rows)
            ),
        }
    )


def test_profile_basic_statistics():
    dataframe = make_dataframe()

    profiler = MarketDataProfiler()

    result = profiler.profile(dataframe)

    assert result["row_count"] == 20
    assert result["commodity_count"] == 1
    assert result["state_count"] == 1
    assert result["market_count"] == 1
    assert result["district_count"] == 1


def test_profile_date_range():
    dataframe = make_dataframe()

    profiler = MarketDataProfiler()

    result = profiler.profile(dataframe)

    assert str(result["date_min"]) == "2026-01-01"
    assert str(result["date_max"]) == "2026-01-20"


def test_missing_values_are_detected():
    dataframe = make_dataframe()

    dataframe.loc[3, "modal_price"] = np.nan

    profiler = MarketDataProfiler()

    result = profiler.profile(dataframe)

    assert result["missing_values"]["modal_price"] == 1


def test_invalid_prices_are_detected():
    dataframe = make_dataframe()

    dataframe.loc[3, "max_price"] = 1000

    profiler = MarketDataProfiler()

    validation = profiler.validate(
        dataframe
    )

    assert validation["valid"] is False

    assert any(
        "invalid_price_relationships"
        in error
        for error in validation["errors"]
    )


def test_negative_values_are_detected():
    dataframe = make_dataframe()

    dataframe.loc[2, "arrival_quantity"] = -10

    profiler = MarketDataProfiler()

    validation = profiler.validate(
        dataframe
    )

    assert validation["valid"] is False

    assert any(
        "negative_arrival_quantity"
        in error
        for error in validation["errors"]
    )


def test_coverage_report_detects_missing_dates():
    dataframe = make_dataframe()

    dataframe = dataframe.drop(
        index=[5, 10]
    ).reset_index(drop=True)

    profiler = MarketDataProfiler()

    result = profiler.coverage_report(
        dataframe
    )

    assert result["date_count"] == 18
    assert result["expected_date_count"] == 20

    assert result["coverage_ratio"] == 0.9

    assert len(
        result["missing_dates"]
    ) == 2


def test_empty_dataframe_is_rejected():
    profiler = MarketDataProfiler()

    with pytest.raises(ValueError):
        profiler.profile(
            pd.DataFrame()
        )


def test_missing_columns_are_rejected():
    dataframe = make_dataframe()

    dataframe = dataframe.drop(
        columns=["modal_price"]
    )

    profiler = MarketDataProfiler()

    with pytest.raises(ValueError):
        profiler.profile(
            dataframe
        )