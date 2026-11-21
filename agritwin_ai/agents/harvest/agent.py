from agritwin_ai.runtime.engine import AgentEngine

from agritwin_ai.agents.harvest.prompts import (
    HARVEST_AGENT_PROMPT,
)

from agritwin_ai.agents.harvest.workflow import (
    HarvestWorkflow,
)

from agritwin_ai.agents.harvest.evaluator import (
    HarvestEvaluator,
)

from agritwin_ai.agents.harvest.tool_schema import (
    TOOLS,
)



def create_engine(tools_override=None):
    """Create an isolated harvest engine (used by the web session manager)."""
    selected_tools = tools_override if tools_override is not None else TOOLS
    return AgentEngine(
        prompt=HARVEST_AGENT_PROMPT,
        workflow_factory=HarvestWorkflow,
        evaluator=HarvestEvaluator(),
        tools=selected_tools,
        decision_label='Deterministic harvest decision',
    )


engine = create_engine()


def run_agent(user_message: str):
    return engine.run(user_message)
