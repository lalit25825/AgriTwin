"""Build immutable system context from deterministic decisions."""

from typing import Any, Mapping, Optional


class DecisionContextBuilder:
    """Serialize a Python decision engine result for the explanation LLM."""

    def build(self, decision: Optional[Mapping[str, Any]]) -> Optional[dict[str, str]]:

        if decision is None:
            return None

        lines = []

        lines.append("IMMUTABLE DETERMINISTIC DECISION")
        lines.append("The Python Decision Engine is authoritative.")
        lines.append("Explain this result faithfully. Do not alter, override, or make a new agricultural recommendation.")

        for key, value in decision.items():

            lines.append(f"{key}: {value}")

        return {

            "role": "system",

            "content": "\n".join(lines)

        }
