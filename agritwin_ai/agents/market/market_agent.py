from __future__ import annotations

from typing import Any

import pandas as pd

from agritwin_ai.agents.market.decision_engine import (
    MarketDecisionEngine,
)
from agritwin_ai.agents.market.market_context import (
    MarketContextBuilder,
)
from agritwin_ai.agents.market.market_economics import (
    MarketEconomicAnalyzer,
)
from agritwin_ai.agents.market.market_risk import (
    MarketRiskAnalyzer,
)
from agritwin_ai.models.market.forecast_service import (
    MarketForecastService,
)


class MarketAgent:
    """
    End-to-end agricultural market intelligence agent.

    Pipeline:

        Market History
            ↓
        Market Context
            ↓
        Risk Analysis
            ↓
        Price Forecast
            ↓
        Economic Analysis
            ↓
        Deterministic Decision
    """

    name = "market"

    def __init__(
        self,
        forecast_service: MarketForecastService | None = None,
        decision_engine: MarketDecisionEngine | None = None,
        context_builder: MarketContextBuilder | None = None,
        risk_analyzer: MarketRiskAnalyzer | None = None,
        economic_analyzer: MarketEconomicAnalyzer | None = None,
    ) -> None:
        self.forecast_service = (
            forecast_service
            or MarketForecastService()
        )

        self.decision_engine = (
            decision_engine
            or MarketDecisionEngine()
        )

        self.context_builder = (
            context_builder
            or MarketContextBuilder()
        )

        self.risk_analyzer = (
            risk_analyzer
            or MarketRiskAnalyzer()
        )

        self.economic_analyzer = (
            economic_analyzer
            or MarketEconomicAnalyzer()
        )

    def run(
        self,
        dataframe: pd.DataFrame,
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

        # ---------------------------------------------------------
        # 1. Market context
        # ---------------------------------------------------------

        context = self.context_builder.build(
            dataframe=dataframe,
            commodity=commodity,
            market=market,
        )

        # ---------------------------------------------------------
        # 2. Filter market history
        # ---------------------------------------------------------

        filtered = dataframe[
            dataframe["commodity"]
            .astype(str)
            .str.strip()
            .str.lower()
            == commodity.strip().lower()
        ].copy()

        normalized_markets = (
            filtered["market"]
            .astype(str)
            .str.strip()
            .str.lower()
            .str.replace(
                " ",
                "",
                regex=False,
            )
        )

        requested_market = (
            market
            .strip()
            .lower()
            .replace(" ", "")
        )

        exact_market = filtered[
            normalized_markets == requested_market
        ].copy()

        if not exact_market.empty:
            filtered = exact_market
        else:
            filtered = filtered[
                normalized_markets.str.contains(
                    requested_market,
                    regex=False,
                    na=False,
                )
            ].copy()

        prices = (
            pd.to_numeric(
                filtered["modal_price"],
                errors="coerce",
            )
            .dropna()
            .tolist()
        )

        # ---------------------------------------------------------
        # 3. Risk analysis
        # ---------------------------------------------------------

        risk = self.risk_analyzer.analyze(
            prices
        )

        # ---------------------------------------------------------
        # 4. Forecast
        # ---------------------------------------------------------

        forecast_result = (
            self.forecast_service.forecast(
                dataframe=dataframe,
                commodity=commodity,
                market=market,
                horizon=horizon,
            )
        )

        forecast_prices = [
            float(item["predicted_price"])
            for item in forecast_result["forecasts"]
        ]

        expected_price = float(
            forecast_prices[-1]
        )

        # ---------------------------------------------------------
        # 5. Economic analysis
        # ---------------------------------------------------------

        economic = self.economic_analyzer.analyze(
            current_price=context["current_price"],
            expected_price=expected_price,
            nearby_market_price=nearby_market_price,
            transport_cost=transport_cost,
            storage_cost=storage_cost,
            expected_spoilage_pct=expected_spoilage_pct,
        )

        # ---------------------------------------------------------
        # 6. Determine nearby-market signal
        # ---------------------------------------------------------

        if nearby_market_price is not None:
            decision_nearby_advantage_pct = max(
                0.0,
                float(
                    economic.get(
                        "net_nearby_gain_pct",
                        0.0,
                    )
                ),
            )
        else:
            decision_nearby_advantage_pct = (
                nearby_market_advantage_pct
            )

        # ---------------------------------------------------------
        # 7. Deterministic decision
        # ---------------------------------------------------------

        decision = self.decision_engine.decide(
            current_price=context[
                "current_price"
            ],
            forecast_prices=forecast_prices,
            volatility_pct=risk[
                "volatility_pct"
            ],
            storage_available=storage_available,
            nearby_market_advantage_pct=(
                decision_nearby_advantage_pct
            ),
        )

        # ---------------------------------------------------------
        # 8. Unified agent response
        # ---------------------------------------------------------

        return {
            "agent": self.name,
            "commodity": commodity.strip(),
            "market": market.strip(),
            "context": context,
            "risk": risk,
            "forecast": forecast_result[
                "forecasts"
            ],
            "model": forecast_result[
                "model"
            ],
            "model_metrics": forecast_result[
                "model_metrics"
            ],
            "economics": economic,
            "decision": decision.to_dict(),
        }