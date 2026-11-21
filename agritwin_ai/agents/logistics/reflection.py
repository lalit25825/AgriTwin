from __future__ import annotations


class LogisticsReflection:
    def check(self, workflow, intent: str) -> dict:
        missing = workflow.needs_information(intent)
        return {"ready": not missing, "missing": missing}
