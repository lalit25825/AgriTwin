from __future__ import annotations

from pathlib import Path

import pandas as pd


GROUP_COLUMNS = [
    "state",
    "district",
    "market",
    "commodity",
    "variety",
    "grade",
]

LAG_WINDOWS = [1, 3, 7, 14, 30]
ROLLING_WINDOWS = [7, 14, 30]


class MarketFeatureBuilder:
    """
    Leakage-safe market feature builder.

    Used by the newer forecasting pipeline.
    """

    def __init__(
        self,
        group_columns: list[str] | None = None,
    ) -> None:
        self.group_columns = group_columns or GROUP_COLUMNS.copy()

    def build(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        df = dataframe.copy()

        # Some historical/test datasets do not contain optional
        # variety and grade columns. Preserve them as null values.
        for column in self.group_columns:
            if column not in df.columns:
                df[column] = None

        required_columns = [
            "date",
            "modal_price",
            *self.group_columns,
        ]

        missing = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing:
            raise ValueError(
                f"Missing required market feature columns: {missing}"
            )

        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce",
        )

        df["modal_price"] = pd.to_numeric(
            df["modal_price"],
            errors="coerce",
        )

        df = df.dropna(
            subset=[
                "date",
                "modal_price",
            ]
        ).copy()

        df = df.sort_values(
            [*self.group_columns, "date"]
        ).reset_index(drop=True)

        grouped = df.groupby(
            self.group_columns,
            sort=False,
            dropna=False,
        )["modal_price"]

        for window in LAG_WINDOWS:
            df[f"lag_{window}"] = grouped.shift(window)

        shifted = grouped.shift(1)

        shifted_grouped = shifted.groupby(
            [
                df[column]
                for column in self.group_columns
            ],
            sort=False,
            dropna=False,
        )

        for window in ROLLING_WINDOWS:
            df[f"rolling_mean_{window}"] = (
                shifted_grouped
                .rolling(
                    window=window,
                    min_periods=1,
                )
                .mean()
                .reset_index(
                    level=self.group_columns,
                    drop=True,
                )
            )

            df[f"rolling_std_{window}"] = (
                shifted_grouped
                .rolling(
                    window=window,
                    min_periods=1,
                )
                .std()
                .reset_index(
                    level=self.group_columns,
                    drop=True,
                )
            )

        df["pct_change_1d"] = grouped.pct_change(1)
        df["pct_change_7d"] = grouped.pct_change(7)
        df["pct_change_30d"] = grouped.pct_change(30)

        df["target_price_1d"] = grouped.shift(-1)

        current_price = df["modal_price"]

        df["target_pct_change_1d"] = (
            (
                df["target_price_1d"]
                - current_price
            )
            / current_price
        )

        df["has_lag_7"] = df["lag_7"].notna()
        df["has_lag_30"] = df["lag_30"].notna()

        df["training_ready"] = (
            df["lag_7"].notna()
            & df["target_price_1d"].notna()
        )

        return df

    def transform(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        return self.build(dataframe)

    def fit_transform(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        return self.build(dataframe)

    def training_columns(self) -> list[str]:
        return [
            "modal_price",
            "lag_1",
            "lag_3",
            "lag_7",
            "lag_14",
            "lag_30",
            "rolling_mean_7",
            "rolling_mean_14",
            "rolling_mean_30",
            "rolling_std_7",
            "rolling_std_14",
            "rolling_std_30",
            "pct_change_1d",
            "pct_change_7d",
            "pct_change_30d",
            "has_lag_7",
            "has_lag_30",
        ]

    def target_columns(self) -> list[str]:
        return [
            "target_price_1d",
            "target_pct_change_1d",
        ]


class MarketFeatureEngineer(MarketFeatureBuilder):
    """
    Backward-compatible feature engineer.

    Keeps the original market-model feature names while the newer
    MarketFeatureBuilder remains available for the forecasting pipeline.
    """

    IDENTIFIER_COLUMNS = {
        "date",
        "state",
        "district",
        "market",
        "commodity",
        "variety",
        "grade",
    }

    def transform(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        df = dataframe.copy()

        # ---------------------------------------------------------
        # Required columns
        # ---------------------------------------------------------

        required = [
            "date",
            "state",
            "district",
            "market",
            "commodity",
            "modal_price",
        ]

        missing = [
            column
            for column in required
            if column not in df.columns
        ]

        if missing:
            raise ValueError(
                f"Missing required market columns: {missing}"
            )

        # Older datasets may not contain these columns.
        if "arrival_quantity" not in df.columns:
            df["arrival_quantity"] = 0.0

        if "variety" not in df.columns:
            df["variety"] = None

        if "grade" not in df.columns:
            df["grade"] = None

        # ---------------------------------------------------------
        # Normalize types
        # ---------------------------------------------------------

        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce",
        )

        df["modal_price"] = pd.to_numeric(
            df["modal_price"],
            errors="coerce",
        )

        df["arrival_quantity"] = pd.to_numeric(
            df["arrival_quantity"],
            errors="coerce",
        ).fillna(0.0)

        df = df.dropna(
            subset=[
                "date",
                "modal_price",
            ]
        ).copy()

        # ---------------------------------------------------------
        # Sort time series
        # ---------------------------------------------------------

        group_columns = [
            "state",
            "district",
            "market",
            "commodity",
            "variety",
            "grade",
        ]

        df = df.sort_values(
            [
                *group_columns,
                "date",
            ]
        ).reset_index(drop=True)

        price_group = df.groupby(
            group_columns,
            sort=False,
            dropna=False,
        )["modal_price"]

        arrival_group = df.groupby(
            group_columns,
            sort=False,
            dropna=False,
        )["arrival_quantity"]

        # =========================================================
        # CALENDAR FEATURES
        # =========================================================

        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month
        df["day"] = df["date"].dt.day
        df["day_of_week"] = df["date"].dt.dayofweek
        df["day_of_year"] = df["date"].dt.dayofyear
        df["week_of_year"] = (
            df["date"]
            .dt.isocalendar()
            .week
            .astype(int)
        )
        df["quarter"] = df["date"].dt.quarter

        df["is_weekend"] = (
            df["day_of_week"] >= 5
        ).astype(int)

        df["is_month_start"] = (
            df["date"].dt.is_month_start
        ).astype(int)

        df["is_month_end"] = (
            df["date"].dt.is_month_end
        ).astype(int)

        # =========================================================
        # PRICE LAG FEATURES
        # =========================================================

        for window in [1, 3, 7, 14, 30]:
            df[f"price_lag_{window}"] = (
                price_group.shift(window)
            )

        # Newer naming retained too.
        for window in [1, 3, 7, 14, 30]:
            df[f"lag_{window}"] = (
                df[f"price_lag_{window}"]
            )

        # =========================================================
        # PRICE ROLLING FEATURES
        # =========================================================

        shifted_price = price_group.shift(1)

        shifted_price_group = shifted_price.groupby(
            [
                df[column]
                for column in group_columns
            ],
            sort=False,
            dropna=False,
        )

        for window in [7, 14, 30]:
            df[f"price_rolling_mean_{window}"] = (
                shifted_price_group
                .rolling(
                    window=window,
                    min_periods=1,
                )
                .mean()
                .reset_index(
                    level=group_columns,
                    drop=True,
                )
            )

            df[f"price_rolling_std_{window}"] = (
                shifted_price_group
                .rolling(
                    window=window,
                    min_periods=1,
                )
                .std()
                .reset_index(
                    level=group_columns,
                    drop=True,
                )
            )

            # Newer naming retained.
            df[f"rolling_mean_{window}"] = (
                df[f"price_rolling_mean_{window}"]
            )

            df[f"rolling_std_{window}"] = (
                df[f"price_rolling_std_{window}"]
            )

        # =========================================================
        # PRICE CHANGE FEATURES
        # =========================================================

        df["price_change_1d"] = (
            price_group.diff(1)
        )

        df["price_change_7d"] = (
            price_group.diff(7)
        )

        df["price_change_30d"] = (
            price_group.diff(30)
        )

        df["price_pct_change_1d"] = (
            price_group.pct_change(1)
        )

        df["price_pct_change_7d"] = (
            price_group.pct_change(7)
        )

        df["price_pct_change_30d"] = (
            price_group.pct_change(30)
        )

        # Newer naming.
        df["pct_change_1d"] = (
            df["price_pct_change_1d"]
        )

        df["pct_change_7d"] = (
            df["price_pct_change_7d"]
        )

        df["pct_change_30d"] = (
            df["price_pct_change_30d"]
        )

        # =========================================================
        # ARRIVAL FEATURES
        # =========================================================

        df["arrival_lag_1"] = (
            arrival_group.shift(1)
        )

        df["arrival_lag_7"] = (
            arrival_group.shift(7)
        )

        df["arrival_change_1d"] = (
            arrival_group.diff(1)
        )

        df["arrival_change_7d"] = (
            arrival_group.diff(7)
        )

        df["arrival_pct_change_1d"] = (
            arrival_group.pct_change(1)
        )

        df["arrival_pct_change_7d"] = (
            arrival_group.pct_change(7)
        )

        shifted_arrival = arrival_group.shift(1)

        shifted_arrival_group = (
            shifted_arrival.groupby(
                [
                    df[column]
                    for column in group_columns
                ],
                sort=False,
                dropna=False,
            )
        )

        df["arrival_rolling_mean_7"] = (
            shifted_arrival_group
            .rolling(
                window=7,
                min_periods=1,
            )
            .mean()
            .reset_index(
                level=group_columns,
                drop=True,
            )
        )

        # =========================================================
        # TARGET
        # =========================================================

        df["target_price_1d"] = (
            price_group.shift(-1)
        )

        df["target_pct_change_1d"] = (
            (
                df["target_price_1d"]
                - df["modal_price"]
            )
            / df["modal_price"]
        )

        # =========================================================
        # TRAINING FLAGS
        # =========================================================

        df["has_lag_7"] = (
            df["price_lag_7"].notna()
        )

        df["has_lag_30"] = (
            df["price_lag_30"].notna()
        )

        df["training_ready"] = (
            df["price_lag_7"].notna()
            & df["target_price_1d"].notna()
        )

        return df

    def engineer(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        return self.transform(dataframe)

    def create_features(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        return self.transform(dataframe)

    def get_feature_columns(
        self,
        dataframe: pd.DataFrame,
    ) -> list[str]:
        """
        Return engineered model features.

        Raw market measurements and identifiers are excluded.
        Targets and training flags are also excluded.
        """

        excluded = self.IDENTIFIER_COLUMNS | {
            # Raw target/input measurements
            "modal_price",
            "arrival_quantity",

            # Targets
            "target_price_1d",
            "target_pct_change_1d",

            # Training metadata
            "training_ready",
        }

        return [
            column
            for column in dataframe.columns
            if column not in excluded
        ]   
    def build_market_features(
        input_path: str | Path,
        output_path: str | Path,
    ) -> pd.DataFrame:
        input_path = Path(input_path)
        output_path = Path(output_path)

        dataframe = pd.read_csv(input_path)

        features = MarketFeatureBuilder().build(
            dataframe
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        features.to_csv(
            output_path,
            index=False,
        )

        return features