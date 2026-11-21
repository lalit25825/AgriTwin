from __future__ import annotations

from typing import Any

from agritwin_ai.agents.market.reflection import MarketReflection
from agritwin_ai.agents.market.state import MarketState


class MarketWorkflow:
    """
    Own transient state for one Market Agent request.

    Responsibilities:
    - load remembered market information
    - determine missing information
    - store tool observations
    - determine whether deterministic evaluation is required

    The workflow does NOT make the market decision.
    """

    MARKET_INTENTS = frozenset(
        {
            "market_price",
            "market_analysis",
            "price_forecast",
            "commodity_price",
            "sell_price",
            "market",
        }
    )

    def __init__(self) -> None:
        self.state = MarketState()
        self.reflection = MarketReflection()

    def load_memory(self, memory: dict[str, Any]) -> None:

        if "commodity" in memory:
            item = memory["commodity"]
            self.state.commodity = getattr(
                item,
                "value",
                item,
            )

        if "crop" in memory and not self.state.commodity:
            item = memory["crop"]
            self.state.commodity = getattr(
                item,
                "value",
                item,
            )

        if "market" in memory:
            item = memory["market"]
            self.state.market = getattr(
                item,
                "value",
                item,
            )

        if "state" in memory:
            item = memory["state"]
            self.state.state = getattr(
                item,
                "value",
                item,
            )

        if "district" in memory:
            item = memory["district"]
            self.state.district = getattr(
                item,
                "value",
                item,
            )

        if "date" in memory:
            item = memory["date"]
            self.state.date = getattr(
                item,
                "value",
                item,
            )

        if "quantity" in memory:
            item = memory["quantity"]

            value = getattr(
                item,
                "value",
                item,
            )

            if isinstance(value, (int, float)):
                self.state.horizon = int(value)

        if "horizon" in memory:
            item = memory["horizon"]
            value = getattr(item, "value", item)
            if isinstance(value, (int, float)):
                self.state.horizon = int(value)

        # A city may identify the mandi when the user says, for example,
        # "onion price in Nashik". This must run with or without a horizon.
        if not self.state.market:
            city = memory.get("city")
            if city:
                self.state.market = getattr(city, "value", city)
    def needs_information(self, intent: str) -> list[str]:
        missing: list[str] = []

        if intent in self.MARKET_INTENTS:

            if not self.state.commodity:
                missing.append("commodity")

            if not self.state.market:
                missing.append("market")

        return missing

    def set_market_data(
        self,
        market_data: dict[str, Any],
    ) -> None:
        self.state.market_data = market_data

    def set_forecast(
        self,
        forecast: dict[str, Any],
    ) -> None:
        self.state.forecast = forecast

    def set_risk(
        self,
        risk: dict[str, Any],
    ) -> None:
        self.state.risk = risk

    def set_economics(
        self,
        economics: dict[str, Any],
    ) -> None:
        self.state.economics = economics

    def set_current_price(
        self,
        current_price: float,
    ) -> None:
        self.state.current_price = float(
            current_price
        )

    def handle_tool_result(
        self,
        action: str,
        result: dict[str, Any],
    ) -> None:

        if action == "get_market_price":
            self.set_market_data(result)

            if result.get("current_price") is not None:
                self.set_current_price(
                    result["current_price"]
                )

        elif action == "get_market_analysis":
            self.set_market_data(result)

            if result.get("current_price") is not None:
                self.set_current_price(
                    result["current_price"]
                )

            if result.get("risk") is not None:
                self.set_risk(
                    result["risk"]
                )

            if result.get("forecast") is not None:
                self.set_forecast(
                    result["forecast"]
                )

            if result.get("economics") is not None:
                self.set_economics(
                    result["economics"]
                )

    def set_decision(
        self,
        decision: dict[str, Any],
    ) -> None:
        self.state.decision = decision

    def requires_decision(
        self,
        intent: str,
    ) -> bool:
        return intent in {
            "market_analysis",
            "sell_price",
            "market_decision",
        }

    def ready_for_evaluation(self) -> bool:
        return (
            self.state.market_data is not None
            and self.state.current_price is not None
            and self.state.forecast is not None
            and self.state.risk is not None
        )

    def complete(self) -> None:
        self.state.completed = True

    def reflect(
        self,
        intent: str,
    ) -> dict[str, Any]:
        return self.reflection.check(
            self,
            intent,
        )