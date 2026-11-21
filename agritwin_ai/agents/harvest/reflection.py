"""Harvest workflow readiness reflection."""

from typing import Any


class HarvestReflection:
    """Identify the missing farmer inputs for a harvest workflow."""

    def check(self, workflow: Any, intent: str) -> dict[str, Any]:

        missing = workflow.needs_information(intent)

        if missing:

            return {
                "ready": False,
                "missing": missing
            }

        return {
            "ready": True,
                "missing": []
        }
