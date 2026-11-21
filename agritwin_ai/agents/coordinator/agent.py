from agritwin_ai.runtime.engine import AgentEngine
from agritwin_ai.agents.coordinator.prompts import build_coordinator_prompt
from agritwin_ai.agents.coordinator.workflow import CoordinatorWorkflow
from agritwin_ai.agents.coordinator.evaluator import CoordinatorEvaluator
from agritwin_ai.agents.coordinator.tool_schema import TOOLS


def create_engine(tools_override=None):
    """Create a coordinator with either default or session-isolated tools."""
    selected_tools = tools_override if tools_override is not None else TOOLS
    return AgentEngine(
        prompt=build_coordinator_prompt(selected_tools),
        workflow_factory=CoordinatorWorkflow,
        evaluator=CoordinatorEvaluator(),
        tools=selected_tools,
        decision_label="Coordinator",
    )


engine = create_engine()


def run_agent(user_message: str):
    return engine.run(user_message)
