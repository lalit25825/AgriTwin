import pandas as pd
import pytest

from agritwin_ai.data.market.features import MarketFeatureEngineer


def make_dataframe():
    dates = pd.date_range(
        "2026-01-01",
        periods=40,
        freq="D",
    )

    return pd.DataFrame(
        {
            "date": dates,
            "state": ["Maharashtra"] * 40,
            "district": ["Nashik"] * 40,
            "market": ["Lasalgaon"] * 40,
            "commodity": ["Onion"] * 40,
            "modal_price": range(1800, 1840),
            "arrival_quantity": range(1000, 1040),
        }
    )


def test_feature_engineering_creates_calendar_features():
    engineer = MarketFeatureEngineer()

    result = engineer.transform(
        make_dataframe()
    )

    assert "day_of_week" in result.columns
    assert "month" in result.columns
    assert "year" in result.columns


def test_feature_engineering_creates_lag_features():
    engineer = MarketFeatureEngineer()

    result = engineer.transform(
        make_dataframe()
    )

    assert "price_lag_1" in result.columns
    assert "price_lag_7" in result.columns
    assert "price_lag_30" in result.columns

    assert pd.isna(
        result.iloc[0]["price_lag_1"]
    )

    assert result.iloc[7]["price_lag_7"] == 1800


def test_feature_engineering_creates_rolling_features():
    engineer = MarketFeatureEngineer()

    result = engineer.transform(
        make_dataframe()
    )

    assert "price_rolling_mean_7" in result.columns
    assert "price_rolling_std_7" in result.columns
    assert "price_rolling_mean_30" in result.columns


def test_feature_engineering_creates_price_changes():
    engineer = MarketFeatureEngineer()

    result = engineer.transform(
        make_dataframe()
    )

    assert "price_change_1d" in result.columns
    assert "price_change_7d" in result.columns


def test_feature_engineering_creates_arrival_features():
    engineer = MarketFeatureEngineer()

    result = engineer.transform(
        make_dataframe()
    )

    assert "arrival_lag_1" in result.columns
    assert "arrival_change_1d" in result.columns


def test_feature_engineering_requires_columns():
    engineer = MarketFeatureEngineer()

    with pytest.raises(ValueError):
        engineer.transform(
            pd.DataFrame(
                {
                    "date": ["2026-01-01"],
                    "modal_price": [2000],
                }
            )
        )


def test_feature_columns_exclude_identifiers():
    engineer = MarketFeatureEngineer()

    result = engineer.transform(
        make_dataframe()
    )

    features = engineer.get_feature_columns(result)

    assert "modal_price" not in features
    assert "commodity" not in features
    assert "market" not in features
    assert "price_lag_1" in features