from agritwin_ai.runtime.engine import AgentEngine
from agritwin_ai.agents.logistics.prompts import LOGISTICS_AGENT_PROMPT
from agritwin_ai.agents.logistics.workflow import LogisticsWorkflow
from agritwin_ai.agents.logistics.evaluator import LogisticsEvaluator
from agritwin_ai.agents.logistics.tool_schema import TOOLS



def create_engine(tools_override=None):
    """Create an isolated logistics engine (used by the web session manager)."""
    selected_tools = tools_override if tools_override is not None else TOOLS
    return AgentEngine(
        prompt=LOGISTICS_AGENT_PROMPT,
        workflow_factory=LogisticsWorkflow,
        evaluator=LogisticsEvaluator(),
        tools=selected_tools,
        decision_label='Logistics',
    )


engine = create_engine()


def run_agent(user_message: str):
    return engine.run(user_message)
