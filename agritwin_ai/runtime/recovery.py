import json


def recovery_observation(message):

    return json.dumps({
        "error": message
    })


def retry_prompt(message):

    return (
        f"{message}\n"
        "Respond again using valid JSON only."
    )