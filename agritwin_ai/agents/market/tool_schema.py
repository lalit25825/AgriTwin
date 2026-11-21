from __future__ import annotations

from agritwin_ai.agents.market.tools import (
    get_market_analysis,
    get_market_price,
)


TOOLS = {

    "get_market_price": {

        "function": get_market_price,

        "description": (
            "Get source-stamped modal wholesale prices for a commodity in a "
            "city, district, state or mandi. Resolves nearby mandis if the "
            "requested district has no matching crop observations. Prices are INR per quintal."
        ),

        "arguments": {
            "commodity": str,
            "market": str,
        },

    },

    "get_market_analysis": {

        "function": get_market_analysis,

        "description": (
            "Run regional mandi intelligence including source-stamped prices, "
            "nearby mandi comparison, walk-forward backtested price forecast, "
            "risk context and a conservative market decision."
        ),

        "arguments": {
            "commodity": str,
            "market": str,
            "horizon": int,
            "storage_available": bool,
            "nearby_market_advantage_pct": float,
            "nearby_market_price": float,
            "transport_cost": float,
            "storage_cost": float,
            "expected_spoilage_pct": float,
        },
        # The economic inputs are optional. A forecast needs only a
        # commodity and market; profit comparisons can add these later.
        "required": {"commodity", "market"},
    },

}


TOOL_SCHEMA = [

    {

        "name": "get_market_price",

        "description": (
            "Get the current market price of a commodity."
        ),

        "parameters": {

            "commodity": "string",

            "market": "string",

        },

    },

    {

        "name": "get_market_analysis",

        "description": (
            "Run market forecast, risk, economics, "
            "and deterministic market decision."
        ),

        "parameters": {
            "commodity": "string",
            "market": "string",
            "horizon": "integer (optional; defaults to 7)",
            "storage_available": "boolean (optional; defaults to false)",
            "nearby_market_advantage_pct": "number (optional; defaults to 0)",
            "nearby_market_price": "number (optional)",
            "transport_cost": "number (optional; defaults to 0)",
            "storage_cost": "number (optional; defaults to 0)",
            "expected_spoilage_pct": "number (optional; defaults to 0)",
        },
        "required": ["commodity", "market"],
    },

]