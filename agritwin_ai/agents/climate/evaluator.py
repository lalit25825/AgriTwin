from agritwin_ai.decision.climate import evaluate_climate


class ClimateEvaluator:

    def evaluate(self, workflow, intent):

        if workflow.state.current_weather is not None:

            return evaluate_climate(

                weather=workflow.state.current_weather

            )

        return evaluate_climate(

            forecast=workflow.state.forecast

        )
