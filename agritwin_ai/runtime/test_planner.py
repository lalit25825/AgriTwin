"""Unit tests for the Planner class."""

import unittest
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch

from agritwin_ai.understanding.schema import UnderstandingResult
from agritwin_ai.runtime.planner import Planner, Plan, ToolAction


class TestPlanner(unittest.TestCase):
    """Test cases for the Planner class."""

    def setUp(self):
        """Set up test fixtures."""
        self.planner = Planner()
        # Fix the current date for consistent testing
        self.planner._current_date = date(2026, 8, 26)

    def create_understanding(self, intent, entities):
        """Create an UnderstandingResult mock for testing."""
        # We'll create a simple object that mimics UnderstandingResult
        # Since we don't want to depend on the exact structure, we'll use a mock
        understanding = Mock(spec=UnderstandingResult)
        understanding.intent = intent
        understanding.entities = entities
        return understanding

    def test_five_day_forecast(self):
        """Test 5 day forecast request."""
        understanding = self.create_understanding(
            "weather_forecast",
            {"city": {"value": "Nashik"}, "quantity": {"value": 5}}
        )
        workflow = Mock()
        workflow.reflect.return_value = {"ready": True}
        working_memory = {}

        plan = self.planner.plan(understanding, workflow, working_memory)

        # Assert exactly one action
        self.assertEqual(len(plan.actions), 1)
        action = plan.actions[0]
        # Assert action name is get_weather_forecast
        self.assertEqual(action.name, "get_weather_forecast")
        # Assert arguments
        self.assertEqual(action.arguments, {"city": "Nashik", "days": 5})
        # Assert "forecast" is NOT present in arguments
        self.assertNotIn("forecast", action.arguments)
        # Assert days == 5
        self.assertEqual(action.arguments["days"], 5)

    def test_tomorrow(self):
        """Test tomorrow forecast request."""
        understanding = self.create_understanding(
            "weather_forecast",
            {"city": {"value": "Nashik"}, "date": {"value": "tomorrow"}}
        )
        workflow = Mock()
        workflow.reflect.return_value = {"ready": True}
        working_memory = {}

        plan = self.planner.plan(understanding, workflow, working_memory)

        self.assertEqual(len(plan.actions), 1)
        action = plan.actions[0]
        self.assertEqual(action.name, "get_weather_forecast")
        self.assertEqual(action.arguments, {"city": "Nashik", "days": 2})
        # Assert target date is 2026-08-27 (today + 1 day)
        # The planner returns days=2, which means forecast for today and tomorrow
        self.assertEqual(action.arguments["days"], 2)

    def test_day_after_tomorrow(self):
        """Test day after tomorrow forecast request."""
        understanding = self.create_understanding(
            "weather_forecast",
            {"city": {"value": "Nashik"}, "date": {"value": "day after tomorrow"}}
        )
        workflow = Mock()
        workflow.reflect.return_value = {"ready": True}
        working_memory = {}

        plan = self.planner.plan(understanding, workflow, working_memory)

        self.assertEqual(len(plan.actions), 1)
        action = plan.actions[0]
        self.assertEqual(action.name, "get_weather_forecast")
        self.assertEqual(action.arguments, {"city": "Nashik", "days": 3})
        # Assert target date is 2026-08-28 (today + 2 days)
        self.assertEqual(action.arguments["days"], 3)

    def test_harvest_today(self):
        """Test harvest decision for today."""
        understanding = self.create_understanding(
            "harvest_decision",
            {"crop": {"value": "onion"}, "city": {"value": "Nashik"}, "date": {"value": "2026-08-26"}}
        )
        workflow = Mock()
        workflow.reflect.return_value = {"ready": True}
        working_memory = {}

        plan = self.planner.plan(understanding, workflow, working_memory)

        # Should have two actions: get_crop_info and get_weather
        self.assertEqual(len(plan.actions), 2)
        # Check get_crop_info action
        crop_action = next((a for a in plan.actions if a.name == "get_crop_info"), None)
        self.assertIsNotNone(crop_action)
        self.assertEqual(crop_action.arguments, {"crop": "onion"})
        # Check get_weather action
        weather_action = next((a for a in plan.actions if a.name == "get_weather"), None)
        self.assertIsNotNone(weather_action)
        self.assertEqual(weather_action.arguments, {"city": "Nashik"})
        # Do NOT call get_weather_forecast
        forecast_actions = [a for a in plan.actions if a.name == "get_weather_forecast"]
        self.assertEqual(len(forecast_actions), 0)

    def test_harvest_future_date(self):
        """Test harvest decision for future date."""
        understanding = self.create_understanding(
            "harvest_decision",
            {"crop": {"value": "onion"}, "city": {"value": "Nashik"}, "date": {"value": "2026-08-27"}}
        )
        workflow = Mock()
        workflow.reflect.return_value = {"ready": True}
        working_memory = {}

        plan = self.planner.plan(understanding, workflow, working_memory)

        # Should have two actions: get_crop_info and get_weather_forecast
        self.assertEqual(len(plan.actions), 2)
        # Check get_crop_info action
        crop_action = next((a for a in plan.actions if a.name == "get_crop_info"), None)
        self.assertIsNotNone(crop_action)
        self.assertEqual(crop_action.arguments, {"crop": "onion"})
        # Check get_weather_forecast action
        forecast_action = next((a for a in plan.actions if a.name == "get_weather_forecast"), None)
        self.assertIsNotNone(forecast_action)
        # For date 2026-08-27 (tomorrow), days should be 2 (today + tomorrow)
        self.assertEqual(forecast_action.arguments, {"city": "Nashik", "days": 2})

    def test_exact_date_selection(self):
        """Test exact date selection (2026-08-27) returns correct forecast days."""
        understanding = self.create_understanding(
            "weather_forecast",
            {"city": {"value": "Nashik"}, "date": {"value": "2026-08-27"}}
        )
        workflow = Mock()
        workflow.reflect.return_value = {"ready": True}
        working_memory = {}

        plan = self.planner.plan(understanding, workflow, working_memory)

        self.assertEqual(len(plan.actions), 1)
        action = plan.actions[0]
        self.assertEqual(action.name, "get_weather_forecast")
        # For date 2026-08-27 (tomorrow), days should be 2
        self.assertEqual(action.arguments["days"], 2)
        # The planner does not select forecast records; it only determines the number of days.
        # The actual selection of the forecast record for 2026-08-27 would be done by the tool or workflow.
        # This test verifies the planner requests the correct date range.

    def test_tool_argument_purity(self):
        """Verify that Planner actions contain only tool input parameters."""
        test_cases = [
            # (intent, entities, expected_action_name, expected_arguments_keys)
            (
                "weather_current",
                {"city": {"value": "Nashik"}},
                "get_weather",
                ["city"]
            ),
            (
                "weather_forecast",
                {"city": {"value": "Nashik"}, "quantity": {"value": 3}},
                "get_weather_forecast",
                ["city", "days"]
            ),
            (
                "harvest_decision",
                {"crop": {"value": "onion"}, "city": {"value": "Nashik"}},
                "get_crop_info",
                ["crop"]
            ),
            (
                "harvest_decision",
                {"crop": {"value": "onion"}, "city": {"value": "Nashik"}, "date": {"value": "tomorrow"}},
                "get_weather_forecast",
                ["city", "days"]
            ),
        ]

        for intent, entities, expected_action, expected_keys in test_cases:
            with self.subTest(intent=intent):
                understanding = self.create_understanding(intent, entities)
                workflow = Mock()
                workflow.reflect.return_value = {"ready": True}
                working_memory = {}

                plan = self.planner.plan(understanding, workflow, working_memory)

                # Find the action we're testing
                action = next((a for a in plan.actions if a.name == expected_action), None)
                self.assertIsNotNone(action, f"Expected action {expected_action} not found in plan")

                # Check that arguments contain only expected keys
                actual_keys = list(action.arguments.keys())
                self.assertEqual(
                    sorted(actual_keys),
                    sorted(expected_keys),
                    f"Action {expected_action} has unexpected arguments. Expected: {expected_keys}, Got: {actual_keys}"
                )

                # Ensure no argument contains a key named "forecast"
                self.assertNotIn(
                    "forecast",
                    actual_keys,
                    f"Action {expected_action} should not have a 'forecast' key in arguments"
                )

                # Ensure no argument contains a list of weather forecast records
                # We'll check that none of the argument values are lists (since forecast records would be lists)
                for key, value in action.arguments.items():
                    self.assertNotIsInstance(
                        value,
                        list,
                        f"Action {expected_action} argument '{key}' should not be a list (forecast records)"
                    )


if __name__ == "__main__":
    unittest.main()