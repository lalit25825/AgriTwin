from __future__ import annotations

from typing import Any

import pandas as pd

from agritwin_ai.agents.market.market_agent import MarketAgent


class MarketCoordinatorAdapter:
    """
    Thin adapter between the existing Coordinator and MarketAgent.

    The Coordinator should not know Market Agent internals.
    """

    intent_names = {
        "market",
        "market_analysis",
        "price_forecast",
        "market_price",
        "commodity_price",
        "sell_price",
    }

    def __init__(
        self,
        agent: MarketAgent | None = None,
    ) -> None:
        self.agent = agent or MarketAgent()

    def can_handle(
        self,
        intent: str,
    ) -> bool:
        return (
            intent.strip().lower()
            in self.intent_names
        )

    def execute(
        self,
        *,
        dataframe: pd.DataFrame,
        commodity: str,
        market: str,
        horizon: int = 7,
        storage_available: bool = False,
        nearby_market_advantage_pct: float = 0.0,
    ) -> dict[str, Any]:
        return self.agent.run(
            dataframe=dataframe,
            commodity=commodity,
            market=market,
            horizon=horizon,
            storage_available=storage_available,
            nearby_market_advantage_pct=(
                nearby_market_advantage_pct
            ),
        )