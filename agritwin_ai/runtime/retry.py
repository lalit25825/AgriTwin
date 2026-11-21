"""
Retry logic for the Agent Engine.

Retry only when the parser could not understand
the LLM response.
"""


def should_retry(parsed_response: dict) -> bool:
    """
    Returns True only if the parser marked the
    response as invalid.

    Valid parser types:

    - tool
    - final
    - invalid
    """

    return parsed_response["type"] == "invalid"