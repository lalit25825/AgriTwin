from __future__ import annotations

from typing import Any

import pandas as pd

from agritwin_ai.models.market.backtester import (
    MarketTemporalBacktester,
)
from agritwin_ai.models.market.baseline import (
    MovingAverageForecaster,
    NaiveMarketForecaster,
)
from agritwin_ai.models.market.random_forest import (
    MarketRandomForest,
)


class MarketModelSelector:
    """
    Compares candidate market forecasting models using
    chronological backtesting.
    """

    def __init__(
        self,
        backtester: MarketTemporalBacktester | None = None,
    ) -> None:
        self.backtester = (
            backtester
            or MarketTemporalBacktester(
                test_size=0.2,
                min_train_size=30,
            )
        )

    def compare(
        self,
        dataframe: pd.DataFrame,
        X: pd.DataFrame,
        y: pd.Series,
    ) -> pd.DataFrame:
        if dataframe.empty:
            raise ValueError(
                "Market dataframe cannot be empty."
            )

        if X.empty or y.empty:
            raise ValueError(
                "Training data cannot be empty."
            )

        X_train, X_test, y_train, y_test = (
            self.backtester.split(X, y)
        )

        results: list[dict[str, Any]] = []

        # ---------------------------------------------------------
        # Naive baseline
        # ---------------------------------------------------------

        naive = NaiveMarketForecaster()

        naive_predictions = naive.predict(
            dataframe.loc[X_test.index]
        )

        naive_metrics = self.backtester.evaluate_baseline(
            naive_predictions,
            y_test,
        )

        results.append(
            {
                "model": "naive",
                **naive_metrics,
            }
        )

        # ---------------------------------------------------------
        # Moving average baseline
        # ---------------------------------------------------------

        moving_average = MovingAverageForecaster(
            window=7,
        )

        moving_predictions = moving_average.predict(
            dataframe.loc[X_test.index]
        )

        moving_metrics = self.backtester.evaluate_baseline(
            moving_predictions,
            y_test,
        )

        results.append(
            {
                "model": "moving_average",
                **moving_metrics,
            }
        )

        # ---------------------------------------------------------
        # Random Forest
        # ---------------------------------------------------------

        random_forest = MarketRandomForest(
            n_estimators=300,
            random_state=42,
        )

        rf_metrics = self.backtester.evaluate_model(
            random_forest,
            X,
            y,
        )

        results.append(
            {
                "model": "random_forest",
                **rf_metrics,
            }
        )

        # ---------------------------------------------------------
        # Rank by lowest MAE
        # ---------------------------------------------------------

        return (
            pd.DataFrame(results)
            .sort_values(
                "mae",
                ascending=True,
            )
            .reset_index(drop=True)
        )

    @staticmethod
    def select_best(
        comparison: pd.DataFrame,
    ) -> dict[str, Any]:
        if comparison.empty:
            raise ValueError(
                "Comparison results cannot be empty."
            )

        required_columns = {
            "model",
            "mae",
            "rmse",
            "mape",
        }

        missing = required_columns - set(
            comparison.columns
        )

        if missing:
            raise ValueError(
                f"Comparison is missing columns: "
                f"{sorted(missing)}"
            )

        # Lower MAE = better forecasting performance.
        best = comparison.loc[
            comparison["mae"].idxmin()
        ]

        return {
            "model": best["model"],
            "mae": float(best["mae"]),
            "rmse": float(best["rmse"]),
            "mape": float(best["mape"]),
        }