from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor


class MarketRandomForest:
    """
    Random Forest regression model for next-day market price.
    """

    def __init__(
        self,
        n_estimators: int = 300,
        max_depth: int | None = 12,
        random_state: int = 42,
    ) -> None:
        self.model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            n_jobs=-1,
        )

        self.feature_columns: list[str] = []

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
    ) -> "MarketRandomForest":
        if X.empty:
            raise ValueError("Training data cannot be empty.")

        if len(X) != len(y):
            raise ValueError(
                "X and y must contain the same number of rows."
            )

        self.feature_columns = list(X.columns)

        self.model.fit(X, y)

        return self

    def predict(
        self,
        X: pd.DataFrame,
    ) -> pd.Series:
        if not self.feature_columns:
            raise RuntimeError(
                "Model must be fitted before prediction."
            )

        missing = set(self.feature_columns) - set(X.columns)

        if missing:
            raise ValueError(
                f"Missing model features: {sorted(missing)}"
            )

        predictions = self.model.predict(
            X[self.feature_columns]
        )

        return pd.Series(
            predictions,
            index=X.index,
            name="predicted_price",
        )

    def feature_importance(self) -> pd.DataFrame:
        if not self.feature_columns:
            raise RuntimeError(
                "Model must be fitted before feature importance."
            )

        return (
            pd.DataFrame(
                {
                    "feature": self.feature_columns,
                    "importance": (
                        self.model.feature_importances_
                    ),
                }
            )
            .sort_values(
                "importance",
                ascending=False,
            )
            .reset_index(drop=True)
        )

    def save(
        self,
        path: str | Path,
    ) -> None:
        path = Path(path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        joblib.dump(
            {
                "model": self.model,
                "feature_columns": self.feature_columns,
            },
            path,
        )

    @classmethod
    def load(
        cls,
        path: str | Path,
    ) -> "MarketRandomForest":
        payload = joblib.load(path)

        instance = cls()

        instance.model = payload["model"]
        instance.feature_columns = payload["feature_columns"]

        return instance