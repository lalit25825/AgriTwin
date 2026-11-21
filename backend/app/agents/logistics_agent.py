from urllib.parse import quote_plus
import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict
from backend.app.agents.schemas import AgentRunRequest


class _MapsSettings(BaseSettings):
    google_maps_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


async def run(request: AgentRunRequest) -> dict:
    origin = request.origin or request.location
    destination = request.destination
    if not origin or not destination:
        return {
            "id": "logistics", "name": "Logistics Agent", "status": "needs_input",
            "headline": "Route endpoints required",
            "summary": "Provide a dispatch origin and delivery destination to build a route.",
            "data": {}, "actions": ["Enter pickup and destination locations"],
            "source": "Google Maps directions link", "live": False,
        }

    maps_url = (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={quote_plus(origin)}&destination={quote_plus(destination)}&travelmode=driving"
    )
    details = {"origin": origin, "destination": destination, "maps_url": maps_url}
    settings = _MapsSettings()
    if settings.google_maps_api_key:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://maps.googleapis.com/maps/api/directions/json",
                    params={"origin": origin, "destination": destination, "mode": "driving", "key": settings.google_maps_api_key},
                )
                response.raise_for_status()
                payload = response.json()
            routes = payload.get("routes") or []
            if payload.get("status") == "OK" and routes:
                leg = routes[0].get("legs", [{}])[0]
                details.update({
                    "distance": (leg.get("distance") or {}).get("text"),
                    "duration": (leg.get("duration") or {}).get("text"),
                    "start_address": leg.get("start_address"),
                    "end_address": leg.get("end_address"),
                })
                summary = "Google Maps returned a driving route. Open the map to inspect the route and traffic-aware options."
                live = True
            else:
                summary = "A Google Maps route link is ready; route metrics were not returned by the Directions API."
                live = False
        except httpx.HTTPError:
            summary = "A Google Maps route link is ready. Live route metrics could not be retrieved."
            live = False
    else:
        summary = "A Google Maps directions link is ready. Add GOOGLE_MAPS_API_KEY to retrieve route distance and duration inside AgriTwin."
        live = False

    return {
        "id": "logistics", "name": "Logistics Agent", "status": "completed",
        "headline": "Route prepared", "summary": summary,
        "data": details, "actions": ["Open the route in Google Maps", "Confirm vehicle capacity and delivery time"],
        "source": "Google Maps Directions API / Maps URL", "live": live,
    }
