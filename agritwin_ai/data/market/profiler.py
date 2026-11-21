from __future__ import annotations

from typing import Any

import pandas as pd


class MarketDataProfiler:
    """
    Profiles normalized agricultural market data before it enters
    forecasting and decision pipelines.
    """

    REQUIRED_COLUMNS = {
        "date",
        "state",
        "market",
        "commodity",
        "arrival_quantity",
        "min_price",
        "max_price",
        "modal_price",
    }

    def profile(
        self,
        dataframe: pd.DataFrame,
    ) -> dict[str, Any]:
        if dataframe.empty:
            raise ValueError(
                "Cannot profile an empty market dataframe."
            )

        self._validate_columns(dataframe)

        df = dataframe.copy()

        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce",
        )

        summary = {
            "row_count": int(len(df)),
            "column_count": int(len(df.columns)),
            "date_min": (
                df["date"].min().date()
                if df["date"].notna().any()
                else None
            ),
            "date_max": (
                df["date"].max().date()
                if df["date"].notna().any()
                else None
            ),
            "commodity_count": int(
                df["commodity"].nunique(dropna=True)
            ),
            "state_count": int(
                df["state"].nunique(dropna=True)
            ),
            "market_count": int(
                df["market"].nunique(dropna=True)
            ),
            "district_count": (
                int(df["district"].nunique(dropna=True))
                if "district" in df.columns
                else 0
            ),
            "duplicate_rows": int(
                df.duplicated().sum()
            ),
            "missing_values": self._missing_values(df),
            "invalid_records": self._invalid_records(df),
            "commodity_distribution": (
                self._commodity_distribution(df)
            ),
            "market_distribution": (
                self._market_distribution(df)
            ),
            "price_statistics": (
                self._price_statistics(df)
            ),
        }

        return summary

    def coverage_report(
        self,
        dataframe: pd.DataFrame,
    ) -> dict[str, Any]:
        if dataframe.empty:
            raise ValueError(
                "Cannot create coverage report from empty data."
            )

        self._validate_columns(dataframe)

        df = dataframe.copy()

        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce",
        )

        valid_dates = (
            df["date"]
            .dropna()
            .dt.normalize()
            .drop_duplicates()
            .sort_values()
        )

        if valid_dates.empty:
            return {
                "date_count": 0,
                "expected_date_count": 0,
                "missing_dates": [],
                "coverage_ratio": 0.0,
            }

        expected_dates = pd.date_range(
            valid_dates.min(),
            valid_dates.max(),
            freq="D",
        )

        actual_dates = set(valid_dates)

        missing_dates = [
            timestamp.date()
            for timestamp in expected_dates
            if timestamp not in actual_dates
        ]

        coverage_ratio = (
            len(valid_dates)
            / len(expected_dates)
        )

        return {
            "date_count": int(len(valid_dates)),
            "expected_date_count": int(
                len(expected_dates)
            ),
            "missing_dates": missing_dates,
            "coverage_ratio": float(
                coverage_ratio
            ),
        }

    def validate(
        self,
        dataframe: pd.DataFrame,
    ) -> dict[str, Any]:
        if dataframe.empty:
            raise ValueError(
                "Cannot validate an empty market dataframe."
            )

        self._validate_columns(dataframe)

        df = dataframe.copy()

        errors: list[str] = []

        # Date validation
        parsed_dates = pd.to_datetime(
            df["date"],
            errors="coerce",
        )

        invalid_dates = int(
            parsed_dates.isna().sum()
        )

        if invalid_dates:
            errors.append(
                f"invalid_dates={invalid_dates}"
            )

        # Numeric validation
        numeric_columns = [
            "arrival_quantity",
            "min_price",
            "max_price",
            "modal_price",
        ]

        for column in numeric_columns:
            numeric = pd.to_numeric(
                df[column],
                errors="coerce",
            )

            invalid_count = int(
                numeric.isna().sum()
            )

            if invalid_count:
                errors.append(
                    f"invalid_{column}={invalid_count}"
                )

            negative_count = int(
                (numeric < 0).sum()
            )

            if negative_count:
                errors.append(
                    f"negative_{column}={negative_count}"
                )

        # Price relationship
        min_price = pd.to_numeric(
            df["min_price"],
            errors="coerce",
        )

        max_price = pd.to_numeric(
            df["max_price"],
            errors="coerce",
        )

        modal_price = pd.to_numeric(
            df["modal_price"],
            errors="coerce",
        )

        invalid_price_relationships = int(
            (
                (max_price < min_price)
                | (modal_price < min_price)
                | (modal_price > max_price)
            ).sum()
        )

        if invalid_price_relationships:
            errors.append(
                "invalid_price_relationships="
                f"{invalid_price_relationships}"
            )

        # Required text validation
        for column in [
            "state",
            "market",
            "commodity",
        ]:
            empty_count = int(
                df[column]
                .fillna("")
                .astype(str)
                .str.strip()
                .eq("")
                .sum()
            )

            if empty_count:
                errors.append(
                    f"empty_{column}={empty_count}"
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    @staticmethod
    def _validate_columns(
        dataframe: pd.DataFrame,
    ) -> None:
        missing = (
            MarketDataProfiler.REQUIRED_COLUMNS
            - set(dataframe.columns)
        )

        if missing:
            raise ValueError(
                "Missing required columns: "
                f"{sorted(missing)}"
            )

    @staticmethod
    def _missing_values(
        dataframe: pd.DataFrame,
    ) -> dict[str, int]:
        missing = dataframe.isna().sum()

        return {
            column: int(count)
            for column, count in missing.items()
            if count > 0
        }

    @staticmethod
    def _invalid_records(
        dataframe: pd.DataFrame,
    ) -> dict[str, int]:
        result: dict[str, int] = {}

        for column in [
            "arrival_quantity",
            "min_price",
            "max_price",
            "modal_price",
        ]:
            numeric = pd.to_numeric(
                dataframe[column],
                errors="coerce",
            )

            invalid_numeric = int(
                numeric.isna().sum()
            )

            negative_values = int(
                (numeric < 0).sum()
            )

            if invalid_numeric:
                result[
                    f"{column}_invalid_numeric"
                ] = invalid_numeric

            if negative_values:
                result[
                    f"{column}_negative"
                ] = negative_values

        min_price = pd.to_numeric(
            dataframe["min_price"],
            errors="coerce",
        )

        max_price = pd.to_numeric(
            dataframe["max_price"],
            errors="coerce",
        )

        modal_price = pd.to_numeric(
            dataframe["modal_price"],
            errors="coerce",
        )

        invalid_relationships = int(
            (
                (max_price < min_price)
                | (modal_price < min_price)
                | (modal_price > max_price)
            ).sum()
        )

        if invalid_relationships:
            result[
                "invalid_price_relationships"
            ] = invalid_relationships

        return result

    @staticmethod
    def _commodity_distribution(
        dataframe: pd.DataFrame,
    ) -> dict[str, int]:
        distribution = (
            dataframe["commodity"]
            .value_counts(dropna=False)
            .to_dict()
        )

        return {
            str(key): int(value)
            for key, value in distribution.items()
        }

    @staticmethod
    def _market_distribution(
        dataframe: pd.DataFrame,
    ) -> dict[str, int]:
        distribution = (
            dataframe["market"]
            .value_counts(dropna=False)
            .head(20)
            .to_dict()
        )

        return {
            str(key): int(value)
            for key, value in distribution.items()
        }

    @staticmethod
    def _price_statistics(
        dataframe: pd.DataFrame,
    ) -> dict[str, dict[str, float]]:
        numeric = dataframe[
            [
                "min_price",
                "max_price",
                "modal_price",
            ]
        ].apply(
            pd.to_numeric,
            errors="coerce",
        )

        statistics: dict[
            str,
            dict[str, float],
        ] = {}

        for column in numeric.columns:
            series = numeric[column].dropna()

            if series.empty:
                continue

            statistics[column] = {
                "min": float(series.min()),
                "max": float(series.max()),
                "mean": float(series.mean()),
                "median": float(series.median()),
                "std": float(series.std()),
            }

        return statistics