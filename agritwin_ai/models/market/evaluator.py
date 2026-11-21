from __future__ import annotations

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error


class MarketForecastEvaluator:

    @staticmethod
    def evaluate(
        actual,
        predicted,
    ) -> dict[str, float]:

        actual = np.asarray(actual, dtype=float)
        predicted = np.asarray(predicted, dtype=float)

        if len(actual) != len(predicted):
            raise ValueError(
                "Actual and predicted values must have equal length."
            )

        if len(actual) == 0:
            raise ValueError(
                "Cannot evaluate an empty dataset."
            )

        mae = mean_absolute_error(
            actual,
            predicted,
        )

        rmse = np.sqrt(
            mean_squared_error(
                actual,
                predicted,
            )
        )

        non_zero = actual != 0

        if non_zero.any():
            mape = np.mean(
                np.abs(
                    (
                        actual[non_zero]
                        - predicted[non_zero]
                    )
                    / actual[non_zero]
                )
            ) * 100
        else:
            mape = float("inf")

        return {
            "mae": float(mae),
            "rmse": float(rmse),
            "mape": float(mape),
        }