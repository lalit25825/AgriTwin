from __future__ import annotations

from typing import Any

import pandas as pd


class MarketContextBuilder:
    """
    Builds contextual market signals from historical observations.

    Market names can be supplied as:
        APMC Lasalgaon
        Lasalgaon(Niphad)
        Lasalgaon(Vinchur)

    A shorter market name such as:
        Lasalgaon

    is treated as a market-family/location query.
    """

    @staticmethod
    def _normalize(value: Any) -> str:
        return (
            str(value)
            .strip()
            .lower()
            .replace(" ", "")
        )

    def _filter_market(
        self,
        dataframe: pd.DataFrame,
        market: str,
    ) -> pd.DataFrame:

        requested = self._normalize(market)

        normalized_markets = (
            dataframe["market"]
            .astype(str)
            .map(self._normalize)
        )

        # First prefer an exact market match.
        exact = dataframe[
            normalized_markets == requested
        ].copy()

        if not exact.empty:
            return exact

        # If the requested name is shorter, treat it as
        # a market-family/location query.
        contains = dataframe[
            normalized_markets.str.contains(
                requested,
                regex=False,
                na=False,
            )
        ].copy()

        return contains

    def build(
        self,
        dataframe: pd.DataFrame,
        commodity: str,
        market: str,
    ) -> dict[str, Any]:

        if dataframe.empty:
            raise ValueError(
                "Market dataframe cannot be empty."
            )

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
                f"Missing required columns: {sorted(missing)}"
            )

        filtered = dataframe[
            dataframe["commodity"]
            .astype(str)
            .str.strip()
            .str.lower()
            == commodity.strip().lower()
        ].copy()

        if filtered.empty:
            raise ValueError(
                f"No market history found for commodity: {commodity}"
            )

        filtered = self._filter_market(
            filtered,
            market,
        )

        if filtered.empty:
            raise ValueError(
                f"No market history found for market: {market}"
            )

        filtered["date"] = pd.to_datetime(
            filtered["date"],
            errors="coerce",
        )

        filtered["modal_price"] = pd.to_numeric(
            filtered["modal_price"],
            errors="coerce",
        )

        filtered = filtered.dropna(
            subset=[
                "date",
                "modal_price",
            ]
        )

        if filtered.empty:
            raise ValueError(
                "No valid market prices found."
            )

        filtered = filtered.sort_values(
            "date"
        )

        # -----------------------------------------------------
        # Current observations
        # -----------------------------------------------------

        latest_date = filtered["date"].max()

        latest = filtered[
            filtered["date"] == latest_date
        ].copy()

        prices = latest[
            "modal_price"
        ].dropna()

        if prices.empty:
            raise ValueError(
                "No valid current market prices found."
            )

        # If several market records match a market-family query,
        # calculate the average modal price for the latest date.
        current_price = float(
            prices.mean()
        )

        # -----------------------------------------------------
        # Previous observation
        # -----------------------------------------------------

        historical_daily = (
            filtered.groupby(
                "date"
            )["modal_price"]
            .mean()
            .sort_index()
        )

        if len(historical_daily) >= 2:
            previous_price = float(
                historical_daily.iloc[-2]
            )
        else:
            previous_price = current_price

        price_change_pct = (
            (
                current_price
                - previous_price
            )
            / previous_price
            * 100
            if previous_price != 0
            else 0.0
        )

        # -----------------------------------------------------
        # Matched market names
        # -----------------------------------------------------

        matched_markets = sorted(
            filtered["market"]
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )

        return {
            "commodity": commodity.strip(),
            "market": market.strip(),
            "matched_markets": matched_markets,
            "current_price": round(
                current_price,
                2,
            ),
            "previous_price": round(
                previous_price,
                2,
            ),
            "price_change_pct": round(
                price_change_pct,
                3,
            ),
            "observations": int(
                len(filtered)
            ),
            "latest_market_records": int(
                len(latest)
            ),
            "last_date": latest_date.date(),
        }