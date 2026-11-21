
import re


SUPPORTED_CROPS = [
    "onion",
    "wheat",
    "rice"
]


def extract_crop(question):

    question = question.lower()

    for crop in SUPPORTED_CROPS:

        if crop in question:

            return crop

    return None


def extract_city(question):

    question = question.lower()

    match = re.search(
        r"in\s+([a-zA-Z ]+)",
        question
    )

    if match:

        city = match.group(1).strip()

        city = city.replace("today", "").strip()

        return city.title()

    return None