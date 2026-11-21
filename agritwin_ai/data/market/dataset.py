from __future__ import annotations

import pandas as pd

from agritwin_ai.data.market.features import MarketFeatureEngineer


class MarketDatasetBuilder:
    """
    Builds supervised time-series datasets for market-price forecasting.

    Target:
        Next-day modal price.
    """

    TARGET = "target_next_day_price"

    def __init__(
        self,
        feature_engineer: MarketFeatureEngineer | None = None,
    ) -> None:
        self.feature_engineer = (
            feature_engineer or MarketFeatureEngineer()
        )

    def build(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        if dataframe.empty:
            return dataframe.copy()

        df = self.feature_engineer.transform(dataframe)

        group = df.groupby(
            ["commodity", "market"],
            group_keys=False,
        )

        df[self.TARGET] = group[
            "modal_price"
        ].shift(-1)

        feature_columns = self._get_feature_columns(df)

        columns = (
            [
                "date",
                "commodity",
                "market",
                "modal_price",
            ]
            + feature_columns
            + [self.TARGET]
        )

        columns = list(dict.fromkeys(columns))

        return df[columns].copy()

    def prepare_training_data(
        self,
        dataframe: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.Series]:
        dataset = self.build(dataframe)

        feature_columns = self._get_feature_columns(dataset)

        usable = dataset.dropna(
            subset=feature_columns + [self.TARGET]
        )

        X = usable[feature_columns].copy()
        y = usable[self.TARGET].copy()

        return X, y

    def _get_feature_columns(
        self,
        dataframe: pd.DataFrame,
    ) -> list[str]:
        excluded = {
            "date",
            "commodity",
            "market",
            "state",
            "district",
            "variety",
            "grade",
            "source",
            "collected_at",
            "modal_price",
            self.TARGET,
        }

        return [
            column
            for column in dataframe.columns
            if column not in excluded
        ]