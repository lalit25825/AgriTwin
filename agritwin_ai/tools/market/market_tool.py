from __future__ import annotations

from typing import Any

import pandas as pd

from agritwin_ai.agents.market.market_agent import MarketAgent


class MarketTool:
    """
    Tool interface for executing the Market Agent.

    The Market Agent derives market risk and volatility from
    the supplied price history, so volatility is not passed
    directly through the tool.
    """

    name = "market"

    description = (
        "Analyze agricultural market prices, forecast future "
        "prices, assess market risk, and recommend an action."
    )

    def __init__(
        self,
        agent: MarketAgent | None = None,
    ) -> None:
        self.agent = agent or MarketAgent()

    def execute(
        self,
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

    def health_check(self) -> bool:
        """
        Check whether the Market Tool can be initialized
        and its underlying Market Agent is available.
        """

        try:
            return self.agent is not None
        except Exception:
            return False