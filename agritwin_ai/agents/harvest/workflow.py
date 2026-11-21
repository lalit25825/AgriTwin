from __future__ import annotations

from typing import Any

from agritwin_ai.agents.harvest.reflection import HarvestReflection
from agritwin_ai.agents.harvest.state import HarvestState


class HarvestWorkflow:
    """
    Own transient state for one Harvest Agent request.

    The workflow is responsible for:
    - loading remembered facts
    - determining whether required information exists
    - storing tool observations
    - determining whether a deterministic harvest decision is required

    It does NOT make the final harvest decision itself.
    """

    HARVEST_INTENTS = frozenset(
        {
            "harvest_decision",
            "harvest_forecast",
        }
    )

    WEATHER_INTENTS = frozenset(
        {
            "weather_current",
            "weather_forecast",
            "rainfall_forecast",
            "temperature_forecast",
            "humidity_forecast",
            "wind_forecast",
            "climate_summary",
            "extreme_weather_alert",
            "heatwave_warning",
            "coldwave_warning",
            "irrigation_weather",
            "harvest_weather_window",
        }
    )

    def __init__(self) -> None:
        self.state = HarvestState()
        self.reflection = HarvestReflection()

    # ============================================================
    # MEMORY
    # ============================================================

    def load_memory(self, memory: dict[str, Any]) -> None:
        """
        Load remembered entities into the current request state.
        """

        if "crop" in memory:
            item = memory["crop"]

            self.state.crop = getattr(
                item,
                "value",
                item,
            )

        if "city" in memory:
            item = memory["city"]

            self.state.city = getattr(
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

    # ============================================================
    # INFORMATION REQUIREMENTS
    # ============================================================

    def needs_information(self, intent: str) -> list[str]:
        """
        Determine which information is required before execution.

        Harvest requests require:
            crop + city

        Weather-only requests require:
            city
        """

        missing: list[str] = []

        # --------------------------------------------------------
        # Harvest requests
        # --------------------------------------------------------

        if intent in self.HARVEST_INTENTS:

            if not self.state.crop:
                missing.append("crop")

            if not self.state.city:
                missing.append("city")

        # --------------------------------------------------------
        # Weather requests
        # --------------------------------------------------------

        elif intent in self.WEATHER_INTENTS:

            if not self.state.city:
                missing.append("city")

        # --------------------------------------------------------
        # Crop recommendation
        # --------------------------------------------------------

        elif intent == "crop_recommendation":

            if not self.state.city:
                missing.append("city")

        return missing

    # ============================================================
    # TOOL RESULTS
    # ============================================================

    def set_weather(self, weather: dict[str, Any]) -> None:
        self.state.weather = weather

    def set_forecast(
        self,
        forecast: dict[str, Any],
    ) -> None:
        self.state.forecast = forecast

    def set_crop_info(
        self,
        crop_info: dict[str, Any],
    ) -> None:
        self.state.crop_info = crop_info

    def handle_tool_result(
        self,
        action: str,
        result: dict[str, Any],
    ) -> None:
        """
        Route a successful tool result into HarvestState.
        """

        if action == "get_weather":
            self.set_weather(result)

        elif action == "get_weather_forecast":
            self.set_forecast(result)

        elif action == "get_crop_info":
            self.set_crop_info(result)

    # ============================================================
    # DECISION
    # ============================================================

    def set_decision(
        self,
        decision: dict[str, Any],
    ) -> None:
        self.state.decision = decision

    def requires_decision(self, intent: str) -> bool:
        """
        Only harvest intents require the Harvest Decision Engine.

        Weather questions must NOT enter harvest decision logic.
        """

        return intent in self.HARVEST_INTENTS

    # ============================================================
    # EVALUATION
    # ============================================================

    def ready_for_evaluation(self) -> bool:
        """
        Harvest evaluation requires:
            weather OR forecast
            AND crop information
        """

        has_weather = (
            self.state.weather is not None
            or self.state.forecast is not None
        )

        has_crop_info = self.state.crop_info is not None

        return has_weather and has_crop_info

    # ============================================================
    # LIFECYCLE
    # ============================================================

    def complete(self) -> None:
        self.state.completed = True

    # ============================================================
    # REFLECTION
    # ============================================================

    def reflect(
        self,
        intent: str,
    ) -> dict[str, Any]:

        return self.reflection.check(
            self,
            intent,
        )

