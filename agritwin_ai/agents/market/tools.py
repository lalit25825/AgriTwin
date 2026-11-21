from __future__ import annotations

from typing import Any

from agritwin_ai.agents.market.market_runtime import MarketRuntime


_runtime = MarketRuntime()


def get_market_price(
    commodity: str,
    market: str,
) -> dict[str, Any]:
    """
    Retrieve the latest deterministic market price.

    This is intentionally separate from full market analysis.
    A current-price question should not trigger forecasting,
    risk analysis, economics, or a market decision.
    """

    if not commodity:
        return {
            "error": "Commodity is required."
        }

    if not market:
        return {
            "error": "Market is required."
        }

    try:
        result = _runtime.get_current_price(
            commodity=str(commodity).strip(),
            market=str(market).strip(),
        )

        return result

    except Exception as exc:
        return {
            "error": str(exc)
        }


def get_market_analysis(
    commodity: str,
    market: str,
    horizon: int = 7,
    storage_available: bool = False,
    nearby_market_advantage_pct: float = 0.0,
    nearby_market_price: float | None = None,
    transport_cost: float = 0.0,
    storage_cost: float = 0.0,
    expected_spoilage_pct: float = 0.0,
) -> dict[str, Any]:
    """
    Run complete deterministic market intelligence.
    """

    if not commodity:
        return {
            "error": "Commodity is required."
        }

    if not market:
        return {
            "error": "Market is required."
        }

    if horizon <= 0:
        return {
            "error": "Forecast horizon must be greater than zero."
        }

    try:
        return _runtime.get_market_analysis(
            commodity=str(commodity).strip(),
            market=str(market).strip(),
            horizon=int(horizon),
            storage_available=bool(storage_available),
            nearby_market_advantage_pct=float(nearby_market_advantage_pct),
            nearby_market_price=(
                float(nearby_market_price)
                if nearby_market_price is not None
                else None
            ),
            transport_cost=float(transport_cost),
            storage_cost=float(storage_cost),
            expected_spoilage_pct=float(expected_spoilage_pct),
        )

    except Exception as exc:
        return {
            "error": str(exc)
        }