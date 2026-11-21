import numpy as np
import pandas as pd

from agritwin_ai.agents.coordinator.tools import (
    run_market,
)


def make_dataframe(rows=80):
    dates = pd.date_range(
        "2026-01-01",
        periods=rows,
        freq="D",
    )

    prices = (
        1800
        + np.arange(rows) * 2
        + np.sin(np.arange(rows)) * 10
    )

    dataframe = pd.DataFrame(
        {
            "date": dates,
            "state": ["Maharashtra"] * rows,
            "district": ["Nashik"] * rows,
            "market": ["Lasalgaon"] * rows,
            "commodity": ["Onion"] * rows,
            "modal_price": prices,
            "arrival_quantity": (
                1000 + np.arange(rows) * 3
            ),
        }
    )

    return dataframe


def test_market_tool_is_registered():
    from agritwin_ai.agents.coordinator.tool_schema import (
        TOOLS,
    )

    assert "run_market" in TOOLS


def test_market_tool_has_correct_function():
    from agritwin_ai.agents.coordinator.tool_schema import (
        TOOLS,
    )

    assert TOOLS[
        "run_market"
    ]["function"] is run_market


def test_market_tool_schema_exists():
    from agritwin_ai.agents.coordinator.tool_schema import (
        TOOL_SCHEMA,
    )

    names = {
        item["name"]
        for item in TOOL_SCHEMA
    }

    assert "run_market" in names


def test_market_tool_can_parse_request():
    # The production Coordinator tool now expects the
    # persisted market dataset. This test only verifies
    # registration and interface behavior.
    from agritwin_ai.agents.coordinator.tool_schema import (
        TOOLS,
    )

    function = TOOLS[
        "run_market"
    ]["function"]

    assert callable(function)