from agritwin_ai.orchestration.response_merger import ResponseMerger


class AgentOrchestrator:

    def __init__(self):

        self.merger = ResponseMerger()

    def execute(

        self,

        plan,

        agent,

        user_message

    ):

        """
        Phase 1

        Only one agent.

        Later this becomes parallel execution.
        """

        response = agent.run(
            user_message
        )

        return self.merger.merge(

            [

                response

            ]

        )