import asyncio
import uuid
from datetime import datetime, timezone
from backend.app.agents import climate_agent, equity_agent, harvesting_agent, logistics_agent, market_agent, storage_agent
from backend.app.agents.schemas import AgentRunRequest


AGENTS = [
    {"id": "harvesting", "name": "Harvesting Agent", "description": "Crop-stage readiness and harvest preparation", "capability": "Field stage assessment"},
    {"id": "climate", "name": "Climate Agent", "description": "Current conditions and short-range weather risk", "capability": "Open-Meteo live forecast"},
    {"id": "logistics", "name": "Logistics Agent", "description": "Pickup-to-destination route planning", "capability": "Google Maps directions"},
    {"id": "storage", "name": "Storage Agent", "description": "Post-harvest handling and storage guidance", "capability": "Crop-specific storage checklist"},
    {"id": "market", "name": "Market Agent", "description": "Mandi arrivals, modal prices, and indicative trend projection", "capability": "data.gov.in / Agmarknet"},
    {"id": "equity", "name": "Equity Agent", "description": "Farmer-side net realisation and price transparency", "capability": "Price and cost comparison"},
]


def get_agent_status() -> list[dict]:
    from backend.app.agents.logistics_agent import _MapsSettings
    from backend.app.agents.market_agent import _MarketSettings
    maps = _MapsSettings()
    market = _MarketSettings()
    market_ready = bool(market.data_gov_in_api_key and market.agmarknet_resource_id)
    return [
        {**AGENTS[0], "status": "ready"},
        {**AGENTS[1], "status": "ready", "provider": "Open-Meteo (coordinates required)"},
        {**AGENTS[2], "status": "ready", "provider": "Directions link" if not maps.google_maps_api_key else "Directions API + Maps"},
        {**AGENTS[3], "status": "ready"},
        {**AGENTS[4], "status": "ready" if market_ready else "needs_configuration", "provider": "data.gov.in" if market_ready else "Set API key and resource ID"},
        {**AGENTS[5], "status": "ready"},
    ]


async def run_agent_team(request: AgentRunRequest) -> dict:
    climate_task = climate_agent.run(request)
    logistics_task = logistics_agent.run(request)
    market_task = market_agent.run(request)
    climate, logistics, market = await asyncio.gather(climate_task, logistics_task, market_task)
    harvesting = harvesting_agent.run(request)
    storage = storage_agent.run(request)
    equity = equity_agent.run(request, market)
    results = [harvesting, climate, logistics, storage, market, equity]
    completed = sum(1 for item in results if item.get("status") == "completed")
    live = sum(1 for item in results if item.get("live"))
    return {
        "run_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "agents_total": len(results),
            "agents_completed": completed,
            "live_sources": live,
            "attention_required": sum(1 for item in results if item.get("status") in {"needs_input", "configuration_required", "unavailable", "no_data"}),
        },
        "agents": results,
    }
