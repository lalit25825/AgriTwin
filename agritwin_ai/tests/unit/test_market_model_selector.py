import numpy as np
import pandas as pd
import pytest

from agritwin_ai.data.market.dataset import (
    MarketDatasetBuilder,
)
from agritwin_ai.models.market.model_selector import (
    MarketModelSelector,
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


def test_model_selector_compares_models():
    dataframe = make_dataframe()

    builder = MarketDatasetBuilder()

    X, y = builder.prepare_training_data(
        dataframe
    )

    selector = MarketModelSelector()

    result = selector.compare(
        dataframe,
        X,
        y,
    )

    assert len(result) == 3

    assert set(result["model"]) == {
        "naive",
        "moving_average",
        "random_forest",
    }


def test_model_comparison_contains_metrics():
    dataframe = make_dataframe()

    builder = MarketDatasetBuilder()

    X, y = builder.prepare_training_data(
        dataframe
    )

    selector = MarketModelSelector()

    result = selector.compare(
        dataframe,
        X,
        y,
    )

    assert "mae" in result.columns
    assert "rmse" in result.columns
    assert "mape" in result.columns

    assert (result["mae"] >= 0).all()


def test_models_are_sorted_by_mae():
    dataframe = make_dataframe()

    builder = MarketDatasetBuilder()

    X, y = builder.prepare_training_data(
        dataframe
    )

    selector = MarketModelSelector()

    result = selector.compare(
        dataframe,
        X,
        y,
    )

    assert result["mae"].tolist() == sorted(
        result["mae"].tolist()
    )


def test_select_best():
    comparison = pd.DataFrame(
        [
            {
                "model": "naive",
                "mae": 100,
                "rmse": 120,
                "mape": 5,
            },
            {
                "model": "random_forest",
                "mae": 50,
                "rmse": 70,
                "mape": 2.5,
            },
        ]
    )

    selector = MarketModelSelector()

    best = selector.select_best(
        comparison
    )

    assert best["model"] == "random_forest"
    assert best["mae"] == 50


def test_empty_comparison_is_rejected():
    selector = MarketModelSelector()

    with pytest.raises(ValueError):
        selector.select_best(
            pd.DataFrame()
        )