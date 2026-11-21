from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from agritwin_ai.data.market.dataset import (
    MarketDatasetBuilder,
)
from agritwin_ai.models.market.baseline import (
    MovingAverageForecaster,
    NaiveMarketForecaster,
)
from agritwin_ai.models.market.model_selector import (
    MarketModelSelector,
)
from agritwin_ai.models.market.random_forest import (
    MarketRandomForest,
)


class MarketForecastService:
    """
    Produces short-term agricultural market-price forecasts.

    The service first compares candidate forecasting models using
    chronological backtesting, selects the best model, and then
    produces a recursive multi-day forecast.
    """

    def __init__(
        self,
        selector: MarketModelSelector | None = None,
        dataset_builder: MarketDatasetBuilder | None = None,
    ) -> None:
        self.selector = (
            selector or MarketModelSelector()
        )

        self.dataset_builder = (
            dataset_builder
            or MarketDatasetBuilder()
        )

    def forecast(
        self,
        dataframe: pd.DataFrame,
        commodity: str,
        market: str,
        horizon: int = 7,
    ) -> dict[str, Any]:
        if dataframe.empty:
            raise ValueError(
                "Market dataframe cannot be empty."
            )

        if horizon <= 0:
            raise ValueError(
                "Forecast horizon must be positive."
            )

        commodity = commodity.strip()
        market = market.strip()

        if not commodity:
            raise ValueError(
                "Commodity cannot be empty."
            )

        if not market:
            raise ValueError(
                "Market cannot be empty."
            )

        history = self._filter_history(
            dataframe=dataframe,
            commodity=commodity,
            market=market,
        )

        if history.empty:
            raise ValueError(
                "No market history found for the requested "
                f"commodity={commodity!r}, market={market!r}."
            )

        distinct_days = int(pd.to_datetime(history["date"], errors="coerce").dropna().dt.date.nunique())
        if distinct_days < 30:
            raise ValueError(
                "Price forecasting is unavailable: only "
                f"{distinct_days} distinct daily market observations are available for "
                f"{commodity!r} in {market!r}; at least 30 days are required. "
                "Refresh the historical mandi dataset before requesting a forecast."
            )

        history = (
            history
            .sort_values("date")
            .reset_index(drop=True)
        )

        X, y = (
            self.dataset_builder
            .prepare_training_data(history)
        )

        if len(X) < 30:
            raise ValueError(
                "At least 30 usable historical observations "
                "are required for forecasting."
            )

        comparison = self.selector.compare(
            history,
            X,
            y,
        )

        best = self.selector.select_best(
            comparison
        )

        forecasts = self._forecast_with_model(
            history=history,
            X=X,
            y=y,
            model_name=best["model"],
            horizon=horizon,
        )

        return {
            "commodity": commodity,
            "market": market,
            "model": best["model"],
            "model_metrics": best,
            "horizon": horizon,
            "last_observed_date": self._to_date(
                history["date"].iloc[-1]
            ),
            "last_observed_price": float(
                history["modal_price"].iloc[-1]
            ),
            "forecasts": forecasts,
        }

    def _forecast_with_model(
        self,
        history: pd.DataFrame,
        X: pd.DataFrame,
        y: pd.Series,
        model_name: str,
        horizon: int,
    ) -> list[dict[str, Any]]:
        if model_name == "naive":
            return self._forecast_naive(
                history,
                horizon,
            )

        if model_name == "moving_average":
            return self._forecast_moving_average(
                history,
                horizon,
            )

        if model_name == "random_forest":
            return self._forecast_random_forest(
                history,
                X,
                y,
                horizon,
            )

        raise ValueError(
            f"Unsupported forecasting model: {model_name!r}"
        )

    @staticmethod
    def _forecast_naive(
        history: pd.DataFrame,
        horizon: int,
    ) -> list[dict[str, Any]]:
        last_price = float(
            history["modal_price"].iloc[-1]
        )

        last_date = pd.to_datetime(
            history["date"].iloc[-1]
        )

        forecasts = []

        for step in range(1, horizon + 1):
            forecasts.append(
                {
                    "date": (
                        last_date
                        + pd.Timedelta(days=step)
                    ).date(),
                    "predicted_price": last_price,
                }
            )

        return forecasts

    @staticmethod
    def _forecast_moving_average(
        history: pd.DataFrame,
        horizon: int,
        window: int = 7,
    ) -> list[dict[str, Any]]:
        prices = [
            float(price)
            for price in history["modal_price"]
        ]

        last_date = pd.to_datetime(
            history["date"].iloc[-1]
        )

        forecasts = []

        for step in range(1, horizon + 1):
            recent = prices[-window:]

            prediction = float(
                np.mean(recent)
            )

            prices.append(prediction)

            forecasts.append(
                {
                    "date": (
                        last_date
                        + pd.Timedelta(days=step)
                    ).date(),
                    "predicted_price": prediction,
                }
            )

        return forecasts

    def _forecast_random_forest(
        self,
        history: pd.DataFrame,
        X: pd.DataFrame,
        y: pd.Series,
        horizon: int,
    ) -> list[dict[str, Any]]:
        model = MarketRandomForest(
            n_estimators=300,
            random_state=42,
        )

        model.fit(
            X,
            y,
        )

        working = history.copy()

        working["date"] = pd.to_datetime(
            working["date"]
        )

        forecasts = []

        for _ in range(horizon):
            features = (
                self._build_prediction_features(
                    working
                )
            )

            latest_features = features.iloc[
                [-1]
            ].copy()

            prediction = float(
                model.predict(
                    latest_features
                ).iloc[0]
            )

            next_date = (
                working["date"].iloc[-1]
                + pd.Timedelta(days=1)
            )

            forecasts.append(
                {
                    "date": next_date.date(),
                    "predicted_price": prediction,
                }
            )

            next_row = working.iloc[
                [-1]
            ].copy()

            next_row["date"] = next_date
            next_row["modal_price"] = prediction

            working = pd.concat(
                [
                    working,
                    next_row,
                ],
                ignore_index=True,
            )

        return forecasts

    def _build_prediction_features(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        transformed = (
            self.dataset_builder
            .feature_engineer
            .transform(dataframe)
        )

        feature_columns = (
            self.dataset_builder
            ._get_feature_columns(
                transformed
            )
        )

        features = transformed[
            feature_columns
        ].copy()

        features = features.replace(
            [np.inf, -np.inf],
            np.nan,
        )

        features = features.ffill()
        features = features.bfill()

        return features

    @staticmethod
    def _filter_history(
        dataframe: pd.DataFrame,
        commodity: str,
        market: str,
    ) -> pd.DataFrame:
        required = {
            "date",
            "commodity",
            "market",
            "modal_price",
        }

        missing = required - set(
            dataframe.columns
        )

        if missing:
            raise ValueError(
                "Missing required columns: "
                f"{sorted(missing)}"
            )

        filtered = dataframe[
            dataframe["commodity"]
            .astype(str)
            .str.strip()
            .str.lower()
            == commodity.lower()
        ]

        normalized_markets = (
            filtered["market"]
            .astype(str)
            .str.strip()
            .str.lower()
            .str.replace(" ", "", regex=False)
        )
        requested_market = market.strip().lower().replace(" ", "")

        exact = filtered[normalized_markets == requested_market].copy()
        if not exact.empty:
            return exact

        # Short mandi names such as "Lasalgaon" should include matching
        # records such as "APMC Lasalgaon" and "Lasalgaon(Niphad)".
        matched = filtered[
            normalized_markets.str.contains(requested_market, regex=False, na=False)
        ]
        return matched.copy()

    @staticmethod
    def _to_date(
        value: Any,
    ) -> date:
        return pd.to_datetime(
            value
        ).date()