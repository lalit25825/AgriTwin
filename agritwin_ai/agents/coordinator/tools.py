from agritwin_ai.agents.harvest.agent import (
    run_agent as run_harvest,
)

from agritwin_ai.agents.climate.agent import (
    run_agent as run_climate,
)

from agritwin_ai.agents.market.market_runtime import (
    MarketRuntime,
)

from agritwin_ai.agents.market.request_parser import (
    MarketRequestParser,
)

from agritwin_ai.agents.logistics.tools import (
    get_logistics_analysis,
)

import re


_market_runtime = MarketRuntime()

_market_parser = MarketRequestParser()


def run_market(
    user_message: str,
):
    """
    Coordinator-facing Market Agent tool.

    Converts a natural-language market request into a structured
    request and executes the Market Runtime.
    """

    request = _market_parser.parse(user_message)
    markets = request.markets or (request.market,)
    lowered = user_message.lower()
    current_price_only = any(
        phrase in lowered
        for phrase in (
            "current price", "current market price", "today's price", "todays price",
            "price today", "market rate now", "just the price",
            "only the price", "don't calculate my profit",
            "dont calculate my profit",
        )
    ) or bool(re.search(r"\bcurrent\b.{0,40}\b(price|rate)\b", lowered))

    if current_price_only:
        results = [
            _market_runtime.get_current_price(request.commodity, market)
            for market in markets
        ]
        return results[0] if len(results) == 1 else {
            "agent": "market",
            "intent": "current_price_comparison",
            "commodity": request.commodity,
            "results": results,
        }

    analysis_runner = getattr(_market_runtime, "get_market_analysis", None)
    if callable(analysis_runner):
        results = [
            analysis_runner(
                commodity=request.commodity,
                market=market,
                horizon=request.horizon,
            )
            for market in markets
        ]
    else:
        # Backward-compatible test/runtime adapter.
        results = [
            _market_runtime.run(
                commodity=request.commodity,
                market=market,
                horizon=request.horizon,
            )
            for market in markets
        ]
    return results[0] if len(results) == 1 else {
        "agent": "market",
        "intent": "price_forecast_comparison",
        "commodity": request.commodity,
        "horizon_days": request.horizon,
        "results": results,
    }


def run_logistics(
    user_message: str,
):
    """
    Coordinator-facing Logistics Agent tool.

    The Logistics Agent is responsible for extracting the required
    logistics information and executing the logistics analysis.

    The original user message is passed through so that the
    Logistics layer can preserve the complete request.
    """

    # ------------------------------------------------------------
    # Temporary deterministic extraction
    #
    # The main Logistics Planner already handles structured
    # logistics requests. This coordinator wrapper currently
    # provides the integration point for the Logistics Agent.
    # ------------------------------------------------------------

    from agritwin_ai.agents.logistics.agent import (
        run_agent as run_logistics_agent,
    )

    return run_logistics_agent(
        user_message
    )


__all__ = [
    "run_harvest",
    "run_climate",
    "run_market",
    "run_logistics",
]