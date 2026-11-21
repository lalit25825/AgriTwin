from __future__ import annotations


class MarketReflection:
    """
    Determines whether a Market workflow has the information
    required for the requested operation.
    """

    def check(self, workflow, intent: str) -> dict:
        missing = workflow.needs_information(intent)

        return {
            "ready": len(missing) == 0,
            "missing": missing,
        }