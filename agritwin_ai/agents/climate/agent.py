from agritwin_ai.runtime.engine import AgentEngine
from agritwin_ai.agents.climate.prompts import CLIMATE_AGENT_PROMPT
from agritwin_ai.agents.climate.evaluator import ClimateEvaluator
from agritwin_ai.agents.climate.tool_schema import TOOLS
from agritwin_ai.agents.climate.workflow import ClimateWorkflow



def create_engine(tools_override=None):
    """Create an isolated climate engine (used by the web session manager)."""
    selected_tools = tools_override if tools_override is not None else TOOLS
    return AgentEngine(
        prompt=CLIMATE_AGENT_PROMPT,
        workflow_factory=ClimateWorkflow,
        evaluator=ClimateEvaluator(),
        tools=selected_tools,
        decision_label='climate',
    )


engine = create_engine()


def run_agent(user_message: str):
    return engine.run(user_message)
