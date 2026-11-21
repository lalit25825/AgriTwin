from typing import Any, Dict

from .state import LogisticsState


LOGISTICS_INTENTS = {
    "logistics",
    "transport_cost",
    "transport_route",
    "transport_time",
    "logistics_recommendation",
}


class LogisticsWorkflow:

    def __init__(self):
        self.state = LogisticsState()
        # Retain the raw provider result for the web layer so a later
        # "show me the map" request can reuse the exact route.
        self.last_analysis_result: Dict[str, Any] | None = None

    # ============================================================
    # MEMORY
    # ============================================================

    def load_memory(self, memory: Dict[str, Any]):
        """
        Load known logistics information from AgriTwin working memory.

        Existing AgriTwin vocabulary is supported:

            crop          -> commodity
            quantity      -> quantity_tons
            city          -> origin
            destination   -> destination
            market        -> market
        """

        if not memory:
            return

        commodity = (
            self._extract(memory.get("commodity"))
            or self._extract(memory.get("crop"))
        )

        if commodity is not None:
            self.state.commodity = commodity

        quantity = (
            self._extract(memory.get("quantity_tons"))
            or self._extract(memory.get("quantity"))
        )

        if quantity is not None:
            converted_quantity = self._to_float(quantity)

            if converted_quantity is not None:
                self.state.quantity_tons = converted_quantity

        origin = (
            self._extract(memory.get("origin"))
            or self._extract(memory.get("city"))
        )

        if origin is not None:
            self.state.origin = origin

        destination = self._extract(memory.get("destination"))

        if destination is not None:
            self.state.destination = destination

        market = self._extract(memory.get("market"))

        if market is not None:
            self.state.market = market

    # ============================================================
    # UNDERSTANDING -> STATE
    # ============================================================

    def update_from_understanding(
        self,
        entities: Dict[str, Any],
        updates: Dict[str, Any],
    ):
        """
        Convert UnderstandingResult data into deterministic
        LogisticsState.

        Example:

        entities:
            crop = onion
            city = Nashik
            quantity = 5

        updates:
            destination = Lasalgaon
        """

        # --------------------------------------------------------
        # Entities
        # --------------------------------------------------------

        if entities:

            crop = self._extract(entities.get("crop"))

            if crop is not None:
                self.state.commodity = crop

            city = self._extract(entities.get("city"))

            if city is not None:
                self.state.origin = city

            quantity = self._extract(entities.get("quantity"))

            if quantity is not None:
                converted_quantity = self._to_float(quantity)

                if converted_quantity is not None:
                    self.state.quantity_tons = converted_quantity

            # Support logistics-specific entity names too
            for key in (
                "commodity",
                "origin",
                "destination",
                "market",
                "quantity_tons",
            ):
                value = self._extract(entities.get(key))

                if value is not None:
                    self._assign(key, value)

        # --------------------------------------------------------
        # Updates
        # --------------------------------------------------------

        if updates:

            for key, value in updates.items():

                value = self._extract(value)

                if value is None:
                    continue

                if key == "crop":
                    self.state.commodity = value

                elif key == "city":
                    self.state.origin = value

                elif key == "quantity":
                    converted_quantity = self._to_float(value)

                    if converted_quantity is not None:
                        self.state.quantity_tons = converted_quantity

                elif key in {
                    "commodity",
                    "origin",
                    "destination",
                    "market",
                    "quantity_tons",
                }:
                    self._assign(key, value)

    # ============================================================
    # REFLECTION
    # ============================================================

    def reflect(self, intent: str) -> Dict[str, Any]:
        """
        Determine whether enough information exists to execute
        the logistics workflow.

        Planner expects a dictionary:

            {
                "ready": bool,
                "missing": [...]
            }
        """

        if intent not in LOGISTICS_INTENTS:
            return {
                "ready": False,
                "missing": [],
            }

        required = {
            "commodity": self.state.commodity,
            "quantity_tons": self.state.quantity_tons,
            "origin": self.state.origin,
            "destination": self.state.destination,
        }

        missing = [
            field
            for field, value in required.items()
            if value is None or value == ""
        ]

        return {
            "ready": len(missing) == 0,
            "missing": missing,
        }

    def requires_decision(self, intent: str) -> bool:
        return intent in {
            "logistics_recommendation",
            "transport_cost",
            "transport_route",
            "transport_time",
        }

    # ============================================================
    # REQUEST
    # ============================================================

    def build_request(self) -> Dict[str, Any]:
        """
        Build the deterministic logistics request.

        No LLM is involved here.
        """

        return {
            "commodity": self.state.commodity,
            "quantity_tons": self.state.quantity_tons,
            "origin": self.state.origin,
            "destination": self.state.destination,
            "market": self.state.market,
        }

    # ============================================================
    # TOOL RESULT ROUTING
    # ============================================================

    def handle_tool_result(
        self,
        tool_name: str,
        result: Dict[str, Any],
    ):
        """
        Apply tool results back into LogisticsState.
        """

        if not result:
            return

        if tool_name == "get_logistics_analysis":
            self._apply_result(result)

        elif tool_name == "geocode_location":
            self._handle_geocode(result)

        elif tool_name == "get_route":
            self._handle_route(result)

        elif tool_name == "get_weather":
            self._handle_weather(result)

    # ============================================================
    # TOOL RESULT HANDLERS
    # ============================================================

    def _apply_result(self, result: Dict[str, Any]):
        """
        Normalize the nested logistics tool result into LogisticsState.

        The tool returns structured sections such as:
            origin
            destination
            route
            weather
            vehicle
            cost
            risk
            data_quality

        LogisticsState stores these in normalized fields so the
        response layer can consume them reliably.
        """

        if not result:
            return

        self.last_analysis_result = result

        # ========================================================
        # BASIC SHIPMENT INFORMATION
        # ========================================================

        commodity = result.get("commodity")

        if commodity is not None:
            self.state.commodity = commodity

        quantity_tons = result.get("quantity_tons")

        if quantity_tons is not None:
            converted_quantity = self._to_float(quantity_tons)

            if converted_quantity is not None:
                self.state.quantity_tons = converted_quantity

        # ========================================================
        # ORIGIN
        # ========================================================

        origin = result.get("origin")

        if isinstance(origin, dict):

            self.state.origin = (
                origin.get("display_name")
                or origin.get("query")
                or self.state.origin
            )

            self.state.origin_lat = origin.get("latitude")
            self.state.origin_lon = origin.get("longitude")

        elif origin is not None:

            self.state.origin = origin

        # ========================================================
        # DESTINATION
        # ========================================================

        destination = result.get("destination")

        if isinstance(destination, dict):

            self.state.destination = (
                destination.get("display_name")
                or destination.get("query")
                or self.state.destination
            )

            self.state.destination_lat = destination.get("latitude")
            self.state.destination_lon = destination.get("longitude")

        elif destination is not None:

            self.state.destination = destination

        # ========================================================
        # MARKET
        # ========================================================

        market = result.get("market")

        if market is not None:
            self.state.market = market

        # ========================================================
        # ROUTE
        # ========================================================

        route = result.get("route")

        if isinstance(route, dict):

            self.state.route = route

            routes = route.get("routes", [])

            if isinstance(routes, list) and routes:

                first_route = routes[0]

                if isinstance(first_route, dict):

                    self.state.distance_km = first_route.get(
                        "distance_km"
                    )

                    self.state.duration_minutes = first_route.get(
                        "duration_minutes"
                    )

                self.state.alternative_routes = [
                    item
                    for item in routes[1:]
                    if isinstance(item, dict)
                ]

            # If the tool ever returns distance/duration directly
            # at route level, support that too.
            if self.state.distance_km is None:
                self.state.distance_km = route.get(
                    "distance_km"
                )

            if self.state.duration_minutes is None:
                self.state.duration_minutes = route.get(
                    "duration_minutes"
                )

        # ========================================================
        # WEATHER
        # ========================================================

        weather = result.get("weather")

        if isinstance(weather, dict):

            origin_weather = weather.get("origin")

            if isinstance(origin_weather, dict):
                self.state.origin_weather = origin_weather

            destination_weather = weather.get("destination")

            if isinstance(destination_weather, dict):
                self.state.destination_weather = destination_weather

            # Preserve provider errors if present.
            weather_errors = weather.get("errors")

            if isinstance(weather_errors, list):
                for error in weather_errors:
                    if error and error not in self.state.errors:
                        self.state.errors.append(str(error))

        # ========================================================
        # VEHICLE
        # ========================================================

        vehicle = result.get("vehicle")

        if isinstance(vehicle, dict):

            self.state.vehicle_type = vehicle.get("type")

            self.state.vehicle_capacity_tons = self._to_float(
                vehicle.get("capacity_tons")
            )

            
        # ========================================================
        # COST
        # ========================================================

        cost = result.get("cost")

        if isinstance(cost, dict):

            self.state.total_cost = self._to_float(
                cost.get("estimated_total_inr")
            )

            self.state.cost_per_ton = self._to_float(
                cost.get("estimated_cost_per_ton_inr")
            )

            self.state.transport_cost = self._to_float(
                cost.get("estimated_total_inr")
            )

            self.state.fuel_cost = self._to_float(
                cost.get("fuel_cost_inr")
            )

            self.state.driver_cost = self._to_float(
                cost.get("driver_cost_inr")
            )

            self.state.loading_cost = self._to_float(
                cost.get("handling_cost_inr")
            )

            self.state.toll_cost = self._to_float(
                cost.get("tolls_inr")
            )

        # ========================================================
        # RISK
        # ========================================================

        risk = result.get("risk")

        if isinstance(risk, dict):

            self.state.logistics_risk = risk.get("level")

            # Weather-specific risk is currently derived from the
            # same risk assessment because the tool combines
            # weather factors into the logistics risk.
            self.state.weather_risk = risk.get("level")

        # ========================================================
        # DATA QUALITY / SOURCES
        # ========================================================

        data_quality = result.get("data_quality")

        if isinstance(data_quality, dict):

            self.state.data_sources = data_quality

        # ========================================================
        # PROVIDER TIMESTAMP
        # ========================================================

        provider_timestamp = result.get(
            "provider_timestamp_utc"
        )

        if provider_timestamp is not None:

            self.state.data_sources[
                "provider_timestamp_utc"
            ] = provider_timestamp

        # ========================================================
        # MAP URL
        # ========================================================

        maps_url = result.get("maps_url")

        if maps_url is not None:

            self.state.data_sources["maps_url"] = maps_url

    def _handle_geocode(self, result: Dict[str, Any]):
        location = result.get("location")

        latitude = result.get("latitude")
        longitude = result.get("longitude")

        if location == self.state.origin:

            self.state.origin_lat = latitude
            self.state.origin_lon = longitude

        elif location == self.state.destination:

            self.state.destination_lat = latitude
            self.state.destination_lon = longitude

    def _handle_route(self, result: Dict[str, Any]):
        self.state.distance_km = result.get("distance_km")

        self.state.duration_minutes = result.get(
            "duration_minutes"
        )

        self.state.route = result

        alternatives = result.get("alternatives")

        if isinstance(alternatives, list):
            self.state.alternative_routes = alternatives

    def _handle_weather(self, result: Dict[str, Any]):
        location = result.get("location")

        if location == self.state.origin:

            self.state.origin_weather = result

        elif location == self.state.destination:

            self.state.destination_weather = result

    # ============================================================
    # HELPERS
    # ============================================================

    def _assign(self, key: str, value: Any):
        """
        Assign a normalized value to LogisticsState.
        """

        if not hasattr(self.state, key):
            return

        if key == "quantity_tons":

            converted_quantity = self._to_float(value)

            if converted_quantity is not None:
                setattr(
                    self.state,
                    key,
                    converted_quantity,
                )

            return

        setattr(self.state, key, value)

    @staticmethod
    def _extract(value: Any):
        """
        Extract the actual value from:

        - normal values
        - MemoryItem-like objects
        - {"value": ...} dictionaries
        """

        if value is None:
            return None

        # MemoryItem / similar objects
        if hasattr(value, "value"):
            return value.value

        # Understanding entity dictionaries
        if isinstance(value, dict):
            return value.get("value")

        return value

    @staticmethod
    def _to_float(value):
        """
        Safely convert quantity to float.
        """

        if value is None:
            return None

        if isinstance(value, bool):
            return None

        try:
            return float(value)

        except (TypeError, ValueError):
            return None

    def _to_float(self, value):
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None


    def _to_int(self, value):
        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None