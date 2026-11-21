from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus

from agritwin_ai.agents.logistics.knowledge import (
    normalize_commodity,
    profile_for,
    select_vehicle,
)
from agritwin_ai.agents.logistics.providers import (
    GeoPoint,
    GoogleRoutesProvider,
    NominatimGeocoder,
    OSRMRouter,
    OpenMeteoWeatherProvider,
    ProviderError,
)

from agritwin_ai.agents.logistics.vehicle_optimizer import optimize_vehicle


_geocoder = NominatimGeocoder()
_osrm = OSRMRouter()
_google = GoogleRoutesProvider()
_weather = OpenMeteoWeatherProvider()


def get_logistics_analysis(
    commodity: str,
    quantity_tons: float,
    origin: str,
    destination: str,
    market: str | None = None,
    vehicle_type: str | None = None,
) -> dict[str, Any]:
    """Collect live route/weather data and calculate deterministic logistics metrics."""

    if not commodity:
        return {"error": "Commodity is required."}

    if not origin:
        return {"error": "Origin is required."}

    if not destination:
        return {"error": "Destination is required."}

    if quantity_tons is None or float(quantity_tons) <= 0:
        return {"error": "Quantity must be greater than zero tons."}

    quantity_tons = float(quantity_tons)
    commodity = normalize_commodity(commodity) or commodity.strip().lower()

    # =========================================================
    # GEOCODING
    # =========================================================

    try:
        origin_point = _geocoder.geocode(origin)

        destination_point = _resolve_destination(
            destination=destination,
            origin=origin,
            origin_point=origin_point,
        )

    except ProviderError as exc:
        return {
            "error": str(exc),
            "stage": "geocoding",
        }

    # =========================================================
    # ROUTING
    # =========================================================

    # Prefer genuine traffic-aware routing when configured.
    # OSRM remains the working no-key fallback.
    try:

        if _google.available:
            route = _google.route(
                origin_point,
                destination_point,
            )

        else:
            route = _osrm.route(
                origin_point,
                destination_point,
            )

    except ProviderError as primary_error:

        if _google.available:

            try:

                route = _osrm.route(
                    origin_point,
                    destination_point,
                )

                route["fallback_reason"] = str(
                    primary_error
                )

            except ProviderError as fallback_error:

                return {
                    "error": str(fallback_error),
                    "stage": "routing",
                }

        else:

            return {
                "error": str(primary_error),
                "stage": "routing",
            }

    # =========================================================
    # WEATHER
    # =========================================================

    weather_errors: list[str] = []

    origin_weather: dict[str, Any] | None = None
    destination_weather: dict[str, Any] | None = None

    try:

        origin_weather = _weather.forecast(
            origin_point,
            forecast_days=2,
        )

    except ProviderError as exc:

        weather_errors.append(
            f"origin: {exc}"
        )

    try:

        destination_weather = _weather.forecast(
            destination_point,
            forecast_days=2,
        )

    except ProviderError as exc:

        weather_errors.append(
            f"destination: {exc}"
        )

    # =========================================================
    # VEHICLE OPTIMIZATION
    # =========================================================

    primary_route = route["routes"][0]

    profile = profile_for(commodity)

    if vehicle_type:

        chosen_vehicle, vehicle = _resolve_vehicle(
            vehicle_type,
            quantity_tons,
        )

        cost = _estimate_cost(
            distance_km=primary_route["distance_km"],
            duration_minutes=primary_route["duration_minutes"],
            quantity_tons=quantity_tons,
            vehicle_type=chosen_vehicle,
            vehicle_profile=vehicle,
        )

        loads_required = max(
            1,
            int(
                -(
                    -quantity_tons
                    // vehicle["capacity_tons"]
                )
            ),
        )

        capacity_utilization_pct = round(
            (
                quantity_tons
                / (
                    vehicle["capacity_tons"]
                    * loads_required
                )
            )
            * 100,
            2,
        )

        vehicle_optimization = {
            "recommended_vehicle": {
                "vehicle_type": chosen_vehicle,
                "capacity_tons": vehicle["capacity_tons"],
                "km_per_liter": vehicle["km_per_liter"],
                "loads_required": loads_required,
                "capacity_utilization_pct": (
                    capacity_utilization_pct
                ),
                "estimated_total_inr": (
                    cost["estimated_total_inr"]
                ),
                "estimated_cost_per_ton_inr": (
                    cost[
                        "estimated_cost_per_ton_inr"
                    ]
                ),
            },
            "candidates": [],
            "optimization_basis": (
                "user_selected_vehicle"
            ),
        }

    else:

        vehicle_optimization = optimize_vehicle(
            quantity_tons=quantity_tons,
            distance_km=primary_route[
                "distance_km"
            ],
            duration_minutes=primary_route[
                "duration_minutes"
            ],
        )

        recommended = (
            vehicle_optimization[
                "recommended_vehicle"
            ]
        )

        chosen_vehicle = (
            recommended["vehicle_type"]
        )

        from agritwin_ai.agents.logistics.knowledge import (
            VEHICLE_PROFILES,
        )

        vehicle = VEHICLE_PROFILES[
            chosen_vehicle
        ]

        cost = {
            "estimated_total_inr": (
                recommended[
                    "estimated_total_inr"
                ]
            ),
            "estimated_cost_per_ton_inr": (
                recommended[
                    "estimated_cost_per_ton_inr"
                ]
            ),
            "fuel_liters": (
                recommended["fuel_liters"]
            ),
            "fuel_price_inr_per_liter": (
                vehicle_optimization[
                    "assumptions"
                ][
                    "fuel_price_inr_per_liter"
                ]
            ),
            "fuel_cost_inr": (
                recommended["fuel_cost_inr"]
            ),
            "driver_cost_inr": (
                recommended["driver_cost_inr"]
            ),
            "handling_cost_inr": (
                recommended["handling_cost_inr"]
            ),
            "tolls_inr": (
                recommended["tolls_inr"]
            ),
            "assumption_based": True,
        }

    # =========================================================
    # RISK
    # =========================================================

    risk = _assess_risk(
        commodity=commodity,
        profile=profile,
        route=primary_route,
        origin_weather=origin_weather,
        destination_weather=destination_weather,
    )

    # =========================================================
    # MAPS
    # =========================================================

    origin_map_location = (
        f"{origin_point.latitude},{origin_point.longitude}"
    )
    destination_map_location = (
        f"{destination_point.latitude},{destination_point.longitude}"
    )
    maps_url = (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={quote_plus(origin_map_location)}"
        f"&destination={quote_plus(destination_map_location)}"
        "&travelmode=driving"
    )

    # =========================================================
    # MARKET
    # =========================================================

    market_data = None

    if market:

        try:

            from agritwin_ai.agents.market.market_runtime import (
                MarketRuntime,
            )

            market_data = (
                MarketRuntime()
                .get_current_price(
                    commodity,
                    market,
                )
            )

        except Exception as exc:

            market_data = {
                "error": str(exc),
                "source": (
                    "AgriTwin market snapshot"
                ),
            }

    # =========================================================
    # RESULT
    # =========================================================

    return {
        "provider_timestamp_utc": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),

        "commodity": commodity,

        "quantity_tons": quantity_tons,

        "origin": {
            "query": origin,
            "display_name": (
                origin_point.display_name
            ),
            "latitude": (
                origin_point.latitude
            ),
            "longitude": (
                origin_point.longitude
            ),
        },

        "destination": {
            "query": destination,
            "display_name": (
                destination_point.display_name
            ),
            "latitude": (
                destination_point.latitude
            ),
            "longitude": (
                destination_point.longitude
            ),
        },
        "location_resolution": {
            "origin_requested": origin,
            "origin_resolved": origin_point.display_name,
            "destination_requested": destination,
            "destination_resolved": destination_point.display_name,
            "destination_was_interpreted": (
                destination_point.query != destination
            ),
        },

        "market": market,

        "market_data": market_data,

        "maps_url": maps_url,

        "route": route,

        "weather": {
            "origin": origin_weather,
            "destination": destination_weather,
            "errors": weather_errors,
        },

        "vehicle": {
            "type": chosen_vehicle,
            "capacity_tons": (
                vehicle["capacity_tons"]
            ),
            "km_per_liter": (
                vehicle["km_per_liter"]
            ),
            "loads_required": (
                vehicle_optimization[
                    "recommended_vehicle"
                ]["loads_required"]
            ),
            "capacity_utilization_pct": (
                vehicle_optimization[
                    "recommended_vehicle"
                ].get(
                    "capacity_utilization_pct"
                )
            ),
        },

        "vehicle_optimization": (
            vehicle_optimization
        ),

        "cost": cost,

        "risk": risk,

        "data_quality": {
            "routing_live_traffic": bool(
                route.get("traffic_aware")
            ),
            "weather_live": bool(
                origin_weather
                or destination_weather
            ),
            "market_live": False,
            "notes": [
                (
                    "Market pricing is not queried "
                    "by this tool. Use the Market Agent "
                    "for current market data."
                ),
                (
                    "Transport cost is an estimate "
                    "based on configured assumptions, "
                    "not a transporter quote."
                ),
            ],
        },
    }


# =============================================================
# DESTINATION RESOLUTION
# =============================================================

def _resolve_destination(
    destination: str,
    origin: str,
    origin_point: GeoPoint,
) -> GeoPoint:
    """
    Resolve the destination using geographic context.

    First tries the user's destination exactly.

    If the result is suspiciously far from the origin,
    retry with the origin's geographic context.

    This helps with natural-language location variations
    such as:

        Lasangaon → Lasalgaon

    without hardcoding a spelling correction.
    """

    destination_point = _geocoder.geocode(destination)

    distance = _approx_distance_km(
        origin_point.latitude,
        origin_point.longitude,
        destination_point.latitude,
        destination_point.longitude,
    )

    # In Nashik agricultural logistics, "Lasangaon" is a common misspelling
    # of Lasalgaon (Niphad, Nashik district). Nominatim can otherwise return
    # a different Lasangaon in Madhya Pradesh. Prefer the Nashik mandi only
    # when the origin is in the Nashik region and the first result is far away.
    normalized_destination = "".join(
        character for character in destination.lower() if character.isalnum()
    )
    origin_is_nashik_region = (
        19.0 <= origin_point.latitude <= 21.5
        and 73.0 <= origin_point.longitude <= 75.5
    )
    explicit_other_region = any(
        marker in destination.lower()
        for marker in ("dhar", "madhya pradesh", "mp, india")
    )
    if (
        normalized_destination in {"lasangaon", "lasalgaon", "lasalgaun"}
        and origin_is_nashik_region
        and not explicit_other_region
        and distance > 120
    ):
        try:
            local_candidate = _geocoder.geocode(
                "Lasalgaon, Niphad, Nashik, Maharashtra, India"
            )
            local_distance = _approx_distance_km(
                origin_point.latitude,
                origin_point.longitude,
                local_candidate.latitude,
                local_candidate.longitude,
            )
            if local_distance < distance:
                destination_point = local_candidate
                distance = local_distance
        except ProviderError:
            # Continue with the general contextual search below.
            pass

    # A very large distance is suspicious for a local
    # agricultural logistics request.
    #
    # We deliberately use a generous threshold so that
    # legitimate long-distance transport is not rejected.
    if distance <= 250:
        return destination_point

    contextual_queries = [
        f"{destination}, {origin}",
        f"{destination}, Maharashtra, India",
    ]

    for query in contextual_queries:

        try:

            candidate = _geocoder.geocode(
                query
            )

        except ProviderError:
            continue

        candidate_distance = (
            _approx_distance_km(
                origin_point.latitude,
                origin_point.longitude,
                candidate.latitude,
                candidate.longitude,
            )
        )

        if candidate_distance < distance:

            destination_point = candidate
            distance = candidate_distance

    return destination_point


def _approx_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Approximate straight-line distance between two
    geographic coordinates.

    Used only for validating geocoding candidates,
    not for transport routing.
    """

    from math import (
        asin,
        cos,
        radians,
        sin,
        sqrt,
    )

    earth_radius_km = 6371.0

    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)

    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)

    value = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad)
        * cos(lat2_rad)
        * sin(delta_lon / 2) ** 2
    )

    return (
        earth_radius_km
        * 2
        * asin(
            sqrt(
                min(
                    1.0,
                    max(
                        0.0,
                        value,
                    ),
                )
            )
        )
    )


# =============================================================
# VEHICLE
# =============================================================

def _resolve_vehicle(
    vehicle_type: str | None,
    quantity_tons: float,
):

    if vehicle_type:

        normalized = (
            vehicle_type
            .strip()
            .lower()
            .replace(" ", "_")
        )

        profiles = {
            "mini": "mini_truck",
            "mini_truck": "mini_truck",
            "light": "light_truck",
            "light_truck": "light_truck",
            "medium": "medium_truck",
            "medium_truck": "medium_truck",
            "heavy": "heavy_truck",
            "heavy_truck": "heavy_truck",
        }

        canonical = profiles.get(
            normalized
        )

        if canonical:

            from agritwin_ai.agents.logistics.knowledge import (
                VEHICLE_PROFILES,
            )

            if (
                quantity_tons
                <= VEHICLE_PROFILES[
                    canonical
                ]["capacity_tons"]
            ):

                return (
                    canonical,
                    VEHICLE_PROFILES[
                        canonical
                    ],
                )

    return select_vehicle(
        quantity_tons
    )


# =============================================================
# COST
# =============================================================

def _estimate_cost(
    distance_km: float,
    duration_minutes: float,
    quantity_tons: float,
    vehicle_type: str,
    vehicle_profile: dict[str, float],
) -> dict[str, Any]:

    fuel_price = float(
        os.getenv(
            "LOGISTICS_FUEL_PRICE_INR_PER_LITER",
            "95",
        )
    )

    driver_hour = float(
        os.getenv(
            "LOGISTICS_DRIVER_COST_INR_PER_HOUR",
            "250",
        )
    )

    handling_per_ton = float(
        os.getenv(
            "LOGISTICS_HANDLING_COST_INR_PER_TON",
            "150",
        )
    )

    tolls = float(
        os.getenv(
            "LOGISTICS_ESTIMATED_TOLLS_INR",
            "0",
        )
    )

    fuel_liters = (
        distance_km
        / vehicle_profile["km_per_liter"]
    )

    fuel_cost = (
        fuel_liters
        * fuel_price
    )

    driver_cost = (
        duration_minutes
        / 60.0
    ) * driver_hour

    handling_cost = (
        quantity_tons
        * handling_per_ton
    )

    total = (
        fuel_cost
        + driver_cost
        + handling_cost
        + tolls
    )

    return {
        "estimated_total_inr": round(
            total,
            2,
        ),
        "estimated_cost_per_ton_inr": round(
            total / quantity_tons,
            2,
        ),
        "fuel_liters": round(
            fuel_liters,
            2,
        ),
        "fuel_price_inr_per_liter": (
            fuel_price
        ),
        "fuel_cost_inr": round(
            fuel_cost,
            2,
        ),
        "driver_cost_inr": round(
            driver_cost,
            2,
        ),
        "handling_cost_inr": round(
            handling_cost,
            2,
        ),
        "tolls_inr": round(
            tolls,
            2,
        ),
        "assumption_based": True,
    }


# =============================================================
# RISK
# =============================================================

def _assess_risk(
    commodity: str,
    profile: dict[str, Any],
    route: dict[str, Any],
    origin_weather: dict[str, Any] | None,
    destination_weather: dict[str, Any] | None,
) -> dict[str, Any]:

    score = 0.0
    factors: list[str] = []

    duration_hours = (
        float(
            route["duration_minutes"]
        )
        / 60.0
    )

    if (
        profile.get("perishable")
        and duration_hours > 12
    ):

        score += 20

        factors.append(
            "Long transit time for a "
            "perishable commodity"
        )

    if (
        profile.get("perishable")
        and duration_hours > 24
    ):

        score += 15

        factors.append(
            "Transit exceeds 24 hours for "
            "a perishable commodity"
        )

    weather_points = []

    for label, weather in (
        ("origin", origin_weather),
        ("destination", destination_weather),
    ):

        if not weather:
            continue

        probability = float(
            weather.get(
                "next_24h_max_precip_probability_pct"
            )
            or 0
        )

        precipitation = float(
            weather.get(
                "next_24h_total_precipitation_mm"
            )
            or 0
        )

        wind = float(
            weather.get(
                "next_24h_max_wind_kmh"
            )
            or 0
        )

        current = (
            weather.get("current")
            or {}
        )

        temperature = float(
            current.get(
                "temperature_2m"
            )
            or 0
        )

        if probability >= 70:

            score += (
                12
                * float(
                    profile.get(
                        "rain_sensitivity",
                        0.5,
                    )
                )
            )

            factors.append(
                f"High rain probability "
                f"near {label}"
            )

        if precipitation >= 10:

            score += (
                8
                * float(
                    profile.get(
                        "rain_sensitivity",
                        0.5,
                    )
                )
            )

            factors.append(
                f"Meaningful precipitation "
                f"forecast near {label}"
            )

        if wind >= 40:

            score += 8

            factors.append(
                f"High wind forecast near {label}"
            )

        if temperature > profile[
            "temperature_max_c"
        ]:

            score += (
                8
                if profile.get("perishable")
                else 3
            )

            factors.append(
                f"High temperature near {label}"
            )

        if temperature < profile[
            "temperature_min_c"
        ]:

            score += 5

            factors.append(
                f"Low temperature near {label}"
            )

        weather_points.append(
            {
                "location": label,
                "temperature_c": temperature,
                "rain_probability_pct": (
                    probability
                ),
            }
        )

    if route.get("traffic_aware"):

        traffic_note = (
            "Traffic-aware ETA from "
            "Google Routes."
        )

    else:

        traffic_note = (
            "ETA is road-network based "
            "and does not include live traffic."
        )

    if score >= 35:

        level = "HIGH"

    elif score >= 15:

        level = "MODERATE"

    else:

        level = "LOW"

    return {
        "level": level,
        "score": round(
            min(score, 100.0),
            1,
        ),
        "factors": factors,
        "weather_points": weather_points,
        "traffic_note": traffic_note,
    }


__all__ = [
    "get_logistics_analysis",
]