import json
import re

from agritwin_ai.understanding.schema import UnderstandingResult


def parse_understanding_response(response: str) -> UnderstandingResult:
    """
    Parses the LLM response from the Understanding Layer.

    Expected JSON:

    {
        "intent": "...",
        "entities": {},
        "missing": [],
        "updates": {},
        "confidence": 0.95
    }
    """

    # -------------------------
    # Remove markdown if present
    # -------------------------

    cleaned = re.sub(
        r"```json|```",
        "",
        response
    ).strip()

    # -------------------------
    # Extract first JSON object
    # -------------------------

    match = re.search(
        r"\{.*\}",
        cleaned,
        re.DOTALL
    )

    if not match:

        raise ValueError(
            "No JSON object found in LLM response."
        )

    data = json.loads(match.group())

    # -------------------------
    # Convert to dataclass
    # -------------------------

    return UnderstandingResult(

        intent=data.get(
            "intent",
            "unknown"
        ),

        entities=data.get(
            "entities",
            {}
        ),

        missing=data.get(
            "missing",
            []
        ),

        updates=data.get(
            "updates",
            {}
        ),

        confidence=float(
            data.get(
                "confidence",
                0.0
            )
        )
    )