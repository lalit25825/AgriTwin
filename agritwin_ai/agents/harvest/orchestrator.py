from agritwin_ai.agents.harvest.extractor import extract_city
from agritwin_ai.agents.harvest.extractor import extract_crop

from agritwin_ai.tools.weather.weather import get_weather
from agritwin_ai.agents.harvest.knowledge import get_crop_info
from agritwin_ai.decision.harvest import evaluate_harvest


def solve(question):

    city = extract_city(question)
    crop = extract_crop(question)

    if city is None:

        return {
            "error": "City not found."
        }

    if crop is None:

        return {
            "error": "Crop not found."
        }

    weather = get_weather(city)

    if "error" in weather:

        return weather

    crop_info = get_crop_info(crop)

    if "error" in crop_info:

        return crop_info

    decision = evaluate_harvest(
        weather,
        crop_info
    )

    return {

        "city": city,

        "crop": crop,

        "weather": weather,

        "crop_info": crop_info,

        "decision": decision

    }
