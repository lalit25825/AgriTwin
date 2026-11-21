from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import date

import pandas as pd

from agritwin_ai.agents.market.market_agent import MarketAgent
from agritwin_ai.agents.market.market_intelligence import MarketIntelligenceService


class MarketRuntime:
    """
    Runtime bridge for the Market Agent.

    Loads persisted market data and exposes a structured
    interface for the Coordinator/tool layer.
    """

    def __init__(
        self,
        data_path: str | Path = (
            "data/market/processed/market_records.csv"
        ),
        agent: MarketAgent | None = None,
        intelligence: MarketIntelligenceService | None = None,
    ) -> None:
        requested_path = Path(data_path)
        if requested_path.is_absolute():
            self.data_path = requested_path
        else:
            project_root = Path(__file__).resolve().parents[3]
            self.data_path = project_root / requested_path
        self.agent = agent or MarketAgent()
        self.intelligence = intelligence or MarketIntelligenceService(data_path=self.data_path)

    def load_data(self) -> pd.DataFrame:
        if not self.data_path.exists():
            raise FileNotFoundError(
                f"Market data not found: {self.data_path}"
            )

        dataframe = pd.read_csv(
            self.data_path
        )

        if dataframe.empty:
            raise ValueError(
                "Market dataset is empty."
            )

        return dataframe

    def run(
        self,
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

        dataframe = self.load_data()

        return self.agent.run(
            dataframe=dataframe,
            commodity=commodity,
            market=market,
            horizon=horizon,
            storage_available=storage_available,
            nearby_market_advantage_pct=(
                nearby_market_advantage_pct
            ),
            nearby_market_price=nearby_market_price,
            transport_cost=transport_cost,
            storage_cost=storage_cost,
            expected_spoilage_pct=(
                expected_spoilage_pct
            ),
        )

    def health_check(self) -> bool:
        try:
            dataframe = self.load_data()

            return not dataframe.empty

        except Exception:
            return False

    def get_market_dashboard(
        self,
        commodity: str = "Onion",
        region: str = "Nashik",
        horizon: int = 7,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Return the regional Market Watch dashboard payload."""
        return self.intelligence.get_dashboard(
            region=region,
            commodity=commodity,
            horizon=horizon,
            force_refresh=force_refresh,
        )

    def get_current_price(
        self,
        commodity: str,
        market: str,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Return a source-stamped regional modal-price comparison.

        A city/district query resolves to all matching mandis. When no local
        mandi has a record for the requested crop, the live-data service checks
        its configured neighbouring districts before using wider fallbacks.
        """
        return self.intelligence.get_current_price(
            commodity=commodity,
            region=market,
            force_refresh=force_refresh,
        )

    def get_market_analysis(
        self,
        commodity: str,
        market: str,
        horizon: int = 7,
        **economics: Any,
    ) -> dict[str, Any]:
        """Return live regional prices, forecasts and a conservative signal."""
        return self.intelligence.get_analysis(
            commodity=commodity,
            region=market,
            horizon=horizon,
            **economics,
        )
