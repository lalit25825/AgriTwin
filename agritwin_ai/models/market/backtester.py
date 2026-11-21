from __future__ import annotations

import pandas as pd

from agritwin_ai.data.market.dataset import MarketDatasetBuilder
from agritwin_ai.models.market.evaluator import MarketForecastEvaluator


class MarketTemporalBacktester:
    """
    Chronological train/test evaluation for market forecasting.

    No random shuffling. Past trains on past, future remains unseen.
    """

    def __init__(
        self,
        test_size: float = 0.2,
        min_train_size: int = 30,
    ) -> None:
        if not 0 < test_size < 1:
            raise ValueError("test_size must be between 0 and 1.")

        if min_train_size <= 0:
            raise ValueError("min_train_size must be positive.")

        self.test_size = test_size
        self.min_train_size = min_train_size
        self.evaluator = MarketForecastEvaluator()

    def split(
        self,
        X: pd.DataFrame,
        y: pd.Series,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        if len(X) != len(y):
            raise ValueError("X and y must have equal length.")

        if len(X) < self.min_train_size + 2:
            raise ValueError("Dataset is too small for backtesting.")

        split_index = int(len(X) * (1 - self.test_size))

        if split_index < self.min_train_size:
            raise ValueError(
                "Training portion is smaller than min_train_size."
            )

        X_train = X.iloc[:split_index].copy()
        X_test = X.iloc[split_index:].copy()

        y_train = y.iloc[:split_index].copy()
        y_test = y.iloc[split_index:].copy()

        return X_train, X_test, y_train, y_test

    def evaluate_model(
        self,
        model,
        X: pd.DataFrame,
        y: pd.Series,
    ) -> dict[str, float]:
        X_train, X_test, y_train, y_test = self.split(X, y)

        model.fit(X_train, y_train)

        predictions = model.predict(X_test)

        return self.evaluator.evaluate(
            y_test,
            predictions,
        )

    def evaluate_baseline(
        self,
        predictions,
        actual,
    ) -> dict[str, float]:
        return self.evaluator.evaluate(
            actual,
            predictions,
        )