from __future__ import annotations

import numpy as np
import pandas as pd


class NaiveMarketForecaster:
    """
    Baseline model:
    tomorrow's price = today's price.
    """

    def predict(self, dataframe: pd.DataFrame) -> np.ndarray:
        if "modal_price" not in dataframe.columns:
            raise ValueError(
                "Dataframe must contain 'modal_price'."
            )

        return dataframe["modal_price"].to_numpy(dtype=float)


class MovingAverageForecaster:
    """
    Baseline model using the previous N observations.
    """

    def __init__(self, window: int = 7) -> None:
        if window <= 0:
            raise ValueError("window must be positive.")

        self.window = window

    def predict(self, dataframe: pd.DataFrame) -> np.ndarray:
        if "modal_price" not in dataframe.columns:
            raise ValueError(
                "Dataframe must contain 'modal_price'."
            )

        prices = dataframe["modal_price"].astype(float)

        predictions = (
            prices
            .shift(1)
            .rolling(self.window)
            .mean()
        )

        # For the first observations where the full window
        # does not exist, use the most recent available price.
        predictions = predictions.fillna(
            prices.shift(1)
        )

        predictions = predictions.fillna(
            prices.iloc[0]
        )

        return predictions.to_numpy(dtype=float)