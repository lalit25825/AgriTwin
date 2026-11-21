from agritwin_ai.runtime.engine import AgentEngine

from agritwin_ai.agents.market.prompts import (
    MARKET_AGENT_PROMPT,
)

from agritwin_ai.agents.market.workflow import (
    MarketWorkflow,
)

from agritwin_ai.agents.market.evaluator import (
    MarketEvaluator,
)

from agritwin_ai.agents.market.tool_schema import (
    TOOLS,
)



def create_engine(tools_override=None):
    """Create an isolated market engine (used by the web session manager)."""
    selected_tools = tools_override if tools_override is not None else TOOLS
    return AgentEngine(
        prompt=MARKET_AGENT_PROMPT,
        workflow_factory=MarketWorkflow,
        evaluator=MarketEvaluator(),
        tools=selected_tools,
        decision_label='deterministic market decision',
    )


engine = create_engine()


def run_agent(user_message: str):
    return engine.run(user_message)
