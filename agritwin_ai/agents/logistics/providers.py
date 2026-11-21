from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests


class ProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class GeoPoint:
    query: str
    latitude: float
    longitude: float
    display_name: str


class NominatimGeocoder:
    """OpenStreetMap Nominatim geocoder with a polite request interval."""

    BASE_URL = "https://nominatim.openstreetmap.org/search"
    _last_request = 0.0

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": os.getenv(
                "LOGISTICS_USER_AGENT",
                "AgriTwin/1.0 (agricultural logistics research application)",
            ),
            "Accept": "application/json",
        })

    def geocode(self, query: str) -> GeoPoint:
        if not query or not query.strip():
            raise ProviderError("Location is required for geocoding.")

        # Public Nominatim services request responsible usage. Do not hammer the
        # endpoint from a chat loop. A real deployment should use a hosted/local
        # geocoder for high volume.
        elapsed = time.monotonic() - self._last_request
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)

        try:
            response = self.session.get(
                self.BASE_URL,
                params={
                    "q": query.strip(),
                    "format": "jsonv2",
                    "limit": 1,
                    "countrycodes": "in",
                    "addressdetails": 1,
                },
                timeout=self.timeout,
            )
            self._last_request = time.monotonic()
            response.raise_for_status()
            rows = response.json()
        except requests.RequestException as exc:
            raise ProviderError(f"Geocoding service failed: {exc}") from exc

        if not rows:
            raise ProviderError(f"Could not find location: {query}")

        row = rows[0]
        return GeoPoint(
            query=query,
            latitude=float(row["lat"]),
            longitude=float(row["lon"]),
            display_name=row.get("display_name", query),
        )


class OSRMRouter:
    """Road routing fallback using the public OSRM HTTP API."""

    BASE_URL = "https://router.project-osrm.org/route/v1/driving"

    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "AgriTwin/1.0"})

    def route(self, origin: GeoPoint, destination: GeoPoint) -> dict[str, Any]:
        coordinates = (
            f"{origin.longitude},{origin.latitude};"
            f"{destination.longitude},{destination.latitude}"
        )
        try:
            response = self.session.get(
                f"{self.BASE_URL}/{coordinates}",
                params={
                    "alternatives": "true",
                    "overview": "false",
                    "steps": "false",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise ProviderError(f"Routing service failed: {exc}") from exc

        if payload.get("code") != "Ok" or not payload.get("routes"):
            raise ProviderError(payload.get("message", "No road route found."))

        routes = []
        for index, route in enumerate(payload["routes"], start=1):
            routes.append({
                "route_index": index,
                "distance_km": round(float(route["distance"]) / 1000.0, 2),
                "duration_minutes": round(float(route["duration"]) / 60.0, 1),
                "provider": "OSRM",
                "traffic_aware": False,
            })

        return {
            "provider": "OSRM",
            "traffic_aware": False,
            "alternatives_available": len(routes) > 1,
            "routes": routes,
            "source": "OpenStreetMap road data via OSRM",
        }


class GoogleRoutesProvider:
    """Optional traffic-aware routing provider when GOOGLE_MAPS_API_KEY exists."""

    BASE_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

    def __init__(self, api_key: str | None = None, timeout: float = 15.0) -> None:
        self.api_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY")
        self.timeout = timeout
        self.session = requests.Session()

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def route(self, origin: GeoPoint, destination: GeoPoint) -> dict[str, Any]:
        if not self.api_key:
            raise ProviderError("GOOGLE_MAPS_API_KEY is not configured.")

        body = {
            "origin": {"location": {"latLng": {
                "latitude": origin.latitude,
                "longitude": origin.longitude,
            }}},
            "destination": {"location": {"latLng": {
                "latitude": destination.latitude,
                "longitude": destination.longitude,
            }}},
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE",
            "computeAlternativeRoutes": True,
            "units": "METRIC",
        }
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "routes.distanceMeters,routes.duration,routes.staticDuration,"
                "routes.description"
            ),
        }

        try:
            response = self.session.post(
                self.BASE_URL,
                json=body,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise ProviderError(f"Google Routes service failed: {exc}") from exc

        if not payload.get("routes"):
            raise ProviderError("Google Routes returned no routes.")

        routes = []
        for index, route in enumerate(payload["routes"], start=1):
            duration = _parse_google_duration(route.get("duration"))
            static_duration = _parse_google_duration(route.get("staticDuration"))
            routes.append({
                "route_index": index,
                "distance_km": round(float(route["distanceMeters"]) / 1000.0, 2),
                "duration_minutes": round(duration / 60.0, 1),
                "static_duration_minutes": round(static_duration / 60.0, 1) if static_duration else None,
                "provider": "Google Routes",
                "traffic_aware": True,
                "description": route.get("description"),
            })

        return {
            "provider": "Google Routes",
            "traffic_aware": True,
            "alternatives_available": len(routes) > 1,
            "routes": routes,
            "source": "Google Routes API",
        }


def _parse_google_duration(value: Any) -> float:
    if not value:
        return 0.0
    if isinstance(value, str) and value.endswith("s"):
        return float(value[:-1])
    if isinstance(value, dict) and "seconds" in value:
        return float(value["seconds"])
    return 0.0


class OpenMeteoWeatherProvider:
    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "AgriTwin/1.0"})

    def forecast(self, point: GeoPoint, forecast_days: int = 2) -> dict[str, Any]:
        forecast_days = max(1, min(int(forecast_days), 7))
        params = {
            "latitude": point.latitude,
            "longitude": point.longitude,
            "current": (
                "temperature_2m,relative_humidity_2m,precipitation,"
                "wind_speed_10m,weather_code"
            ),
            "hourly": (
                "temperature_2m,relative_humidity_2m,precipitation_probability,"
                "precipitation,wind_speed_10m,weather_code"
            ),
            "forecast_days": forecast_days,
            "timezone": "auto",
        }
        try:
            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise ProviderError(f"Weather service failed: {exc}") from exc

        current = payload.get("current", {})
        hourly = payload.get("hourly", {})
        probabilities = hourly.get("precipitation_probability", []) or []
        precipitation = hourly.get("precipitation", []) or []
        wind = hourly.get("wind_speed_10m", []) or []

        return {
            "provider": "Open-Meteo",
            "location": point.display_name,
            "latitude": point.latitude,
            "longitude": point.longitude,
            "timezone": payload.get("timezone"),
            "current": current,
            "next_24h_max_precip_probability_pct": max(probabilities[:24], default=0),
            "next_24h_total_precipitation_mm": round(sum(precipitation[:24]), 2),
            "next_24h_max_wind_kmh": round(max(wind[:24], default=0), 1),
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        }
