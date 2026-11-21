"""Backward-compatible harvest evaluator facade."""

from datetime import datetime, timedelta
from typing import Any

from agritwin_ai.decision.forecast import find_best_harvest_day
from agritwin_ai.decision.harvest import evaluate_harvest


class HarvestEvaluator:
    """Evaluate a ready workflow using its available weather data.

    New runtime code should use :class:`DecisionManager`, which selects the
    evaluator from intent and rejects tool failures.
    """

    def _days_needed_from_date_string(self, date_str: str) -> int:
        """
        Return number of days from today to the target date.
        Negative if target date is in the past.
        """
        if not date_str or not isinstance(date_str, str):
            return -2  # sentinel for invalid

        date_str_clean = date_str.strip().lower().replace("_", " ")
        if date_str_clean in {"day-after-tomorrow", "day after tomorrow"}:
            date_str_clean = "day after tomorrow"
        current_date = datetime.now().date()

        # Relative dates
        if date_str_clean == "today":
            return 0
        if date_str_clean == "tomorrow":
            return 1
        if date_str_clean == "day after tomorrow":
            return 2
        if date_str_clean == "yesterday":
            return -1

        # Try to parse as "DD month" or "DD Month"
        try:
            parts = date_str_clean.split()
            if len(parts) == 2:
                day_str, month_str = parts
                day = int(day_str)
                month_map = {
                    'january': 1, 'jan': 1,
                    'february': 2, 'feb': 2,
                    'march': 3, 'mar': 3,
                    'april': 4, 'apr': 4,
                    'may': 5,
                    'june': 6, 'jun': 6,
                    'july': 7, 'jul': 7,
                    'august': 8, 'aug': 8,
                    'september': 9, 'sep': 9, 'sept': 9,
                    'october': 10, 'oct': 10,
                    'november': 11, 'nov': 11,
                    'december': 12, 'dec': 12
                }
                month = month_map.get(month_str.lower())
                if month and 1 <= day <= 31:
                    # Assume current year if not specified
                    target_date = datetime(current_date.year, month, day).date()
                    return (target_date - current_date).days
                # Handle formats like "25-aug", "25-august"
                elif len(parts) == 1 and '-' in parts[0]:
                    day_str, month_str = parts[0].split('-', 1)
                    day = int(day_str)
                    month_map = {
                        'january': 1, 'jan': 1,
                        'february': 2, 'feb': 2,
                        'march': 3, 'mar': 3,
                        'april': 4, 'apr': 4,
                        'may': 5,
                        'june': 6, 'jun': 6,
                        'july': 7, 'jul': 7,
                        'august': 8, 'aug': 8,
                        'september': 9, 'sep': 9, 'sept': 9,
                        'october': 10, 'oct': 10,
                        'november': 11, 'nov': 11,
                        'december': 12, 'dec': 12
                    }
                    month = month_map.get(month_str.lower())
                    if month and 1 <= day <= 31:
                        target_date = datetime(current_date.year, month, day).date()
                        return (target_date - current_date).days
        except (ValueError, IndexError):
            pass

        # Try to parse as YYYY-MM-DD
        try:
            if len(date_str_clean) == 10 and date_str_clean.count('-') == 2:
                year, month, day = map(int, date_str_clean.split('-'))
                target_date = datetime(year, month, day).date()
                return (target_date - current_date).days
        except ValueError:
            pass

        # If we cannot parse, treat as invalid (will fallback to default behavior)
        return -2

    def evaluate(self, workflow: Any, intent: str) -> dict[str, Any]:
        # If we have weather data available, use current weather mode
        if workflow.state.weather is not None:
            return evaluate_harvest(
                workflow.state.weather,
                workflow.state.crop_info
            )

        # For harvest_decision with a specific date, select that day's forecast
        if intent == "harvest_decision" and workflow.state.date is not None and workflow.state.forecast is not None:
            days_needed = self._days_needed_from_date_string(workflow.state.date)
            forecast_list = workflow.state.forecast.get("forecast")
            if isinstance(forecast_list, list) and days_needed >= 0 and days_needed < len(forecast_list):
                # Evaluate exactly the requested forecast day using the same
                # minimum/maximum-temperature average rule as forecast mode.
                # The previous code used temperature_max as a proxy, which
                # disagreed with the forecast scorer and could also miss dates
                # such as "day_after_tomorrow" because of underscore tokens.
                day_entry = forecast_list[days_needed]
                required_fields = (
                    "temperature_min",
                    "temperature_max",
                    "humidity",
                    "rain_probability",
                )
                if all(day_entry.get(field) is not None for field in required_fields):
                    decision = find_best_harvest_day(
                        [day_entry],
                        workflow.state.crop_info,
                    )
                    decision["requested_date"] = day_entry.get("date")
                    decision["evaluation_scope"] = "requested_date_only"
                    return decision

        # Otherwise, if we have forecast data available, use forecast mode
        if workflow.state.forecast is not None:
            return find_best_harvest_day(
                workflow.state.forecast["forecast"],
                workflow.state.crop_info
            )

        # If neither is available, return a safe default (should not happen if ready_for_evaluation passed)
        return evaluate_harvest(
            None,
            workflow.state.crop_info
        )
