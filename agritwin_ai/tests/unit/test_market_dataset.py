import pandas as pd

from agritwin_ai.data.market.dataset import (
    MarketDatasetBuilder,
)


def make_dataframe():
    dates = pd.date_range(
        "2026-01-01",
        periods=50,
        freq="D",
    )

    return pd.DataFrame(
        {
            "date": dates,
            "state": ["Maharashtra"] * 50,
            "district": ["Nashik"] * 50,
            "market": ["Lasalgaon"] * 50,
            "commodity": ["Onion"] * 50,
            "modal_price": range(1800, 1850),
            "arrival_quantity": range(1000, 1050),
        }
    )


def test_dataset_creates_next_day_target():
    builder = MarketDatasetBuilder()

    result = builder.build(
        make_dataframe()
    )

    assert "target_next_day_price" in result.columns

    assert (
        result.iloc[0]["target_next_day_price"]
        == 1801
    )


def test_last_row_has_no_future_target():
    builder = MarketDatasetBuilder()

    result = builder.build(
        make_dataframe()
    )

    assert pd.isna(
        result.iloc[-1]["target_next_day_price"]
    )


def test_prepare_training_data_removes_missing_rows():
    builder = MarketDatasetBuilder()

    X, y = builder.prepare_training_data(
        make_dataframe()
    )

    assert len(X) == len(y)
    assert len(X) > 0
    assert not X.isna().any().any()
    assert not y.isna().any()


def test_training_target_is_next_day_price():
    builder = MarketDatasetBuilder()

    X, y = builder.prepare_training_data(
        make_dataframe()
    )

    assert y.iloc[0] == 1831


def test_features_do_not_include_target():
    builder = MarketDatasetBuilder()

    X, y = builder.prepare_training_data(
        make_dataframe()
    )

    assert "target_next_day_price" not in X.columns
    assert "modal_price" not in X.columns