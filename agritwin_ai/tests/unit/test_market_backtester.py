import numpy as np
import pandas as pd
import pytest

from agritwin_ai.models.market.backtester import (
    MarketTemporalBacktester,
)
from agritwin_ai.models.market.random_forest import (
    MarketRandomForest,
)


def make_data(rows=60):
    X = pd.DataFrame(
        {
            "price_lag_1": np.arange(100, 100 + rows),
            "price_lag_7": np.arange(90, 90 + rows),
            "rolling_mean": np.arange(95, 95 + rows),
        }
    )

    y = X["price_lag_1"] * 1.02

    return X, y


def test_split_is_chronological():
    X, y = make_data()

    backtester = MarketTemporalBacktester(
        test_size=0.2,
        min_train_size=30,
    )

    X_train, X_test, y_train, y_test = (
        backtester.split(X, y)
    )

    assert len(X_train) == 48
    assert len(X_test) == 12

    assert X_train.index.max() < X_test.index.min()
    assert y_train.index.max() < y_test.index.min()


def test_split_does_not_shuffle():
    X, y = make_data()

    backtester = MarketTemporalBacktester()

    X_train, X_test, _, _ = backtester.split(X, y)

    assert X_train.iloc[-1]["price_lag_1"] == 147
    assert X_test.iloc[0]["price_lag_1"] == 148


def test_backtester_evaluates_model():
    X, y = make_data()

    backtester = MarketTemporalBacktester(
        min_train_size=30,
    )

    model = MarketRandomForest(
        n_estimators=20,
        random_state=42,
    )

    result = backtester.evaluate_model(
        model,
        X,
        y,
    )

    assert "mae" in result
    assert "rmse" in result
    assert "mape" in result

    assert result["mae"] >= 0
    assert result["rmse"] >= 0


def test_small_dataset_is_rejected():
    X, y = make_data(rows=20)

    backtester = MarketTemporalBacktester(
        min_train_size=30,
    )

    with pytest.raises(ValueError):
        backtester.split(X, y)


def test_invalid_test_size_is_rejected():
    with pytest.raises(ValueError):
        MarketTemporalBacktester(
            test_size=1.5,
        )


def test_invalid_train_size_is_rejected():
    with pytest.raises(ValueError):
        MarketTemporalBacktester(
            min_train_size=0,
        )