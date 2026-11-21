from agritwin_ai.routing.registry import AGENT_REGISTRY


class AgentRouter:

    def route(self, understanding):

        return AGENT_REGISTRY.get(

            understanding.intent,

            "harvest"

        )