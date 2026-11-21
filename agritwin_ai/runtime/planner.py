"""Deterministic Planner for AgriTwin agent system."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from agritwin_ai.understanding.schema import UnderstandingResult


@dataclass
class ToolAction:
    """Represents a single tool execution action."""
    name: str
    arguments: Dict[str, Any]


@dataclass
class Plan:
    """Represents a complete execution plan."""
    actions: List[ToolAction]


class Planner:
    """
    Deterministic planner that converts UnderstandingResult into
    deterministic tool actions.

    The Planner is responsible for:

    - determining which tools to call based on intent
    - constructing correct tool arguments
    - handling date normalization
    - handling forecast horizons
    - preparing deterministic logistics requests
    - never calling the LLM
    """

    def __init__(self):
        self._current_date = datetime.now().date()

    # ============================================================
    # MAIN PLANNER
    # ============================================================

    def plan(
        self,
        understanding: UnderstandingResult,
        workflow,
        working_memory: Dict[str, Any],
    ) -> Plan:
        """
        Create deterministic execution plan from UnderstandingResult.
        """

        # Accept the complete UnderstandingResult contract while remaining
        # tolerant of lightweight test doubles and partial integrations.
        entities = getattr(understanding, "entities", None) or {}
        updates = getattr(understanding, "updates", None) or {}
        intent = getattr(understanding, "intent", "unknown")

        # --------------------------------------------------------
        # Direct conversational intents
        # --------------------------------------------------------

        if intent in {
            "greeting",
            "thanks",
            "farewell",
            "acknowledgement",
        }:
            return Plan(actions=[])

        # --------------------------------------------------------
        # Coordinator workflow
        # --------------------------------------------------------

        if (
            hasattr(workflow, "__class__")
            and workflow.__class__.__name__ == "CoordinatorWorkflow"
        ):
            return Plan(actions=[])

        # --------------------------------------------------------
        # LOGISTICS
        #
        # IMPORTANT:
        # Logistics must be handled BEFORE the generic reflection
        # check because its workflow needs the CURRENT understanding
        # and updates to populate its state.
        # --------------------------------------------------------

        if intent in {
            "logistics",
            "transport_cost",
            "transport_route",
            "transport_time",
            "logistics_recommendation",
        }:
            return self._plan_logistics(
                entities=entities,
                updates=updates,
                working_memory=working_memory,
                workflow=workflow,
            )

        # --------------------------------------------------------
        # Generic workflow readiness
        # --------------------------------------------------------

        reflection = workflow.reflect(intent)

        if not reflection["ready"]:
            return Plan(actions=[])

        # --------------------------------------------------------
        # Climate intents
        # --------------------------------------------------------

        if intent == "weather_current":
            return self._plan_weather_current(
                entities,
                working_memory,
            )

        if intent == "weather_forecast":
            return self._plan_weather_forecast(
                entities,
                working_memory,
            )

        # --------------------------------------------------------
        # Harvest intents
        # --------------------------------------------------------

        if intent == "harvest_decision":
            return self._plan_harvest_decision(
                entities,
                working_memory,
            )

        if intent == "harvest_forecast":
            return self._plan_harvest_forecast(
                entities,
                working_memory,
            )

        # --------------------------------------------------------
        # Market intents
        # --------------------------------------------------------

        if intent == "market_price":
            return self._plan_market_price(
                entities,
                working_memory,
            )

        if intent in {
            "market_analysis",
            "price_forecast",
            "commodity_price",
            "sell_price",
        }:
            return self._plan_market_analysis(
                entities,
                working_memory,
            )

        # --------------------------------------------------------
        # Other intents
        # --------------------------------------------------------

        return Plan(actions=[])

    # ============================================================
    # WEATHER
    # ============================================================

    def _plan_weather_current(
        self,
        entities: Dict[str, Any],
        working_memory: Dict[str, Any],
    ) -> Plan:
        """Plan for current weather request."""

        city = (
            self._get_entity_value(entities, "city")
            or self._get_memory_value(working_memory, "city")
        )

        if not city:
            return Plan(actions=[])

        return Plan(
            actions=[
                ToolAction(
                    name="get_weather",
                    arguments={
                        "city": city,
                    },
                )
            ]
        )

    def _plan_weather_forecast(
        self,
        entities: Dict[str, Any],
        working_memory: Dict[str, Any],
    ) -> Plan:
        """Plan for weather forecast request."""

        city = (
            self._get_entity_value(entities, "city")
            or self._get_memory_value(working_memory, "city")
        )

        if not city:
            return Plan(actions=[])

        days = self._calculate_forecast_days(
            entities,
            working_memory,
        )

        return Plan(
            actions=[
                ToolAction(
                    name="get_weather_forecast",
                    arguments={
                        "city": city,
                        "days": days,
                    },
                )
            ]
        )

    # ============================================================
    # HARVEST
    # ============================================================

    def _plan_harvest_decision(
        self,
        entities: Dict[str, Any],
        working_memory: Dict[str, Any],
    ) -> Plan:
        """Plan for harvest decision request."""

        actions = []

        # --------------------------------------------------------
        # Crop information
        # --------------------------------------------------------

        crop = (
            self._get_entity_value(entities, "crop")
            or self._get_memory_value(working_memory, "crop")
        )

        if crop:
            actions.append(
                ToolAction(
                    name="get_crop_info",
                    arguments={
                        "crop": crop,
                    },
                )
            )

        # --------------------------------------------------------
        # Weather information
        # --------------------------------------------------------

        city = (
            self._get_entity_value(entities, "city")
            or self._get_memory_value(working_memory, "city")
        )

        if city:

            date_entity = self._get_entity_value(
                entities,
                "date",
            )

            quantity = self._get_entity_value(
                entities,
                "quantity",
            )

            if date_entity:

                days_needed = self._calculate_days_from_date(
                    date_entity
                )

                if days_needed > 0:

                    days = days_needed + 1

                    actions.append(
                        ToolAction(
                            name="get_weather_forecast",
                            arguments={
                                "city": city,
                                "days": days,
                            },
                        )
                    )

                else:

                    actions.append(
                        ToolAction(
                            name="get_weather",
                            arguments={
                                "city": city,
                            },
                        )
                    )

            elif (
                quantity
                and isinstance(quantity, (int, float))
                and quantity > 0
            ):

                days = int(quantity)

                actions.append(
                    ToolAction(
                        name="get_weather_forecast",
                        arguments={
                            "city": city,
                            "days": days,
                        },
                    )
                )

            else:

                actions.append(
                    ToolAction(
                        name="get_weather",
                        arguments={
                            "city": city,
                        },
                    )
                )

        return Plan(actions=actions)

    def _plan_harvest_forecast(
        self,
        entities: Dict[str, Any],
        working_memory: Dict[str, Any],
    ) -> Plan:
        """Plan for harvest forecast request."""

        actions = []

        crop = (
            self._get_entity_value(entities, "crop")
            or self._get_memory_value(working_memory, "crop")
        )

        if crop:
            actions.append(
                ToolAction(
                    name="get_crop_info",
                    arguments={
                        "crop": crop,
                    },
                )
            )

        city = (
            self._get_entity_value(entities, "city")
            or self._get_memory_value(working_memory, "city")
        )

        if city:

            days = self._calculate_forecast_days(
                entities,
                working_memory,
            )

            actions.append(
                ToolAction(
                    name="get_weather_forecast",
                    arguments={
                        "city": city,
                        "days": days,
                    },
                )
            )

        return Plan(actions=actions)

    # ============================================================
    # MARKET
    # ============================================================

    @staticmethod
    def _market_names(market: Any) -> list[str]:
        """Split a user-supplied multi-mandi entity into known markets."""
        if market is None:
            return []
        from agritwin_ai.agents.market.request_parser import MarketRequestParser

        names = MarketRequestParser._extract_markets(str(market))
        return names or [str(market)]

    def _plan_market_price(
        self,
        entities: Dict[str, Any],
        working_memory: Dict[str, Any],
    ) -> Plan:

        commodity = (
            self._get_entity_value(
                entities,
                "crop",
            )
            or self._get_entity_value(
                entities,
                "commodity",
            )
            or self._get_memory_value(
                working_memory,
                "crop",
            )
            or self._get_memory_value(
                working_memory,
                "commodity",
            )
        )

        market = (
            self._get_entity_value(
                entities,
                "market",
            )
            or self._get_memory_value(
                working_memory,
                "market",
            )
            or self._get_memory_value(
                working_memory,
                "city",
            )
        )

        if not commodity or not market:
            return Plan(actions=[])

        markets = self._market_names(market)

        date_entity = self._get_entity_value(
            entities,
            "date",
        )

        quantity = self._get_entity_value(
            entities,
            "quantity",
        )

        # --------------------------------------------------------
        # Future price request
        # --------------------------------------------------------

        if (
            date_entity
            and str(date_entity).lower() != "today"
        ):

            horizon = self._calculate_forecast_days(
                entities,
                working_memory,
            )

            return Plan(
                actions=[
                    ToolAction(
                        name="get_market_analysis",
                        arguments={
                            "commodity": commodity,
                            "market": market_name,
                            "horizon": horizon,
                        },
                    )
                    for market_name in markets
                ]
            )

        # --------------------------------------------------------
        # Quantity-based horizon
        # --------------------------------------------------------

        if (
            quantity
            and isinstance(quantity, (int, float))
            and quantity > 0
        ):

            return Plan(
                actions=[
                    ToolAction(
                        name="get_market_analysis",
                        arguments={
                            "commodity": commodity,
                            "market": market_name,
                            "horizon": min(max(int(quantity), 1), 16),
                        },
                    )
                    for market_name in markets
                ]
            )

        # --------------------------------------------------------
        # Current price
        # --------------------------------------------------------

        return Plan(
            actions=[
                ToolAction(
                    name="get_market_price",
                    arguments={
                        "commodity": commodity,
                        "market": market_name,
                    },
                )
                for market_name in markets
            ]
        )

    def _plan_market_analysis(
        self,
        entities: Dict[str, Any],
        working_memory: Dict[str, Any],
    ) -> Plan:

        commodity = (
            self._get_entity_value(
                entities,
                "crop",
            )
            or self._get_entity_value(
                entities,
                "commodity",
            )
            or self._get_memory_value(
                working_memory,
                "crop",
            )
            or self._get_memory_value(
                working_memory,
                "commodity",
            )
        )

        market = (
            self._get_entity_value(
                entities,
                "market",
            )
            or self._get_memory_value(
                working_memory,
                "market",
            )
        )

        if not commodity or not market:
            return Plan(actions=[])

        markets = self._market_names(market)

        horizon = self._get_entity_value(
            entities,
            "quantity",
        )

        if not horizon:
            horizon = self._get_memory_value(
                working_memory,
                "quantity",
            )

        if not horizon:
            horizon = self._get_memory_value(
                working_memory,
                "horizon",
            )

        try:
            horizon = int(horizon)
        except (TypeError, ValueError):
            horizon = 7

        horizon = min(
            max(horizon, 1),
            16,
        )

        return Plan(
            actions=[
                ToolAction(
                    name="get_market_analysis",
                    arguments={
                        "commodity": commodity,
                        "market": market_name,
                        "horizon": horizon,
                    },
                )
                for market_name in markets
            ]
        )

    # ============================================================
    # LOGISTICS
    # ============================================================

    def _plan_logistics(
        self,
        entities: Dict[str, Any],
        updates: Dict[str, Any],
        working_memory: Dict[str, Any],
        workflow,
    ) -> Plan:
        """
        Build a deterministic logistics tool call.

        The LLM never constructs logistics tool arguments.

        Information flow:

            working memory
                  ↓
            current entities
                  ↓
            current updates
                  ↓
            LogisticsWorkflow
                  ↓
            validation
                  ↓
            get_logistics_analysis
        """

        # --------------------------------------------------------
        # 1. Load previous memory
        # --------------------------------------------------------

        if hasattr(workflow, "load_memory"):
            workflow.load_memory(
                working_memory or {}
            )

        # --------------------------------------------------------
        # 2. Apply CURRENT understanding
        #
        # This must happen AFTER memory so the current request
        # overrides stale memory.
        # --------------------------------------------------------

        if hasattr(
            workflow,
            "update_from_understanding",
        ):
            workflow.update_from_understanding(
                entities=entities or {},
                updates=updates or {},
            )

        # --------------------------------------------------------
        # 3. Reflect AFTER state has been populated
        # --------------------------------------------------------

        reflection = workflow.reflect(
            "logistics"
        )

        if not reflection["ready"]:
            return Plan(actions=[])

        # --------------------------------------------------------
        # 4. Get normalized request from workflow
        # --------------------------------------------------------

        request = workflow.build_request()

        commodity = request.get(
            "commodity"
        )

        quantity = request.get(
            "quantity_tons"
        )

        origin = request.get(
            "origin"
        )

        destination = request.get(
            "destination"
        )

        market = request.get(
            "market"
        )

        # --------------------------------------------------------
        # 5. Final validation
        # --------------------------------------------------------

        if not commodity:
            return Plan(actions=[])

        if not origin:
            return Plan(actions=[])

        if not destination:
            return Plan(actions=[])

        try:
            quantity = float(quantity)
        except (TypeError, ValueError):
            return Plan(actions=[])

        if quantity <= 0:
            return Plan(actions=[])

        # --------------------------------------------------------
        # 6. Build deterministic tool arguments
        # --------------------------------------------------------

        arguments = {
            "commodity": str(commodity),
            "quantity_tons": quantity,
            "origin": str(origin),
            "destination": str(destination),
        }

        if market:
            arguments["market"] = str(market)

        # --------------------------------------------------------
        # 7. Return deterministic tool action
        # --------------------------------------------------------

        return Plan(
            actions=[
                ToolAction(
                    name="get_logistics_analysis",
                    arguments=arguments,
                )
            ]
        )

    # ============================================================
    # ENTITY / MEMORY HELPERS
    # ============================================================

    def _get_entity_value(
        self,
        entities: Dict[str, Any],
        key: str,
    ) -> Any:
        """
        Extract entity value while supporting:

        - normal values
        - MemoryItem-like objects
        - {"value": ...} dictionaries
        """

        if not entities:
            return None

        value = entities.get(key)

        if value is None:
            return None

        if hasattr(value, "value"):
            return value.value

        if isinstance(value, dict):
            return value.get("value")

        return value

    def _get_memory_value(
        self,
        working_memory: Dict[str, Any],
        key: str,
    ) -> Any:
        """
        Extract values from working memory.

        WorkingMemory stores MemoryItem objects, while some
        callers may provide plain values.
        """

        if not working_memory:
            return None

        value = working_memory.get(key)

        if value is None:
            return None

        if hasattr(value, "value"):
            return value.value

        if isinstance(value, dict):
            return value.get("value")

        return value

    # ============================================================
    # FORECAST DATE HELPERS
    # ============================================================

    def _calculate_forecast_days(
        self,
        entities: Dict[str, Any],
        working_memory: Dict[str, Any],
    ) -> int:
        """
        Calculate number of forecast days needed.
        """

        date_entity = self._get_entity_value(
            entities,
            "date",
        )

        if date_entity:

            days_needed = self._calculate_days_from_date(
                date_entity
            )

            if days_needed >= 0:

                days = days_needed + 1

                return min(
                    max(days, 1),
                    16,
                )

        quantity = self._get_entity_value(
            entities,
            "quantity",
        )

        if quantity is None:
            quantity = self._get_memory_value(
                working_memory,
                "quantity",
            )

        try:
            quantity = float(quantity)
        except (TypeError, ValueError):
            quantity = None

        if quantity is not None and quantity > 0:

            return min(
                max(int(quantity), 1),
                16,
            )

        return 1

    def _calculate_days_from_date(
        self,
        date_entity: Any,
    ) -> int:
        """
        Calculate number of days from the current date.

        Supports:

        today
        tomorrow
        day after tomorrow
        yesterday
        DD month
        DD-month
        YYYY-MM-DD
        """

        if not date_entity:
            return 0

        if not isinstance(
            date_entity,
            str,
        ):
            return 0

        date_str = (
            date_entity
            .lower()
            .strip()
            .replace("_", " ")
        )

        # --------------------------------------------------------
        # Relative dates
        # --------------------------------------------------------

        if date_str == "today":
            return 0

        if date_str == "tomorrow":
            return 1

        if date_str == "day after tomorrow":
            return 2

        if date_str == "yesterday":
            return -1

        # --------------------------------------------------------
        # Month names
        # --------------------------------------------------------

        month_map = {
            "january": 1,
            "jan": 1,
            "february": 2,
            "feb": 2,
            "march": 3,
            "mar": 3,
            "april": 4,
            "apr": 4,
            "may": 5,
            "june": 6,
            "jun": 6,
            "july": 7,
            "jul": 7,
            "august": 8,
            "aug": 8,
            "september": 9,
            "sep": 9,
            "sept": 9,
            "october": 10,
            "oct": 10,
            "november": 11,
            "nov": 11,
            "december": 12,
            "dec": 12,
        }

        # --------------------------------------------------------
        # DD month
        # --------------------------------------------------------

        try:

            parts = date_str.split()

            if len(parts) == 2:

                day_str, month_str = parts

                day = int(day_str)

                month = month_map.get(
                    month_str
                )

                if (
                    month
                    and 1 <= day <= 31
                ):

                    target_date = datetime(
                        self._current_date.year,
                        month,
                        day,
                    ).date()

                    return (
                        target_date
                        - self._current_date
                    ).days

            # ----------------------------------------------------
            # DD-month
            # ----------------------------------------------------

            if (
                len(parts) == 1
                and "-" in parts[0]
            ):

                day_str, month_str = parts[0].split(
                    "-",
                    1,
                )

                day = int(day_str)

                month = month_map.get(
                    month_str
                )

                if (
                    month
                    and 1 <= day <= 31
                ):

                    target_date = datetime(
                        self._current_date.year,
                        month,
                        day,
                    ).date()

                    return (
                        target_date
                        - self._current_date
                    ).days

        except (
            ValueError,
            IndexError,
        ):
            pass

        # --------------------------------------------------------
        # YYYY-MM-DD
        # --------------------------------------------------------

        try:

            if (
                len(date_str) == 10
                and date_str.count("-") == 2
            ):

                year, month, day = map(
                    int,
                    date_str.split("-"),
                )

                target_date = datetime(
                    year,
                    month,
                    day,
                ).date()

                return (
                    target_date
                    - self._current_date
                ).days

        except ValueError:
            pass

        return 0