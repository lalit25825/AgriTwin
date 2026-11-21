from agritwin_ai.agents.climate.tools import (
    get_weather,
    get_weather_forecast
)


TOOLS = {

    "get_weather": {

        "function": get_weather,

        "description": "Get current weather of a city.",

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

        "description": "Get weather forecast for multiple days.",

        "parameters": {

            "city": "string",

            "days": "integer"

        }

    }

]