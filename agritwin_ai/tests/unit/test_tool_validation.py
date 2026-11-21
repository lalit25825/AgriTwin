from agritwin_ai.understanding.validator import validate_tool
from agritwin_ai.agents.harvest.tool_schema import TOOLS


def test_tool_validation_rejects_missing_or_wrong_typed_arguments() -> None:
    assert validate_tool("get_weather", {}, TOOLS)[0] is False
    assert validate_tool("get_weather_forecast", {"city": "Nashik", "days": "5"}, TOOLS)[0] is False


def test_tool_validation_accepts_registered_schema() -> None:
    assert validate_tool("get_weather_forecast", {"city": "Nashik", "days": 5}, TOOLS) == (True, None)
