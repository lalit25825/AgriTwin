from agritwin_ai.agents.logistics.tools import (
    get_logistics_analysis,
)


TOOLS = {
    "get_logistics_analysis": {
        "function": get_logistics_analysis,
        "description": (
            "Collect live geocoding, road routing, "
            "optional traffic-aware ETA, weather, "
            "vehicle, transport cost and agricultural "
            "logistics risk data."
        ),
        "arguments": {
            "commodity": str,
            "quantity_tons": float,
            "origin": str,
            "destination": str,
            "market": str,
            "vehicle_type": str,
        },
        "required": {
            "commodity",
            "quantity_tons",
            "origin",
            "destination",
        },
    }
}