from agritwin_ai.routing.router import AgentRouter
from agritwin_ai.understanding.schema import UnderstandingResult


router = AgentRouter()


tests = [

    "harvest_decision",

    "market_price",

    "disease_detection",

    "weather_forecast",

    "unknown"

]


for intent in tests:

    result = UnderstandingResult(

        intent=intent,

        entities={},

        missing=[],

        updates={},

        confidence=1.0

    )

    print(

        intent,

        "->",

        router.route(result)

    )