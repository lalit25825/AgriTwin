class ClimateReflection:

    def check(self, workflow, intent):

        missing = workflow.needs_information(intent)

        return {

            "ready": len(missing) == 0,

            "missing": missing

        }