from agritwin_ai.agents.harvest.tools import (
    get_weather,
    get_weather_forecast,
    get_crop_info
)

TOOLS = {

    "get_weather": {

        "function": get_weather,

        "description": "Get the current weather of a city.",

        "arguments": {
            "city": str
        }

    },

    "get_weather_forecast": {

        "function": get_weather_forecast,

        "description": "Get weather forecast for the next few days.",

        "arguments": {

            "city": str,

            "days": int

        }

    },

    "get_crop_info": {

        "function": get_crop_info,

        "description": "Get harvesting knowledge about a crop.",

        "arguments": {
            "crop": str
        }

    }

}


TOOL_SCHEMA = [

    {

        "name": "get_weather",

        "description": "Get the current weather of a city.",

        "parameters": {
            "city": "string"
        }

    },

    {

        "name": "get_weather_forecast",

        "description": "Get weather forecast for the next few days.",

        "parameters": {

            "city": "string",

            "days": "integer"

        }

    },

    {

        "name": "get_crop_info",

        "description": "Retrieve agricultural knowledge for a crop.",

        "parameters": {
            "crop": "string"
        }

    }

]
