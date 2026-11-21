from __future__ import annotations

from typing import Any

import numpy as np


class MarketRiskAnalyzer:
    """
    Calculates deterministic market-risk signals from price history.
    """

    def analyze(
        self,
        prices: list[float],
    ) -> dict[str, Any]:
        if not prices:
            raise ValueError(
                "Price history cannot be empty."
            )

        if any(price < 0 for price in prices):
            raise ValueError(
                "Prices cannot be negative."
            )

        values = np.asarray(
            prices,
            dtype=float,
        )

        if len(values) < 2:
            volatility_pct = 0.0
        else:
            previous = values[:-1]

            current = values[1:]

            valid = previous != 0

            if valid.any():
                returns = (
                    (
                        current[valid]
                        - previous[valid]
                    )
                    / previous[valid]
                ) * 100

                volatility_pct = float(
                    np.std(returns)
                )
            else:
                volatility_pct = 0.0

        if volatility_pct >= 20:
            risk_level = "HIGH"
        elif volatility_pct >= 10:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "volatility_pct": round(
                volatility_pct,
                3,
            ),
            "risk_level": risk_level,
            "observations": len(values),
        }