from agritwin_ai.agents.climate.state import ClimateState
from agritwin_ai.agents.climate.reflection import ClimateReflection


class ClimateWorkflow:

    def __init__(self):
        self.state = ClimateState()
        self.reflection = ClimateReflection()

    def load_memory(self, memory):
        if "city" in memory:
            item = memory["city"]
            self.state.city = item.value if hasattr(item, 'value') else item
        if "quantity" in memory:
            item = memory["quantity"]
            self.state.quantity = item.value if hasattr(item, 'value') else item

    def needs_information(self, intent):
        missing = []
        climate_intents = [
            "climate_summary",
            "weather_current",
            "weather_forecast",
            "rainfall_forecast",
            "temperature_forecast",
            "humidity_forecast",
            "wind_forecast",
            "extreme_weather_alert",
            "heatwave_warning",
            "coldwave_warning",
            "irrigation_weather",
            "harvest_weather_window",
        ]
        if intent in climate_intents:
            if not self.state.city:
                missing.append("city")
        return missing

    def set_current_weather(self, weather):
        self.state.current_weather = weather
        self.state.weather = weather

    def set_forecast(self, forecast):
        self.state.forecast = forecast

    def set_alerts(self, alerts):
        self.state.alerts = alerts

    def set_decision(self, decision):
        self.state.decision = decision

    def handle_tool_result(self, action, result):
        if action == "get_weather":
            self.set_current_weather(result)
        elif action == "get_weather_forecast":
            self.set_forecast(result)

    def requires_decision(self, intent):
        return intent in {
            "climate_summary",
            "irrigation_weather",
            "harvest_weather_window",
        }

    def ready_for_evaluation(self):
        observations = (self.state.current_weather, self.state.forecast)
        return (
            any(item is not None for item in observations)
            and not any(isinstance(item, dict) and "error" in item for item in observations)
        )

    def complete(self):
        self.state.completed = True

    def reflect(self, intent):
        return self.reflection.check(
            self,
            intent
        )