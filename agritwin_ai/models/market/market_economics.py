from __future__ import annotations

from typing import Any


class MarketEconomicAnalyzer:
    """
    Deterministic economic analysis for market decisions.

    Converts gross price differences into farmer-relevant
    net economic signals after transport and storage costs.
    """

    def analyze(
        self,
        current_price: float,
        expected_price: float,
        nearby_market_price: float | None = None,
        transport_cost: float = 0.0,
        storage_cost: float = 0.0,
        expected_spoilage_pct: float = 0.0,
    ) -> dict[str, Any]:
        self._validate_non_negative(
            current_price,
            "current_price",
        )

        self._validate_non_negative(
            expected_price,
            "expected_price",
        )

        self._validate_non_negative(
            transport_cost,
            "transport_cost",
        )

        self._validate_non_negative(
            storage_cost,
            "storage_cost",
        )

        if not 0 <= expected_spoilage_pct <= 100:
            raise ValueError(
                "expected_spoilage_pct must be between 0 and 100."
            )

        expected_price_change_pct = (
            (
                expected_price - current_price
            )
            / current_price
            * 100
            if current_price > 0
            else 0.0
        )

        storage_adjusted_price = (
            expected_price
            * (1 - expected_spoilage_pct / 100)
            - storage_cost
        )

        result: dict[str, Any] = {
            "current_price": round(
                current_price,
                2,
            ),
            "expected_price": round(
                expected_price,
                2,
            ),
            "expected_price_change_pct": round(
                expected_price_change_pct,
                3,
            ),
            "storage_adjusted_price": round(
                storage_adjusted_price,
                2,
            ),
            "storage_cost": round(
                storage_cost,
                2,
            ),
            "transport_cost": round(
                transport_cost,
                2,
            ),
        }

        if nearby_market_price is not None:
            self._validate_non_negative(
                nearby_market_price,
                "nearby_market_price",
            )

            gross_nearby_gain = (
                nearby_market_price
                - current_price
            )

            net_nearby_gain = (
                gross_nearby_gain
                - transport_cost
            )

            gross_nearby_gain_pct = (
                gross_nearby_gain
                / current_price
                * 100
                if current_price > 0
                else 0.0
            )

            net_nearby_gain_pct = (
                net_nearby_gain
                / current_price
                * 100
                if current_price > 0
                else 0.0
            )

            result.update(
                {
                    "nearby_market_price": round(
                        nearby_market_price,
                        2,
                    ),
                    "gross_nearby_gain": round(
                        gross_nearby_gain,
                        2,
                    ),
                    "net_nearby_gain": round(
                        net_nearby_gain,
                        2,
                    ),
                    "gross_nearby_gain_pct": round(
                        gross_nearby_gain_pct,
                        3,
                    ),
                    "net_nearby_gain_pct": round(
                        net_nearby_gain_pct,
                        3,
                    ),
                }
            )

        return result

    @staticmethod
    def _validate_non_negative(
        value: float,
        name: str,
    ) -> None:
        if value < 0:
            raise ValueError(
                f"{name} cannot be negative."
            )