import numpy as np
import pandas as pd
import pytest

from agritwin_ai.models.market.baseline import (
    MovingAverageForecaster,
    NaiveMarketForecaster,
)
from agritwin_ai.models.market.evaluator import (
    MarketForecastEvaluator,
)
from agritwin_ai.models.market.random_forest import (
    MarketRandomForest,
)


def make_training_data():
    X = pd.DataFrame(
        {
            "price_lag_1": np.arange(100, 150),
            "price_lag_7": np.arange(90, 140),
            "price_rolling_mean_7": np.arange(95, 145),
            "arrival_quantity": np.arange(1000, 1050),
        }
    )

    y = (
        X["price_lag_1"] * 1.02
        + X["arrival_quantity"] * 0.01
    )

    return X, y


def test_naive_forecaster():
    df = pd.DataFrame(
        {
            "modal_price": [
                1800,
                1850,
                1900,
            ]
        }
    )

    model = NaiveMarketForecaster()

    predictions = model.predict(df)

    assert predictions.tolist() == [
        1800,
        1850,
        1900,
    ]


def test_moving_average_forecaster():
    df = pd.DataFrame(
        {
            "modal_price": [
                100,
                110,
                120,
                130,
            ]
        }
    )

    model = MovingAverageForecaster(
        window=2
    )

    predictions = model.predict(df)

    assert predictions[0] == 100
    assert predictions[1] == 100
    assert predictions[2] == 105
    assert predictions[3] == 115


def test_random_forest_fit_and_predict():
    X, y = make_training_data()

    model = MarketRandomForest(
        n_estimators=50,
        random_state=42,
    )

    model.fit(X, y)

    predictions = model.predict(X)

    assert len(predictions) == len(y)
    assert not predictions.isna().any()


def test_random_forest_feature_importance():
    X, y = make_training_data()

    model = MarketRandomForest(
        n_estimators=20,
        random_state=42,
    )

    model.fit(X, y)

    importance = model.feature_importance()

    assert len(importance) == len(X.columns)
    assert set(importance["feature"]) == set(
        X.columns
    )


def test_random_forest_requires_fit():
    X, _ = make_training_data()

    model = MarketRandomForest()

    with pytest.raises(RuntimeError):
        model.predict(X)


def test_evaluator():
    actual = [
        100,
        110,
        120,
    ]

    predicted = [
        102,
        108,
        121,
    ]

    result = MarketForecastEvaluator.evaluate(
        actual,
        predicted,
    )

    assert result["mae"] > 0
    assert result["rmse"] > 0
    assert result["mape"] > 0


def test_evaluator_rejects_empty_data():
    with pytest.raises(ValueError):
        MarketForecastEvaluator.evaluate(
            [],
            [],
        )