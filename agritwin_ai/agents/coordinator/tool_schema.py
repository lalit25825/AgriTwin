from agritwin_ai.agents.coordinator.tools import (
    run_harvest,
    run_climate,
    run_market,
    run_logistics,
)


TOOLS = {

    "run_harvest": {

        "function": run_harvest,

        "description": "Run Harvest Agent.",

        "arguments": {
            "user_message": str
        },

    },

    "run_climate": {

        "function": run_climate,

        "description": "Run Climate Agent.",

        "arguments": {
            "user_message": str
        },

    },

    "run_market": {

        "function": run_market,

        "description": (
            "Run Market Agent to forecast agricultural "
            "prices and recommend SELL, HOLD, STORE, "
            "or REDIRECT."
        ),

        "arguments": {
            "user_message": str
        },

    },

    "run_logistics": {

        "function": run_logistics,

        "description": (
            "Run Logistics Agent to analyze agricultural "
            "transport routes, travel time, weather, "
            "vehicle requirements, transport cost, and "
            "logistics risk."
        ),

        "arguments": {
            "user_message": str
        },

    },
}


TOOL_SCHEMA = [

    {

        "name": "run_harvest",

        "description": "Execute Harvest Agent.",

        "parameters": {
            "user_message": "string"
        },

    },

    {

        "name": "run_climate",

        "description": "Execute Climate Agent.",

        "parameters": {
            "user_message": "string"
        },

    },

    {

        "name": "run_market",

        "description": (
            "Execute Market Agent for agricultural "
            "price forecasting and market decisions."
        ),

        "parameters": {
            "user_message": "string"
        },

    },

    {

        "name": "run_logistics",

        "description": (
            "Execute Logistics Agent for agricultural "
            "transport planning, routing, cost estimation, "
            "weather, vehicle selection, and logistics risk."
        ),

        "parameters": {
            "user_message": "string"
        },

    },

]