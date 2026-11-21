
import json
import re


def parse_response(response):

    try:

        cleaned = re.sub(
            r"```json|```",
            "",
            response
        ).strip()

        match = re.search(
            r"\{.*\}",
            cleaned,
            re.DOTALL
        )

        if not match:
            raise ValueError("No JSON found.")

        data = json.loads(match.group())

        if (
            isinstance(data, dict)
            and "action" in data
            and "arguments" in data
        ):

            return {
                "type": "tool",
                "data": data
            }

        if (
            isinstance(data, dict)
            and "final_answer" in data
        ):

            return {
                "type": "final",
                "data": data["final_answer"]
            }

    except Exception:

        pass

    return {
        "type": "invalid",
        "data": response
    }